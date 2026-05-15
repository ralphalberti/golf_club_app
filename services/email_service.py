from __future__ import annotations

import re
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

from app.utils import now_iso

EMAIL_MAX_RETRIES = 3
EMAIL_RETRY_DELAY_SECONDS = 2


class EmailService:
    def __init__(self, db):
        self.db = db

    def _load_settings(self):
        with self.db.get_conn() as conn:
            return conn.execute("SELECT * FROM app_settings WHERE id = 1").fetchone()

    def _is_valid_email(self, email: str) -> bool:
        email = email.strip()
        if not email:
            return False

        return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None

    def _is_transient_error(self, exc: Exception) -> bool:
        text = str(exc).lower()

        transient_markers = [
            "timeout",
            "temporarily",
            "try again",
            "rate limit",
            "too many",
            "connection reset",
            "connection unexpectedly closed",
            "server disconnected",
        ]

        return any(marker in text for marker in transient_markers)

    def _build_message(
        self,
        *,
        from_email: str,
        to_email: str,
        subject: str,
        body_text: str,
        attachments: list[Path],
        bcc_emails: list[str] | None = None,
        body_html: str | None = None,
        reply_to: str | None = None,
    ) -> EmailMessage:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = to_email

        if reply_to:
            message["Reply-To"] = reply_to

        if bcc_emails:
            message["Bcc"] = ", ".join(bcc_emails)

        message.set_content(body_text)

        if body_html:
            message.add_alternative(body_html, subtype="html")

        for attachment in attachments:
            data = attachment.read_bytes()
            maintype = "application"
            subtype = "pdf" if attachment.suffix == ".pdf" else "octet-stream"
            message.add_attachment(
                data,
                maintype=maintype,
                subtype=subtype,
                filename=attachment.name,
            )

        return message

    def _open_smtp(self, settings):
        smtp = smtplib.SMTP(settings["smtp_host"], settings["smtp_port"] or 587)
        smtp.starttls()

        if settings["smtp_username"]:
            smtp.login(settings["smtp_username"], settings["smtp_password"] or "")

        return smtp

    def send_email(
        self,
        outing_id: int,
        to_email: str,
        subject: str,
        body_text: str,
        attachments: list[Path],
        recipient_type: str = "member",
        bcc_emails: list[str] | None = None,
        body_html: str | None = None,
        reply_to: str | None = None,
    ):
        settings = self._load_settings()
        if not settings["smtp_host"]:
            self._log(
                outing_id,
                to_email,
                recipient_type,
                subject,
                "failed",
                [str(p) for p in attachments],
                "SMTP is not configured",
            )
            raise RuntimeError("SMTP is not configured in app_settings.")

        from_email = settings["smtp_from_email"] or settings["smtp_username"]

        message = self._build_message(
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            bcc_emails=bcc_emails,
            reply_to=reply_to,
        )

        with self._open_smtp(settings) as smtp:
            smtp.send_message(message)

        self._log(
            outing_id,
            ",".join(bcc_emails) if bcc_emails else to_email,
            recipient_type,
            subject,
            "sent",
            [str(p) for p in attachments],
            None,
        )

    def send_personalized_bulk(
        self,
        *,
        outing_id: int,
        messages: list[dict],
        recipient_type: str = "member",
    ) -> dict:
        settings = self._load_settings()
        if not settings["smtp_host"]:
            raise RuntimeError("SMTP is not configured in app_settings.")

        from_email = settings["smtp_from_email"] or settings["smtp_username"]

        attempted = 0
        sent = 0
        skipped: list[dict] = []
        failed: list[dict] = []

        valid_messages: list[dict] = []

        for item in messages:
            to_email = str(item.get("to_email") or "").strip()

            if not self._is_valid_email(to_email):
                skipped.append(
                    {
                        "email": to_email,
                        "reason": "Invalid or missing email address",
                    }
                )
                continue

            valid_messages.append(item)

        smtp = self._open_smtp(settings)

        try:
            for item in valid_messages:
                to_email = str(item["to_email"]).strip()
                attempted += 1

                message = self._build_message(
                    from_email=from_email,
                    to_email=to_email,
                    subject=str(item["subject"]),
                    body_text=str(item["body_text"]),
                    body_html=item.get("body_html"),
                    attachments=item.get("attachments", []),
                    reply_to=item.get("reply_to"),
                )

                last_error: Exception | None = None

                for attempt in range(1, EMAIL_MAX_RETRIES + 1):
                    try:
                        smtp.send_message(message)

                        self._log(
                            outing_id,
                            to_email,
                            recipient_type,
                            str(item["subject"]),
                            "sent",
                            [str(p) for p in item.get("attachments", [])],
                            None,
                        )

                        sent += 1
                        last_error = None
                        break

                    except Exception as exc:
                        last_error = exc

                        if not self._is_transient_error(exc):
                            break

                        if attempt < EMAIL_MAX_RETRIES:
                            time.sleep(EMAIL_RETRY_DELAY_SECONDS * attempt)

                            try:
                                smtp.noop()
                            except Exception:
                                try:
                                    smtp.quit()
                                except Exception:
                                    pass
                                smtp = self._open_smtp(settings)

                if last_error is not None:
                    error_message = str(last_error)

                    self._log(
                        outing_id,
                        to_email,
                        recipient_type,
                        str(item["subject"]),
                        "failed",
                        [str(p) for p in item.get("attachments", [])],
                        error_message,
                    )

                    failed.append(
                        {
                            "email": to_email,
                            "error": error_message,
                        }
                    )

        finally:
            try:
                smtp.quit()
            except Exception:
                pass

        return {
            "attempted": attempted,
            "sent_count": sent,
            "skipped": skipped,
            "failed": failed,
        }

    def _log(
        self,
        outing_id,
        recipient_email,
        recipient_type,
        subject,
        status,
        attachments,
        error_message,
    ):
        with self.db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO email_logs
                (outing_id, recipient_email, recipient_type, subject, status, attachment_paths, error_message, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outing_id,
                    recipient_email,
                    recipient_type,
                    subject,
                    status,
                    ",".join(attachments),
                    error_message,
                    now_iso(),
                ),
            )
