from pathlib import Path
import logging

from study_helper.engine import QuizEngine
from .logging_config import setup_logging 
from .step1  import AnswerValidationError, EvidenceValidationError, OptionValidationError, SchemaValidationError, verificationQuiz

def updateIndDix(indDict: dict):
    
    total = sum(indDict.values())
    
    if total == 0:
        return indDict
    
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
        "Options" : 0,
        "EngineFailure": 0
        }
    
    correctInxDis = {
        0 : 0,
        1 : 0,
        2 : 0,
        3 : 0
    }
    
    winCount = 0
    attempts = 0
    fistTry = 0

    for i in range(numOfRuns):
        attempt = 0

        try:
            logger.info(f"{i} run")
            logger.info("==========================================================================")

            engine = QuizEngine(quizSpecs, AISpecs,verificationQuiz)
            parsed, attempt = engine.generate(study_text)

            winCount += 1
            attempts += attempt

            fistTry += 1 if attempt == 1 else 0
            correctInxDis = calculateInd(parsed, correctInxDis)
        
        except SchemaValidationError:
            Failures["Schema"] += 1

        except EvidenceValidationError:
            Failures["Evidence"] += 1

        except AnswerValidationError:
            Failures["Answer"] += 1

        except OptionValidationError:
            Failures["Options"] += 1

        except RuntimeError:
            Failures["EngineFailure"] += 1
    
    correctInxDis = updateIndDix(correctInxDis)

    attemptsAvg = attempts / winCount if winCount > 0 else 0

    evaluationDict = {

        "Runs" : numOfRuns,
        "Success rate" : round(winCount / numOfRuns * 100, 2),
        "first-Attempt%" : round(fistTry  / numOfRuns * 100, 2),
        "Avg attempts" : attemptsAvg,
        "Failures" : Failures,
        "Correct index distribution" : correctInxDis
    }

    return evaluationDict

def displayEval(evalDict: dict)-> None:

    Runs = evalDict.get("Runs", 0)
    SuccessRate = evalDict.get("Success rate", 0)
    AvgAttempts = evalDict.get("Avg attempts", 0) 
    failures = evalDict.get("Failures", {})
    CorrectIndx = evalDict.get("Correct index distribution", {})

    banner = f'''
            Runs completed : {Runs}
            Success Rate : {SuccessRate}
            Average attempts : {AvgAttempts}
            failures : 
                Schema : {failures["Schema"]}
                Evidence : {failures["Evidence"]}
                Answer : {failures["Answer"]}
                Options : {failures["Options"]}
                Engine : {failures["EngineFailure"]}
            Correct index distribution :
                1 : {CorrectIndx[0]}
                2 : {CorrectIndx[1]}
                3 : {CorrectIndx[2]}
                4 : {CorrectIndx[3]}
            '''
    print(banner)
    
    