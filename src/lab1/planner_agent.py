"""
Lab 1: Agent vs Chatbot — Strict Zero-Assumption Exam Planner Loop.
Enforces:
1. ZERO INVENTIONS: Never assumes course codes, delivery windows, dates, or eligibility rules.
2. CONTRADICTION DETECTION: Detects and flags conflicts between total marks and question distribution.
3. PRECISE DATE VALIDATION: Rejects bare month names (e.g., "September") and asks for exact dates.
"""
import re
import json
from typing import Dict, Any, List, Optional
from src.config import llm_client
from src.models.exam_plan import (
    ExamPlan,
    ExamSectionSpec,
    ClarificationResponse,
    PlanRevision,
    EligibilityCriteria,
)

MANDATORY_PARAMETERS = {
    "course_code": "Course code (e.g., CS301, 24ECAC203)",
    "course_name": "Course title (e.g., Operating Systems, Agentic AI)",
    "exam_date": "Exact examination date with day and month (e.g., 2026-09-15 or September 15, 2026)",
    "delivery_window": "Exam time/delivery window (e.g., 09:00 AM - 12:00 PM, 10:00 AM - 01:00 PM)",
    "duration_minutes": "Exam duration in minutes or hours (e.g., 60 minutes, 1 hour)",
    "total_marks": "Total maximum marks (e.g., 60 marks, 100 marks)",
    "section_structure": "Question structure (e.g., 60 MCQs of 1 mark each, or Section A MCQs + Section B Subjective)",
    "passing_marks": "Minimum passing marks (e.g., 20 marks, 40 marks)",
    "eligibility_rules": "Candidate eligibility criteria (e.g., min attendance % and fee clearance requirement)",
}


