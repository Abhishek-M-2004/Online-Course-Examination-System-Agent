"""
Tests for Lab 2: Tool-Using Agent with Semantic Discovery and Verified PDF Extraction.
"""
import pytest
from src.tools.question_pool_tool import (
    read_question_pool,
    get_question_pool_stats,
    filter_questions_by_topic,
    resolve_and_validate_path,
)
from src.tools.eligibility_tool import (
    read_student_roster,
    verify_candidate_eligibility,
)
from src.tools.exam_compute_tool import (
    validate_marks_consistency,
    compute_exam_feasibility,
)
from src.lab2.tool_agent import ToolAugmentedExamAgent, score_file_relevance
from src.models.exam_plan import ExamPlan, ExamSectionSpec, EligibilityCriteria


def test_lab2_question_pool_reader_configurable_paths():
    """Verify Question Pool Reader works with user-specified PDF, CSV, and JSON paths."""
    # 1. Custom PDF path with verification checks
    pdf_qs = read_question_pool(source_path="data/Agentic_AI_Questions.pdf")
    assert len(pdf_qs) >= 2
    assert any(q.type == "MCQ" for q in pdf_qs)

    stats = get_question_pool_stats(source_path="data/os_questions.pdf")
    assert stats.pages_processed >= 1
    assert stats.extraction_status == "VERIFIED_COMPLETE"
    assert len(stats.extraction_warnings) == 0

    # 2. Custom CSV path
    csv_qs = read_question_pool(source_path="data/question_pool.csv")
    assert len(csv_qs) >= 5

    # 3. Custom JSON path
    json_qs = read_question_pool(source_path="data/question_pool.json")
    assert len(json_qs) >= 5


def test_lab2_candidate_roster_reader_configurable_paths():
    """Verify Candidate Roster Reader works with user-specified CSV and JSON paths."""
    csv_students = read_student_roster(source_path="data/6th_Sem_CSE_Students.csv")
    assert len(csv_students) >= 8

    res = verify_candidate_eligibility(
        source_path="data/6th_Sem_CSE_Students.csv",
        course_code="24ECAC203",
        criteria=EligibilityCriteria(min_attendance_percentage=75.0, require_fee_clearance=True),
    )
    assert res.total_candidates_evaluated == len(csv_students)
    assert res.eligible_count > 0
    assert res.ineligible_count > 0

    json_students = read_student_roster(source_path="data/student_roster.json")
    assert len(json_students) >= 8


def test_lab2_strict_file_rejection_no_fallbacks():
    """Verify that missing or unsupported files raise clear errors and do not fall back."""
    with pytest.raises(FileNotFoundError) as exc_info:
        read_question_pool(source_path="data/non_existent_bank.pdf")
    assert "File not found" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        read_question_pool(source_path="data/syllabus.docx")
    assert "Unsupported file format" in str(exc_info.value)


def test_lab2_domain_calculator_with_configurable_sources():
    """Verify Domain Calculator validates math and checks feasibility against specified files."""
    plan = ExamPlan(
        course_code="24ECAC203",
        course_name="Agentic AI",
        exam_date="2026-09-15",
        delivery_window="09:00 AM - 12:00 PM",
        total_marks=12.0,
        passing_marks=5.0,
        sections=[
            ExamSectionSpec(
                section_name="Section A: MCQs",
                section_type="MCQ",
                question_count=2,
                marks_per_question=1.0,
                total_section_marks=2.0,
            ),
            ExamSectionSpec(
                section_name="Section B: Subjective",
                section_type="Subjective",
                question_count=1,
                marks_per_question=10.0,
                total_section_marks=10.0,
            ),
        ],
    )

    feasibility = compute_exam_feasibility(
        plan=plan,
        pool_source="data/Agentic_AI_Questions.pdf",
        roster_source="data/6th_Sem_CSE_Students.csv",
    )
    assert feasibility["marks_validation"]["is_valid"] is True
    assert feasibility["pool_verification"]["available_mcqs"] >= 2
    assert feasibility["candidate_verification"]["total_candidates"] >= 8


