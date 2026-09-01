"""
Data models for Exam Planning, Clarification, and Revisions.
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class ExamSectionSpec(BaseModel):
    """Specification for an exam section (e.g., MCQs, Descriptive)."""
    section_name: str = Field(description="Name of the section, e.g., 'Section A: Objective MCQs'")
    section_type: str = Field(description="Type: 'MCQ' or 'Subjective'")
    question_count: int = Field(description="Number of questions in this section", ge=1)
    marks_per_question: float = Field(description="Marks allocated per question", ge=0.01)
    total_section_marks: float = Field(description="Total marks for this section", ge=0.01)
    topics_covered: List[str] = Field(default_factory=list, description="Specific topics or syllabus units")


class EligibilityCriteria(BaseModel):
    """Eligibility thresholds for candidate registration."""
    min_attendance_percentage: float = Field(default=75.0, ge=0.0, le=100.0)
    require_fee_clearance: bool = Field(default=True)
    require_prerequisites: bool = Field(default=True)


class ExamPlan(BaseModel):
    """Structured, locked specification of an examination."""
    course_code: str = Field(description="e.g. 'CS301'")
    course_name: str = Field(description="e.g. 'Operating Systems'")
    exam_title: str = Field(default="Semester Examination")
    duration_minutes: int = Field(default=120, ge=15)
    exam_date: str = Field(default="2026-09-01", description="Date of the exam, e.g. '2026-09-15'")
    delivery_window: str = Field(default="09:00 AM - 12:00 PM", description="Allowed session access window")
    total_marks: float = Field(default=50.0, ge=1.0)
    passing_marks: float = Field(default=20.0, ge=0.0)
    sections: List[ExamSectionSpec] = Field(default_factory=list)
    eligibility_rules: EligibilityCriteria = Field(default_factory=EligibilityCriteria)
    proctoring_enabled: bool = Field(default=True)
    status: str = Field(default="DRAFT", description="Status: DRAFT, LOCKED, APPROVED, PUBLISHED")

    def validate_marks_balance(self) -> bool:
        """Verify that section totals match overall total marks."""
        calculated = sum(s.total_section_marks for s in self.sections)
        return abs(calculated - self.total_marks) < 0.01


class ClarificationResponse(BaseModel):
    """Result of analyzing an exam request for completeness."""
    is_complete: bool = Field(description="True if all critical exam parameters are specified")
    extracted_params: Dict[str, Any] = Field(default_factory=dict)
    missing_params: List[str] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(
        default_factory=list,
        description="Questions asked to user to resolve ambiguity"
    )
    explanation: str = Field(default="")
    conflict_warning: Optional[str] = Field(default=None, description="Explicit warning when user inputs contradict each other")
    engine_used: str = Field(default="rule_based", description="e.g. 'Live Google Gemini (gemini-flash-latest)' or 'Rule-Based Deterministic Engine'")


class PlanRevision(BaseModel):
    """Details of changes made to an exam plan based on feedback."""
    revision_summary: str
    modified_fields: List[str]
    revised_plan: ExamPlan