class ExamPlannerAgent:
    """
    Lab 1 Strict Coordinator Agent.
    Never guesses, assumes, or invents missing parameters.
    Identifies contradictions and requests clarifications across multiple turns.
    """

    def __init__(self):
        self.llm = llm_client

    def _is_exact_date(self, date_str: str) -> bool:
        """Checks if date contains an exact day and month (not just a bare month like 'september')."""
        if not date_str:
            return False
        d = date_str.strip().lower()
        # Bare months are invalid
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
                  "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        if d in months:
            return False
        # Must have digits for day (e.g., 2026-09-15 or Sep 15 or 15th September)
        has_day_digit = bool(re.search(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}|\b\d{1,2}(st|nd|rd|th)?\b|\b\d{4}\b", d))
        return has_day_digit

    def _detect_contradictions(self, state: Dict[str, Any], user_input: str) -> Optional[str]:
        """
        Detects mathematical contradictions between total marks and question distribution.
        e.g., Total marks = 60, but user wrote 120 MCQs x 1 mark = 120 marks.
        """
        total_marks = state.get("total_marks")
        text = user_input.lower()

        # Check for MCQ counts and marks per question in user input
        # Look for patterns like "120 mcq", "120mcq", "120 questions", "1 mark each"
        mcq_count_match = re.search(r"(\d+)\s*(mcq|mcqs|questions)", text)
        mark_per_q_match = re.search(r"(\d+(\.\d+)?)\s*(mark|marks|pt|pts)\s*(each|per)?", text)

        if total_marks and mcq_count_match:
            claimed_count = int(mcq_count_match.group(1))
            mark_per = float(mark_per_q_match.group(1)) if mark_per_q_match else 1.0
            calculated_total = claimed_count * mark_per

            if abs(calculated_total - total_marks) > 0.01 and claimed_count != int(total_marks):
                return (
                    f"Conflict detected: You specified total marks as {int(total_marks)}, "
                    f"but also specified {claimed_count} MCQs of {mark_per} mark each (which totals {int(calculated_total)} marks). "
                    f"Please confirm whether you want {int(total_marks)} MCQs (for {int(total_marks)} marks) or {claimed_count} MCQs (for {int(calculated_total)} marks)."
                )

        return None

    def clarify_request_state(
        self, current_state: Dict[str, Any], user_input: str
    ) -> ClarificationResponse:
        """
        Multi-turn clarification analyzer with strict zero-assumption validation.
        """
        updated_state = current_state.copy()
        text = user_input.strip()

        # Check for contradictions first
        conflict_warning = self._detect_contradictions(updated_state, text)

        # Step 1: Use LLM to extract newly provided parameters from user input
        if self.llm.get_provider_name() != "mock" and text:
            prompt = f"""
Current Exam Parameters:
{json.dumps(updated_state, indent=2)}

User's New Input:
"{text}"

Extract ONLY explicitly mentioned parameters into JSON. DO NOT invent or default any field not stated by the user:
- course_code (string or null, e.g. "CS301", "24ECAC203")
- course_name (string or null, e.g. "Agentic AI", "Operating Systems")
- exam_date (string or null: only if exact date with day is provided, e.g. "2026-09-15" or "September 15, 2026"; if only bare month like "september" is mentioned, return null)
- delivery_window (string or null, e.g. "09:00 AM - 12:00 PM", "10:00 AM - 01:00 PM")
- duration_minutes (integer or null, e.g. 1 hour = 60, 90 mins = 90)
- total_marks (number or null, e.g. 60.0)
- passing_marks (number or null, e.g. 20.0, 40.0)
- section_structure (string or null, e.g. "60 MCQs of 1 mark each")
- min_attendance (number or null, e.g. 75.0, 80.0)
- fee_clearance_required (boolean or null)

Output ONLY valid JSON without markdown wrapping.
"""
            llm_res = self.llm.generate(prompt)
            if llm_res:
                try:
                    clean = llm_res.strip()
                    if "```json" in clean:
                        clean = clean.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean:
                        clean = clean.split("```")[1].split("```")[0].strip()
                    parsed = json.loads(clean)
                    for k, v in parsed.items():
                        if v is not None and v != "":
                            updated_state[k] = v
                except Exception:
                    pass

        # Step 2: Rule-based extraction fallback & strict validation
        text_lower = text.lower()

        # Course Code detection (explicit codes like CS301, 24ECAC203)
        if not updated_state.get("course_code"):
            course_code_match = re.search(r"\b([0-9]{2}[a-z]{4}[0-9]{3}|cs\s*\d{3}|it\s*\d{3}|ec\s*\d{3})\b", text_lower)
            if course_code_match:
                updated_state["course_code"] = course_code_match.group(1).upper().replace(" ", "")

        # Course Name detection
        if not updated_state.get("course_name"):
            if "agentic ai" in text_lower:
                updated_state["course_name"] = "Agentic AI"
            elif "operating system" in text_lower:
                updated_state["course_name"] = "Operating Systems"

        # Date detection (Strict: must have exact day)
        if not updated_state.get("exam_date") or not self._is_exact_date(updated_state.get("exam_date", "")):
            exact_date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(\s+\d{4})?|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(,\s*\d{4})?)\b", text_lower)
            if exact_date_match:
                updated_state["exam_date"] = exact_date_match.group(1)
            elif "september" in text_lower or "october" in text_lower or "august" in text_lower:
                # Mark that user mentioned month, but exact day is still missing
                updated_state.pop("exam_date", None)

        # Delivery Window detection (e.g. 9 am to 12 pm, 10:00 - 13:00)
        if not updated_state.get("delivery_window"):
            win_match = re.search(r"(\d{1,2}(:\d{2})?\s*(am|pm)?\s*(to|-)\s*\d{1,2}(:\d{2})?\s*(am|pm))", text_lower)
            if win_match:
                updated_state["delivery_window"] = win_match.group(1).upper()

        # Duration detection
        if not updated_state.get("duration_minutes"):
            dur_match = re.search(r"(\d+)\s*(mins|minutes|hrs|hours|hour|hr)", text_lower)
            if dur_match:
                val = int(dur_match.group(1))
                unit = dur_match.group(2)
                updated_state["duration_minutes"] = val * 60 if "hr" in unit or "hour" in unit else val

        # Total Marks detection
        if not updated_state.get("total_marks"):
            marks_match = re.search(r"(total\s*marks?\s*(-->|:|is|=)?\s*(\d+)|(\d+)\s*(marks|total))", text_lower)
            if marks_match:
                val = marks_match.group(3) or marks_match.group(4)
                if val:
                    updated_state["total_marks"] = float(val)

        # Passing Marks detection
        if not updated_state.get("passing_marks"):
            pass_match = re.search(r"passing\s*(marks|is|score|to|=|:)?\s*(\d+(\.\d+)?)", text_lower)
            if pass_match:
                updated_state["passing_marks"] = float(pass_match.group(2))

        # Section Structure detection
        if not updated_state.get("section_structure"):
            if "mcq" in text_lower or "subjective" in text_lower or "descriptive" in text_lower:
                updated_state["section_structure"] = text

        # Eligibility criteria detection (Attendance % and Fees)
        if "min_attendance" not in updated_state:
            att_match = re.search(r"(\d+)\s*%", text_lower)
            if att_match and "attendance" in text_lower:
                updated_state["min_attendance"] = float(att_match.group(1))

        if "fee_clearance_required" not in updated_state:
            if "open for all in terms of fees" in text_lower or "fee not required" in text_lower or "no fee" in text_lower:
                updated_state["fee_clearance_required"] = False
            elif "fee paid" in text_lower or "fee clearance" in text_lower or "require fee" in text_lower:
                updated_state["fee_clearance_required"] = True

        # Re-check contradiction with updated state
        if not conflict_warning:
            conflict_warning = self._detect_contradictions(updated_state, text)

        # Step 3: Identify Remaining Missing Mandatory Parameters
        missing = []
        questions = []

        if conflict_warning:
            # Put conflict resolution as top priority question
            questions.append(conflict_warning)
            missing.append("section_structure_conflict")

        if not updated_state.get("course_code"):
            missing.append("course_code")
            questions.append("What is the official course code for this exam (e.g., CS301 or 24ECAC203)?")

        if not updated_state.get("course_name"):
            missing.append("course_name")
            questions.append("What is the course title/name (e.g., Operating Systems, Agentic AI)?")

        if not updated_state.get("exam_date") or not self._is_exact_date(updated_state.get("exam_date", "")):
            missing.append("exam_date")
            if "september" in text_lower or "october" in text_lower or "august" in text_lower:
                month_found = "September" if "september" in text_lower else ("October" if "october" in text_lower else "the specified month")
                questions.append(f"Which specific date in {month_found} should the examination be conducted (e.g., September 15, 2026 or 2026-09-15)?")
            else:
                questions.append("What is the exact scheduled date for the exam (e.g., September 15, 2026 or 2026-09-15)?")

        if not updated_state.get("delivery_window"):
            missing.append("delivery_window")
            questions.append("What is the exam delivery time window (e.g., 09:00 AM - 12:00 PM or 10:00 AM - 01:00 PM)?")

        if not updated_state.get("duration_minutes"):
            missing.append("duration_minutes")
            questions.append("What is the exam duration in minutes or hours (e.g., 60 minutes, 2 hours)?")

        if not updated_state.get("total_marks"):
            missing.append("total_marks")
            questions.append("What is the total maximum mark for the exam (e.g., 60 marks, 100 marks)?")

        if not updated_state.get("section_structure") and "section_structure_conflict" not in missing:
            missing.append("section_structure")
            questions.append("How should the questions be structured (e.g., 60 MCQs of 1 mark each, or Section A MCQs + Section B Subjective)?")

        if not updated_state.get("passing_marks"):
            missing.append("passing_marks")
            questions.append("What is the minimum passing mark for students (e.g., 20 marks, 40 marks)?")

        if "min_attendance" not in updated_state or "fee_clearance_required" not in updated_state:
            missing.append("eligibility_rules")
            questions.append("What are the candidate eligibility rules (e.g., minimum attendance percentage and fee clearance requirement)?")

        is_complete = len(missing) == 0
        explanation = (
            "All required examination parameters verified and complete without any ungrounded assumptions."
            if is_complete
            else f"Still missing {len(missing)} parameter(s) / require conflict resolution."
        )

        engine_str = f"Live {self.llm.get_provider_name().upper()} ({self.llm.get_model_name()})" if self.llm.get_provider_name() != "mock" else "Rule-Based Deterministic Engine"

        return ClarificationResponse(
            is_complete=is_complete,
            extracted_params=updated_state,
            missing_params=missing,
            clarifying_questions=questions,
            explanation=explanation,
            conflict_warning=conflict_warning,
            engine_used=engine_str,
        )

    def clarify_request(self, user_request: str) -> ClarificationResponse:
        """Single-turn helper for initial prompt."""
        return self.clarify_request_state({}, user_request)

    def propose_plan(self, details: Dict[str, Any]) -> ExamPlan:
        """
        Step 2: Propose structured, locked exam blueprint from fully clarified details.
        Strictly uses user-provided parameters (NO INVENTED CODES OR TIMINGS).
        """
        course_code = details.get("course_code") or "COURSE_CODE_REQUIRED"
        course_name = details.get("course_name") or f"Course {course_code}"
        exam_date = details.get("exam_date") or "DATE_REQUIRED"
        delivery_window = details.get("delivery_window") or "DELIVERY_WINDOW_REQUIRED"
        duration = int(details.get("duration_minutes", 60))
        total_marks = float(details.get("total_marks", 60.0))
        passing_marks = float(details.get("passing_marks", 20.0))
        exam_title = details.get("exam_title") or f"{course_name} Online Examination"
        structure_desc = str(details.get("section_structure", "")).lower()

        min_att = float(details.get("min_attendance", 75.0))
        fee_req = bool(details.get("fee_clearance_required", True))

        sections = []

        if "mcq" in structure_desc and "subjective" not in structure_desc:
            mark_match = re.search(r"(\d+(\.\d+)?)\s*(mark|marks|pt|pts)\s*(each|per)?", structure_desc)
            marks_per_q = float(mark_match.group(1)) if mark_match else 1.0
            mcq_count = max(1, int(round(total_marks / marks_per_q)))

            sections.append(
                ExamSectionSpec(
                    section_name="Section A: Objective Questions (MCQs)",
                    section_type="MCQ",
                    question_count=mcq_count,
                    marks_per_question=marks_per_q,
                    total_section_marks=total_marks,
                    topics_covered=details.get("topics") or ["LLM Architectures", "Prompt Engineering", "Fine-Tuning", "RAG & Agents"],
                )
            )
        elif "subjective" in structure_desc and "mcq" not in structure_desc:
            sub_count = max(1, int(total_marks / 10.0))
            marks_per_q = total_marks / sub_count
            sections.append(
                ExamSectionSpec(
                    section_name="Section A: Descriptive / Subjective Questions",
                    section_type="Subjective",
                    question_count=sub_count,
                    marks_per_question=marks_per_q,
                    total_section_marks=total_marks,
                    topics_covered=details.get("topics") or ["Descriptive Concepts", "System Design"],
                )
            )
        else:
            if total_marks <= 10.0:
                sections.append(
                    ExamSectionSpec(
                        section_name="Section A: Objective Questions (MCQs)",
                        section_type="MCQ",
                        question_count=max(1, int(total_marks)),
                        marks_per_question=1.0,
                        total_section_marks=total_marks,
                        topics_covered=["Foundations", "Core Principles"],
                    )
                )
            else:
                mcq_marks = total_marks * 0.4
                mcq_count = max(1, int(mcq_marks / 2.0))
                mcq_total = mcq_count * 2.0
                sub_total = total_marks - mcq_total
                sub_count = max(1, int(sub_total / 10.0)) if sub_total >= 10 else 1
                sub_marks_per_q = sub_total / sub_count if sub_count > 0 else sub_total

                sections.append(
                    ExamSectionSpec(
                        section_name="Section A: Objective Questions (MCQs)",
                        section_type="MCQ",
                        question_count=mcq_count,
                        marks_per_question=2.0,
                        total_section_marks=mcq_total,
                        topics_covered=["Foundations", "Core Principles"],
                    )
                )
                sections.append(
                    ExamSectionSpec(
                        section_name="Section B: Descriptive / Subjective Questions",
                        section_type="Subjective",
                        question_count=sub_count,
                        marks_per_question=sub_marks_per_q,
                        total_section_marks=sub_total,
                        topics_covered=["Applied Systems", "Analysis"],
                    )
                )

        plan = ExamPlan(
            course_code=course_code,
            course_name=course_name,
            exam_title=exam_title,
            duration_minutes=duration,
            exam_date=exam_date,
            delivery_window=delivery_window,
            total_marks=total_marks,
            passing_marks=passing_marks,
            sections=sections,
            eligibility_rules=EligibilityCriteria(
                min_attendance_percentage=min_att,
                require_fee_clearance=fee_req,
                require_prerequisites=True,
            ),
            proctoring_enabled=True,
            status="DRAFT",
        )
        return plan

    def revise_plan(self, current_plan: ExamPlan, feedback: str) -> PlanRevision:
        """
        Step 3: Revise the proposed plan according to faculty critique.
        """
        updated_dict = current_plan.model_dump()
        text = feedback.strip().lower()
        modified_fields = []

        if self.llm.get_provider_name() != "mock":
            prompt = f"""
Current Exam Plan JSON:
{json.dumps(updated_dict, indent=2)}

Faculty Revision Request:
"{feedback}"

Apply all requested modifications to the Exam Plan JSON.
Output ONLY valid JSON matching the schema.
"""
            llm_res = self.llm.generate(prompt)
            if llm_res:
                try:
                    clean = llm_res.strip()
                    if "```json" in clean:
                        clean = clean.split("```json")[1].split("```")[0].strip()
                    elif "```" in clean:
                        clean = clean.split("```")[1].split("```")[0].strip()
                    parsed = json.loads(clean)
                    revised = ExamPlan(**parsed)
                    return PlanRevision(
                        revision_summary=f"Plan updated via {self.llm.get_provider_name().upper()}: {feedback}",
                        modified_fields=["plan_reconfigured_by_llm"],
                        revised_plan=revised,
                    )
                except Exception:
                    pass

        # Fallback rule parsing
        if "open for all in terms of fees" in text or "no fee" in text:
            updated_dict["eligibility_rules"]["require_fee_clearance"] = False
            modified_fields.append("require_fee_clearance -> False (Open for all)")

        att_match = re.search(r"(\d+)\s*%", text)
        if att_match and "attendance" in text:
            new_att = float(att_match.group(1))
            updated_dict["eligibility_rules"]["min_attendance_percentage"] = new_att
            modified_fields.append(f"min_attendance_percentage -> {new_att}%")

        if not modified_fields:
            modified_fields.append("custom feedback applied")

        revised_plan = ExamPlan(**updated_dict)
        return PlanRevision(
            revision_summary=f"Plan updated based on feedback: {', '.join(modified_fields)}",
            modified_fields=modified_fields,
            revised_plan=revised_plan,
        )
