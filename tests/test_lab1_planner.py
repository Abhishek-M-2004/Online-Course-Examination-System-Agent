"""
Tests for Lab 1: Agent vs Chatbot — Strict Zero-Assumption Exam Planner Loop.
"""
import pytest
from src.lab1.planner_agent import ExamPlannerAgent
from src.models.exam_plan import ExamPlan


def test_lab1_vague_prompt_generates_at_least_two_clarifying_questions():
    """Acceptance test: Vague request MUST ask >= 2 clarifying questions."""
    agent = ExamPlannerAgent()
    vague_request = "Create an online exam for my students"

    clarification = agent.clarify_request(vague_request)

    assert clarification.is_complete is False
    assert len(clarification.clarifying_questions) >= 2
    assert "course_code" in clarification.missing_params
    assert "total_marks" in clarification.missing_params


def test_lab1_contradiction_detection_between_marks_and_questions():
    """Verify that contradiction between total marks and MCQ count triggers warning."""
    agent = ExamPlannerAgent()
    state = {"total_marks": 60.0}
    
    # User claims 120 MCQs of 1 mark each while total marks is 60
    input_text = "120 MCQs of 1 mark each"
    clar = agent.clarify_request_state(state, input_text)

    assert clar.is_complete is False
    assert clar.conflict_warning is not None
    assert "Conflict detected" in clar.conflict_warning
    assert "60" in clar.conflict_warning
    assert "120" in clar.conflict_warning


def test_lab1_bare_month_rejected_until_exact_day_provided():
    """Verify that bare month 'September' is rejected until exact date is specified."""
    agent = ExamPlannerAgent()
    state = {}

    # Turn 1: User says only 'September'
    clar1 = agent.clarify_request_state(state, "The exam will be conducted in september")
    assert "exam_date" in clar1.missing_params
    assert clar1.is_complete is False
    assert any("specific date in September" in q for q in clar1.clarifying_questions)

    # Turn 2: User provides exact date
    clar2 = agent.clarify_request_state(clar1.extracted_params, "Exact date is September 15, 2026")
    assert "exam_date" not in clar2.missing_params
    assert clar2.extracted_params.get("exam_date") is not None


def test_lab1_multi_turn_clarification_accumulates_state_without_invention():
    """Test that multi-turn clarification gathers parameters without inventing missing fields."""
    agent = ExamPlannerAgent()
    
    # Turn 1: Vague prompt
    state = {}
    clar1 = agent.clarify_request_state(state, "conduct an exam")
    state = clar1.extracted_params
    assert clar1.is_complete is False

    # Turn 2: User provides course code and course title
    clar2 = agent.clarify_request_state(state, "Course code is 24ECAC203 and title is Agentic AI, duration is 60 minutes")
    state = clar2.extracted_params
    assert state.get("course_code") == "24ECAC203"
    assert state.get("course_name") == "Agentic AI"
    assert state.get("duration_minutes") == 60
    assert clar2.is_complete is False

    # Turn 3: User provides exact date, window, marks, sections, passing marks, eligibility
    turn3_text = (
        "Date is 2026-09-15, time is 09:00 AM - 12:00 PM, total marks 60, "
        "60 MCQs of 1 mark each, passing marks is 20, min attendance 80%, open for all in terms of fees"
    )
    clar3 = agent.clarify_request_state(state, turn3_text)
    state = clar3.extracted_params

    assert state.get("exam_date") == "2026-09-15"
    assert state.get("delivery_window") == "09:00 AM - 12:00 PM"
    assert state.get("total_marks") == 60.0
    assert state.get("passing_marks") == 20.0
    assert state.get("min_attendance") == 80.0
    assert state.get("fee_clearance_required") is False
    assert clar3.is_complete is True


def test_lab1_propose_plan_marks_balance():
    """Test that propose_plan builds a valid plan with balanced marks."""
    agent = ExamPlannerAgent()
    details = {
        "course_code": "24ECAC203",
        "course_name": "Agentic AI",
        "exam_date": "2026-09-15",
        "delivery_window": "09:00 AM - 12:00 PM",
        "total_marks": 60.0,
        "passing_marks": 20.0,
        "duration_minutes": 60,
        "section_structure": "60 MCQs of 1 mark each",
        "min_attendance": 80.0,
        "fee_clearance_required": False,
    }
    plan = agent.propose_plan(details)

    assert isinstance(plan, ExamPlan)
    assert plan.course_code == "24ECAC203"
    assert plan.course_name == "Agentic AI"
    assert plan.total_marks == 60.0
    assert plan.passing_marks == 20.0
    assert plan.duration_minutes == 60
    assert plan.exam_date == "2026-09-15"
    assert plan.delivery_window == "09:00 AM - 12:00 PM"
    assert plan.eligibility_rules.min_attendance_percentage == 80.0
    assert plan.eligibility_rules.require_fee_clearance is False
    assert plan.validate_marks_balance() is True
    assert len(plan.sections) >= 1
