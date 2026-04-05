from __future__ import annotations

from typing import TypedDict

from services.outing_service import OutingService
from services.settings_service import SettingsService


class RenderedEmailDraft(TypedDict):
    subject_text: str
    body_text: str
    body_html: str | None


class EmailRenderService:
    VALID_AUDIENCE_TYPES = {"member", "course"}
    VALID_TEMPLATE_TYPES = {
        "invitation",
        "pairings",
        "revised_pairings",
        "course_hold_request",
        "course_final_schedule",
    }

    def __init__(self, db):
        self.db = db
        self.outing_service = OutingService(db)
        self.settings_service = SettingsService(db)

    def render(
        self,
        *,
        outing_id: int,
        template_row,
        extra_context: dict[str, str] | None = None,
    ) -> RenderedEmailDraft:
        outing = self.outing_service.get_outing(outing_id)
        if not outing:
            raise ValueError(f"Outing not found: {outing_id}")

        context = self.build_context(outing, extra_context=extra_context)

        subject = self._render_text(
            str(template_row["subject_template"] or ""), context
        )
        body_text = self._render_text(
            str(template_row["body_text_template"] or ""),
            context,
        )

        body_html_template = template_row["body_html_template"]
        body_html: str | None = None
        if body_html_template:
            body_html = self._render_text(str(body_html_template), context)

        return {
            "subject_text": subject,
            "body_text": body_text,
            "body_html": body_html,
        }

    def build_context(
        self,
        outing,
        *,
        extra_context: dict[str, str] | None = None,
    ) -> dict[str, str]:
        settings = self.settings_service.get_all()

        fee_value = outing["fee"] if "fee" in outing.keys() else None
        if fee_value in (None, ""):
            green_fee = ""
        else:
            green_fee = f"${fee_value}"

        context: dict[str, str] = {
            "club_name": str(settings.get("club_name", "") or ""),
            "course_name": str(outing["course_name"] or ""),
            "outing_date": str(outing["outing_date"] or ""),
            "start_time": str(outing["start_time"] or ""),
            "green_fee": green_fee,
            "tee_time_count": str(outing["tee_time_count"] or ""),
            "sender_name": "",
            "course_contact_name": "",
            "course_contact_email": "",
            "rsvp_link": "",
            "schedule_text": "",
            "schedule_html": "",
            "open_spots_text": "",
            "open_spots_html": "",
            "open_spot_signup_link": "",
            "requested_tee_time_count": "",
            "player_count": "",
        }

        if "contact_name" in outing.keys():
            context["course_contact_name"] = str(outing["contact_name"] or "")

        if "contact_email" in outing.keys():
            context["course_contact_email"] = str(outing["contact_email"] or "")

        if extra_context:
            for key, value in extra_context.items():
                context[str(key)] = "" if value is None else str(value)

        return context

    def _render_text(self, template_text: str, context: dict[str, str]) -> str:
        rendered = template_text

        for key, value in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)

        return rendered
