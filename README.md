We'll be using Qwen 2.5 7b model (qwen2.5:7b)

## Initial Assessment Specifications
### Initial Assessment Question Bank
In the `initial_assessment_grader/initial_assessment_question_bank` directory, you will find several directories containing a question bank for each domain. There are two types of questions in the initial assessment: *MCQ* and *Short-essay* questions.
Each question bank is in the form of JSON file. Sample of an *MCQ* and *Short-essay* is as follows:

```json
{
      "question_id": "AD-M3-302",
      "domain": "Auth & Device",
      "difficulty": 3,
      "type": "mcq",
      "stem": "While riding the subway you notice a stranger quickly glancing at your phone as you type your PIN. They appear to angle their own camera toward your screen.",
      "choices": {
        "A": "Turn slightly, shield the screen, and continue typing",
        "B": "If possible, wait to unlock until you reach a private spot",
        "C": "Let them watch; the PIN is short anyway",
        "D": "Say your PIN out loud to confuse them"
      },
      "correct_choice": "B",
      "rubric": null
    },
{
      "question_id": "AD-T3-316",
      "domain": "Auth & Device",
      "difficulty": 3,
      "type": "essay",
      "stem": "You must share your phone temporarily with a sibling to let them use a navigation app. In 1–3 sentences, describe how you would protect your private apps and data during that time.",
      "choices": null,
      "correct_choice": null,
      "rubric": [
        {
          "point": "Enable guest mode or app lock/folder lock",
          "value": 1,
          "weight": 0.40
        },
        {
          "point": "Log out or hide sensitive apps (banking, email)",
          "value": 1,
          "weight": 0.35
        },
        {
          "point": "Supervise usage or set time limit, then review device afterward",
          "value": 1,
          "weight": 0.25
        }
      ]
    }
```

JSON file attributes explanation for the initial assessment questions:

  - `question_id`            , unique question_id
    - First part contains initials represent domain name.
      ```
      - AD -> Authentication & Device Security
      - PH -> Phishing
      - PW -> Password Hygiene
      - SB -> Safe Browsing & Public Wi-Fi
      - FI -> Financial & Payment Security
      - DP -> Data Privacy & Responsible Sharing
      ```
    - Second part is the type of question with the difficulty level (e.g., M3 -> MCQ with difficulty level 3, T5 -> Short-essay with difficulty level 5)
      ```
      -  M  -> MCQ
      -  T  -> Short-essay question
      
      -  M3 -> MCQ with difficulty level 3
      -  T5 -> Short-essay with difficulty level 5
      ```
    - Third part is the unique ID of the question.
  
  - `domain`        , name of the domain the question is coming from (e.g., Phishing, Auth & Device, Data Privacy, Financial Security, Password Hygiene, Safe Browsing)
    ```
    - Phishing
    - Auth & Device
    - Data Privacy
    - Financial Security
    - Password Hygiene
    - Safe Browsing
    ```
  
  - `difficulty`    , difficulty level (1 -> 5), most of the questions start from level 3.
  
  - `type`          , type of question
    ```
    - mcq -> MCQ
    - essay -> Short-essay question
    ```
    
  - `stem`          , the question text
  - `choices`       , dictionary of four choices (MCQ only)
  - `correct_choice` , the letter of the correct answer (e.g., A, B, C, D)
  - `rubric`        , list of {point,value,weight}, model uses it to correct the user's answer (grading schema) (Short-essay questions only)<br><br><br>


### Input & Output to and from the model
`NOTE:- For now, we will be assigning 15 MCQs and 5 short-essay questions for each assessment, randomly selected from the question banks for each user, questions are picked from all 6 domains' question banks.`<br><br>
The model receives a JSON object with attribute `assessment_id` uniquely generated for each user, and an array called `questions`. Each element in `questions` provides:

  - `id`            , unique question_id
  - `type`          , "mcq" or "essay"
  - `stem`          , the question text
  - `choices`       , array of answer choices (MCQ only)
  - `user_answer`   , the user’s answer
  - `correct_choice` , (MCQ only)
  - `rubric`         , (essay only) → list of {point,value,weight}
  
#### Sample Input to the model
```json
{
  "assessment_id": "IA-20250604-213320",
  "questions": [
    {
      "id": "PH-M2-008",
      "type": "mcq",
      "stem": "Your sister sent you an email saying \u201cNeed help; send money to this wallet.\u201d What would you do?",
      "choices": [
        "Send small amount to be safe",
        "Forward email to parents for advice",
        "Call her on the phone before doing anything",
        "Reply asking more questions over email"
      ],
      "user_answer": "A",
      "correct_choice": "C",
      "rubric": null
    },
    {
      "id": "PH-M5-018",
      "type": "mcq",
      "stem": "A loyalty-points email urges you to transfer points to a friend within 2 hours or they expire, requiring you to sign in through a page that asks for both password and security answers.",
      "choices": [
        "Sign in and move points fast",
        "Log in through the retailer\u2019s own app instead of the email link",
        "Reply asking them to extend deadline",
        "Print email as proof first"
      ],
      "user_answer": "A",
      "correct_choice": "B",
      "rubric": null
    },
    {
      "id": "PH-T3-022",
      "type": "essay",
      "stem": "A restaurant table has a laminated QR code saying \u201cleave a tip and get a surprise gift.\u201d Describe, in a few sentences, the steps you would follow before scanning and entering any payment details.",
      "choices": null,
      "user_answer": "I wouldn't do anything",
      "correct_choice": null,
      "rubric": [
        {
          "point": "Check with staff that the code belongs to the restaurant",
          "value": 1,
          "weight": 0.4
        },
        {
          "point": "Look at the web address after scanning before paying",
          "value": 1,
          "weight": 0.35
        },
        {
          "point": "Decide not to enter card data on pages you don\u2019t fully trust",
          "value": 1,
          "weight": 0.25
        }
      ]
    }
  ]
}
```


#### Sample Output from the model
```json
{
  "scores": [
    {
      "id": "PH-M2-008",
      "score": 0,
      "explanation": "Option A is wrong because sending any amount of money without verification first could be a scam."
    },
    {
      "id": "PH-M5-018",
      "score": 0,
      "explanation": "Option A is wrong because clicking on suspicious links can lead to phishing attacks where your credentials are stolen. Option B is the correct approach, as using the retailer\u2019s own app ensures a safer login process."
    },
    {
      "id": "PH-T3-022",
      "score": 0.75,
      "explanation": "You mentioned not doing anything but it would be better to take steps first: check with staff and ensure you're on their official website before making any payments."
    }
  ],
  "overall": {
    "score": 1.75,
    "max_score": 3.0,
    "percentage": 58,
    "feedback": "You demonstrated a good understanding of not taking immediate actions in phishing scenarios, but there's room for improvement by following specific steps like checking with staff and verifying the website."
  }
}
```
