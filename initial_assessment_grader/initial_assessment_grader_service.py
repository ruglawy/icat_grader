# """
# Run with:
#     uvicorn grader_service:app --host 0.0.0.0 --port 8000
# """
#
# import json, os
# from typing import List, Optional
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel, Field
# from fastapi.responses import JSONResponse
# import ollama
# from ollama import Client
#
# # ---------- config ----------
# OLLAMA_MODEL = os.getenv("ICAT_MODEL", "llama3.2:latest")
# OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
#
# _client = Client(host=OLLAMA_HOST)
#
# # SYSTEM_PROMPT = """
# # You are *iCAT Initial-Assessment Grader v1*.
# # You receive a JSON object with an array called `questions`.
# # Each element provides:
# #   • `id`            – unique question_id
# #   • `type`          – "mcq" or "essay"
# #   • `user_answer`   – learner’s answer
# #   • `correct_choice` (MCQ only)
# #   • `rubric`          (essay only) → list of {point,value,weight}
# #
# # Grade each question:
# #   – For MCQ, `score` is 1 for correct, 0 for wrong.
# #   – For essay, compare `user_answer` against rubric items:
# #         score = Σ(value_i × weight_i) / Σ(value_i)
# #
# # Return **valid JSON ONLY** in the format:
# # {
# #   "scores":[
# #     {"id":"...", "score":0-1 float, "explanation":"one concise sentence"},
# #     ...
# #   ],
# #   "overall":{
# #     "score":float,
# #     "max_score":float,
# #     "percentage":int,
# #     "feedback":"3-5 sentence paragraph addressing strengths & weaknesses, with specific suggestions for improvement."
# #   }
# # }
# # Feedback for each question should be concise and specific. For MCQ, explain why the answer is correct or incorrect. For essay, highlight strengths and areas for improvement based on the rubric.
# # Ensure the overall score is calculated as the sum of individual scores, with a maximum score equal to the number of questions. The percentage should be rounded to the nearest integer.
# # Do not output anything else.
# # Return ONLY the raw JSON object with no markdown, no back-ticks, no explanation
# # """
# with open("SYSTEM_PROMPT_INITIAL_ASSESSMENT.txt", encoding="utf-8") as f:
#     SYSTEM_PROMPT = f.read()
#
# # ---------- Pydantic ----------
# class EssayRubric(BaseModel):
#     point: str
#     value: int = Field(..., ge=0, le=1)
#     weight: float = Field(..., ge=0, le=1)
#
# class QuestionIn(BaseModel):
#     id: str
#     type: str = Field(..., pattern="^(mcq|essay)$")
#     user_answer: str
#     correct_choice: Optional[str] = None
#     rubric: Optional[List[EssayRubric]] = None
#
# class AssessmentIn(BaseModel):
#     assessment_id: str
#     questions: List[QuestionIn]
#
# # ---------- FastAPI ----------
# app = FastAPI(title="iCAT Grader", version="1.0.0")
#
# def _prompt(payload: AssessmentIn) -> str:
#     return f"{SYSTEM_PROMPT}\nUSER_JSON:\n{payload.model_dump_json()}"
#
# def _build_messages(payload: AssessmentIn):
#     """Return a proper chat array: system instructions, then user JSON."""
#     return [
#         {
#             "role": "system",
#             "content": SYSTEM_PROMPT.strip()
#         },
#         {
#             "role": "user",
#             "content": payload.model_dump_json()
#         }
#     ]
#
# def _ask_llm(payload: AssessmentIn) -> str:
#     """Send the 2-turn chat to Ollama and return raw text."""
#     rsp = _client.chat(
#         model=OLLAMA_MODEL,
#         messages=_build_messages(payload),
#         stream=False
#     )
#     return rsp["message"]["content"]
#
# @app.post("/grade")
# def grade(assessment: AssessmentIn):
#     try:
#         raw = _ask_llm(assessment)
#         return json.loads(raw)
#     except json.JSONDecodeError:
#         return JSONResponse(
#             status_code=500,
#             content={"detail":"Model sent non-JSON", "body": raw[:300]}
#         )

import json, os, re
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from ollama import Client

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
OLLAMA_MODEL = os.getenv("ICAT_MODEL", "qwen2.5:7b")
OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
_client = Client(host=OLLAMA_HOST)

# ─────────────────────────────────────────────────────────────────────────────
#  SYSTEM PROMPT (updated)
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
<introduction>
You are *iCAT Initial-Assessment Grader v1*, a friendly security‐awareness instructor. 
You receive a JSON object with an array called `questions`. Each element provides:
  • `id`            – unique question_id
  • `type`          – "mcq" or "essay"
  • `stem`          – the question text
  • `choices`       – array of answer choices (MCQ only)
  • `user_answer`   – the learner’s answer
  • `correct_choice` (MCQ only)
  • `rubric`          (essay only) → list of {point,value,weight}
</introduction>

<instructions>
Before grading each question, thoroughly analyze the question to provide accurate feedback.

