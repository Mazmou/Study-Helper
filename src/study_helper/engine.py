import time
import logging 
from study_helper.step1 import QuizValidationError, build_prompt, call_ollama, EvidenceValidationError, normalize_text, similiraty_check
from typing import Callable

logger = logging.getLogger(__name__)

class QuizEngine: 
    def __init__(self, quiz_specs: dict, ai_specs: dict, validator: Callable[[str, str], dict]):
        self.validator = validator
        self.quiz_specs = quiz_specs
        self.ai_specs = ai_specs
        self.text = quiz_specs.get("study_text", "")
        self.max_attempts = quiz_specs.get("maxAttempts", 5)
        self.max_seconds = quiz_specs.get("maxSec", 60)
        self.num_questions = quiz_specs.get("numQues", 5)
        self.currAttempt = 0
        self.total_failures = {
            "Validation": 0,
            "Unexpected": 0,
            "Empty": 0,
            "Evidence": 0
        }
        self.timeToFinish = 0

    def _attempt_once(self, numQuesRemaining):

        AIprompt = build_prompt(self.text, numQuesRemaining)
        self.currAttempt += 1

        res = call_ollama(
                AIprompt , 
                self.ai_specs
            )
        
        if not res.strip():
                logger.warning('Empty response from API')
                self.total_failures["Empty"] += 1
                return None

        try:
            parsed = self.validator(res, self.text)

            questions = parsed.get("questions", [])

            if len(questions) < numQuesRemaining:
                raise QuizValidationError(
                    f"Expected {numQuesRemaining}, got {len(questions)}"
                )

            if len(questions) > numQuesRemaining:
                parsed["questions"] = questions[:numQuesRemaining]

            return parsed
        
        except EvidenceValidationError as e:
            logger.warning("Evidence error (%d) : %s", self.currAttempt, e)
            self.total_failures["Evidence"] += 1
            return None

        except QuizValidationError as e:
            logger.warning("Quiz validation error (%d) failed: %s", self.currAttempt, e)
            self.total_failures["Validation"] += 1
            return None

        except Exception as e:
            logger.warning("Unexpected error on attempt %d: %s", self.currAttempt, e)
            self.total_failures["Unexpected"] += 1
            return None
    
    def generateNormal(self):

        self.currAttempt = 0
        start = time.time()
        
        for _ in range(1, self.max_attempts + 1):

            if time.time() - start > self.max_seconds:
                raise RuntimeError(
                    f"Timed out after {self.max_seconds}s."
                )

            parsed = self._attempt_once(self.num_questions)

            if parsed is None :
                continue

            end = time.time()
            self.timeToFinish = end - start
            print(f"Time taken to end : {self.timeToFinish}")

            return parsed

        raise RuntimeError(f"Failed after {self.max_attempts} attempts with unknown error.")
    

    def generateBatch(self):

        self.currAttempt = 0
        start = time.time()

        collected = []
        seen = set()
        count = 0

        while len(collected) < self.num_questions and count < self.max_attempts :
        
            remaining = self.num_questions - len(collected)
            logger.info("=========================================================================================================")
            logger.info("Need %d more questions...", remaining)

            count += 1
            
            chunk = min(remaining, 5)
            batch = self._attempt_once(chunk)

            if batch is None:
                continue

            logger.info("Batch returned %d questions", len(batch.get("questions", [])))

            
            for q in batch.get("questions", []):
                ques = normalize_text(q["question"])
                if ques in seen or similiraty_check(collected, q):
                    logger.info(f"Filtered question : {ques}")
                    continue
                seen.add(ques)
                collected.append(q)
                if len(collected) >= self.num_questions:
                    break
                    
        self.timeToFinish = time.time() - start
        print(f"Time taken to end : {self.timeToFinish}")

        return {
            "questions": collected[:self.num_questions],
            "complete": len(collected) == self.num_questions,
            "requested": self.num_questions,
            "generated": len(collected),
            "batch_attempts": count,
        }
    
    def showStats(self):
        print(f"Number of validation failures : {self.total_failures.get('Validation', 0)}")
        print(f"Number of evidence failures : {self.total_failures.get('Evidence', 0)}")
        print(f"Number of unexpected failures : {self.total_failures.get('Unexpected', 0)}")
        print(f"Number of empty failures : {self.total_failures.get('Empty', 0)}")
