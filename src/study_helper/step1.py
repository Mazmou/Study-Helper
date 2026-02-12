import json
from pathlib import Path
from .paths import PROJECT_ROOT, DATA_DIR
from jsonschema import Draft202012Validator
import logging 
from textwrap import dedent
import requests
import time
import re
import random

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
#MODEL = "phi3:mini"
#NUM_QUESTIONS = 5

QUIZ_SCHEMA = {
    "type": "object",
    "required": ["questions"],
    "additionalProperties": False,
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["question", "options", "correct_index", "correct_answer", "evidence"],
                "additionalProperties": False,
                "properties": {
                    "question": {"type": "string", "minLength": 1},
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {"type": "string", "minLength": 1, "maxLength": 120},
                    },
                    "correct_index": {"type": "integer", "minimum": 0, "maximum": 3},
                    "correct_answer": {"type": "string", "minLength": 1, "maxLength": 100},
                    "evidence": {"type": "string", "minLength": 1, "maxLength":  400 },
                },
            },
        }
    },
}

validator = Draft202012Validator(QUIZ_SCHEMA)


def call_ollama(prompt: str, AIspecs: dict) -> str:
    payload = {
        "model": AIspecs["model"],
        "prompt": prompt,
        "stream": False,
        "format": QUIZ_SCHEMA,
        "options": {"temperature": AIspecs["temp"]},
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=180)
    r.raise_for_status()
    data = r.json()

    if "response" not in data:
        logger.error(f"Unexpected Ollama response keys: {list(data.keys())}")
        raise ValueError(f"Unexpected Ollama response keys: {list(data.keys())}")

    return data["response"]

def build_prompt(study_text: str, num_questions: int) -> str:
    return dedent(f"""
    You are an expert teacher, skilled in producing detailed student assessments that effectively demonstrate their learning. Your task is to create a mcq quiz for university students.

    TASK:
    Create {num_questions} multiple-choice questions (MCQ) that test ONLY the information in the STUDY MATERIAL.

    STRICT RULES:

    You are a JSON generator, not a conversational assistant.

    Output MUST be valid JSON and NOTHING ELSE.

    Do not include explanations, comments, headings, or text outside the JSON object.

    Questions must be answerable using ONLY the study material.

    Each question must include:

    question (string)

    options (array of exactly 4 strings)

    correct_index (integer 0 to 3)

    correct_answer must exactly equal options[correct_index].

    evidence (exact verbatim substring copied character-for-character from the study material) . Evidence must be 10 to 60 words.

    All options must be derived from terms or statements present in the study material.
    
    Each option must be ≤ 12 words and ≤ 80 characters, and must end at a full word (no truncation).

    You must always output exactly 4 options. If you cannot produce 4, discard the question. 

    The options array length must be 4.

    Do not always place the correct answer at index 0. Distribute correct_index across positions 0, 1, 2, and 3 when possible.

    Do not introduce new facts or concepts.

    Each question must rely on a single, contiguous part of the study material.

    If evidence cannot be copied exactly, do not generate that question.

    If no valid questions can be generated, output an empty questions array.

    Do NOT ask acronym expansion questions unless the STUDY MATERIAL explicitly contains the full expanded form.

    OUTPUT JSON SCHEMA:
    {{
    "questions": [
        {{
        "question": "…",
        "options": ["…","…","…","…"],
        "correct_index": 2 ,
        "correct_answer": "…",
        "evidence": "…"
        }}
    ]
    }}

    STUDY MATERIAL:
    \"\"\"{study_text}\"\"\"
    """).strip()


def validate_schema(parsed: dict) -> None:
    errors = sorted(validator.iter_errors(parsed), key=lambda e: list(e.path))

    if errors:
        messages = []
        for e in errors:
            path = "$"
            for p in e.path:
                if isinstance(p, int):
                    path += f"[{p!r}]"  
                else:
                    path += f".{p}"
            messages.append(f"{path}: {e.message}")
        raise ValueError("Schema validation failed:\n" + "\n".join(messages)) 

def normalize_correct_index(q: dict, *, allow_one_based: bool = True) -> None:
    """
    Ensure q['correct_index'] ends up as an int in [0, 3].
    If allow_one_based=True, accept [1..4] and convert to [0..3].
    Otherwise only accept [0..3].
    """
    if "correct_index" not in q:
        raise ValueError("Missing correct_index")

    idx = q["correct_index"]

    if isinstance(idx, bool) or not isinstance(idx, int):
        raise ValueError(f"correct_index must be an int, got {type(idx).__name__}: {idx!r}")

    if 0 <= idx <= 3:
        return

    if allow_one_based and 1 <= idx <= 4:
        q["correct_index"] = idx - 1
        return

    raise ValueError(f"correct_index out of range: {idx} (expected 0..3" +
                     (" or 1..4" if allow_one_based else "") + ")")

