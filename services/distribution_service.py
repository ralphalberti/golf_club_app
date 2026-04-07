from __future__ import annotations

from pathlib import Path
import base64
import hashlib
import hmac

from app.config import EXPORT_DIR

from app.config import RSVP_SERVER_HOST, RSVP_SERVER_PORT
from services.rsvp_token_service import RSVPTokenService


class DistributionService:
    def __init__(self, db, pdf_service, export_service, email_service):
        self.db = db
        self.pdf_service = pdf_service
        self.export_service = export_service
        self.email_service = email_service
        self.rsvp_token_service = RSVPTokenService()

    def build_outputs(
        self, outing: dict, tee_times: list[dict], assignments: list[dict]
    ):
        pdf_path = self.pdf_service.export_master_schedule_pdf(
            outing, tee_times, assignments
        )
        csv_path = self.export_service.export_course_csv(outing, tee_times, assignments)
        return pdf_path, csv_path

    def preview_invitation_emails_to_file(
        self,
        outing: dict,
        members: list[dict],
        *,
        base_url: str = f"http://{RSVP_SERVER_HOST}:{RSVP_SERVER_PORT}/rsvp/yes",
    ) -> Path:
        preview_dir = EXPORT_DIR / "preview"
        preview_dir.mkdir(parents=True, exist_ok=True)

        path = (
            preview_dir
            / f"outing_{outing['id']}_invitation_preview_v{outing['version']}.txt"
        )

        subject = f"Invitation: {outing['outing_date']} - {outing['course_name']}"

        lines: list[str] = []
        lines.append(f"OUTING ID: {outing['id']}")
        lines.append(f"DATE: {outing['outing_date']}")
        lines.append(f"COURSE: {outing['course_name']}")
        lines.append(f"SUBJECT: {subject}")
        lines.append("")

        fee_value = outing["fee"] if "fee" in outing.keys() else None
        fee_text = "" if fee_value in (None, "") else f"${fee_value}"

        for member in members:
            email = (member["email"] or "").strip()
            if not email:
                continue

            token = self.rsvp_token_service.create_token(
                int(outing["id"]),
                int(member["id"]),
            )
            rsvp_link = f"{base_url}?token={token}"

            body_lines = [
                f"Hello {member['first_name']},",
                "",
                "You are invited to our next outing.",
                "",
                f"Date: {outing['outing_date']}",
                f"Course: {outing['course_name']}",
            ]

            if fee_text:
                body_lines.append(f"Greens Fee: {fee_text}")

            body_lines.extend(
                [
                    "",
                    "Click the link below to RSVP YES:",
                    rsvp_link,
                    "",
                    "Spots are first come, first served based on when your Yes response is received.",
                ]
            )

            lines.append("=" * 72)
            lines.append(f"MEMBER ID: {member['id']}")
            lines.append(f"TO: {email}")
            lines.append(f"SUBJECT: {subject}")
            lines.append("")
            lines.extend(body_lines)
            lines.append("")
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
        return path
