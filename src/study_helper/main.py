from pathlib import Path
import logging
from .logging_config import setup_logging
from .step1 import initiate_QuizGen_batch, initiate_QuizGen
from .render import render_quiz_terminal, render_quiz_markdown
from .paths import DATA_DIR, PROJECT_ROOT
import json
import argparse


project_root = PROJECT_ROOT
defInput = project_root / "data" / "input2.txt"
defOuput = DATA_DIR

def main(input_path: Path, output_path: Path, write_files: bool, terminal_quiz: bool, quizSpecs: dict, AIspecs: dict):

    text = input_path.read_text(encoding="utf-8-sig")
    quiz = initiate_QuizGen(text, output_path, quizSpecs, AIspecs)

    #if len(quiz.get("questions", [])) < 30:
    #    raise ValueError(f"Only got {len(quiz.get('questions', []))} questions, expected 30")

    if terminal_quiz:
        render_quiz_terminal(quiz)

    if write_files:
        output_path.mkdir(parents=True, exist_ok=True)

        (output_path / "questions.json").write_text(
            json.dumps(quiz, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        render_quiz_markdown(quiz, output_path / "questions.md")

if __name__ == "__main__":

    setup_logging("INFO")
    logger = logging.getLogger(__name__)

    try:
        parser = argparse.ArgumentParser(
                    prog='ProgramName',
                    description='AI powered quiz generator',
                    epilog='Thanks for using the software')

        parser.add_argument('--input', default=str(defInput), help="Path to input study text file")
        parser.add_argument('--out', default=str(DATA_DIR), help="Output directory")
        parser.add_argument('--no-quiz', action='store_true', help="Do not generate a quiz in the terminal")
        parser.add_argument('--no-write', action="store_true", help="Do not write output files")
        parser.add_argument("--model", default="phi3:mini", help="Choose what AI model to use")
        parser.add_argument("--num-questions", type=int, default=5, help="How much questions you want")
        parser.add_argument("--temperature", type=float, default=0.2)
        parser.add_argument("--max-attempts", type=int, default=8)
        parser.add_argument("--max-seconds", type=int, default=60)

        args = parser.parse_args()

        input_p = Path(args.input)
        out_dir = Path(args.out)
        generate_quiz = not args.no_quiz
        write_files = not args.no_write
        AImodel = args.model
        numQues = args.num_questions
        temp = args.temperature
        maxAttempts = args.max_attempts
        maxSec = args.max_seconds

        AIspecs = {
            "model": AImodel,
            "temp": temp
        }
        quizSpecs = {
            "numQues": numQues,
            "maxAttempts": maxAttempts,
            "maxSec": maxSec
        }

        main(input_p, out_dir, write_files, generate_quiz, quizSpecs, AIspecs)

    except Exception:
        logger.exception("Main failed")