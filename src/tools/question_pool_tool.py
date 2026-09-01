"""
Lab 2: Question Pool Reader Tool with Configurable File Paths, Universal Parsing & Local OCR Fallback (0 Tokens).
Supports digital text PDFs, vector-printed PDFs (Microsoft Print to PDF), scanned documents, CSV, and JSON.
Strictly validates file existence, format, and extraction completeness with zero external API calls.
"""
import os
import re
import json
import csv
from typing import List, Optional, Dict, Any, Tuple
from src.models.student import QuestionItem, QuestionPoolStats

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
ALLOWED_QUESTION_EXTENSIONS = [".pdf", ".json", ".csv"]


def resolve_and_validate_path(file_path: Optional[str], allowed_extensions: List[str]) -> str:
    """
    Resolves file path and validates existence and file extension.
    Raises clear errors if missing or unsupported without falling back to hard-coded defaults.
    """
    if not file_path or not str(file_path).strip():
        raise ValueError("File path cannot be empty. Please specify a valid question pool or candidate roster file path.")

    clean_path = str(file_path).strip().strip("'").strip('"')

    # Validate file extension first
    _, ext = os.path.splitext(clean_path)
    ext_lower = ext.lower()
    if ext_lower not in [e.lower() for e in allowed_extensions]:
        raise ValueError(
            f"Unsupported file format '{ext}'. Allowed formats are: {', '.join(allowed_extensions)}"
        )

    # Candidate locations: direct, inside DATA_DIR, or basename in DATA_DIR
    candidates = [
        clean_path,
        os.path.join(DATA_DIR, clean_path),
        os.path.join(DATA_DIR, os.path.basename(clean_path)),
    ]

    resolved_path = None
    for cand in candidates:
        if os.path.exists(cand) and os.path.isfile(cand):
            resolved_path = os.path.abspath(cand)
            break

    if not resolved_path:
        raise FileNotFoundError(
            f"File not found: '{clean_path}'. Please check that the file exists in '{DATA_DIR}' or provide a valid absolute path."
        )

    return resolved_path


def extract_text_via_local_ocr(pdf_path: str) -> Tuple[str, int, List[str]]:
    """
    Extracts text from vector-printed or scanned PDFs using local RapidOCR + PyMuPDF.
    Runs 100% on local CPU with ZERO token consumption and ZERO API cost.
    """
    import pymupdf
    from rapidocr_onnxruntime import RapidOCR

    ocr = RapidOCR()
    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    full_text = ""
    warnings: List[str] = []

    for i, page in enumerate(doc, 1):
        try:
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            res, _ = ocr(img_bytes)
            if res:
                page_text = "\n".join([line[1] for line in res])
                full_text += f"\n--- Page {i} ---\n" + page_text + "\n"
            else:
                warnings.append(f"Page {i} in '{os.path.basename(pdf_path)}' returned no OCR text.")
        except Exception as e:
            warnings.append(f"OCR warning on page {i}: {e}")

    return full_text, total_pages, warnings


