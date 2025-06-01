"""
python test_initial_assessment_grader.py  path/to/Phishing_bank.json
"""

import json, random, sys, requests, datetime, pathlib

GRADER_URL = "http://localhost:8000/grade"
NUM_MCQ, NUM_ESSAY = 2, 1
random_answers = True

def load_bank(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def sample_q(bank):
    mcq   = [q for q in bank if q["type"]=="mcq"]
    essay = [q for q in bank if q["type"]=="essay"]
    import random
    return random.sample(mcq, min(NUM_MCQ,len(mcq))) + \
           random.sample(essay, min(NUM_ESSAY,len(essay)))

def fill(qs):
    for q in qs:
        if random_answers and q["type"]=="mcq":
            q["user_answer"] = random.choice(["A","B","C","D"])
        elif random_answers:
            q["user_answer"] = "I wouldn't do anything"
        else:
            q["user_answer"] = ""
    return qs

def build_payload(qs):
    questions_payload = []
    for q in qs:
        # For MCQ, transform choices dict into a list [A, B, C, D]
        choices_list = None
        if q["type"] == "mcq":
            # q["choices"] is a dict {"A": "...", "B": "...", "C": "...", "D": "..."}
            # We extract in order A, B, C, D
            choices_list = [
                q["choices"].get("A"),
                q["choices"].get("B"),
                q["choices"].get("C"),
                q["choices"].get("D")
            ]

        questions_payload.append({
            "id": q["question_id"],
            "type": q["type"],
            "stem": q["stem"],
            "choices": choices_list,            # now a list or None
            "user_answer": q["user_answer"],
            "correct_choice": q.get("correct_choice"),
            "rubric": q.get("rubric")
        })

    return {
        "assessment_id": "IA-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"),
        "questions": questions_payload
    }


def main():
    bank = load_bank(pathlib.Path(sys.argv[1])) if len(sys.argv)>1 else []
    payload = build_payload(fill(sample_q(bank)))
    print("Payload →", json.dumps(payload, indent=2))
    r = requests.post(GRADER_URL, json=payload, timeout=60)
    try:
        resp_json = r.json()
        print("\nLLM response ({}):\n".format(r.status_code),
              json.dumps(resp_json, indent=2))
    except ValueError:
        print("\nNon-JSON response ({}):\n".format(r.status_code), r.text[:500])


if __name__ == "__main__":
    main()
