"""
send_phish.py  –  generate & send a simulated phishing e-mail

Usage:
    python send_phish.py alice@example.com bob@example.com
    (or put addresses in recipients.txt and read from there)
"""

import smtplib, uuid, sys, json
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from rich import print
from ollama import Client
import os, random, textwrap as tw

# ─────────────────── config ────────────────────────────
load_dotenv()

SMTP_HOST  = os.getenv("SMTP_HOST")
SMTP_PORT  = int(os.getenv("SMTP_PORT"))
SMTP_USER  = os.getenv("SMTP_USER")
SMTP_PASS  = os.getenv("SMTP_PASS")

FROM_NAME  = os.getenv("FROM_NAME")
FROM_EMAIL = os.getenv("FROM_EMAIL")

OLLAMA_HOST  = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
LINK_URL     = os.getenv("LINK_URL", "https://google.com")

client = Client(host=OLLAMA_HOST)

LOG_FILE = Path("phish_send_log.jsonl")

# ────────────────── scenario templates ─────────────────
# ────────────────── scenario templates ─────────────────
SCENARIOS = [
    # 1 ─ VPN password reset
    {
      "tag": "vpn_reset",
      "subject": "URGENT: VPN password reset required",
      "seed": """
Write a professional phishing email that appears to come from the company
IT help desk. Goal: make the user click a “Reset VPN Password” button
today. Tone: polite urgency, reference security audit, use first name
placeholder <<NAME>> in greeting. Return ONLY the raw HTML for the email
body (120–160 words) with a single <b>Reset Now</b> button—no markdown or
explanations.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    },

    # 2 ─ Session re-authentication
    {
      "tag": "account_reauth",
      "subject": "Session expired – re-authenticate your corporate account",
      "seed": """
Compose a friendly but time-sensitive email telling the employee their
single-sign-on session expired and they must sign in again to avoid
interruption. Use <<NAME>> in the salutation. Add one sentence referencing
a routine update. Include a single <b>Sign In</b> button.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    },

    # 3 ─ Payroll update lure
    {
      "tag": "payroll_update",
      "subject": "Action needed: Payroll information verification",
      "seed": """
Craft a realistic email from the HR payroll department asking the employee
to verify direct-deposit details before the upcoming payday. Friendly but
official tone. Use <<NAME>> as greeting. Mention “bi-annual payroll audit”.
Include one <b>Verify Details</b> button.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    },

    # 4 ─ Fake OneDrive share
    {
      "tag": "onedrive_share",
      "subject": "<<NAME>>, a file has been shared with you on OneDrive",
      "seed": """
Write a convincing share-notification that looks like Microsoft OneDrive.
It should say a “2025 Q3 Budget.xlsx” file was shared and needs review.
Short and corporate, blue accent links. Greeting uses <<NAME>>. Single
<b>Open Document</b> button.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    },

    # 5 ─ Tax compliance notice
    {
      "tag": "tax_compliance",
      "subject": "Important: Digital tax form signature required",
      "seed": """
Create an urgent but polite email from “Finance Compliance” stating that
new digital tax forms must be signed to avoid reporting delays. Salutation
with <<NAME>>. Reference internal memo #2025-TX-17. Provide a single
<b>Review Form</b> button.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    },

    # 6 ─ Benefits enrollment reminder
    {
      "tag": "benefits_enroll",
      "subject": "Open enrollment closes Friday – confirm your selections",
      "seed": """
Draft a benefits-team email reminding employees that open enrollment ends
this week. Encourage them to confirm health-plan selections. Friendly,
HR-style language. Use <<NAME>>. Include one <b>Confirm Enrollment</b>
button.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    },

    # 7 ─ Software-license termination scare
    {
      "tag": "license_termination",
      "subject": "Software license termination notice – immediate action required",
      "seed": """
Write a slightly technical email pretending to be from the “Software Asset
Management” team warning that the employee’s Adobe Creative Cloud license
will be terminated unless they re-validate their account. Greeting uses
<<NAME>>. One <b>Re-Validate License</b> button.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    },

    # 8 ─ Parcel-delivery scam (highly relatable)
    {
      "tag": "parcel_delivery",
      "subject": "Package held at customs – confirm shipping fee",
      "seed": """
Compose an email that appears to come from an international parcel service
claiming a package for <<NAME>> is on hold because a small customs fee is
unpaid. Friendly but urgent tone (“will be returned in 48 hrs”). Include a
single <b>Pay Fee</b> button.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    },

    # 9 ─ Calendar invite update
    {
      "tag": "calendar_update",
      "subject": "<<NAME>>, meeting time changed – please reconfirm",
      "seed": """
Create an Outlook-style meeting update stating that tomorrow’s “Project
Sync” has moved from 3 pm to 1 pm. Ask the attendee to reconfirm via the
updated invitation. Greeting with <<NAME>>. One <b>Accept New Time</b>
button.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    },

    # 10 ─ Teams voicemail notice
    {
      "tag": "teams_voicemail",
      "subject": "You have 1 unread Teams voicemail",
      "seed": """
Generate a Microsoft Teams notification email telling <<NAME>> they missed
a voicemail from an internal extension. Instruct them to click to listen.
Brief, corporate Teams styling. Single <b>Play Voicemail</b> button.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    }
]

# ────────────────── helpers ────────────────────────────
def pick_scenario():
    return random.choice(SCENARIOS)

def render_email_body(seed: str, first_name: str):
    """Call the LLM once; inject <<NAME>> afterwards."""
    rsp = client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": seed}],
        stream=False
    )
    html = rsp["message"]["content"]
    return html.replace("<<NAME>>", first_name)

def send_one(recipient: str, html_body: str, subject: str, token: str):
    msg = EmailMessage()
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"]   = recipient
    msg["Subject"] = subject

    # replace the placeholder button label with our link
    link = f"{LINK_URL}?id={token}"
    html_body = html_body.replace(
        "Reset Now", f"<a href='{link}' style='padding:10px 20px;"
                     f"background:#0063ce;color:#fff;text-decoration:none;"
                     f"border-radius:4px;'>Reset&nbsp;Now</a>"
    ).replace(
        "Sign In",  f"<a href='{link}' style='padding:10px 20px;"
                     f"background:#0063ce;color:#fff;text-decoration:none;"
                     f"border-radius:4px;'>Sign&nbsp;In</a>"
    )

    msg.set_content(
        "This message contains HTML. "
        "Please view it in an HTML-capable e-mail client."
    )
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

def log_event(**kwargs):
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(kwargs) + "\n")

# ────────────────── main procedure ─────────────────────
def main():
    # collect recipients
    if len(sys.argv) > 1:
        recipients = sys.argv[1:]
    elif Path("recipients.txt").exists():
        recipients = [line.strip() for line in Path("recipients.txt").read_text().splitlines() if line.strip()]
    else:
        print("[red]No recipients provided.[/red]")
        sys.exit(1)

    scenario = pick_scenario()
    subj     = scenario["subject"]

    for email in recipients:
        first = email.split("@")[0].split(".")[0].title()  # naive first-name
        token = uuid.uuid4().hex
        html  = render_email_body(scenario["seed"], first)

        try:
            send_one(email, html, subj, token)
            print(f"[green]✓ sent[/green] {email}  ({scenario['tag']})")
            log_event(time=datetime.utcnow().isoformat(),
                      scenario=scenario["tag"],
                      to=email,
                      token=token)
        except Exception as e:
            print(f"[red]✗ failed[/red] {email} : {e}")

if __name__ == "__main__":
    main()