def normalize_quiz(parsed: dict, *, allow_one_based: bool = True) -> dict:
    questions = parsed.get("questions")
    if not isinstance(questions, list):
        raise ValueError("Missing/invalid questions array")

    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            raise ValueError(f"Question {i} is not an object")
        normalize_correct_index(q, allow_one_based=allow_one_based)

    return parsed

def normalize_quiz(parsed):

    for i in range(len(parsed["questions"])):
        index = parsed["questions"][i]["correct_index"]

        if 1 <= index <= 4:
            parsed["questions"][i]["correct_index"] -= 1
        elif 0 <= index <= 3:
            continue
        else:
            raise ValueError("Index value out of permitted range")
    return parsed

def normalize_text(s:str) -> str:
    s = s.replace("\r\n", "\n").lower()
    s = re.sub(r"[^\w\s'\n]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def validate_evidence(parsed, study_text):

    overlap_threshold=0.60
    study_norm = normalize_text(study_text)
    for i, question in enumerate(parsed["questions"]):
        evidence_raw = question.get("evidence", "")
        ans_raw = question.get("correct_answer","")

        if not evidence_raw or not evidence_raw.strip():
            raise ValueError(f"Missing 'evidence' key in question {i}")
        
        word_count = len(evidence_raw.split())
        if word_count < 10 or word_count > 60:
            raise ValueError(f"Evidence {i} must be 10 to 60 words (got {word_count})")
        
        ev_norm = normalize_text(evidence_raw)
        ans_norm = normalize_text(ans_raw)

        if ev_norm in study_norm:
            continue

        ev_tokens = [t for t in ev_norm.split() if len(t) >= 3] 
        ans_tokens = [t for t in ans_norm.split() if len(t) >= 3]

        if not ev_tokens:
            raise ValueError(f"Evidence {i} has no meaningful tokens")

        hits = sum(1 for t in ev_tokens if t in study_norm)
        ratioToText = hits / len(ev_tokens)

        hits = sum(1 for t in ans_tokens if t in ev_norm)
        ratioToAns = hits / len(ans_tokens)

        if ratioToText < overlap_threshold:
            raise ValueError(
                f"Evidence {i} seems unrelated to the text (token overlap {ratioToText:.2f} < {overlap_threshold}). Evidence: {evidence_raw}"
            )
        if ratioToAns < 0.3:
            raise ValueError(
                f"Evidence {i} seems unrelated to the answer (token overlap {ratioToAns:.2f} < 0.3). Evidence: {evidence_raw}"
            )
                
def validate_answer(parsed: dict) -> None:
    for i, q in enumerate(parsed["questions"]):

        options_raw = q.get("options", [])
        ans_raw = q.get("correct_answer", "")

        if not isinstance(options_raw, list) or len(options_raw) != 4:
            raise ValueError(f"Question {i} has invalid options: {options_raw!r}")

        if not isinstance(ans_raw, str) or not ans_raw.strip():
            raise ValueError(f"Question {i} has invalid correct_answer: {ans_raw!r}")

        ans_norm = normalize_text(ans_raw)
        options_norm = [normalize_text(o) for o in options_raw]


        match_idx = None
        for idx, optn in enumerate(options_norm):
            if optn == ans_norm:
                match_idx = idx
                break

        if match_idx is None:
            options_raw[-1] = ans_raw
            q["options"] = options_raw
            q["correct_index"] = 3
            q["correct_answer"] = options_raw[3]
            logger.info("Repaired options by injecting correct answer (question %d)", i)
            continue

        q["correct_index"] = match_idx
        q["correct_answer"] = options_raw[match_idx]

        if q["options"][q["correct_index"]] != q["correct_answer"]:
            raise ValueError(f"Answer alignment failed after repair in question {i}")

        
def shuffle_answer(question: dict) -> None:
    options = question["options"]
    correct_answer = question["correct_answer"]

    random.shuffle(options)

    if correct_answer not in options:
        raise ValueError("Correct answer disappeared after shuffle (duplicate/normalization issue)")

    question["correct_index"] = options.index(correct_answer)

    assert question["options"][question["correct_index"]] == question["correct_answer"], \
        "Shuffle corrupted correct_answer / correct_index alignment"

def shuffle_quiz(parsed: dict) -> dict:

    for q in parsed["questions"]:
        shuffle_answer(q)
    return parsed

def validate_options(parsed):

    for i, q in enumerate(parsed["questions"]):
        if not allUnique(q["options"]):
            raise ValueError(f"Options are not unique in question {i}")
        
        for j, opt in enumerate(q.get("options", [])):
            if len(opt) > 120:
                raise ValueError(f"Option too long (q{i} opt{j} len={len(opt)}): {opt!r}")
    

def allUnique(x):
    seen = set()
    return not any(i in seen or seen.add(i) for i in x)

#Temporary fix (MUST BE REMOVED LATER)
def validate_question_quality(parsed: dict) -> None:
    banned_option_phrases = (
        "all of the above",
        "none of the above",
        "both a and b",
        "all are correct",
    )

    banned_question_patterns = (
        r"\bwhat\s+protocol\s+does\s+tcp\s+use\b",
        r"\bwhat\s+protocol\s+does\s+ip\s+use\b",
        r"\bwhat\s+does\s+tcp\s+use\b",
        r"\bwhat\s+does\s+ip\s+use\b",
    )

    multi_select_cues = (
        "select all",
        "all that apply",
        "which of the following are",
        "what are the four",
        "what are the layers",
        "which layers",
    )

    for i, q in enumerate(parsed.get("questions", [])):
        qtext = (q.get("question") or "").strip().lower()
        options = [ (o or "").strip().lower() for o in q.get("options", []) ]

        # A) ban option patterns
        for o in options:
            if any(p in o for p in banned_option_phrases):
                raise ValueError(f"Bad option pattern in question {i}: {o!r}")

        # B) ban concept-inversion question templates
        for pat in banned_question_patterns:
            if re.search(pat, qtext):
                raise ValueError(f"Concept-inversion question in question {i}: {qtext!r}")

        # C) ban multi-select questions (single-answer only MVP)
        if any(cue in qtext for cue in multi_select_cues):
            raise ValueError(f"Multi-select style question in question {i}: {qtext!r}")

def generate_until_valid(study_text: str, output_dir: Path, quizSpecs: dict, AISpecs: dict):
    start = time.time()
    last_error = None

    max_attempts = quizSpecs["maxAttempts"] if "maxAttempts" in quizSpecs else (logger.info("maxAttempts not found. Defaulting to 5.") or 5)
    max_seconds = quizSpecs["maxSec"] if "maxSec" in quizSpecs else (logger.info("maxSec not found. Defaulting to 60.") or 60)
    NUM_QUESTIONS = quizSpecs["numQues"] if "numQues" in quizSpecs else (logger.info("numQues not found. Defaulting to 5.") or 5)

    for attempt in range(1, max_attempts+1):
        if time.time() - start > max_seconds:
            raise RuntimeError(f"Timed out after {max_seconds}s. Last error: {last_error}")
        
        res = call_ollama(build_prompt(study_text, NUM_QUESTIONS), AISpecs)

        if res.strip() == "":
            continue

        try: 
            parsed = normalize_quiz(json.loads(res))

            if not parsed.get("questions"):
                raise ValueError("Model returned empty questions array")
            
            validate_schema(parsed)         
            validate_evidence(parsed, study_text)
            validate_answer(parsed)
            validate_options(parsed)
            validate_question_quality(parsed)

            parsed = shuffle_quiz(parsed)

            return parsed
        
        except  Exception as e:
            last_error = e
            
            logger.warning("Attempt %d failed: %s", attempt, e)

            debug_path = output_dir / "last_raw.txt"
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            debug_path.write_text(res, encoding="utf-8")
            time.sleep(0.5)

    raise RuntimeError(f"Failed after {max_attempts} attempts. Last error: {last_error}")

def initiate_QuizGen(study_text: str, output_dir: Path, quizSpecs: dict, AISpecs: dict):

    logger.info("Starting quiz generation (model=%s, num_questions=%d)", AISpecs["model"], quizSpecs["numQues"])

    logger.info("Reading study material")
    
    logger.info("Study material loaded (%d chars)", len(study_text))

    logger.info("Calling Ollama at %s (model=%s)", OLLAMA_URL, AISpecs["model"])
    parsed = generate_until_valid(study_text, output_dir, quizSpecs, AISpecs)
    logger.info("Ollama returned (%d chars)", len(json.dumps(parsed)))

    return parsed

def initiate_QuizGen_batch(study_text: str, output_dir: Path, quizSpecs: dict, AISpecs: dict, batchSize: int = 20) -> dict:

    logger.info("Batch mode: generating %d questions in chunks of %d", batchSize, quizSpecs.get("numQues", 5))

    collected = []
    seen = set()

    while len(collected) < batchSize:
        remaining = batchSize - len(collected)
        logger.info("=========================================================================================================")
        logger.info("Need %d more questions...", remaining)

       
        batch = generate_until_valid(study_text, output_dir, quizSpecs, AISpecs)
        logger.info("Batch returned %d questions", len(batch.get("questions", [])))

        for q in batch.get("questions", []):
            ques = normalize_text(q["question"]) + "|" + normalize_text(q["evidence"])
            if ques in seen:
                continue
            seen.add(ques)
            collected.append(q)
            if len(collected) >= batchSize:
                break
    
    return {"questions": collected[:batchSize]}
