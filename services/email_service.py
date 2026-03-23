from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.utils import now_iso

class EmailService:
    def __init__(self, db):
        self.db = db

    def _load_settings(self):
        with self.db.get_conn() as conn:
            return conn.execute("SELECT * FROM app_settings WHERE id = 1").fetchone()

    def send_email(self, outing_id: int, recipient_email: str, subject: str, body: str, attachments: list[Path], recipient_type: str = "member"):
        settings = self._load_settings()
        if not settings["smtp_host"]:
            self._log(outing_id, recipient_email, recipient_type, subject, "failed", [str(p) for p in attachments], "SMTP is not configured")
            raise RuntimeError("SMTP is not configured in app_settings.")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings["smtp_from_email"] or settings["smtp_username"]
        message["To"] = recipient_email
        message.set_content(body)

        for attachment in attachments:
            data = attachment.read_bytes()
            maintype = "application"
            subtype = "pdf" if attachment.suffix == ".pdf" else "octet-stream"
            message.add_attachment(data, maintype=maintype, subtype=subtype, filename=attachment.name)

        with smtplib.SMTP(settings["smtp_host"], settings["smtp_port"] or 587) as smtp:
            smtp.starttls()
            if settings["smtp_username"]:
                smtp.login(settings["smtp_username"], settings["smtp_password"] or "")
            smtp.send_message(message)

        self._log(outing_id, recipient_email, recipient_type, subject, "sent", [str(p) for p in attachments], None)

    def _log(self, outing_id, recipient_email, recipient_type, subject, status, attachments, error_message):
        with self.db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO email_logs
                (outing_id, recipient_email, recipient_type, subject, status, attachment_paths, error_message, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (outing_id, recipient_email, recipient_type, subject, status, ",".join(attachments), error_message, now_iso()),
            )
