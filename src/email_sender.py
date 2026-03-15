from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import settings

logger = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send a plain-text email via Gmail SMTP using an App Password.

    Returns True on success, False on failure/misconfiguration.
    """
    if not settings.email_from or not settings.google_app_password:
        logger.warning("Email not sent: EMAIL_FROM or GOOGLE_APP_PASSWORD not configured")
        return False

    if not to_email:
        logger.warning("Email not sent: no recipient address")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain"))

    try:
        await asyncio.to_thread(_smtp_send, msg, to_email)
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def _smtp_send(msg: MIMEMultipart, to_email: str) -> None:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(settings.email_from, settings.google_app_password)
        server.sendmail(settings.email_from, to_email, msg.as_string())
