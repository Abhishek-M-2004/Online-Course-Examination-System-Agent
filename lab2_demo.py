"""
Interactive CLI Demo for Lab 2: Tool-Using Agent with Configurable File Paths.
Demonstrates the explicit flow:
Agent -> Tool Invocation -> External Data / Computation -> Verified Result -> Agent
"""
import os
import json
from src.lab2.tool_agent import ToolAugmentedExamAgent
from src.models.exam_plan import ExamPlan, ExamSectionSpec, EligibilityCriteria

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def print_banner(text: str):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_tool_execution(tool_name: str, target_data: str, inputs: dict, verified_output: dict):
    print("\n" + "-" * 60)
    print(f"🔧 STEP 1: AGENT DECIDES TOOL CALL -> [{tool_name}]")
    print(f"📂 STEP 2: TOOL ACCESSES EXTERNAL DATA -> {target_data}")
    print(f"📥 STEP 3: TOOL INPUT PARAMETERS -> {json.dumps(inputs, indent=2)}")
    print(f"📊 STEP 4: VERIFIED RETURNED RESULT (NO LLM GUESSWORK):")
    print(json.dumps(verified_output, indent=2))
    print(f"🤖 STEP 5: AGENT GROUNDS RESPONSE ON VERIFIED DATA")
    print("-" * 60)


def list_available_data_files():
    if not os.path.exists(DATA_DIR):
        return []
    return sorted(os.listdir(DATA_DIR))


