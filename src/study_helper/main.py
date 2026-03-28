from pathlib import Path
import logging
from .logging_config import setup_logging 
from .render import render_quiz_terminal, render_quiz_markdown
from .paths import DATA_DIR, PROJECT_ROOT
import json
import argparse
from .evaluation import evaluation, displayEval
from study_helper.step1 import verificationQuiz
from study_helper.engine import QuizEngine
import sys

project_root = PROJECT_ROOT
defInput = project_root / "data" / "input2.txt"
defOuput = DATA_DIR


def main():

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
    parser.add_argument("--eval", action = 'store_true', help="Activate the Eval mode")

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
    evalMode = args.eval
  
    AIspecs = {
        "model": AImodel,
        "temp": temp
    }
    quizSpecs = {
        "numQues": numQues,
        "maxAttempts": maxAttempts,
        "maxSec": maxSec
    }


    text = input_p.read_text(encoding="utf-8-sig")

    if evalMode:
        displayEval(evaluation(text, out_dir, quizSpecs, AIspecs, 5))
        return
    
    engine = QuizEngine(quiz_specs=quizSpecs,
                        ai_specs=AIspecs,
                        validator=verificationQuiz)
    
    try:
        quiz, attemptNum = engine.generate(text)
        print(f"Quiz generated after {attemptNum}th attempt")
    except Exception as e:
        print(f"Generation failed: {e}")
        sys.exit(1)

    if write_files:
        out_dir.mkdir(parents=True, exist_ok=True)

        (out_dir / "questions.json").write_text(
            json.dumps(quiz, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        render_quiz_markdown(quiz, out_dir / "questions.md")
    
    if generate_quiz:
        render_quiz_terminal(quiz)
 
if __name__ == "__main__":

    setup_logging("INFO")
    logger = logging.getLogger(__name__)

    try:
        main()
    except Exception:
        logger.exception("Main failed")