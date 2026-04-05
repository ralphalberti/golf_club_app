from repositories.email_template_repository import EmailTemplateRepository


class EmailTemplateService:
    VALID_AUDIENCE_TYPES = {"member", "course"}
    VALID_TEMPLATE_TYPES = {
        "invitation",
        "pairings",
        "revised_pairings",
        "course_hold_request",
        "course_final_schedule",
    }

    def __init__(self, db):
        self.repo = EmailTemplateRepository(db)

    def list_templates(self):
        return self.repo.list_all()

    def list_templates_for_course(self, course_id: int | None):
        return self.repo.list_for_course(course_id)

    def get_template_by_id(self, template_id: int):
        return self.repo.get_by_id(template_id)

    def get_best_template(
        self,
        course_id: int | None,
        audience_type: str,
        template_type: str,
    ):
        self._validate_types(audience_type, template_type)
        return self.repo.get_best_match(course_id, audience_type, template_type)

    def save_template(
        self,
        *,
        course_id: int | None,
        audience_type: str,
        template_type: str,
        subject_template: str,
        body_text_template: str,
        body_html_template: str | None = None,
        active: int = 1,
    ) -> int:
        self._validate_types(audience_type, template_type)

        return self.repo.upsert_template(
            course_id=course_id,
            audience_type=audience_type,
            template_type=template_type,
            subject_template=subject_template,
            body_text_template=body_text_template,
            body_html_template=body_html_template,
            active=active,
        )

    def delete_template(self, template_id: int) -> None:
        self.repo.delete(template_id)

    def _validate_types(self, audience_type: str, template_type: str) -> None:
        if audience_type not in self.VALID_AUDIENCE_TYPES:
            raise ValueError(f"Invalid audience_type: {audience_type}")

        if template_type not in self.VALID_TEMPLATE_TYPES:
            raise ValueError(f"Invalid template_type: {template_type}")
