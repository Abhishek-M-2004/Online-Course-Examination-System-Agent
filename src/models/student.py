"""
Data models for Student Eligibility, Candidate Verification, and Question Bank Items.
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class StudentEligibilityRecord(BaseModel):
    """Candidate profile and academic clearance status."""
    student_id: str
    name: str
    email: str
    course_code: str
    attendance_percentage: float = Field(ge=0.0, le=100.0)
    fee_status: str = Field(description="'PAID' or 'PENDING'")
    prerequisite_status: str = Field(description="'CLEARED' or 'NOT_CLEARED'")
    special_accommodations: bool = False


class EligibilityCheckResult(BaseModel):
    """Output of eligibility verification across student cohort."""
    total_candidates_evaluated: int
    eligible_count: int
    ineligible_count: int
    ambiguous_count: int
    eligible_students: List[StudentEligibilityRecord] = Field(default_factory=list)
    disqualified_students: List[Dict[str, Any]] = Field(default_factory=list)
    ambiguous_students: List[Dict[str, Any]] = Field(default_factory=list)
    summary_report: str


class QuestionItem(BaseModel):
    """A single exam question from the bank."""
    id: str
    course_code: str
    course_name: str
    type: str  # 'MCQ' or 'Subjective'
    question: str
    options: Optional[Dict[str, str]] = None
    correct_answer: Optional[str] = None
    rubric: Optional[Dict[str, float]] = None
    marks: float
    topic: str
    difficulty: str
    bloom_level: str


class QuestionPoolStats(BaseModel):
    """Summary of available questions for a course with extraction verification."""
    course_code: str
    total_questions: int
    mcq_count: int
    subjective_count: int
    topics: List[str]
    total_marks_available: float
    pages_processed: int = 1
    extraction_status: str = Field(default="VERIFIED_COMPLETE", description="VERIFIED_COMPLETE, INCOMPLETE, or FAILED")
    extraction_warnings: List[str] = Field(default_factory=list)