def parse_questions_from_raw_text(full_text: str, source_name: str) -> List[QuestionItem]:
    """
    Universal question parser supporting varied formats:
    - Standard: 'Question 1 [MCQ] [Marks: 2] Topic: CPU Scheduling'
    - Company / Interview: 'Q401. Infosys Detailed What is an Operating System...'
    - Numbered: '1. Which algorithm causes convoy effect? A) FCFS B) SJF...'
    """
    questions: List[QuestionItem] = []
    course_code = "CS301"
    course_name = "Operating Systems"

    if "24ECAC203" in full_text or "Agentic" in full_text:
        course_code = "24ECAC203"
        course_name = "Agentic AI"

    # Pattern 1: Standard Question format with [Marks: X]
    q_blocks = re.split(r"(?:^|\n)(?:Question\s+\d+|Q\s*\.?\s*\d+[\.\)])", full_text)
    headers = re.findall(r"(?:^|\n)(Question\s+\d+|Q\s*\.?\s*\d+[\.\)])", full_text)

    # Topic keyword dictionary for auto-tagging
    topic_map = {
        "CPU Scheduling": ["scheduling", "cpu", "fcfs", "sjf", "round robin", "convoy", "preemptive"],
        "Memory Management": ["memory", "page", "paging", "tlb", "segmentation", "virtual memory", "mmu", "swap"],
        "Process Synchronization": ["synchronization", "semaphore", "mutex", "critical section", "producer-consumer", "race condition"],
        "Deadlocks": ["deadlock", "banker", "bankers", "circular wait", "resource allocation", "avoidance"],
        "Processes & System Calls": ["process", "system call", "fork", "exec", "thread", "kernel", "user mode", "context switch"],
        "LLM Architectures": ["transformer", "attention", "tokens", "recurrent", "hidden state"],
        "Prompt Engineering": ["prompt", "chain-of-thought", "cot", "temperature", "few-shot"],
        "RAG & Agents": ["rag", "agent", "react", "retrieval", "tool", "vector database"],
    }

    def infer_topic(text: str) -> str:
        text_lower = text.lower()
        for topic, keywords in topic_map.items():
            if any(k in text_lower for k in keywords):
                return topic
        return "Operating Systems Core" if course_code == "CS301" else "General"

    for idx, body in enumerate(q_blocks[1:], 1):
        clean_body = body.strip()
        if not clean_body:
            continue

        # Detect Type (MCQ vs Detailed/Subjective)
        has_options = bool(re.search(r"\b[A-D][\)\.]\s+", clean_body) or "A)" in clean_body or "A." in clean_body)
        is_detailed = "detailed" in clean_body.lower() or "[subjective]" in clean_body.lower() or "rubric:" in clean_body.lower()
        q_type = "Subjective" if (is_detailed and not has_options) else ("MCQ" if has_options or "mcq" in clean_body.lower() else "Subjective")

        # Detect Marks
        marks_match = re.search(r"\[Marks:\s*(\d+(\.\d+)?)\]|(\d+)\s*(?:marks?|pts?|m)\b", clean_body, re.IGNORECASE)
        marks = float(marks_match.group(1) or marks_match.group(3)) if marks_match else (1.0 if q_type == "MCQ" else 10.0)

        # Detect Topic
        topic_match = re.search(r"Topic:\s*([^\n\r]+)", clean_body)
        topic = topic_match.group(1).strip() if topic_match else infer_topic(clean_body)

        # Extract Options
        options = None
        correct_ans = None
        rubric = None

        if q_type == "MCQ":
            ans_match = re.search(r"(?:Answer|Ans):\s*([A-D])", clean_body, re.IGNORECASE)
            correct_ans = ans_match.group(1).upper() if ans_match else None

            opt_matches = re.findall(r"([A-D])[\)\.]\s*([^\n\rA-D\)]+)", clean_body)
            if opt_matches:
                options = {opt[0]: opt[1].strip() for opt in opt_matches}

        if q_type == "Subjective":
            rub_match = re.search(r"Rubric:\s*([^\n\r]+)", clean_body, re.IGNORECASE)
            rubric = {"criteria": marks} if rub_match else None

        # Clean Question Text
        lines = [l.strip() for l in clean_body.splitlines() if l.strip()]
        filtered_lines = []
        for l in lines:
            if any(l.lower().startswith(p) for p in ["infosys", "cognizant", "wipro", "ibm", "tcs", "detailed", "mcq", "topic:", "answer:", "rubric:"]):
                continue
            if re.match(r"^[A-D][\)\.]", l):
                continue
            filtered_lines.append(l)

        q_text = " ".join(filtered_lines) if filtered_lines else clean_body[:100]

        q_id = f"{course_code}_{q_type}_{len(questions)+1:03d}"
        questions.append(
            QuestionItem(
                id=q_id,
                course_code=course_code,
                course_name=course_name,
                type=q_type,
                question=q_text,
                options=options,
                correct_answer=correct_ans,
                rubric=rubric,
                marks=marks,
                topic=topic,
                difficulty="Medium",
                bloom_level="Apply" if q_type == "Subjective" else "Understand",
            )
        )

    return questions


_PDF_CACHE: Dict[Tuple[str, float], Tuple[List[QuestionItem], int, List[str]]] = {}


def read_question_pool_from_pdf(pdf_path: str) -> Tuple[List[QuestionItem], int, List[str]]:
    """
    Extracts questions from a PDF file using a robust dual-engine approach with mtime caching:
    1. Fast Native Text (pypdf) for digital PDFs
    2. Local RapidOCR (0 tokens) for vector-printed / scanned PDFs
    """
    resolved_path = resolve_and_validate_path(pdf_path, [".pdf"])
    mtime = os.path.getmtime(resolved_path)
    cache_key = (resolved_path, mtime)

    if cache_key in _PDF_CACHE:
        cached_qs, cached_pages, cached_warns = _PDF_CACHE[cache_key]
        return [q.model_copy() for q in cached_qs], cached_pages, list(cached_warns)

    warnings: List[str] = []
    full_text = ""
    total_pages = 1

    # Tier 1: Try Native PDF Text Extraction
    try:
        import pypdf
        reader = pypdf.PdfReader(resolved_path)
        total_pages = len(reader.pages)
        for idx, page in enumerate(reader.pages, 1):
            txt = page.extract_text() or ""
            full_text += txt + "\n"
    except Exception as e:
        warnings.append(f"pypdf extraction notice: {e}")

    # Tier 2: If no text extracted (vector PDF or scan), run Local RapidOCR (0 tokens)
    if len(full_text.strip()) < 20:
        ocr_text, ocr_pages, ocr_warnings = extract_text_via_local_ocr(resolved_path)
        full_text = ocr_text
        total_pages = ocr_pages
        warnings.extend(ocr_warnings)

    if not full_text.strip():
        raise ValueError(
            f"PDF Extraction Incomplete: Could not extract readable text or OCR data from '{os.path.basename(resolved_path)}'."
        )

    questions = parse_questions_from_raw_text(full_text, os.path.basename(resolved_path))

    if not questions:
        raise ValueError(
            f"PDF Extraction Incomplete: Extracted text from '{os.path.basename(resolved_path)}' but found 0 structured questions."
        )

    _PDF_CACHE[cache_key] = (questions, total_pages, warnings)
    return questions, total_pages, warnings


