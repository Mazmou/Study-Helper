import time
import logging 
from study_helper.step1 import QuizValidationError, build_prompt, call_ollama
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class QuizEngine: 
    def __init__(self, quiz_specs: dict, ai_specs: dict, validator: Callable[[str, str], dict]):
        self.validator = validator
        self.quiz_specs = quiz_specs
        self.ai_specs = ai_specs
        self.max_attempts = quiz_specs.get("maxAttempts", 5)
        self.max_seconds = quiz_specs.get("maxSec", 60)
        self.num_questions = quiz_specs.get("numQues", 5)
        self.total_model_calls = 0
        self.total_failures = {
            "Validation": 0,
            "Unexpected": 0,
            "Empty": 0
        }
    
    def generate(self, study_text: str):
        start = time.time()
        last_error = None

        AIprompt = build_prompt(study_text, self.num_questions)

        for attempt in range(1, self.max_attempts + 1):

            if time.time() - start > self.max_seconds:
                raise RuntimeError(
                    f"Timed out after {self.max_seconds}s. Last error: {last_error}"
                )

            self.total_model_calls += 1
            res = call_ollama(
                AIprompt , 
                self.ai_specs
            )

            if not res.strip():
                logger.warning('Empty response from API')
                self.total_failures["empty"] += 1
                continue

            try:
                parsed = self.validator(res, study_text)

                questions = parsed.get("questions", [])

                if len(questions) < self.num_questions:
                    raise QuizValidationError(
                        f"Expected {self.num_questions}, got {len(questions)}"
                    )

                if len(questions) > self.num_questions:
                    parsed["questions"] = questions[:self.num_questions]

                return parsed, attempt

            except QuizValidationError as e:
                last_error = e
                logger.warning("Attempt %d failed: %s", attempt, e)
                self.total_failures["Validation"] += 1
                continue

            except Exception as e:
                last_error = e
                logger.warning("Unexpected error on attempt %d: %s", attempt, e)
                self.total_failures["Unexpected"] += 1
                continue
                    
        #if last_error:
        #    raise last_error

        raise RuntimeError(f"Failed after {self.max_attempts} attempts with unknown error.")

