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
SCENARIOS = [
    {
      "tag": "vpn_reset",
      "subject": "URGENT: VPN password reset required",
      "seed": """
Write a professional phishing email that appears to come from the company
IT help desk. Goal: make the user click a “Reset VPN Password” button today.
Tone: polite urgency, reference security audit, use first name placeholder
<<NAME>> in greeting. Return **HTML only** (max 180 words) with a single
<b>Reset Now</b> button.
Return ONLY the raw HTML for the email body, with no explanation or markdown fence.
""".strip()
    },
    {
      "tag": "account_reauth",
      "subject": "Session expired – re-authenticate your corporate account",
      "seed": """
Compose a friendly but urgent e-mail telling the employee their session
token expired and they need to sign in again. Use <<NAME>> placeholder for
salutation, no scary language, but include a call-to-action button labelled
“Sign In”.  HTML output 150-170 words.
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