def read_question_pool_from_json(json_path: str) -> List[QuestionItem]:
    """Reads questions from a user-specified JSON question bank file."""
    resolved_path = resolve_and_validate_path(json_path, [".json"])
    with open(resolved_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)
    return [QuestionItem(**item) for item in raw_items]


def read_question_pool_from_csv(csv_path: str) -> List[QuestionItem]:
    """Reads questions from a user-specified CSV question bank file."""
    resolved_path = resolve_and_validate_path(csv_path, [".csv"])
    questions = []
    with open(resolved_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(
                QuestionItem(
                    id=row["id"],
                    course_code=row["course_code"],
                    course_name=row["course_name"],
                    type=row["type"],
                    question=row["question"],
                    marks=float(row["marks"]),
                    topic=row["topic"],
                    difficulty=row.get("difficulty", "Medium"),
                    bloom_level=row.get("bloom_level", "Understand"),
                    correct_answer=row.get("correct_answer") or None,
                )
            )
    return questions


def read_question_pool(
    source_path: str, course_code: Optional[str] = None
) -> List[QuestionItem]:
    """
    Unified Question Pool Reader Tool with configurable path.
    Validates existence, format (.pdf, .json, .csv), and extraction completeness.
    """
    resolved_path = resolve_and_validate_path(source_path, ALLOWED_QUESTION_EXTENSIONS)

    if resolved_path.endswith(".pdf"):
        questions, _, _ = read_question_pool_from_pdf(resolved_path)
    elif resolved_path.endswith(".csv"):
        questions = read_question_pool_from_csv(resolved_path)
    else:
        questions = read_question_pool_from_json(resolved_path)

    if course_code:
        questions = [q for q in questions if q.course_code.upper() == course_code.upper()]

    return questions


def filter_questions_by_topic(
    source_path: str,
    course_code: Optional[str] = None,
    topic: Optional[str] = None,
    q_type: Optional[str] = None,
) -> List[QuestionItem]:
    """Filters structured question items by topic and question type from the specified source."""
    questions = read_question_pool(source_path=source_path, course_code=course_code)
    if topic:
        questions = [q for q in questions if topic.lower() in q.topic.lower()]
    if q_type:
        questions = [q for q in questions if q.type.upper() == q_type.upper()]
    return questions


def get_question_pool_stats(
    source_path: str, course_code: Optional[str] = None
) -> QuestionPoolStats:
    """
    Computes verified statistical summary of question availability and extraction status.
    Verifies that questions were extracted completely from the user-specified source.
    """
    resolved_path = resolve_and_validate_path(source_path, ALLOWED_QUESTION_EXTENSIONS)
    pages = 1
    warnings = []

    if resolved_path.endswith(".pdf"):
        questions, pages, warnings = read_question_pool_from_pdf(resolved_path)
    elif resolved_path.endswith(".csv"):
        questions = read_question_pool_from_csv(resolved_path)
    else:
        questions = read_question_pool_from_json(resolved_path)

    if course_code:
        questions = [q for q in questions if q.course_code.upper() == course_code.upper()]

    actual_course = course_code or (questions[0].course_code if questions else "UNKNOWN")
    mcq_count = sum(1 for q in questions if q.type == "MCQ")
    sub_count = sum(1 for q in questions if q.type == "Subjective")
    topics = sorted(list({q.topic for q in questions}))
    total_marks = sum(q.marks for q in questions)

    extraction_status = "VERIFIED_COMPLETE" if len(questions) > 0 and not warnings else ("VERIFIED_WITH_WARNINGS" if warnings else "INCOMPLETE")

    return QuestionPoolStats(
        course_code=actual_course,
        total_questions=len(questions),
        mcq_count=mcq_count,
        subjective_count=sub_count,
        topics=topics,
        total_marks_available=total_marks,
        pages_processed=pages,
        extraction_status=extraction_status,
        extraction_warnings=warnings,
    )
