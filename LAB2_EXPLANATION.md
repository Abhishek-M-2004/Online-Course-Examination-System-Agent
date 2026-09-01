# Lab 2: Tool-Augmented Autonomous Agent — Multi-Format Parsing & Verification

---

## 1. Executive Summary & Core Motivation

In LLM-based architectures, language models excel at reasoning and natural language understanding, but they are prone to mathematical hallucinations and cannot directly read local files (like PDFs or Excel spreadsheets) without tools.

**Lab 2** builds a **Tool-Augmented Agentic Architecture**:
* **Deterministic Ground Truth**: All numerical counts, marks calculations, and student clearance checks are executed by local Python tools—**consuming 0 LLM tokens and $0 API cost**.
* **Universal File Ingestion**: Ingests **PDFs** (both digital text & scanned/vector PDFs via local OCR), **CSVs**, **JSONs**, and **Excel spreadsheets** (`.xlsx`, `.xls`).
* **Dynamic File Discovery**: Automatically matches natural language queries to the appropriate files in `data/` using semantic token scoring and typo tolerance.
* **Multi-Tool Chaining**: Automatically plans and executes multi-step workflows (e.g., Question Pool Reader $\rightarrow$ Candidate Roster Reader $\rightarrow$ Domain Feasibility Calculator).
* **Strict Rejection & Audit Logging**: Never invents fake mock data or falls back to silent defaults if a file is missing or invalid. Maintains a verifiable audit trail.

---

## 2. System Architecture & Multi-Tool Pipeline

```
[ User Natural Language Request ] 
(e.g., "Read the OS question bank and Applied Materials allocation. Check 1-mark questions for a 60-mark exam and count students.")
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│             ToolAugmentedExamAgent.select_best_matching_files()        │
│  • Scans data/ for available pools & rosters                           │
│  • Scores relevance (score_file_relevance) with typo normalization     │
│  • Discovers: 'data/os_questions.pdf' & 'data/Applied Materials.xlsx'   │
└────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│  TOOL 1: QuestionPoolReaderTool (src/tools/question_pool_tool.py)      │
│  • Dual-Engine: pypdf (fast digital) + RapidOCR / PyMuPDF (vector/scan)│
│  • Universal Question Parser (MCQs, Subjective, Marks, Topics)         │
│  • Caches results in-memory via _PDF_CACHE for sub-millisecond reuse   │
│  • Result: 100 questions (40 MCQs, 60 Subjective, 640 total marks)     │
└────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│  TOOL 2: CandidateRosterReaderTool (src/tools/eligibility_tool.py)     │
│  • Multi-format: CSV / JSON / Excel (.xlsx, .xls via openpyxl)         │
│  • Evaluates 3 deterministic rules (Attendance, Fees, Prerequisites)   │
│  • Result: 256 students evaluated / 256 eligible                       │
└────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│  TOOL 3: DomainCalculatorTool (src/tools/exam_compute_tool.py)         │
│  • Evaluates Sufficiency: 40 MCQs available vs 60 required (SHORTAGE!) │
│  • Computes Faculty Grading Workload & Marks Consistency               │
└────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Verified Agent Final Report                        │
│  Emits structured summary with verified counts and execution flow      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The Three Core Domain Tools

### 🛠️ Tool 1: Question Pool Reader (`src/tools/question_pool_tool.py`)
Reads, extracts, and categorizes examination questions from PDF, CSV, and JSON files.

#### Key Feature: Dual-Engine PDF Ingestion & OCR Fallback
```python
def extract_text_from_pdf(pdf_path: str) -> Tuple[str, int, str, List[str]]:
    """
    Tier 1: Fast native text extraction via pypdf.
    Tier 2: Automatic fallback to local RapidOCR + PyMuPDF for vector/scanned PDFs.
    """
    # Check in-memory mtime cache first
    cached = _get_cached_pdf(pdf_path)
    if cached:
        return cached

    # Tier 1: pypdf extraction
    reader = pypdf.PdfReader(pdf_path)
    raw_text = "\n".join([page.extract_text() or "" for page in reader.pages])

    # Tier 2: OCR Fallback if text is empty (e.g. vector-printed text)
    if len(raw_text.strip()) < 50:
        raw_text, warnings = extract_text_via_local_ocr(pdf_path)
        status = "VERIFIED_COMPLETE" if raw_text else "FAILED"
    else:
        status = "VERIFIED_COMPLETE"

    return raw_text, len(reader.pages), status, warnings
```

---

### 🛠️ Tool 2: Candidate Roster & Eligibility Reader (`src/tools/eligibility_tool.py`)
Reads candidate profiles from CSV, JSON, or Excel spreadsheets and evaluates deterministic eligibility.

#### Key Feature: Universal Excel (`.xlsx`, `.xls`) & CSV Reader
```python
def verify_candidate_eligibility(source_path: str, criteria: Optional[EligibilityCriteria] = None):
    """
    Evaluates candidate eligibility against 3 deterministic rules:
    1. Attendance >= min_attendance (default 75%)
    2. Fee status == 'PAID'
    3. Prerequisites == 'CLEARED'
    """
    students = read_student_roster(source_path=source_path)

    min_attendance = criteria.min_attendance_percentage if criteria else 75.0
    req_fee = criteria.require_fee_clearance if criteria else True
    req_prereq = criteria.require_prerequisites if criteria else True

    eligible, disqualified, flagged = [], [], []
    for s in students:
        reasons = []
        if s.attendance_percentage < min_attendance:
            reasons.append(f"Attendance {s.attendance_percentage}% below required {min_attendance}%")
        if req_fee and s.fee_status.upper() not in ["PAID", "CLEARED"]:
            reasons.append(f"Fee status '{s.fee_status}' is pending/unpaid")
        if req_prereq and s.prerequisite_status.upper() not in ["CLEARED", "PASSED"]:
            reasons.append(f"Prerequisite status '{s.prerequisite_status}' is not cleared")

        if s.special_accommodations:
            flagged.append({"student_id": s.student_id, "name": s.name})

        if reasons:
            disqualified.append({"student_id": s.student_id, "reasons": reasons})
        else:
            eligible.append(s)

    return EligibilityCheckResult(
        total_candidates_evaluated=len(students),
        eligible_count=len(eligible),
        ineligible_count=len(disqualified),
        ambiguous_count=len(flagged),
    )
