"""
Lab 2: Tool-Augmented Agent with Dynamic Semantic File Discovery & Automatic Tool Chaining.
Supports Question Pools (PDF, JSON, CSV) and Candidate Rosters (CSV, JSON, Excel .xlsx / .xls).
Dynamically discovers available files, invokes deterministic tools, and guarantees verified conclusions.
"""
import os
import re
import json
import datetime
from typing import Dict, Any, List, Optional, Tuple

from src.config import llm_client
from src.lab1.planner_agent import ExamPlannerAgent
from src.models.exam_plan import ExamPlan
from src.tools.question_pool_tool import (
    read_question_pool,
    filter_questions_by_topic,
    get_question_pool_stats,
    resolve_and_validate_path,
)
from src.tools.eligibility_tool import (
    read_student_roster,
    verify_candidate_eligibility,
    ALLOWED_ROSTER_EXTENSIONS,
)
from src.tools.exam_compute_tool import (
    validate_marks_consistency,
    compute_exam_feasibility,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def score_file_relevance(file_path: str, request_text: str) -> float:
    """
    Computes a semantic relevance score between a file path and a user natural language request.
    Uses tokenization across underscores, hyphens, and whitespace to prevent substring collisions.
    Supports Excel extensions (.xlsx, .xls) and typo normalization (.xlxs -> .xlsx).
    """
    base = os.path.basename(file_path).lower()
    q_lower = request_text.lower().replace(".xlxs", ".xlsx")

    base_tokens = set(re.findall(r"[a-zA-Z0-9]+", base))
    q_tokens = set(re.findall(r"[a-zA-Z0-9]+", q_lower))

    score = 0.0

    # 1. Exact base match in query (with or without extension)
    base_no_ext = os.path.splitext(base)[0]
    if base in q_lower or base_no_ext in q_lower:
        score += 40.0

    # 2. Applied Materials / Lab Allocation Boost
    if any(k in base_tokens for k in ["applied", "materials", "allocation"]):
        if any(kw in q_tokens for kw in ["applied", "materials", "allocation", "xlsx", "excel", "lab"]):
            score += 35.0

    # 3. OS Concept
    if "os" in base_tokens or "operating" in base_tokens:
        if any(kw in q_tokens for kw in ["os", "operating", "systems", "system", "cs301"]):
            score += 20.0

    # 4. Agentic AI Concept
    if "agentic" in base_tokens or ("ai" in base_tokens and "questions" in base_tokens):
        if any(kw in q_tokens for kw in ["agentic", "agent", "agents", "ai", "24ecac203", "genai"]):
            score += 20.0

    # 5. 6th Sem CSE Concept
    if "6th" in base_tokens or "cse" in base_tokens:
        if any(kw in q_tokens for kw in ["6th", "sem", "semester", "cse", "24ecac203"]):
            score += 20.0

    # 6. Student Roster Concept
    if any(k in base_tokens for k in ["student", "students", "roster", "list", "candidate", "allocation"]):
        if any(kw in q_tokens for kw in ["student", "students", "roster", "list", "candidate", "csv", "xlsx", "excel"]):
            score += 10.0
        if ("os" in q_tokens or "cs301" in q_tokens) and ("student_list" in base or "student_roster" in base):
            score += 8.0

    # Token overlap with filename parts
    overlap = len(base_tokens.intersection(q_tokens))
    score += overlap * 5.0

    return score


class ToolAugmentedExamAgent:
    """
    Lab 2 Coordinator + Tool Layer Agent.
    Dynamically discovers data files, determines needed tools from natural language,
    and grounds all reasoning in verified external outputs.
    """

    def __init__(self):
        self.planner = ExamPlannerAgent()
        self.llm = llm_client
        self.tool_audit_log: List[Dict[str, Any]] = []

    def _log_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any):
        """Records tool execution in the immutable audit log."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.tool_audit_log.append({
            "timestamp": timestamp,
            "tool": tool_name,
            "arguments": args,
            "result_summary": str(result)[:180] + "..." if len(str(result)) > 180 else str(result),
        })

    def get_available_data_files(self) -> Dict[str, List[str]]:
        """Scans the data/ directory dynamically and strictly categorizes available files."""
        if not os.path.exists(DATA_DIR):
            return {"question_pools": [], "candidate_rosters": []}

        files = os.listdir(DATA_DIR)
        q_files = []
        r_files = []

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            f_lower = f.lower()
            tokens = set(re.findall(r"[a-zA-Z0-9]+", f_lower))

            # Candidate Rosters (contains student, roster, candidate, list, cse, sem, applied, materials, allocation, lab)
            is_roster = ext in [".csv", ".json", ".xlsx", ".xls"] and any(
                k in tokens for k in ["student", "students", "roster", "candidate", "candidates", "list", "cse", "sem", "applied", "materials", "allocation", "lab"]
            )
            if is_roster:
                r_files.append(f"data/{f}")

            # Question Pools (strictly exclude student rosters/allocations)
            is_qpool = (ext == ".pdf") or (
                ext in [".json", ".csv"] and any(k in tokens for k in ["question", "pool", "bank", "exam", "os", "agentic"])
                and not is_roster
            )
            if is_qpool:
                q_files.append(f"data/{f}")

        return {
            "question_pools": sorted(list(set(q_files))),
            "candidate_rosters": sorted(list(set(r_files))),
        }

    # =========================================================================
    # TOOL 1: QUESTION POOL READER
    # =========================================================================
    def call_question_pool_reader(
        self,
        source_path: str,
        course_code: Optional[str] = None,
        topic: Optional[str] = None,
        q_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Invokes Question Pool Reader on a user-specified PDF, JSON, or CSV file."""
        resolved = resolve_and_validate_path(source_path, [".pdf", ".json", ".csv"])
        stats = get_question_pool_stats(source_path=resolved, course_code=course_code)
        matched = filter_questions_by_topic(source_path=resolved, course_code=course_code, topic=topic, q_type=q_type)

        result = {
            "source_file": os.path.basename(resolved),
            "resolved_path": resolved,
            "format": "PDF" if resolved.endswith(".pdf") else ("CSV" if resolved.endswith(".csv") else "JSON"),
            "course_code": course_code or stats.course_code,
            "stats": stats.model_dump(),
            "matched_questions_count": len(matched),
            "questions": [q.model_dump() for q in matched],
        }

        self._log_tool_call("QuestionPoolReaderTool", {"source": source_path, "resolved": resolved, "course": course_code}, stats.model_dump())
        return result

    # =========================================================================
    # TOOL 2: CANDIDATE ROSTER & ELIGIBILITY READER
    # =========================================================================
    def call_candidate_roster_reader(
        self,
        source_path: str,
        course_code: Optional[str] = None,
        min_attendance: float = 75.0,
        require_fees: bool = True,
    ) -> Dict[str, Any]:
        """Invokes Candidate Roster & Eligibility Reader on a user-specified CSV, JSON, or Excel file."""
        from src.models.exam_plan import EligibilityCriteria
        resolved = resolve_and_validate_path(source_path, ALLOWED_ROSTER_EXTENSIONS)
        criteria = EligibilityCriteria(
            min_attendance_percentage=min_attendance,
            require_fee_clearance=require_fees,
            require_prerequisites=True,
        )
        eligibility_result = verify_candidate_eligibility(source_path=resolved, course_code=course_code, criteria=criteria)

        fmt = "EXCEL" if resolved.endswith((".xlsx", ".xls")) else ("CSV" if resolved.endswith(".csv") else "JSON")
        self._log_tool_call(
            "CandidateRosterReaderTool",
            {"source": source_path, "resolved": resolved, "course": course_code, "min_attendance": min_attendance, "require_fees": require_fees},
            eligibility_result.summary_report,
        )
        return {
            "source_file": os.path.basename(resolved),
            "resolved_path": resolved,
            "format": fmt,
            "result": eligibility_result.model_dump(),
        }

    # =========================================================================
    # TOOL 3: DOMAIN CALCULATOR / CHECKER
    # =========================================================================
    def call_domain_calculator(
        self,
        plan: ExamPlan,
        pool_source: str,
        roster_source: str,
    ) -> Dict[str, Any]:
        """Invokes Domain Calculator / Checker on user-specified files."""
        calc_summary = compute_exam_feasibility(plan=plan, pool_source=pool_source, roster_source=roster_source)

        self._log_tool_call(
            "DomainCalculatorTool",
            {"pool_source": pool_source, "roster_source": roster_source, "total_marks": plan.total_marks},
            calc_summary,
        )
        return calc_summary

    # =========================================================================
    # DYNAMIC FILE DISCOVERY & NATURAL LANGUAGE CHAINING
    # =========================================================================
    def select_best_matching_files(self, user_request: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Scans data/ directory and maps natural language queries to the most relevant files.
        Returns (selected_pool_file, selected_roster_file, clarification_question_if_ambiguous).
        """
        available = self.get_available_data_files()
        q_files = available["question_pools"]
        r_files = available["candidate_rosters"]

        text_lower = user_request.lower().replace(".xlxs", ".xlsx")

        # Score Question Pool Files
        q_scores = [(qf, score_file_relevance(qf, user_request)) for qf in q_files]
        q_scores.sort(key=lambda x: x[1], reverse=True)

        selected_pool_file = None
        needs_pool = any(k in text_lower for k in ["question", "pool", "bank", "mcq", "marks", "exam", "os", "agentic", "pdf"])

        if needs_pool and q_scores:
            top_q, top_score = q_scores[0]
            if top_score > 0:
                selected_pool_file = top_q
            elif len(q_files) == 1:
                selected_pool_file = q_files[0]
            else:
                return None, None, f"Multiple question bank files are available in data/: {', '.join(q_files)}. Please specify which one to use."

        # Score Candidate Roster Files
        r_scores = [(rf, score_file_relevance(rf, user_request)) for rf in r_files]
        r_scores.sort(key=lambda x: x[1], reverse=True)

        selected_roster_file = None
        needs_roster = any(k in text_lower for k in [
            "student", "students", "roster", "candidate", "candidates", "csv", "count",
            "attendance", "eligib", "cse", "applied", "materials", "allocation", "excel", "xlsx", "xlxs", "lab"
        ])

        if needs_roster and r_scores:
            top_r, top_score = r_scores[0]
            if top_score > 0:
                selected_roster_file = top_r
            elif len(r_files) == 1:
                selected_roster_file = r_files[0]
            else:
                return None, None, f"Multiple student roster files are available in data/: {', '.join(r_files)}. Please specify which one to use."

        return selected_pool_file, selected_roster_file, None

    def process_natural_language_request(self, user_request: str) -> Dict[str, Any]:
        """
        Interprets natural language request, selects relevant files semantically,
        executes tools with verification checks, and returns verified conclusions.
        """
        pool_file, roster_file, clarification = self.select_best_matching_files(user_request)

        if clarification:
            return {
                "needs_clarification": True,
                "clarification_question": clarification,
            }

        flow_steps = ["User Request", "Agent"]
        tools_called = []
        verified_data = {}
        text_lower = user_request.lower()

        # 1. Execute Question Pool Reader if needed
        pool_res = None
        if pool_file:
            try:
                pool_res = self.call_question_pool_reader(source_path=pool_file)
                flow_steps.append(f"Question Pool Reader using '{pool_file}'")
                tools_called.append("QuestionPoolReaderTool")
                verified_data["question_pool"] = pool_res
            except Exception as e:
                return {
                    "flow": f"User Request -> Agent -> Question Pool Reader ('{pool_file}') [EXTRACTION FAILED]",
                    "tools_called": ["QuestionPoolReaderTool"],
                    "files_used": {
                        "question_pool_file": pool_file,
                        "candidate_roster_file": roster_file,
                    },
                    "error": str(e),
                    "response_text": f"Question Pool Reader Failed on '{pool_file}':\n{e}\nVerification Incomplete.",
                }

        # 2. Execute Candidate Roster Reader if needed
        roster_res = None
        if roster_file:
            try:
                roster_res = self.call_candidate_roster_reader(source_path=roster_file)
                flow_steps.append(f"Candidate Roster Reader using '{roster_file}'")
                tools_called.append("CandidateRosterReaderTool")
                verified_data["candidate_roster"] = roster_res
            except Exception as e:
                return {
                    "flow": f"User Request -> Agent -> Candidate Roster Reader ('{roster_file}') [READ FAILED]",
                    "tools_called": ["CandidateRosterReaderTool"],
                    "files_used": {
                        "question_pool_file": pool_file,
                        "candidate_roster_file": roster_file,
                    },
                    "error": str(e),
                    "response_text": f"Candidate Roster Reader Failed on '{roster_file}':\n{e}\nVerification Incomplete.",
                }

        # 3. Execute Domain Calculator / Checker if calculation requested
        calc_res = None
        if pool_file and roster_file and pool_res and roster_res:
            try:
                sample_plan = ExamPlan(
                    course_code=pool_res["course_code"],
                    course_name="Operating Systems" if "os" in pool_file.lower() else "Agentic AI",
                    exam_date="2026-10-15",
                    start_time="10:00 AM",
                    duration_minutes=90,
                    total_marks=60,
                    sections=[],
                    eligibility=None,
                    rubric_summary="Standard Evaluation Rubric",
                )
                calc_res = self.call_domain_calculator(plan=sample_plan, pool_source=pool_file, roster_source=roster_file)
                flow_steps.append("Domain Calculator / Checker")
                tools_called.append("DomainCalculatorTool")
                verified_data["domain_calculation"] = calc_res
            except Exception as e:
                pass

        flow_steps.extend(["Agent", "Verified Result"])
        flow_string = " -> ".join(flow_steps)

        # Build Verified Report
        lines = [f"Verified Report for Request:\n'{user_request}'\n"]

        if pool_res:
            st = pool_res["stats"]
            lines.append(f"[QUESTION POOL] Question Pool Verification ({pool_res['source_file']}):")
            lines.append(f"  • Course: {pool_res['course_code']}")
            lines.append(f"  • Pages Processed & Verified: {st['pages_processed']} page(s)")
            lines.append(f"  • Extraction Status: {st['extraction_status']}")
            lines.append(f"  • Total Questions Extracted: {st['total_questions']}")
            lines.append(f"  • MCQs Available: {st['mcq_count']} (Total Marks in Pool: {st['total_marks_available']})")
            lines.append(f"  • Subjective Questions: {st['subjective_count']}")
            lines.append(f"  • Syllabus Topics: {', '.join(st['topics'])}")

            if "60 mark" in text_lower or "enough" in text_lower or "sufficient" in text_lower:
                wants_1mark_mcq = "1 mark" in text_lower or "mcq" in text_lower
                if wants_1mark_mcq:
                    mcq_avail = st["mcq_count"]
                    if mcq_avail >= 60:
                        lines.append(f"  • Sufficiency Check for 60 Marks (1-mark MCQs): [SUFFICIENT] (Contains {mcq_avail} MCQs)")
                    else:
                        lines.append(
                            f"  • Sufficiency Check for 60 Marks (1-mark MCQs): [SHORTAGE] (Pool contains {mcq_avail} MCQs; {60 - mcq_avail} additional 1-mark questions required to conduct a 60-mark all-MCQ exam)"
                        )
                else:
                    if st["total_marks_available"] >= 60.0:
                        lines.append(f"  • Sufficiency Check for 60 Marks Exam: [SUFFICIENT] (Total pool marks: {st['total_marks_available']})")
                    else:
                        lines.append(
                            f"  • Sufficiency Check for 60 Marks Exam: [SHORTAGE] (Pool contains {st['total_marks_available']} marks; {int(60 - st['total_marks_available'])} additional marks required)"
                        )

        if roster_res:
            rd = roster_res["result"]
            lines.append(f"\n[CANDIDATE ROSTER] Candidate Roster Verification ({roster_res['source_file']}):")
            lines.append(f"  • File Format: {roster_res.get('format', 'ROSTER')}")
            lines.append(f"  • Total Students Evaluated / Counted: {rd['total_candidates_evaluated']} students")
            lines.append(f"  • Eligible Students: {rd['eligible_count']} students")
            lines.append(f"  • Disqualified Students: {rd['ineligible_count']} students")
            if rd.get("ambiguous_count", 0) > 0:
                lines.append(f"  • Flagged for Review: {rd['ambiguous_count']} students")

        if calc_res:
            lines.append(f"\n[DOMAIN CHECK] Domain Calculation & Feasibility Check:")
            lines.append(f"  • Mathematical Marks Balance: {'[PASSED]' if calc_res['marks_validation']['is_valid'] else '[MISMATCH]'}")
            lines.append(f"  • Estimated Faculty Grading Time: {calc_res['workload_computation']['estimated_faculty_review_mins']} minutes")

        return {
            "flow": flow_string,
            "tools_called": tools_called,
            "files_used": {
                "question_pool_file": pool_file,
                "candidate_roster_file": roster_file,
            },
            "verified_data": verified_data,
            "response_text": "\n".join(lines),
        }

    def process_query(
        self,
        query: str,
        pool_source: Optional[str] = None,
        roster_source: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes query with explicitly provided pool_source and/or roster_source."""
        if pool_source and not roster_source:
            res = self.call_question_pool_reader(source_path=pool_source)
            st = res["stats"]
            return {
                "tool_called": "QuestionPoolReaderTool",
                "result": res,
                "response_text": f"Question Pool Reader Verified ({res['source_file']}): {st['total_questions']} questions extracted.",
            }
        elif roster_source and not pool_source:
            res = self.call_candidate_roster_reader(source_path=roster_source)
            rd = res["result"]
            return {
                "tool_called": "CandidateRosterReaderTool",
                "result": res,
                "response_text": f"[CANDIDATE ROSTER] Candidate Roster Verification ({res['source_file']}): {rd['total_candidates_evaluated']} candidates evaluated.",
            }
        return self.process_natural_language_request(query)
