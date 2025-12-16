"""Email sending utilities (SMTP)."""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Iterable


class EmailService:
    """Send email notifications via SMTP."""

    def __init__(self) -> None:
        self.enabled = os.getenv("EMAIL_NOTIFICATIONS_ENABLED", "false").lower() in ("1", "true", "yes")
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
        self.from_email = os.getenv("EMAIL_FROM", "")
        self.reply_to = os.getenv("EMAIL_REPLY_TO", "")
        self.subject_prefix = os.getenv("EMAIL_SUBJECT_PREFIX", "[Alliance] ")

    def _validate_config(self) -> None:
        if not self.smtp_host or not self.from_email:
            raise RuntimeError("Missing SMTP_HOST/EMAIL_FROM configuration")

    def send_text(self, to_email: str, subject: str, body: str, bcc: Iterable[str] | None = None) -> None:
        """Send a plain-text email."""
        if not self.enabled:
            return
        self._validate_config()

        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = to_email
        if bcc:
            message["Bcc"] = ", ".join([e for e in bcc if e])
        message["Subject"] = f"{self.subject_prefix}{subject}"
        if self.reply_to:
            message["Reply-To"] = self.reply_to
        message.set_content(body)

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as smtp:
            if self.smtp_use_tls:
                smtp.starttls()
            if self.smtp_username and self.smtp_password:
                smtp.login(self.smtp_username, self.smtp_password)
            smtp.send_message(message)

