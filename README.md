# 🎓 Agentic AI Examination Planning & Tool-Augmented Verification System

An advanced, production-grade **Agentic AI** framework designed for **Automated Examination Planning, Multi-Format Resource Ingestion, and Deterministic Ground-Truth Verification**.

This repository implements **Lab 1** (Multi-Turn Clarification & Planning Loop) and **Lab 2** (Tool-Augmented Autonomous Agent with Universal Data Ingestion) aligned with the **Agentic AI 14-Lab Build Book**.

---

## 📑 Table of Contents
1. [Core Principles & Architecture](#-core-principles--architecture)
2. [Lab 1: Multi-Turn Planning & Clarification Agent](#-lab-1-multi-turn-planning--clarification-agent)
   - [Core Concept: Chatbot vs. Agent](#core-concept-chatbot-vs-agent)
   - [The 9 Mandatory Parameters](#the-9-mandatory-parameters)
   - [Lab 1 Prompt Examples & Interactive Flows](#lab-1-prompt-examples--interactive-flows)
3. [Lab 2: Tool-Augmented Autonomous Agent](#-lab-2-tool-augmented-autonomous-agent)
   - [The 3 Core Domain Tools](#the-3-core-domain-tools)
   - [Dynamic Semantic File Discovery & Typo Tolerance](#dynamic-semantic-file-discovery--typo-tolerance)
   - [Lab 2 Prompt Examples & Interactive Flows](#lab-2-prompt-examples--interactive-flows)
4. [Quick Start & Setup](#-quick-start--setup)
5. [Automated Test Suite](#-automated-test-suite)
6. [Repository Structure](#-repository-structure)

---

## 🏛️ Core Principles & Architecture

```
                                  USER REQUEST
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
       [ Lab 1: Planner Agent ]                     [ Lab 2: Tool Agent ]
    • Zero Assumptions / Inventions             • 0 Token Local Computations ($0 API)
    • Multi-Turn State Persistence              • Dual-Engine PDF + OCR Fallback
    • Mathematical Contradiction Detection      • Excel / CSV / JSON Ingestion
    • Strict Date Precision Validation          • Deterministic Domain Calculators
    • Structured Pydantic ExamPlan              • Multi-Tool Autonomous Chaining
```

---

## 🔬 Lab 1: Multi-Turn Planning & Clarification Agent

### Core Concept: Chatbot vs. Agent
* **A standard Chatbot** guesses, invents, or hallucinates missing parameters (e.g., arbitrarily picking passing marks as 40%, inventing an exam date, or assuming question structures).
* **Our Lab 1 Agent** enforces the **Zero-Assumption Principle**:
  1. **Strict Rejection of Guesses**: The agent refuses to finalize a plan until all required parameters are explicitly provided by faculty.
  2. **Multi-Turn State Tracking**: Preserves accumulated state across turns without losing prior facts.
  3. **Contradiction Detection**: Dynamically spots mathematical conflicts (e.g., Total marks = 60, but user specifies 120 MCQs $\times$ 1 mark = 120 marks).
  4. **Strict Date Precision**: Rejects vague bare months (`"in September"`) and demands an exact day and month.
  5. **Marks Balancing**: Mathematically enforces $\sum (\text{question count} \times \text{marks}) == \text{total marks}$.

### The 9 Mandatory Parameters

| # | Parameter | Description | Validation Rule |
|---|---|---|---|
| 1 | `course_code` | e.g., `CS301`, `24ECAC203` | Required string |
| 2 | `course_name` | e.g., `Operating Systems`, `Agentic AI` | Required string |
| 3 | `exam_date` | Examination date | Must contain exact day and month (e.g., `2026-09-15`). Bare months (`"September"`) are rejected. |
| 4 | `delivery_window` | Access window | e.g., `10:00 AM - 01:00 PM` |
| 5 | `duration_minutes` | Exam duration | Integer $\ge 15$ mins |
| 6 | `total_marks` | Maximum marks | Float $\ge 1.0$ |
| 7 | `passing_marks` | Minimum passing score | Must satisfy $\text{passing\_marks} \le \text{total\_marks}$ |
| 8 | `section_structure` | Question breakdown | MCQs vs Subjective, counts, and marks per question |
| 9 | `eligibility_rules` | Candidate criteria | Attendance threshold (e.g., $75\%$) and fee clearance |

---

### Lab 1 Prompt Examples & Interactive Flows

#### Example 1: Handling a Vague Prompt across Multi-Turn Clarification
**Run**: `python lab1_demo.py`

**Turn 1 — User Initial Prompt:**
```text
Enter your initial exam prompt: Set up an end-semester exam for CS301 Operating Systems
```

**Agent Response (Clarification Turn #1):**
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

**Turn 2 — User Partial Input:**
```text
Your Response: Date is 2026-09-15 from 10:00 AM to 12:00 PM. Duration is 120 mins. Total marks 60, passing marks 24.
```

**Agent Response (Clarification Turn #2 — Questions dynamically reduced):**
```text
======================================================================
  CLARIFICATION TURN #2: MISSING INFORMATION REQUIRED
======================================================================
⚠️ Status: Still missing 2 required parameter(s).

Clarifying Questions for Faculty:
  1. What is the question structure (number of MCQs and descriptive questions)?
  2. What are the candidate eligibility criteria (attendance % and fee requirements)?
```

**Turn 3 — User Final Input:**
```text
Your Response: 60 MCQs of 1 mark each. Attendance 75% and fee clearance required.
```

**Agent Proposes Locked Plan:**
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

---

#### Example 2: Automatic Mathematical Contradiction Detection
**User Input:**
```text
Total marks are 60. Conduct 120 MCQs of 1 mark each.
```

**Agent Response:**
```text
🚨 CONFLICT / CONTRADICTION DETECTED:
   Conflict detected: You specified total marks as 60, but also specified 120 MCQs of 1.0 mark each (which totals 120 marks). Please confirm whether you want 60 MCQs (for 60 marks) or 120 MCQs (for 120 marks).
```

---

#### Example 3: Strict Bare Month Rejection
**User Input:**
```text
The exam will be conducted in September.
```

**Agent Response:**
```text
Clarifying Question:
  • Which specific date in September should the examination be conducted (e.g., September 15, 2026 or 2026-09-15)?
```

---

## 🛠️ Lab 2: Tool-Augmented Autonomous Agent

### The 3 Core Domain Tools

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. QuestionPoolReaderTool (src/tools/question_pool_tool.py)                 │
│    • PDF (Digital text via pypdf + Scanned/Vector via RapidOCR / PyMuPDF)   │
│    • CSV & JSON question pools                                              │
│    • Universal Question Parser (MCQs, Subjective, Marks, Topics)            │
│    • In-memory mtime cache (_PDF_CACHE) for sub-millisecond execution       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. CandidateRosterReaderTool (src/tools/eligibility_tool.py)                │
│    • CSV, JSON, and Excel (.xlsx, .xls via openpyxl)                        │
│    • Dynamic column matching (USN, Name, Branch, Attendance, Fees)          │
│    • Deterministic 3-rule eligibility engine (Attendance, Fees, Prereqs)    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. DomainCalculatorTool (src/tools/exam_compute_tool.py)                    │
│    • Mathematical marks balance verification                                │
│    • Question pool sufficiency check (MCQ count available vs required)      │
│    • Faculty grading workload & grading time computation                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Dynamic Semantic File Discovery & Typo Tolerance
The agent evaluates user prompts against available files in `data/`:
* **Typo Tolerance**: Automatically corrects `.xlxs` $\rightarrow$ `.xlsx`.
* **Semantic Token Matching**: Recognizes terms like `"Applied Materials"`, `"OS"`, `"CSE"`, `"Agentic AI"`, `"allocation"` and routes to the exact file.

---

### Lab 2 Prompt Examples & Interactive Flows

#### Example 1: Reading Excel Allocation Spreadsheet (`Applied Materials -- Lab Allocation.xlsx`)
**Run**: `python lab2_demo.py` $\rightarrow$ Option `4`

**User Input:**
```text
Go throught this Applied Materials -- Lab Allocation.xlxs and count the number of sstudents
```

**Agent Execution Output:**
```text
🔀 Execution Flow:
   User Request -> Agent -> Candidate Roster Reader using 'data/Applied Materials -- Lab Allocation.xlsx' -> Agent -> Verified Result

🛠️ Tools Invoked: CandidateRosterReaderTool
📁 Files Discovered & Selected:
{
  "question_pool_file": null,
  "candidate_roster_file": "data/Applied Materials -- Lab Allocation.xlsx"
}

🤖 Verified Agent Response:
Verified Report for Request:
'Go throught this Applied Materials -- Lab Allocation.xlxs and count the number of sstudents'

[CANDIDATE ROSTER] Candidate Roster Verification (Applied Materials -- Lab Allocation.xlsx):
  • File Format: EXCEL
  • Total Students Evaluated / Counted: 256 students
  • Eligible Students: 256 students
  • Disqualified Students: 0 students
```

---

#### Example 2: PDF Ingestion & Question Pool Sufficiency Check
**User Input:**
```text
Read the OS question bank. Check whether the question pool contains enough 1 mark questions to conduct a 60 mark exam.
```

**Agent Execution Output:**
```text
🔀 Execution Flow:
   User Request -> Agent -> Question Pool Reader using 'data/os_questions.pdf' -> Agent -> Verified Result

🛠️ Tools Invoked: QuestionPoolReaderTool

🤖 Verified Agent Response:
[QUESTION POOL] Question Pool Verification (os_questions.pdf):
  • Course: CS301
  • Pages Processed & Verified: 12 page(s)
  • Extraction Status: VERIFIED_COMPLETE
  • Total Questions Extracted: 100
  • MCQs Available: 40 (Total Marks in Pool: 640.0)
  • Subjective Questions: 60
  • Syllabus Topics: CPU Scheduling, Deadlocks, Memory Management, Operating Systems Core, Process Synchronization, Processes & System Calls
  • Sufficiency Check for 60 Marks (1-mark MCQs): [SHORTAGE] (Pool contains 40 MCQs; 20 additional 1-mark questions required to conduct a 60-mark all-MCQ exam)
```

---

#### Example 3: Full Multi-Tool Chaining (PDF + Excel + Domain Calculator)
**User Input:**
```text
Read the OS question bank and Applied Materials allocation. Check whether the question pool contains enough 1 mark questions to conduct a 60 mark exam and count the students from the Excel file.
```

**Agent Execution Output:**
```text
🔀 Execution Flow:
   User Request -> Agent -> Question Pool Reader ('data/os_questions.pdf') -> Candidate Roster Reader ('data/Applied Materials -- Lab Allocation.xlsx') -> Domain Calculator / Checker -> Agent -> Verified Result

🛠️ Tools Invoked: QuestionPoolReaderTool, CandidateRosterReaderTool, DomainCalculatorTool

[QUESTION POOL] Question Pool Verification (os_questions.pdf):
  • Total Questions Extracted: 100 (40 MCQs, 60 Subjective)
  • Sufficiency Check: [SHORTAGE] (Pool contains 40 MCQs; 20 additional required)

[CANDIDATE ROSTER] Candidate Roster Verification (Applied Materials -- Lab Allocation.xlsx):
  • File Format: EXCEL
  • Total Students Evaluated / Counted: 256 students

[DOMAIN CHECK] Domain Calculation & Feasibility Check:
  • Mathematical Marks Balance: [MISMATCH]
  • Estimated Faculty Grading Time: 0.0 minutes
```

---

## 🚀 Quick Start & Setup

### 1. Prerequisites & Installation
Clone this repository and install the dependencies:
```bash
git clone https://github.com/<YOUR-USERNAME>/<YOUR-REPO>.git
cd <YOUR-REPO>
pip install -r requirements.txt
```

### 2. Configure Environment (Optional for Local Mode)
Create a `.env` file in the root folder:
```env
AI_PROVIDER=groq
GROQ_API_KEY=your_api_key_here
```
*(Note: If no API key is provided, the system seamlessly operates on its deterministic local engine with 100% functionality).*

### 3. Run Interactive Demos
* **Lab 1 Demo (Multi-Turn Planner Loop)**:
  ```bash
  python lab1_demo.py
  ```
* **Lab 2 Demo (Tool-Augmented Autonomous Agent)**:
  ```bash
  python lab2_demo.py
  ```

---

## 🧪 Automated Test Suite

Run the full automated pytest suite:
```bash
python -m pytest tests/ -v
```

**Results (13 of 13 tests passing — 100% success rate):**
```text
tests/test_lab1_planner.py::test_lab1_vague_prompt_generates_at_least_two_clarifying_questions PASSED [  7%]
tests/test_lab1_planner.py::test_lab1_contradiction_detection_between_marks_and_questions PASSED [ 15%]
tests/test_lab1_planner.py::test_lab1_bare_month_rejected_until_exact_day_provided PASSED [ 23%]
tests/test_lab1_planner.py::test_lab1_multi_turn_clarification_accumulates_state_without_invention PASSED [ 30%]
tests/test_lab1_planner.py::test_lab1_propose_plan_marks_balance PASSED  [ 38%]
tests/test_lab2_tools.py::test_lab2_question_pool_reader_configurable_paths PASSED [ 46%]
tests/test_lab2_tools.py::test_lab2_candidate_roster_reader_configurable_paths PASSED [ 53%]
tests/test_lab2_tools.py::test_lab2_strict_file_rejection_no_fallbacks PASSED [ 61%]
tests/test_lab2_tools.py::test_lab2_domain_calculator_with_configurable_sources PASSED [ 69%]
tests/test_lab2_tools.py::test_lab2_agent_invokes_tools_with_configurable_paths_and_logs_audit PASSED [ 76%]
tests/test_lab2_tools.py::test_lab2_semantic_file_selection_for_os_and_agentic_ai PASSED [ 84%]
tests/test_lab2_tools.py::test_lab2_natural_language_request_dynamic_discovery_and_flow PASSED [ 92%]
tests/test_lab2_tools.py::test_lab2_excel_roster_support_and_applied_materials_matching PASSED [100%]
```

---

## 📁 Repository Structure

```
├── data/                       # Directory for question pools & rosters (kept empty in Git)
│   └── .gitkeep
├── src/
│   ├── config.py               # LLM Provider & Client Setup (Groq / Gemini / Local)
│   ├── models/
│   │   ├── exam_plan.py        # Typed ExamPlan, ExamSectionSpec, EligibilityCriteria
│   │   └── student.py          # StudentEligibilityRecord, EligibilityCheckResult, QuestionPoolStats
│   ├── tools/
│   │   ├── question_pool_tool.py # PDF (Text + OCR), CSV, JSON Question Reader
│   │   ├── eligibility_tool.py   # CSV, JSON, Excel (.xlsx, .xls) Roster Reader
│   │   └── exam_compute_tool.py  # Domain Calculator & Feasibility Checker
│   ├── lab1/
│   │   └── planner_agent.py    # Zero-Invention Multi-Turn Exam Planner Agent
│   └── lab2/
│       └── tool_agent.py       # Autonomous Tool-Augmented Orchestrator Agent
├── tests/
│   ├── test_lab1_planner.py    # 5 Lab 1 Verification Unit Tests
│   └── test_lab2_tools.py      # 8 Lab 2 Tool Verification Unit Tests
├── lab1_demo.py                # Interactive CLI for Lab 1
├── lab2_demo.py                # Interactive 6-Option CLI for Lab 2
├── LAB1_EXPLANATION.md         # Detailed Lab 1 Technical Deep-Dive
├── LAB2_EXPLANATION.md         # Detailed Lab 2 Technical Deep-Dive
├── requirements.txt            # Python Dependencies
└── README.md                   # Team-wide Comprehensive Guide
```