Grade each question as follows:
  – **MCQ**:  
    • If the learner’s choice matches `correct_choice`, give `score`: 1 and explanation: “Correct.”  
    • Otherwise, give `score`: 0 and a one‐sentence explanation stating exactly why **that specific chosen option** is wrong (not a generic wrong).
    • Example: “Option A is wrong because it doesn’t check the sender’s domain; the email came from a spoofed address.”
    • If `user_answer` is empty or null, assume the user's answer is incorrect and give `score`: 0 with a generic explanation like “You did not select an answer.”

  – **Essay**:  
    • Compare `user_answer` against each rubric item.  
    • Compute `score = Σ(value_i × weight_i) / Σ(value_i)` (a decimal between 0 and 1).
    • You analyze the user's answer and compare it to the rubric, if no similarities between both at all, give `score`: 0.
    • Provide a brief but friendly sentence: mention what the learner did well (rubric points they hit), what’s missing, and one concrete suggestion.
    • Example: “You nailed the use of a reputable password manager, but forgot to mention generating long passphrases or complex random strings. Consider adding this method too for strong, unique passwords.”
    • If `user_answer` is empty or null, give `score`: 0 and a friendly explanation like “You did not provide an answer.”
    • If `user_answer` is very generic like "I would follow best practice." or something similar in meaning, give `score`: 0 and a friendly explanation like “Your answer is too generic, specific details are required”
    • When giving feedback, you don't reference the rubric points as "Point A" or similar, you reference them as normal sentences.
    

</instructions>

<output_format>
Return **only** a raw JSON object (no markdown fences, no extra text) in this exact format:

{
  "scores": [
    {
      "id": "…",
      "score": 0–1 (float),
      "explanation": "Friendly, specific feedback about that answer."
    },
    …  
  ],
  "overall": {
    "score": float (sum of individual scores, e.g. 13.40),
    "max_score": float (total questions, e.g. 20.00),
    "percentage": int (rounded percentage),
    "feedback": "###:XX.XX – Brief summary paragraph: strengths, weaknesses, suggestions."
  }
}
</output_format>

<notes>
Guidelines:
  • For MCQ explanations: if correct, just “Correct.”  
    If incorrect, point out why that chosen letter is wrong (e.g., “Option A is wrong because it doesn’t check the sender’s domain; the email came from a spoofed address.”).
  • For essays: speak as a friendly teacher. Mention specifically which rubric points they nailed and which they missed (e.g., “You noted the correct URL mismatch but forgot to mention reporting to IT.”).
  • The **overall.feedback** string should provide a brief summary of strengths and about one or two areas to improve (if found) regarding both MCQ and essay questions (e.g., "You demonstrated strong phishing awareness but need to work on …”).
  • The overall feedback should be in regards of the MCQ and short-essay questions, both.
    • Ensure the overall score is calculated as the sum of individual scores, with a maximum score equal to the number of questions. The percentage should be rounded to 2 decimal places.
  • Do **not** include any other commentary or formatting—return exactly the JSON structure above.

Make your voice friendly, modern, and encouraging in the feedback, as if you’re a classroom instructor giving personalized tips.
Only return the JSON object, no extra text or formatting.
</notes>
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Pydantic models (updated to include `stem` and `choices`)
# ─────────────────────────────────────────────────────────────────────────────
class EssayRubricItem(BaseModel):
    point: str
    value: int = Field(..., ge=0, le=1)
    weight: float = Field(..., ge=0, le=1)

class QuestionIn(BaseModel):
    id: str
    type: str = Field(..., pattern="^(mcq|essay)$")
    stem: str
    choices: Optional[List[str]] = None
    user_answer: str
    correct_choice: Optional[str] = None
    rubric: Optional[List[EssayRubricItem]] = None

    @validator("choices", always=True)
    def check_choices(cls, v, values):
        if values.get("type") == "mcq":
            if not isinstance(v, list) or len(v) != 4:
                raise ValueError("MCQ must have exactly 4 choices")
        return v

    @validator("correct_choice", always=True)
    def check_correct_choice(cls, v, values):
        if values.get("type") == "mcq" and v not in ["A", "B", "C", "D"]:
            raise ValueError("MCQ must have correct_choice A-D")
        return v

class AssessmentIn(BaseModel):
    assessment_id: str
    questions: List[QuestionIn]

# ─────────────────────────────────────────────────────────────────────────────
#  FastAPI app
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="iCAT Grader", version="1.0.0")

def _strip_md_fence(text: str) -> str:
    """Remove ``` fences if present."""
    pattern = r"^```(?:json)?\s*(.*?)\s*```$"
    m = re.match(pattern, text.strip(), re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else text

def _build_messages(payload: AssessmentIn):
    """
    Build a two-turn chat:
      1) system instructions,
      2) explicit “GRADE this JSON” + the payload.
    """
    # 1) system prompt remains unchanged
    system_msg = {"role": "system", "content": SYSTEM_PROMPT.strip()}

    # 2) user message must tell the LLM: “Here is the learner’s submission; grade it.”
    grading_directive = "GRADE the following assessment JSON.  Respond with a new JSON containing only “scores” and “overall”, as specified:\n"
    user_content = grading_directive + payload.model_dump_json()
    user_msg = {"role": "user", "content": user_content}

    return [system_msg, user_msg]

def _ask_llm(payload: AssessmentIn) -> str:
    rsp = _client.chat(
        model=OLLAMA_MODEL,
        messages=_build_messages(payload),
        stream=False
    )
    return rsp["message"]["content"]

@app.post("/grade")
def grade(assessment: AssessmentIn):
    raw = _ask_llm(assessment)
    clean = _strip_md_fence(raw)
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=500,
            content={"detail": "Model still sent non-JSON", "body": clean[:300]}
        )

