We'll be using Qwen 2.5 7b model (qwen2.5:7b)
_______
## Initial Assessment Specifications
### Initial Assessment Question Bank
In the `initial_assessment_grader/initial_assessment_question_bank` directory, you will find several directories containing a question bank for each domain. There are two types of questions in the initial assessment: *MCQ* and *Short-essay* questions.<br>
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
    - Second part is the type of question with the difficulty level
      ```
      -  M  -> MCQ
      -  T  -> Short-essay question
      
      -  M3 -> MCQ with difficulty level 3
      -  T5 -> Short-essay with difficulty level 5
      ```
    - Third part is the unique ID of the question.
  
  - `domain`        , name of the domain the question is coming from
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
  - `correct_choice` , the letter of the correct answer (e.g., A, B, C, D)
  - `rubric`         , list of {point,value,weight}, model uses it to correct the user's answer (grading schema) (Short-essay questions only)
  
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

_______

## Module Quiz Specifications
### Module Quiz Question Banks
In the `module_quiz_grader/module_quiz_question_bank` directory, you will find several directories containing a full 5-short-essay-question quiz for each module written so far. Module quizzes only have short-essay questions.<br>
Each module quiz is in the form of JSON file. Sample of a module quiz is as follows:

```json
{
  "quiz_id": "CS01-QZ-0001",
  "module_code": "CS01",
  "questions": [
    {
      "id": "CS01-T3-001",
      "stem": "A friend sends you a cracked video editor that works only if you disable your antivirus first. In 1–3 sentences, explain why this is risky and what safer choice you would make instead.",
      "rubric": [
        {"point": "Disabling protection invites hidden malware/credential-stealers bundled with cracks", "value": 1, "weight": 0.40},
        {"point": "Refuse the cracked copy and look for a legal free/trial or open-source alternative", "value": 1, "weight": 0.35},
        {"point": "Warn the friend or report the source to prevent further spread", "value": 1, "weight": 0.25}
      ],
      "difficulty": 3
    },
    {
      "id": "CS01-T4-002",
      "stem": "After installing a pirated game, your laptop fans roar and the CPU stays at 90 %. Describe, in a few sentences, what may be happening and the immediate steps you would take.",
      "rubric": [
        {"point": "Recognise possible cryptojacking/mining software hidden in the crack", "value": 1, "weight": 0.40},
        {"point": "Uninstall the cracked program and run a full malware scan or clean restore", "value": 1, "weight": 0.35},
        {"point": "Monitor system performance and avoid future untrusted downloads", "value": 1, "weight": 0.25}
      ],
      "difficulty": 4
    }
}
```

JSON file attributes explanation for the initial assessment questions:
- `quiz_id` , unique quiz ID
- `module_code` , unique module code
- `questions` , array containing the questions for that specific quiz, each element in `questions` provides:
  - `id` , unique question id
  - `stem` , the question text
  - `rubric` , list of {point,value,weight}, model uses it to correct the user's answer (grading schema)
  - `difficulty` , difficulty level of the question<br><br><br>



### Input & Output to and from the model
The model receives a JSON object with an array called `questions`. Each element provides:
  - `id`            , unique question_id
  - `stem`          , the question text
  - `user_answer`   , the user’s answer
  - `rubric`        , list of {point,value,weight}, model uses it to correct the user's answer (grading schema)

