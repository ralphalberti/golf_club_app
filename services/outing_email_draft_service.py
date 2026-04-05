from repositories.outing_email_draft_repository import OutingEmailDraftRepository


class OutingEmailDraftService:
    VALID_AUDIENCE_TYPES = {"member", "course"}
    VALID_TEMPLATE_TYPES = {
        "invitation",
        "pairings",
        "revised_pairings",
        "course_hold_request",
        "course_final_schedule",
    }

    def __init__(self, db):
        self.repo = OutingEmailDraftRepository(db)

    def get_draft(
        self,
        outing_id: int,
        audience_type: str,
        template_type: str,
    ):
        self._validate_types(audience_type, template_type)
        return self.repo.get_draft(outing_id, audience_type, template_type)

    def save_draft(
        self,
        *,
        outing_id: int,
        audience_type: str,
        template_type: str,
        subject_text: str,
        body_text: str,
        body_html: str | None = None,
        status: str = "draft",
        sent_at: str | None = None,
    ) -> int:
        self._validate_types(audience_type, template_type)
        return self.repo.upsert_draft(
            outing_id=outing_id,
            audience_type=audience_type,
            template_type=template_type,
            subject_text=subject_text,
            body_text=body_text,
            body_html=body_html,
            status=status,
            sent_at=sent_at,
        )

    def mark_sent(
        self,
        outing_id: int,
        audience_type: str,
        template_type: str,
    ) -> None:
        self._validate_types(audience_type, template_type)
        self.repo.mark_sent(outing_id, audience_type, template_type)

    def delete_draft(
        self,
        outing_id: int,
        audience_type: str,
        template_type: str,
    ) -> None:
        self._validate_types(audience_type, template_type)
        self.repo.delete_draft(outing_id, audience_type, template_type)

    def _validate_types(self, audience_type: str, template_type: str) -> None:
        if audience_type not in self.VALID_AUDIENCE_TYPES:
            raise ValueError(f"Invalid audience_type: {audience_type}")

        if template_type not in self.VALID_TEMPLATE_TYPES:
            raise ValueError(f"Invalid template_type: {template_type}")