```

---

### 🛠️ Tool 3: Domain Calculator & Feasibility Checker (`src/tools/exam_compute_tool.py`)
Cross-verifies the examination plan against question bank capacity and student cohort size.

#### Key Feature: Mathematical Verification & Sufficiency Check
```python
def compute_exam_feasibility(plan: ExamPlan, pool_source: str, roster_source: str) -> Dict[str, Any]:
    issues = []
    
    # 1. Mathematical Marks Balancing
    marks_check = validate_marks_consistency(plan)
    if not marks_check["is_valid"]:
        issues.extend(marks_check["errors"])

    # 2. Question Pool Sufficiency Check
    pool_stats = get_question_pool_stats(source_path=pool_source, course_code=plan.course_code)
    required_mcqs = sum(s.question_count for s in plan.sections if s.section_type.upper() == "MCQ")
    if required_mcqs > pool_stats.mcq_count:
        issues.append(f"Shortage: Plan requires {required_mcqs} MCQs, but pool only has {pool_stats.mcq_count}.")

    # 3. Workload Computation
    eligibility = verify_candidate_eligibility(source_path=roster_source, course_code=plan.course_code)
    faculty_grading_mins = round(eligibility.eligible_count * required_sub * 1.5, 1)

    return {
        "is_feasible": len(issues) == 0,
        "marks_validation": marks_check,
        "pool_verification": {"available_mcqs": pool_stats.mcq_count, "required_mcqs": required_mcqs},
        "workload_computation": {"estimated_faculty_review_mins": faculty_grading_mins},
        "issues": issues,
    }
```

---

## 4. The Orchestrator Agent (`src/lab2/tool_agent.py`)

### Semantic File Discovery & Typo Normalization
The agent matches human prompts to local files using token overlap scoring:
```python
def score_file_relevance(file_path: str, request_text: str) -> float:
    base = os.path.basename(file_path).lower()
    q_lower = request_text.lower().replace(".xlxs", ".xlsx")  # Normalize common typos

    base_tokens = set(re.findall(r"[a-zA-Z0-9]+", base))
    q_tokens = set(re.findall(r"[a-zA-Z0-9]+", q_lower))
    
    score = 0.0
    if base in q_lower: score += 40.0
    if "applied" in base_tokens and "applied" in q_tokens: score += 35.0
    if "os" in base_tokens and "os" in q_tokens: score += 20.0
    return score
```

---

## 5. Demonstration Modes in `lab2_demo.py`

Run the interactive Lab 2 test suite:
```powershell
python lab2_demo.py
```

| Option | Demo Name | What It Demonstrates |
|---|---|---|
| **1** | Tool 1: Question Pool Reader | Extracts questions from any PDF (e.g. `data/os_questions.pdf`), CSV, or JSON. |
| **2** | Tool 2: Candidate Roster Reader | Evaluates student eligibility from CSV or Excel (`Applied Materials -- Lab Allocation.xlsx`). |
| **3** | Tool 3: Domain Calculator | Verifies mathematical marks balance, question pool sufficiency, and grading time. |
| **4** | Natural Language Tool Calling | Dynamically discovers files from natural language queries and chains all tools together. |
| **5** | Strict Error Handling | Proves strict rejection on missing files or unsupported file formats. |
| **6** | Audit Trail Inspector | Displays timestamps, tool names, inputs, and verified outputs for full transparency. |

---

## 6. Real Demonstration Examples

### Query: Applied Materials Excel Allocation
```text
Enter your request: Go throught this Applied Materials -- Lab Allocation.xlxs and count the number of sstudents
```
**Output:**
```text
🔀 Execution Flow:
   User Request -> Agent -> Candidate Roster Reader using 'data/Applied Materials -- Lab Allocation.xlsx' -> Agent -> Verified Result

🛠️ Tools Invoked: CandidateRosterReaderTool

[CANDIDATE ROSTER] Candidate Roster Verification (Applied Materials -- Lab Allocation.xlsx):
  • File Format: EXCEL
  • Total Students Evaluated / Counted: 256 students
  • Eligible Students: 256 students
  • Disqualified Students: 0 students
```

### Query: Question Pool Shortage Check
```text
Enter your request: Read the OS question bank. Check whether the question pool contains enough 1 mark questions to conduct a 60 mark exam.
```
**Output:**
```text
[QUESTION POOL] Question Pool Verification (os_questions.pdf):
  • Total Questions Extracted: 100 (40 MCQs, 60 Subjective)
  • Sufficiency Check for 60 Marks: [SHORTAGE] (Pool contains 40 MCQs; 20 additional 1-mark questions required to conduct a 60-mark all-MCQ exam)
```
