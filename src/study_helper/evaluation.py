from pathlib import Path
import logging
from .logging_config import setup_logging 
from .step1  import AnswerValidationError, EvidenceValidationError, OptionValidationError, QuizValidationError, SchemaValidationError, OLLAMA_URL, call_ollama, build_prompt, generate_until_valid, verificationQuiz
import json

def updateIndDix(indDict: dict):
    
    total = sum(indDict.values())
    
    if total == 0:
        return 0
    
    for key, val in indDict.items():
        indDict[key] = round(val/total*100, 2)

    return indDict

def calculateInd(parsed: dict, indDict: dict):
    
    for i in parsed["questions"]:
        indDict[i.get("correct_index", "")] += 1

    return indDict
        
def evaluation(study_text: str, output_dir: Path, quizSpecs: dict, AISpecs: dict, numOfRuns: int):
    
    setup_logging("INFO")
    logger = logging.getLogger(__name__)

    logger.info("Evaluation started with text of %d char. ", len(study_text))
    logger.info("Evaluation will be run %d times. ", numOfRuns)
    logger.info("Starting quiz generation (model=%s, num_questions=%d)", AISpecs["model"], quizSpecs.get("numQues", 5))

    
    NUM_QUESTIONS = quizSpecs["numQues"] if "numQues" in quizSpecs else (logger.info("numQues not found. Defaulting to 5.") or 5)
    

    
    Failures = {
        "Schema" : 0,
        "Evidence" : 0,
        "Answer" : 0,
        "Options" :0
        }
    correctInxDis = {
        0 : 0,
        1 : 0,
        2 : 0,
        3 : 0
    }
    
    for i in range(numOfRuns):

        didNotPass = True         
        attempts = 0
        winRate = 0
        attemptsAvg = 0

        while didNotPass and attempts <= 30:
            attempts += 1

            try:

                logger.info(f"{i} run")
                logger.info("==========================================================================")
                parsed = generate_until_valid(study_text, output_dir, quizSpecs, AISpecs)
                winCount += 1
                correctInxDis = calculateInd(parsed, correctInxDis)

            except EvidenceValidationError as e:
                logger.warning("Evidence issue: %s", e)
                Failures["Evidence"]  += 1

            except SchemaValidationError as e:
                logger.warning("Schema issue: %s", e)
                Failures["Schema"]  += 1

            except AnswerValidationError as e:
                logger.warning("Answer issue: %s", e)
                Failures["Answer"]  += 1

            except OptionValidationError as e:
                logger.warning("Options issue: %s", e)
                Failures["Options"]  += 1

            except QuizValidationError as e:
                logger.warning("Other validation issue: %s", e)
        
        winRate += 1 / attempts

        attemptsAvg +=  attempts / numOfRuns
    correctInxDis = updateIndDix(correctInxDis)
                
    evaluationDict = {

        "Runs" : numOfRuns,
        "Success rate" : winRate,
        "Avg attempts" : attemptsAvg,
        "Failures" : Failures,
        "Correct index distribution" : correctInxDis
    }

    return evaluationDict