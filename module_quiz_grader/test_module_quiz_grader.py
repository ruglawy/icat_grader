# test_module_quiz.py
# ────────────────────────────────────────────────────────────
"""
Quick tester for module_quiz_grader.py
Usage:
    python test_module_quiz.py  Password_Hygiene_quiz.json
"""

import json, sys, random, requests, datetime, pathlib, textwrap as tw

GRADER_URL = "http://localhost:8000/grade_quiz"
random_answers = False         # set False for interactive mode

def load_quiz(path: pathlib.Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def fill_answers(quiz):
    for q in quiz["questions"]:
        if random_answers:
            # build a fake answer that mentions 1-2 rubric keywords
            keywords = [ri["point"].split()[0] for ri in q["rubric"]]
            picked   = random.sample(keywords, k=min(2, len(keywords)))
            q["user_answer"] = " ".join(picked) + "."
        else:
            print("\n" + tw.fill(q["stem"], 80) + "\n")
            q["user_answer"] = input("Your answer: ").strip() or "No answer."
    return quiz

def main():
    if len(sys.argv) < 2:
        print("Pass path to module-quiz JSON")
        sys.exit(1)

    quiz_path = pathlib.Path(sys.argv[1]).resolve()
    quiz      = load_quiz(quiz_path)
    quiz      = fill_answers(quiz)

    # add a unique quiz_id if missing
    if not quiz.get("quiz_id"):
        quiz["quiz_id"] = "MQ-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    print("\n=== Payload → /grade_quiz ===")
    print(json.dumps(quiz, indent=2))
    print()

    resp = requests.post(GRADER_URL, json=quiz, timeout=120)
    print(f"HTTP {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except ValueError:
        print(resp.text[:500])

if __name__ == "__main__":
    main()
