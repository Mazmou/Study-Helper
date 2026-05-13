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
        
def evaluation(engine: QuizEngine, numOfRuns: int):

    logger = logging.getLogger(__name__)

    Failures = {
        "Schema": 0,
        "Evidence": 0,
        "Answer": 0,
        "Options": 0,
        "EngineFailure": 0
    }

    correctInxDis = {0: 0, 1: 0, 2: 0, 3: 0}

    winCount = 0
    attempts = 0
    fistTry = 0

    for i in range(numOfRuns):

        logger.info(f"Run {i}")
        logger.info("=================================================")

        engine.currAttempt = 0
        engine.total_failures = {
            "Validation": 0,
            "Unexpected": 0,
            "Empty": 0,
            "Evidence": 0
        }

        try:
            parsed = engine.generate()
            attempt = engine.currAttempt

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
        "Runs": numOfRuns,
        "Success rate": round(winCount / numOfRuns * 100, 2),
        "first-Attempt%": round(fistTry / numOfRuns * 100, 2),
        "Avg attempts": attemptsAvg,
        "Failures": Failures,
        "Correct index distribution": correctInxDis
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
    
    