def test_lab2_agent_invokes_tools_with_configurable_paths_and_logs_audit():
    """Verify Agent executes tools on configurable files and maintains audit trail."""
    agent = ToolAugmentedExamAgent()

    r1 = agent.process_query(
        "Check eligibility of 24ECAC203 students with 80% attendance",
        roster_source="data/6th_Sem_CSE_Students.csv",
    )
    assert r1["tool_called"] == "CandidateRosterReaderTool"
    assert "Candidate Roster Verification" in r1["response_text"]

    r2 = agent.process_query(
        "What questions and topics are available in the question bank?",
        pool_source="data/Agentic_AI_Questions.pdf",
    )
    assert r2["tool_called"] == "QuestionPoolReaderTool"
    assert "Question Pool Reader" in r2["response_text"]

    assert len(agent.tool_audit_log) >= 2


def test_lab2_semantic_file_selection_for_os_and_agentic_ai():
    """Verify semantic selection selects os_questions.pdf for OS and Agentic_AI_Questions.pdf for AI."""
    agent = ToolAugmentedExamAgent()

    # Query 1: OS question bank and student roster
    q1 = "Read the OS question bank and student roster. Check whether the question pool contains enough 1 mark questions to conduct a 60 mark exam, and count the number of students from the CSV file."
    p1, r1, clar1 = agent.select_best_matching_files(q1)

    assert clar1 is None
    assert "os_questions" in p1.lower() or "sample_exam" in p1.lower()
    assert "student_list" in r1.lower() or "student_roster" in r1.lower()

    # Query 2: Agentic AI question bank and 6th sem CSE
    q2 = "Read the Agentic AI question bank and 6th Sem CSE student roster."
    p2, r2, clar2 = agent.select_best_matching_files(q2)

    assert clar2 is None
    assert "agentic" in p2.lower()
    assert "6th_sem_cse" in r2.lower()


def test_lab2_natural_language_request_dynamic_discovery_and_flow():
    """Verify Demo 4 multi-tool dynamic discovery and execution flow from user query."""
    agent = ToolAugmentedExamAgent()
    query = (
        "Read the OS question bank and student roster. "
        "Check whether the question pool contains enough 1 mark questions to conduct a 60 mark exam, "
        "and count the number of students from the CSV file. Report the verified results."
    )
    result = agent.process_natural_language_request(query)

    assert result.get("needs_clarification") is not True
    assert "QuestionPoolReaderTool" in result["tools_called"]
    assert "CandidateRosterReaderTool" in result["tools_called"]
    assert "DomainCalculatorTool" in result["tools_called"]

    # Verify that OS questions file was selected (NOT Agentic AI)
    selected_pool = result["files_used"]["question_pool_file"]
    assert "os_questions" in selected_pool.lower() or "sample_exam" in selected_pool.lower()
    assert "agentic" not in selected_pool.lower()

    assert "User Request -> Agent -> Question Pool Reader" in result["flow"]
    assert "Candidate Roster Reader" in result["flow"]
    assert "Domain Calculator / Checker" in result["flow"]
    assert "Verified Result" in result["flow"]
    assert "Pages Processed & Verified" in result["response_text"]
    assert "Extraction Status: VERIFIED_COMPLETE" in result["response_text"]


def test_lab2_excel_roster_support_and_applied_materials_matching():
    """Verify that Excel rosters (.xlsx) are read accurately and matched by natural language queries."""
    agent = ToolAugmentedExamAgent()
    query = "Go throught this Applied Materials -- Lab Allocation.xlxs and count the number of sstudents"
    result = agent.process_natural_language_request(query)

    assert result.get("needs_clarification") is not True
    assert "CandidateRosterReaderTool" in result["tools_called"]
    assert "Applied Materials" in result["files_used"]["candidate_roster_file"]
    assert "Total Students Evaluated / Counted: 256 students" in result["response_text"]

