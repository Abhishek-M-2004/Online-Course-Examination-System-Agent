"""
Lab 2: Domain Calculator / Checker Tool with Configurable Sources.
Performs deterministic mathematical calculations and validation checks locally,
verifying section marks, question bank sufficiency from pool_source, and candidate capacity from roster_source.
"""
from typing import Dict, Any, List, Optional
from src.models.exam_plan import ExamPlan
from src.tools.question_pool_tool import get_question_pool_stats
from src.tools.eligibility_tool import verify_candidate_eligibility


def validate_marks_consistency(plan: ExamPlan) -> Dict[str, Any]:
    """
    Performs local mathematical calculations to verify:
    1. sum(section.total_section_marks) == plan.total_marks
    2. question_count * marks_per_question == total_section_marks for each section
    3. passing_marks <= total_marks
    """
    section_errors = []
    calculated_section_total = 0.0

    for idx, s in enumerate(plan.sections, 1):
        expected_sec_total = round(s.question_count * s.marks_per_question, 2)
        calculated_section_total += s.total_section_marks
        if abs(expected_sec_total - s.total_section_marks) > 0.01:
            section_errors.append(
                f"Section '{s.section_name}': {s.question_count} Qs x {s.marks_per_question} marks = {expected_sec_total}, but total_section_marks is {s.total_section_marks}."
            )

    calculated_section_total = round(calculated_section_total, 2)
    overall_balanced = abs(calculated_section_total - plan.total_marks) < 0.01

    if not overall_balanced:
        section_errors.append(
            f"Overall marks mismatch: Sum of sections is {calculated_section_total}, but plan total_marks is {plan.total_marks}."
        )

    if plan.passing_marks > plan.total_marks:
        section_errors.append(
            f"Passing marks ({plan.passing_marks}) cannot exceed total marks ({plan.total_marks})."
        )

    return {
        "is_valid": len(section_errors) == 0,
        "overall_balanced": overall_balanced,
        "planned_total_marks": plan.total_marks,
        "calculated_section_total": calculated_section_total,
        "passing_marks": plan.passing_marks,
        "errors": section_errors,
    }


def compute_exam_feasibility(
    plan: ExamPlan,
    pool_source: str,
    roster_source: str,
) -> Dict[str, Any]:
    """
    Unified Domain Calculator & Feasibility Checker.
    Cross-checks the plan against user-specified Question Bank (pool_source) and Candidate Roster (roster_source) files.
    """
    issues: List[str] = []

    # 1. Mathematical Consistency Check
    marks_check = validate_marks_consistency(plan)
    if not marks_check["is_valid"]:
        issues.extend(marks_check["errors"])

    # 2. Question Pool Sufficiency Check from user-specified pool_source
    pool_stats = get_question_pool_stats(source_path=pool_source, course_code=plan.course_code)
    required_mcqs = sum(s.question_count for s in plan.sections if s.section_type.upper() == "MCQ")
    required_sub = sum(s.question_count for s in plan.sections if s.section_type.upper() == "SUBJECTIVE")

    if required_mcqs > pool_stats.mcq_count:
        issues.append(
            f"Question Pool Shortage: Plan requires {required_mcqs} MCQs, but '{pool_source}' only contains {pool_stats.mcq_count}."
        )
    if required_sub > pool_stats.subjective_count:
        issues.append(
            f"Question Pool Shortage: Plan requires {required_sub} Subjective questions, but '{pool_source}' only contains {pool_stats.subjective_count}."
        )

    # 3. Candidate & Workload Computation from user-specified roster_source
    eligibility = verify_candidate_eligibility(
        source_path=roster_source, course_code=plan.course_code, criteria=plan.eligibility_rules
    )
    eligible_count = eligibility.eligible_count
    total_obj_evals = eligible_count * required_mcqs
    total_sub_evals = eligible_count * required_sub
    est_faculty_mins = round(total_sub_evals * 1.5, 1)

    is_feasible = len(issues) == 0

    return {
        "is_feasible": is_feasible,
        "marks_validation": marks_check,
        "pool_verification": {
            "source_path": pool_source,
            "available_mcqs": pool_stats.mcq_count,
            "required_mcqs": required_mcqs,
            "available_subjective": pool_stats.subjective_count,
            "required_subjective": required_sub,
            "topics": pool_stats.topics,
            "total_marks_in_pool": pool_stats.total_marks_available,
        },
        "candidate_verification": {
            "source_path": roster_source,
            "total_candidates": eligibility.total_candidates_evaluated,
            "eligible_candidates": eligibility.eligible_count,
            "disqualified_candidates": eligibility.ineligible_count,
            "ambiguous_candidates": eligibility.ambiguous_count,
        },
        "workload_computation": {
            "total_objective_evaluations": total_obj_evals,
            "total_subjective_evaluations": total_sub_evals,
            "estimated_faculty_review_mins": est_faculty_mins,
        },
        "issues": issues,
    }
