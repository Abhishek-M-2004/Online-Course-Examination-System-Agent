# Lab 1: Agent vs Chatbot — Multi-Turn Planning & Clarification Agent

---

## 1. Executive Summary & Core Concept

In traditional conversational AI, a standard **Chatbot** often "guesses" or invents missing parameters (such as assuming passing marks are 40%, picking an arbitrary date, or fabricating question counts). In high-stakes institutional workflows like **Examination Planning**, unverified assumptions lead to serious academic errors.

**Lab 1** implements an **Agentic Planning System** founded on the **Zero-Assumption / Zero-Invention Principle**:
* **Never Guess**: The agent strictly refuses to invent dates, course codes, marks, or eligibility rules.
* **Multi-Turn State Tracking**: Accumulates parameters across multiple conversational turns without losing previously established facts.
* **Contradiction Detection**: Automatically spots mathematical conflicts (e.g., total marks = 60, but user specifies 120 MCQs $\times$ 1 mark = 120 marks).
* **Strict Date Validation**: Rejects vague bare months (e.g., `"in September"`) and demands an exact day and month.
* **Marks Balancing**: Mathematically enforces that $\sum (\text{questions} \times \text{marks}) = \text{total marks}$.

---

## 2. System Architecture & Workflow

```
[ User Initial Prompt ] (e.g. "Conduct an exam for CS301")
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│              ExamPlannerAgent.clarify_request_state()     │
│  1. Extract newly provided fields (via GROQ LLM)         │
│  2. Merge into accumulated_state                         │
│  3. Check Contradictions (_detect_contradictions)        │
│  4. Validate Exact Date Format (_is_exact_date)          │
│  5. Identify Remaining Missing Parameters (from 9 specs) │
└──────────────────────────────────────────────────────────┘
         │
         ├──► [ Missing Parameters / Conflict Found? ]
         │         │
         │         ▼ (Loop back)
         │    Emits Clarifying Questions & Warnings to Faculty
         │    Waits for next faculty response
         │
         └──► [ All 9 Parameters Complete & Validated ]
                   │
                   ▼
┌──────────────────────────────────────────────────────────┐
│              ExamPlannerAgent.propose_plan()             │
│  Constructs locked, typed ExamPlan (Pydantic model)      │
│  Validates Section Marks Balance vs Total Marks          │
└──────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────┐
│              ExamPlannerAgent.revise_plan()              │
│  Interactive Revision Loop (Faculty feedback & sign-off) │
└──────────────────────────────────────────────────────────┘
```

---

## 3. The 9 Mandatory Examination Parameters

The agent will not finalize an exam plan until all **9 mandatory parameters** are fully resolved:

| # | Parameter | Description | Validation Rule |
|---|---|---|---|
| 1 | `course_code` | e.g., `CS301`, `24ECAC203` | Required string |
| 2 | `course_name` | e.g., `Operating Systems`, `Agentic AI` | Required string |
| 3 | `exam_date` | Date of the exam | Must contain exact day and month (e.g., `2026-09-15` or `Sep 15, 2026`). Bare months (`"September"`) are rejected. |
| 4 | `delivery_window` | Access window | e.g., `10:00 AM - 01:00 PM` |
| 5 | `duration_minutes` | Exam duration | Positive integer $\ge 15$ mins |
| 6 | `total_marks` | Maximum marks | Positive float $\ge 1.0$ |
| 7 | `passing_marks` | Minimum passing score | Must satisfy $\text{passing\_marks} \le \text{total\_marks}$ |
| 8 | `section_structure` | Question breakdown | MCQs vs Subjective, count, and marks per question |
| 9 | `eligibility_rules` | Candidate criteria | Attendance threshold (e.g., $75\%$), fee clearance, prerequisites |

---

## 4. Key Code Snippets & Technical Explanation

### A. Mandatory Parameter Registry (`src/lab1/planner_agent.py`)
```python
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
```

---

### B. Contradiction Detection Engine (`src/lab1/planner_agent.py`)
Detects arithmetic clashes before they reach the database or evaluation tools:
```python
def _detect_contradictions(self, state: Dict[str, Any], user_input: str) -> Optional[str]:
    """
    Detects mathematical contradictions between total marks and question distribution.
    e.g., Total marks = 60, but user wrote 120 MCQs x 1 mark = 120 marks.
    """
    total_marks = state.get("total_marks")
    text = user_input.lower()

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
                f"Please confirm whether you want {int(total_marks)} MCQs or {claimed_count} MCQs."
            )
    return None
```

---

### C. Date Precision Enforcement (`src/lab1/planner_agent.py`)
Prevents ambiguous scheduling:
```python
def _is_exact_date(self, date_str: str) -> bool:
    """Checks if date contains an exact day and month (not just a bare month like 'september')."""
    if not date_str:
        return False
    d = date_str.strip().lower()
    months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    if d in months:
        return False  # Rejects bare month
    
    # Requires day digits (e.g. 2026-09-15 or Sep 15 or 15th September)
    has_day_digit = bool(re.search(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}|\b\d{1,2}(st|nd|rd|th)?\b|\b\d{4}\b", d))
    return has_day_digit
```

