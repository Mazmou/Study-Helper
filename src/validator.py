import json
import logging 
from study_helper.step1 import OptionValidationError, normalize_quiz


class QuizValidator:
    def __init__(self, vSchema, vEvidence, vAnswer, vOptions, vQuality, shuffler):
        self.vSchema = vSchema
        self.vEvidence = vEvidence
        self.vAnswer = vAnswer
        self.vOptions = vOptions
        self.vQuality = vQuality
        self.shuffler = shuffler

    def validate(self, raw_res: str, study_text: str) -> dict:

        parsed = normalize_quiz(json.loads(raw_res))

        if not parsed.get("questions"):
            raise OptionValidationError("Model returned empty questions array")
        
        self.vSchema(parsed)         
        self.vEvidence(parsed, study_text)
        self.vAnswer(parsed)
        self.vOptions(parsed)
        self.vQuality(parsed)

        parsed = self.shuffler(parsed)

        return parsed