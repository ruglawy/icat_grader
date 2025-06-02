"""
module_quiz_grader_service.py
─────────────────────────────────────────────────────────
Grades a 5-question module quiz (essay-only) using a local
Qwen-2-7B Ollama model.  Returns per-question scores +
overall feedback in JSON.

Run:   uvicorn module_quiz_grader:app --host 0.0.0.0 --port 8010
"""

import json, os, re
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from ollama import Client
from retriever import DocumentRetriever

# ─── config ────────────────────────────────────────────
OLLAMA_MODEL = os.getenv("ICAT_MODULE_MODEL", "qwen2.5:7b")
OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
_client = Client(host=OLLAMA_HOST)

DB_PATH = r"../chroma_db" #adjust based on where the db is located in the project directory
_rtr = DocumentRetriever(db_path=DB_PATH)

SYSTEM_PROMPT = """
<introduction>
You are *iCAT Module-Quiz Grader v1*, a friendly security‐awareness instructor.
You receive a JSON object with an array called `questions`. Each element provides:
  • `id`            – unique question_id
  • `stem`          – the question text
  • `user_answer`   – the learner’s answer
  • `rubric`        - list of {point,value,weight}
</introduction>

<instructions>
Before grading each question, thoroughly analyze the question to provide accurate feedback.

Grade each question as follows:

    • Compare `user_answer` against each rubric item.
    • Compute `score = Σ(value_i × weight_i) / Σ(value_i)` (a decimal between 0 and 1).
    • You analyze the user's answer and compare it to the rubric and the context given, if no similarities between them at all, give `score`: 0.
    • The context further helps in grading the user's answer, so use it wisely.
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
    "feedback": "Brief summary paragraph: strengths, weaknesses, suggestions."
  }
}
</output_format>

<notes>
Guidelines:
  • Speak as a friendly teacher. Mention specifically which rubric points they nailed and which they missed (e.g., “You noted the correct URL mismatch but forgot to mention reporting to IT.”).
  • The overall.feedback string should provide a brief summary of strengths and about one or two areas to improve (if found) (e.g., "You demonstrated strong phishing awareness but need to work on …”).
  • The overall.feedback summarizes the feedback of all the questions as well.
  • Ensure the overall score is calculated as the sum of individual scores, with a maximum score equal to the number of questions. The percentage should be rounded to 2 decimal places.
  • Do **not** include any other commentary or formatting—return exactly the JSON structure above.

Make your voice friendly, modern, and encouraging in the feedback, as if you’re a classroom instructor giving personalized tips.
Only return the JSON object, no extra text or formatting.
</notes>
"""

# ─── pydantic models ──────────────────────────────────
class RubricItem(BaseModel):
    point: str
    value: int = Field(..., ge=0, le=1)
    weight: float = Field(..., ge=0, le=1)

class QuizQuestion(BaseModel):
    id: str
    stem: str
    user_answer: str
    rubric: List[RubricItem]

class QuizIn(BaseModel):
    quiz_id: str
    module_code: str
    questions: List[QuizQuestion]

# ─── helpers ───────────────────────────────────────────
def _strip_md_fence(text: str) -> str:
    pat = r"^```(?:json)?\s*(.*?)\s*```$"
    m = re.match(pat, text.strip(), re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else text

def _augment_with_context(quiz: QuizIn, k: int = 3):
    """
    For every essay question, fetch top-k passages from the module’s
    Chroma collection and append them under '### Context'.
    """
    coll_name = f"project_{quiz.module_code}"
    if not _rtr.set_collection(coll_name):        # fall back to all_projects
        _rtr.set_collection("all_projects")

    for q in quiz.questions:
        ctx_hits = _rtr.retrieve_documents(q.stem, top_k=k)
        if isinstance(ctx_hits, str) or not ctx_hits:
            continue
        context_block = "\n\n".join(p["text"] for p in ctx_hits)
        q.stem = f"{q.stem}\n\n### Context\n{context_block}"
    return quiz

def _build_messages(payload: QuizIn):
    user_block = (
        "GRADE the following module-quiz JSON. Respond only with the "
        "JSON object specified.\n" + payload.model_dump_json()
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {"role": "user",   "content": user_block}
    ]

def _ask_llm(payload: QuizIn) -> str:
    rsp = _client.chat(
        model=OLLAMA_MODEL,
        messages=_build_messages(payload),
        stream=False
    )
    return rsp["message"]["content"]

# ─── fastapi app ───────────────────────────────────────
app = FastAPI(title="iCAT Module-Quiz Grader", version="1.0.0")

@app.post("/grade_quiz")
def grade_quiz(quiz: QuizIn):
    raw = _ask_llm(_augment_with_context(quiz))
    clean = _strip_md_fence(raw)

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Model did not return valid JSON. Got: {clean[:200]}…"
        )