#### Sample Input to the model
```json
{
  "quiz_id": "CS01-QZ-0001",
  "module_code": "CS01",
  "questions": [
    {
      "id": "CS01-T3-001",
      "stem": "A friend sends you a cracked video editor that works only if you disable your antivirus first. In 1\u20133 sentences, explain why this is risky and what safer choice you would make instead.",
      "rubric": [
        {
          "point": "Disabling protection invites hidden malware/credential-stealers bundled with cracks",
          "value": 1,
          "weight": 0.4
        },
        {
          "point": "Refuse the cracked copy and look for a legal free/trial or open-source alternative",
          "value": 1,
          "weight": 0.35
        },
        {
          "point": "Warn the friend or report the source to prevent further spread",
          "value": 1,
          "weight": 0.25
        }
      ],
      "difficulty": 3,
      "user_answer": "This is not risky as it's a free software, nothing will go wrong."
    },
    {
      "id": "CS01-T4-002",
      "stem": "After installing a pirated game, your laptop fans roar and the CPU stays at 90 %. Describe, in a few sentences, what may be happening and the immediate steps you would take.",
      "rubric": [
        {
          "point": "Recognise possible cryptojacking/mining software hidden in the crack",
          "value": 1,
          "weight": 0.4
        },
        {
          "point": "Uninstall the cracked program and run a full malware scan or clean restore",
          "value": 1,
          "weight": 0.35
        },
        {
          "point": "Monitor system performance and avoid future untrusted downloads",
          "value": 1,
          "weight": 0.25
        }
      ],
      "difficulty": 4,
      "user_answer": "I think mining is happening on my laptop. I would run a full scan from my antivirus to know what's going on."
    },
    {
      "id": "CS01-T4-003",
      "stem": "You open your design files and see a note: \u201cFiles encrypted\u2014pay within 48 h.\u201d You remember installing a cracked plug-in last night. Briefly outline your response plan.",
      "rubric": [
        {
          "point": "Disconnect the device from networks to stop spread of ransomware",
          "value": 1,
          "weight": 0.35
        },
        {
          "point": "Restore data from clean backups instead of paying the ransom",
          "value": 1,
          "weight": 0.35
        },
        {
          "point": "Learn to avoid cracked software that can carry ransomware in future",
          "value": 1,
          "weight": 0.3
        }
      ],
      "difficulty": 4,
      "user_answer": "I would pay to get my files back as soon as possible."
    },
    {
      "id": "CS01-T3-004",
      "stem": "A coworker suggests saving licence fees by using a cracked accounting tool for client data. In 1\u20133 sentences, state the main dangers and a safer alternative.", 
      "rubric": [
        {
          "point": "Highlights risk of data breach or malware stealing sensitive client records",
          "value": 1,
          "weight": 0.4
        },
        {
          "point": "Mentions legal/licensing penalties for using pirated software",
          "value": 1,
          "weight": 0.3
        },
        {
          "point": "Proposes using genuine paid, free, or open-source software instead",
          "value": 1,
          "weight": 0.3
        }
      ],
      "difficulty": 3,
      "user_answer": "Nothing is dangerous about it, I will use the cracked tool."
    },
    {
      "id": "CS01-T5-005",
      "stem": "You used cracked software last week. Today you must buy gifts online but worry a keylogger may be watching. Outline, in 2\u20133 sentences, the precautions you would take before entering card details.",
      "rubric": [
        {
          "point": "Run a reputable malware scan or use a separate clean device",
          "value": 1,
          "weight": 0.35
        },
        {
          "point": "Use virtual/one-time payment methods or two-factor checkout to limit theft impact",
          "value": 1,
          "weight": 0.3
        },
        {
          "point": "Plan to uninstall the crack and reinstall the OS or restore from backup if infection found",
          "value": 1,
          "weight": 0.35
        }
      ],
      "difficulty": 5,
      "user_answer": "I would buy them normally as nothing will happen."
    }
  ]
}

```


#### Sample Output from the model
```json
{
  "scores": [
    {
      "id": "CS01-T3-001",
      "score": 0.2,
      "explanation": "Your answer is too generic, specific details are required."
    },
    {
      "id": "CS01-T4-002",
      "score": 0.75,
      "explanation": "You correctly recognized the possibility of cryptojacking and would run a scan, but did not mention uninstalling the software or monitoring performance as suggested."
    },
    {
      "id": "CS01-T4-003",
      "score": 0.25,
      "explanation": "You noted disconnecting from networks, but missed restoring data from backups and learning to avoid future risks of cracked software."
    },
    {
      "id": "CS01-T3-004",
      "score": 0.1,
      "explanation": "You did not highlight any dangers or suggest alternatives. Your answer is too generic, specific details are required."
    },
    {
      "id": "CS01-T5-005",
      "score": 0.2,
      "explanation": "Your answer is too generic, specific steps to prevent keylogging were not mentioned."
    }
  ],
  "overall": {
    "score": 1.4,
    "max_score": 13.5,
    "percentage": 10.37,
    "feedback": "You demonstrated some understanding of the risks but missed specific actionable steps in your answers. You should focus on providing detailed and practical advice to stay secure."
  }
}
```
