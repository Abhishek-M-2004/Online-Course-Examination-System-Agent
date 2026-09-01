# Agentic AI Examination Planning & Tool-Augmented Verification System

An advanced Agentic AI system for multi-turn examination planning, multi-format question/roster ingestion, and deterministic domain verification.

---

## 🌟 Key Capabilities

### 1. Lab 1: Multi-Turn Planning & Clarification Agent (`src/lab1/`)
- **Zero-Invention Principle**: Strictly refuses to guess or invent missing parameters (dates, course codes, marks, or rules).
- **Multi-Turn State Tracking**: Preserves collected state across conversational turns.
- **Contradiction Detection**: Flags mathematical conflicts (e.g. Total marks vs MCQ counts).
- **Date Precision**: Rejects bare month names and requires exact dates.
- **Marks Balancing**: Mathematically validates $\sum (\text{questions} \times \text{marks}) = \text{total marks}$.

### 2. Lab 2: Tool-Augmented Agent with Universal Ingestion (`src/lab2/`, `src/tools/`)
- **0 Token Local Computations ($0 API Cost)**: All counts, checks, and parsing run locally.
- **Multi-Format Ingestion**:
  - **Question Banks**: PDFs (fast digital text + local RapidOCR fallback), CSV, JSON.
  - **Candidate Rosters**: CSV, JSON, and Excel (`.xlsx`, `.xls` via `openpyxl`).
- **Domain Calculator / Checker**: Evaluates marks balance, question pool sufficiency (e.g. 1-mark question count vs exam requirements), and faculty grading workload.
- **Dynamic File Discovery & Multi-Tool Chaining**: Automatically discovers files in `data/` and chains tools based on natural language queries.
- **Strict Error Handling & Audit Log**: No silent fallback mocks; full verification audit log.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional for Local Mode)
Create a `.env` file in the root directory:
```env
AI_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run Demos
* **Lab 1 Interactive Planner Demo**:
  ```bash
  python lab1_demo.py
  ```
* **Lab 2 Tool-Augmented Autonomous Agent Demo**:
  ```bash
  python lab2_demo.py
  ```

### 4. Run Automated Unit Tests
```bash
python -m pytest tests/ -v
```

---

## 📁 Repository Structure
```
├── data/                       # Directory for question pools & rosters (kept empty in Git)
│   └── .gitkeep
├── src/
│   ├── config.py               # LLM Client setup (Groq / Gemini / Local)
│   ├── models/                 # Strongly-typed Pydantic schemas (ExamPlan, Student, Question)
│   ├── tools/                  # Deterministic Domain Tools (QuestionPool, Roster, Calculator)
│   ├── lab1/                   # Multi-turn Exam Planner Agent
│   └── lab2/                   # Tool-Augmented Orchestrator Agent
├── tests/                      # 13 Automated unit tests (100% pass rate)
├── lab1_demo.py                # Interactive CLI for Lab 1
├── lab2_demo.py                # Interactive CLI for Lab 2
├── LAB1_EXPLANATION.md         # Detailed Lab 1 Architecture & Code Explanation
├── LAB2_EXPLANATION.md         # Detailed Lab 2 Architecture & Code Explanation
└── requirements.txt
```