def main():
    agent = ToolAugmentedExamAgent()
    print_banner("LAB 2: TOOL-USING AGENT (CONFIGURABLE FILE PATHS)\n  External Data Access & Deterministic Computation")
    print("Guiding Principle: No hard-coded file names or fallbacks.")
    print("All file paths are validated against the filesystem dynamically.\n")

    available_files = list_available_data_files()
    print("Available files in data/ directory:")
    for f in available_files:
        print(f"  • data/{f}")

    while True:
        print("\nChoose a Lab 2 Demonstration Mode:")
        print("  1. Tool 1: Read Question Bank (Specify any .pdf, .json, or .csv file)")
        print("  2. Tool 2: Evaluate Student Roster (Specify any .csv or .json file)")
        print("  3. Tool 3: Run Domain Calculator (Specify question pool and roster files)")
        print("  4. Natural Language Mode (Type custom query with configurable datasets)")
        print("  5. Error Handling Test: Provide missing / unsupported file to verify strict rejection")
        print("  6. Inspect Immutable Tool Audit Trail")
        print("  0. Exit")

        choice = input("\nEnter choice [0-6]: ").strip()

        if choice == "0":
            print("\nExiting Lab 2 Demo. Goodbye!")
            break

        elif choice == "1":
            print_banner("DEMO 1: QUESTION POOL READER TOOL (CONFIGURABLE FILE)")
            print("Examples: 'data/Agentic_AI_Questions.pdf', 'data/question_pool.json', 'data/question_pool.csv'")
            file_input = input("Enter question pool file path [default: data/Agentic_AI_Questions.pdf]: ").strip()
            pool_path = file_input or "data/Agentic_AI_Questions.pdf"
            course = input("Enter course code filter (optional, e.g. 24ECAC203 or CS301): ").strip() or None

            try:
                result = agent.call_question_pool_reader(source_path=pool_path, course_code=course)
                print_tool_execution(
                    tool_name="QuestionPoolReaderTool",
                    target_data=f"{result['source_file']} ({result['format']}) at {result['resolved_path']}",
                    inputs={"source_path": pool_path, "course_code": course},
                    verified_output=result["stats"],
                )
                print(f"\n📋 Parsed {len(result['questions'])} structured questions:")
                for q in result["questions"]:
                    print(f"  • [{q['id']}] [{q['type']}] ({q['marks']} marks) Topic: {q['topic']}")
                    print(f"    Q: {q['question']}")
                    if q.get("options"):
                        print(f"    Options: {q['options']} | Answer: {q.get('correct_answer')}")
            except Exception as e:
                print(f"\n❌ Error from Tool: {e}")

        elif choice == "2":
            print_banner("DEMO 2: CANDIDATE ROSTER & ELIGIBILITY TOOL (CONFIGURABLE FILE)")
            print("Examples: 'data/6th_Sem_CSE_Students.csv', 'data/student_roster.csv', 'data/student_roster.json'")
            file_input = input("Enter student roster file path [default: data/6th_Sem_CSE_Students.csv]: ").strip()
            roster_path = file_input or "data/6th_Sem_CSE_Students.csv"
            course = input("Enter course code filter (optional, e.g. 24ECAC203 or CS301): ").strip() or None
            att_input = input("Enter minimum attendance cutoff [default: 75.0%]: ").strip()
            min_att = float(att_input) if att_input else 75.0
            fee_input = input("Require fee clearance? (y/n) [default: y]: ").strip().lower()
            req_fee = False if fee_input == "n" else True

            try:
                result = agent.call_candidate_roster_reader(
                    source_path=roster_path, course_code=course, min_attendance=min_att, require_fees=req_fee
                )
                res_data = result["result"]
                print_tool_execution(
                    tool_name="CandidateRosterReaderTool",
                    target_data=f"{result['source_file']} ({result['format']}) at {result['resolved_path']}",
                    inputs={"source_path": roster_path, "course_code": course, "min_attendance": min_att, "require_fees": req_fee},
                    verified_output={
                        "total_evaluated": res_data["total_candidates_evaluated"],
                        "eligible_count": res_data["eligible_count"],
                        "disqualified_count": res_data["ineligible_count"],
                        "ambiguous_count": res_data["ambiguous_count"],
                        "summary": res_data["summary_report"],
                    },
                )
                print(f"\n👥 Disqualified Students (Calculated deterministically):")
                for dis in res_data["disqualified_students"]:
                    print(f"  ❌ {dis['name']} ({dis['student_id']}): {', '.join(dis['reasons'])}")

                if res_data["ambiguous_students"]:
                    print(f"\n⚠️ Flagged for Faculty Review:")
                    for amb in res_data["ambiguous_students"]:
                        print(f"  ⚠️ {amb['name']} ({amb['student_id']}): {amb['reason']}")
            except Exception as e:
                print(f"\n❌ Error from Tool: {e}")

        elif choice == "3":
            print_banner("DEMO 3: DOMAIN CALCULATOR / CHECKER TOOL")
            pool_input = input("Enter question pool file path [default: data/Agentic_AI_Questions.pdf]: ").strip()
            pool_path = pool_input or "data/Agentic_AI_Questions.pdf"
            roster_input = input("Enter candidate roster file path [default: data/6th_Sem_CSE_Students.csv]: ").strip()
            roster_path = roster_input or "data/6th_Sem_CSE_Students.csv"

            plan = ExamPlan(
                course_code="24ECAC203",
                course_name="Agentic AI",
                exam_date="2026-09-15",
                delivery_window="09:00 AM - 12:00 PM",
                duration_minutes=60,
                total_marks=12.0,
                passing_marks=5.0,
                sections=[
                    ExamSectionSpec(
                        section_name="Section A: Objective Questions",
                        section_type="MCQ",
                        question_count=2,
                        marks_per_question=1.0,
                        total_section_marks=2.0,
                        topics_covered=["LLM Architectures", "Prompt Engineering"],
                    ),
                    ExamSectionSpec(
                        section_name="Section B: Descriptive Questions",
                        section_type="Subjective",
                        question_count=1,
                        marks_per_question=10.0,
                        total_section_marks=10.0,
                        topics_covered=["RAG & Agents"],
                    ),
                ],
            )

            try:
                calc_result = agent.call_domain_calculator(plan, pool_source=pool_path, roster_source=roster_path)
                print_tool_execution(
                    tool_name="DomainCalculatorTool",
                    target_data=f"Computed from '{pool_path}' and '{roster_path}'",
                    inputs={"total_marks": plan.total_marks, "sections": len(plan.sections)},
                    verified_output={
                        "is_feasible": calc_result["is_feasible"],
                        "marks_validation": calc_result["marks_validation"],
                        "pool_verification": calc_result["pool_verification"],
                        "candidate_verification": calc_result["candidate_verification"],
                        "workload_computation": calc_result["workload_computation"],
                    },
                )
            except Exception as e:
                print(f"\n❌ Error from Tool: {e}")

        elif choice == "4":
            print_banner("DEMO 4: NATURAL LANGUAGE TOOL-CALLING (DYNAMIC FILE DISCOVERY)")
            available = agent.get_available_data_files()
            print("Files available in data/ directory for the agent:")
            print(f"  • Question Pools: {', '.join(available['question_pools'])}")
            print(f"  • Candidate Rosters: {', '.join(available['candidate_rosters'])}")
            print("\nExample requests you can try:")
            print("  • 'Read the OS question bank and student roster. Check whether the question pool contains enough 1 mark questions to conduct a 60 mark exam, and count the number of students from the CSV file. Report the verified results.'")
            print("  • 'Go through Applied Materials -- Lab Allocation.xlsx and count the number of students'")
            print("  • 'Check eligibility of 24ECAC203 students in 6th_Sem_CSE_Students.csv with 75% attendance criteria'")
            print("  • 'What questions and topics are available in Agentic_AI_Questions.pdf?'")

            query = input("\nEnter your request: ").strip()
            if query:
                try:
                    response = agent.process_natural_language_request(query)
                    if response.get("needs_clarification"):
                        print(f"\n❓ Clarification Required by Agent:")
                        print(f"   {response['clarification_question']}")
                    else:
                        print(f"\n🔀 Execution Flow:\n   {response.get('flow', '')}")
                        print(f"\n🛠️ Tools Invoked: {', '.join(response.get('tools_called', []))}")
                        if response.get("files_used"):
                            print(f"📁 Files Discovered & Selected:\n{json.dumps(response['files_used'], indent=2)}")
                        print(f"\n🤖 Verified Agent Response:\n{response.get('response_text', '')}")
                except Exception as e:
                    print(f"\n❌ Error: {e}")

        elif choice == "5":
            print_banner("DEMO 5: STRICT ERROR HANDLING & REJECTION")
            print("Testing 1: Non-existent file 'data/non_existent_exam.pdf'...")
            try:
                agent.call_question_pool_reader(source_path="data/non_existent_exam.pdf")
            except Exception as e:
                print(f"✅ Correctly caught error: {e}")

            print("\nTesting 2: Unsupported file extension 'data/notes.docx'...")
            try:
                agent.call_question_pool_reader(source_path="data/notes.docx")
            except Exception as e:
                print(f"✅ Correctly caught error: {e}")

        elif choice == "6":
            print_banner("LAB 2 TOOL AUDIT LOG (IMMUTABLE TRACE)")
            if not agent.tool_audit_log:
                print("No tool calls recorded yet in this session.")
            else:
                for idx, log in enumerate(agent.tool_audit_log, 1):
                    print(f"[{idx}] {log['timestamp']} | Tool: {log['tool']}")
                    print(f"    Args: {json.dumps(log['arguments'])}")
                    print(f"    Output: {log['result_summary']}\n")


if __name__ == "__main__":
    main()
