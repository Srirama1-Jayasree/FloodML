"""SMTP email support for AquaSentinel alerts."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send_email_alert(alert):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT", "25")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    alert_email = os.getenv("ALERT_EMAIL")

    if not all([smtp_host, smtp_username, smtp_password, alert_email]):
        return {"status": "skipped", "message": "Email notifications are not configured."}

    try:
        port = int(smtp_port)
        msg = EmailMessage()
        msg.set_content(alert.get("message", "AquaSentinel flood alert"))
        msg["Subject"] = f"AquaSentinel AI: {alert.get('title', 'Flood Alert')}"
        msg["From"] = smtp_username
        msg["To"] = alert_email

        with smtplib.SMTP(smtp_host, port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        return {"status": "sent", "message": "Alert email sent successfully."}
    except Exception:
        return {"status": "error", "message": "Unable to send email alert at this time."}
