import os
import requests
from dotenv import load_dotenv

load_dotenv()

POWER_AUTOMATE_EMAIL_URL = os.getenv("POWER_AUTOMATE_EMAIL_URL", "")


def send_email_via_power_automate(to_email: str, subject: str, body: str):
    if not POWER_AUTOMATE_EMAIL_URL:
        return "Email skipped: Power Automate URL not configured."

    payload = {
        "to": to_email,
        "subject": subject,
        "body": body
    }

    try:
        response = requests.post(
            POWER_AUTOMATE_EMAIL_URL,
            json=payload,
            timeout=10
        )

        if response.status_code in [200, 201, 202]:
            return "Email sent successfully."
        else:
            return f"Email failed. Status: {response.status_code}, Response: {response.text}"

    except Exception as e:
        return f"Email error: {str(e)}"