---

### D. Multi-Turn Clarification State Accumulator (`src/lab1/planner_agent.py`)
Uses the active LLM (GROQ `gpt-oss-120b` or Gemini) to extract newly provided entities, then validates remaining missing fields:
```python
def clarify_request_state(self, current_state: Dict[str, Any], user_input: str) -> ClarificationResponse:
    updated_state = current_state.copy()
    conflict_warning = self._detect_contradictions(updated_state, user_input)

    # 1. LLM-Powered Extraction
    extracted = self._extract_parameters_with_llm(updated_state, user_input)
    updated_state.update(extracted)

    # 2. Re-validate date precision
    if "exam_date" in updated_state and not self._is_exact_date(updated_state["exam_date"]):
        del updated_state["exam_date"]

    # 3. Identify Missing Parameters
    missing = [k for k in MANDATORY_PARAMETERS if k not in updated_state]

    # 4. Generate targeted clarifying questions for missing items
    questions = self._generate_clarifying_questions(missing, updated_state)

    return ClarificationResponse(
        is_complete=(len(missing) == 0 and conflict_warning is None),
        extracted_params=updated_state,
        missing_params=missing,
        clarifying_questions=questions,
        conflict_warning=conflict_warning,
    )
```

---

### E. Structured Plan Generation & Marks Validation (`src/models/exam_plan.py`)
```python
class ExamPlan(BaseModel):
    course_code: str
    course_name: str
    exam_title: str = "Semester Examination"
    duration_minutes: int = Field(default=120, ge=15)
    exam_date: str
    delivery_window: str
    total_marks: float = Field(ge=1.0)
    passing_marks: float = Field(ge=0.0)
    sections: List[ExamSectionSpec]
    eligibility_rules: EligibilityCriteria
    proctoring_enabled: bool = True
    status: str = "DRAFT"

    def validate_marks_balance(self) -> bool:
        """Enforces that sum(section marks) == total_marks."""
        calculated = sum(s.total_section_marks for s in self.sections)
        return abs(calculated - self.total_marks) < 0.01
```

---

## 5. How to Run the Demo

Execute the interactive Lab 1 CLI:
```powershell
python lab1_demo.py
```

### Example Interactive Session:

1. **Faculty enters vague prompt**:
   ```text
   Enter your initial exam prompt: Set up an exam for CS301 Operating Systems
   ```

2. **Agent analyzes completeness and enters Clarification Turn #1**:
   ```text
   ======================================================================
     CLARIFICATION TURN #1: MISSING INFORMATION REQUIRED
   ======================================================================
   ⚠️ Status: Still missing 7 required parameter(s).

   Clarifying Questions for Faculty:
     1. What is the exact examination date (day and month)?
     2. What is the exam start time or delivery window (e.g., 10:00 AM - 01:00 PM)?
     3. What is the total duration in minutes?
     4. What are the total maximum marks?
     5. What is the question structure (number of MCQs and descriptive questions)?
     6. What are the minimum passing marks?
     7. What are the candidate eligibility criteria (attendance % and fee requirements)?
   ```

3. **Faculty enters partial info**:
   ```text
   Your Response: Date is 2026-09-15 from 10:00 AM to 12:00 PM. Duration is 120 mins. Total marks 60, passing marks 24.
   ```

4. **Agent updates state and asks for remaining fields (Turn #2)**:
   ```text
   Clarifying Questions for Faculty:
     1. What is the question structure (number of MCQs and descriptive questions)?
     2. What are the candidate eligibility criteria (attendance % and fee requirements)?
   ```

5. **Faculty provides final parameters**:
   ```text
   Your Response: 60 MCQs of 1 mark each. Attendance 75% and fee clearance required.
   ```

6. **Agent produces the Verified Structured Plan**:
   ```text
   ======================================================================
     STEP 1: ALL REQUIRED PARAMETERS VERIFIED & COMPLETE
   ======================================================================
   📋 Current Structured Exam Plan:
     • Course: CS301 - Operating Systems
     • Exam Date: 2026-09-15 | Duration: 120 minutes | Window: 10:00 AM - 12:00 PM
     • Total Marks: 60.0 (Passing Marks: 24.0)
     • Eligibility: Min Attendance: 75.0%, Require Fee Clearance: True
     • Sections:
        [1] Section A: Objective Questions: 60 Qs x 1.0 marks = 60.0 marks (MCQ)
     • Marks Balanced: ✅ YES
   ```

7. **Iterative Revision Loop**:
   Faculty can type revisions like `"Change passing marks to 20"` or type `"approve"` to lock and finalize the plan.
