"""
Script to create clean, standards-compliant PDF question banks with exact byte offsets.
Ensures zero xref warnings and clean extraction across all PDF parsers.
"""
import os


def build_pdf_bytes(lines):
    stream_content = "BT\n/F1 12 Tf\n50 720 Td\n"
    for idx, line in enumerate(lines):
        if idx == 0:
            stream_content += f"({line}) Tj\n"
        else:
            stream_content += f"0 -18 Td\n({line}) Tj\n"
    stream_content += "ET\n"
    stream_bytes = stream_content.encode("latin1")
    stream_len = len(stream_bytes)

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    obj4_header = f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin1")
    obj4 = obj4_header + stream_bytes + b"endstream\nendobj\n"
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    header = b"%PDF-1.4\n"
    offset1 = len(header)
    offset2 = offset1 + len(obj1)
    offset3 = offset2 + len(obj2)
    offset4 = offset3 + len(obj3)
    offset5 = offset4 + len(obj4)
    xref_offset = offset5 + len(obj5)

    xref = (
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        + f"{offset1:010d} 00000 n \n".encode("latin1")
        + f"{offset2:010d} 00000 n \n".encode("latin1")
        + f"{offset3:010d} 00000 n \n".encode("latin1")
        + f"{offset4:010d} 00000 n \n".encode("latin1")
        + f"{offset5:010d} 00000 n \n".encode("latin1")
    )
    trailer = f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin1")

    return header + obj1 + obj2 + obj3 + obj4 + obj5 + xref + trailer


def main():
    os.makedirs("data", exist_ok=True)

    # 1. OS Questions PDF
    os_lines = [
        "COURSE: CS301 Operating Systems Question Bank",
        "Question 1 [MCQ] [Marks: 2] Topic: CPU Scheduling",
        "Which scheduling algorithm may lead to the convoy effect?",
        "A. First-Come, First-Served  B. Shortest Job First  C. Round Robin  D. Priority Scheduling",
        "Answer: A",
        "Question 2 [MCQ] [Marks: 2] Topic: Memory Management",
        "What is the primary function of the Translation Lookaside Buffer?",
        "A. Store CPU instructions  B. Speed up virtual-to-physical address translation  C. Prevent deadlock  D. Manage swap",
        "Answer: B",
        "Question 3 [Subjective] [Marks: 10] Topic: Process Synchronization",
        "Explain the Producer-Consumer problem using binary and counting semaphores.",
        "Rubric: Problem Statement 3 marks, Semaphore logic 4 marks, Code trace 3 marks",
    ]
    os_bytes = build_pdf_bytes(os_lines)
    with open("data/os_questions.pdf", "wb") as f:
        f.write(os_bytes)
    with open("data/sample_exam_questions.pdf", "wb") as f:
        f.write(os_bytes)

    # 2. Agentic AI PDF
    ai_lines = [
        "COURSE: 24ECAC203 Agentic AI Question Bank",
        "Question 1 [MCQ] [Marks: 1] Topic: LLM Architectures",
        "Which mechanism allows transformers to process input tokens in parallel?",
        "A. Recurrent Hidden State  B. Multi-Head Self-Attention  C. Convolutional Filters  D. Markov Chains",
        "Answer: B",
        "Question 2 [MCQ] [Marks: 1] Topic: Prompt Engineering",
        "What is the primary benefit of Chain-of-Thought prompting in reasoning tasks?",
        "A. Reduces context length  B. Breaks complex problems into step-by-step rationales  C. Lowers temperature  D. Disables safety filters",
        "Answer: B",
        "Question 3 [Subjective] [Marks: 10] Topic: RAG & Agents",
        "Explain the ReAct framework and contrast its reasoning-acting loop with standard RAG pipelines.",
        "Rubric: ReAct Architecture 4 marks, Tool Calling Trace 3 marks, Comparison with RAG 3 marks",
    ]
    ai_bytes = build_pdf_bytes(ai_lines)
    with open("data/Agentic_AI_Questions.pdf", "wb") as f:
        f.write(ai_bytes)

    print("Clean, compliant PDFs generated with 0 xref warnings.")


if __name__ == "__main__":
    main()
