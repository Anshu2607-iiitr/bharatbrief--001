import os
import smtplib
from email.message import EmailMessage

import httpx

# Email is sent with the first option that is configured:
#
# 1. Brevo HTTP API (use this in production: Render's free plan blocks SMTP ports)
#    BREVO_API_KEY      -> Brevo dashboard > SMTP & API > API Keys
#    BREVO_SENDER_EMAIL -> a sender you verified in Brevo (your Gmail works)
#
# 2. Gmail SMTP (fine for local development)
#    SMTP_USER / SMTP_PASSWORD -> Gmail address + Gmail *App Password*
#
# 3. Nothing configured -> OTP is printed in the backend terminal (dev only)

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = (os.getenv("SMTP_USER") or "").strip() or None
SMTP_PASSWORD = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "") or None

FROM_NAME = os.getenv("SMTP_FROM_NAME", "Bharat Brief")


def build_otp_email(name: str, otp: str, minutes_valid: int):
    subject = f"{otp} is your Bharat Brief verification code"

    text = (
        f"Hi {name},\n\n"
        f"Your Bharat Brief verification code is: {otp}\n\n"
        f"It expires in {minutes_valid} minutes. "
        "If you didn't try to sign up, you can ignore this email.\n\n"
        "- Team Bharat Brief"
    )

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:24px;
                border:1px solid #e8ebf0;border-radius:12px">
      <div style="font-size:20px;font-weight:700;color:#172033">
        Bharat <span style="color:#e66b35">Brief</span>
      </div>
      <p style="color:#4d596b">Hi {name},</p>
      <p style="color:#4d596b">Use this code to verify your email:</p>
      <div style="font-size:32px;font-weight:800;letter-spacing:8px;color:#172b4d;
                  background:#fff0e8;padding:16px;text-align:center;border-radius:8px">
        {otp}
      </div>
      <p style="color:#8993a2;font-size:12px">
        Expires in {minutes_valid} minutes. If you didn't request this, ignore this email.
      </p>
    </div>
    """

    return subject, text, html


def send_with_brevo(to_email, name, subject, text, html):
    response = httpx.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": BREVO_API_KEY, "accept": "application/json"},
        json={
            "sender": {"name": FROM_NAME, "email": BREVO_SENDER_EMAIL},
            "to": [{"email": to_email, "name": name}],
            "subject": subject,
            "textContent": text,
            "htmlContent": html,
        },
        timeout=15,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Brevo error {response.status_code}: {response.text}")


def send_with_smtp(to_email, subject, text, html):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{FROM_NAME} <{SMTP_USER}>"
    message["To"] = to_email
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(message)


def send_otp_email(to_email: str, name: str, otp: str, minutes_valid: int):
    subject, text, html = build_otp_email(name, otp, minutes_valid)

    if BREVO_API_KEY and BREVO_SENDER_EMAIL:
        send_with_brevo(to_email, name, subject, text, html)
    elif SMTP_USER and SMTP_PASSWORD:
        send_with_smtp(to_email, subject, text, html)
    elif os.getenv("VERCEL"):
        # In production, never pretend an OTP was sent
        raise RuntimeError("No email provider configured (set SMTP_USER/SMTP_PASSWORD or BREVO_API_KEY)")
    else:
        print(f"\n[DEV] No email provider configured. OTP for {to_email}: {otp}\n")


def email_status():
    """Which provider is configured, and whether it accepts our credentials.
    Sends no email."""
    if BREVO_API_KEY and BREVO_SENDER_EMAIL:
        response = httpx.get(
            "https://api.brevo.com/v3/account",
            headers={"api-key": BREVO_API_KEY, "accept": "application/json"},
            timeout=15,
        )
        return {"provider": "brevo", "ok": response.status_code < 400,
                "detail": f"HTTP {response.status_code}"}

    if SMTP_USER and SMTP_PASSWORD:
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
            return {"provider": "smtp", "ok": True, "user": SMTP_USER,
                    "password_length": len(SMTP_PASSWORD)}
        except Exception as error:
            return {"provider": "smtp", "ok": False, "user": SMTP_USER,
                    "password_length": len(SMTP_PASSWORD),
                    "detail": f"{type(error).__name__}: {error}"[:300]}

    return {"provider": None, "ok": False,
            "detail": "No SMTP_USER/SMTP_PASSWORD or BREVO_API_KEY/BREVO_SENDER_EMAIL set"}
