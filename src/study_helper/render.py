from pathlib import Path

LETTER_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}
INDEX_TO_LETTER = {v: k for k, v in LETTER_TO_INDEX.items()}

def render_quiz_terminal(quiz: dict) -> None:

    questions = quiz.get("questions", [])
    if not questions:
        print("No questions generated.")
        return

    score = 0

    for i, question in enumerate(questions, start=1):
        print(f"Q{i}." + question["question"])
        
        print(f''' 
            A){question["options"][0]}
            B){question["options"][1]}
            C){question["options"][2]} 
            D){question["options"][3]}''')

        letter_ans = input("What is your answer ? ").strip().upper()
        correct_index = question["correct_index"]

        while letter_ans not in LETTER_TO_INDEX:
            letter_ans = input("Invalid input. Enter A, B, C, or D: ").strip().upper()

        if LETTER_TO_INDEX.get(letter_ans) == question["correct_index"]:
            print("Good job! ")
            score += 1
        else:
            print("Nice try but no!")

        print("Correct answer is :      " + INDEX_TO_LETTER.get(correct_index) + ") " + question["options"][correct_index])
        print("Evidence:      " + question["evidence"])
        print("=========================================================================================================================")
    
    print(f"\nFinal score: {score}/{len(questions)}")


def render_quiz_markdown(quiz: dict, out_path: Path) -> None:

    questions = quiz.get("questions", [])
    lines = []

    if not questions:
        lines.append("_No questions generated._\n")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        return
    
    for i, q in enumerate(quiz["questions"], start=1):
        options = q["options"]
        correct_idx = q["correct_index"]
        correct_letter = INDEX_TO_LETTER[correct_idx]

        lines.append(f"## Q{i}. {q['question']}\n")
        lines.append(f"- A) {options[0]}")
        lines.append(f"- B) {options[1]}")
        lines.append(f"- C) {options[2]}")
        lines.append(f"- D) {options[3]}\n")
        lines.append(f"**Correct:** {correct_letter}) {options[correct_idx]}\n")
        lines.append(f"**Evidence:** {q['evidence']}\n")
        lines.append("---\n")
    
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")