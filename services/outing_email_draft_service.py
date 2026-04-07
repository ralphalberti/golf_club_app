from repositories.outing_email_draft_repository import OutingEmailDraftRepository
from repositories.member_repository import MemberRepository
from repositories.course_repository import CourseRepository
from services.email_template_service import EmailTemplateService
from services.email_render_service import EmailRenderService
from services.email_service import EmailService
from services.outing_service import OutingService


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
        self.template_service = EmailTemplateService(db)
        self.render_service = EmailRenderService(db)
        self.member_repo = MemberRepository(db)
        self.course_repo = CourseRepository(db)
        self.outing_service = OutingService(db)
        self.email_service = EmailService(db)

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

    def get_or_create_draft(
        self,
        *,
        outing_id: int,
        course_id: int | None,
        audience_type: str,
        template_type: str,
        extra_context: dict[str, str] | None = None,
    ):
        self._validate_types(audience_type, template_type)

        existing = self.repo.get_draft(outing_id, audience_type, template_type)
        if existing:
            return existing

        template_row = self.template_service.get_best_template(
            course_id=course_id,
            audience_type=audience_type,
            template_type=template_type,
        )
        if not template_row:
            raise ValueError(
                "No email template found for "
                f"audience_type={audience_type}, template_type={template_type}, "
                f"course_id={course_id}"
            )

        rendered = self.render_service.render(
            outing_id=outing_id,
            template_row=template_row,
            extra_context=extra_context,
        )

        self.repo.upsert_draft(
            outing_id=outing_id,
            audience_type=audience_type,
            template_type=template_type,
            subject_text=rendered["subject_text"],
            body_text=rendered["body_text"],
            body_html=rendered["body_html"],
            status="draft",
            sent_at=None,
        )

        return self.repo.get_draft(outing_id, audience_type, template_type)

    def regenerate_draft_from_template(
        self,
        *,
        outing_id: int,
        course_id: int | None,
        audience_type: str,
        template_type: str,
        extra_context: dict[str, str] | None = None,
    ):
        self._validate_types(audience_type, template_type)

        template_row = self.template_service.get_best_template(
            course_id=course_id,
            audience_type=audience_type,
            template_type=template_type,
        )
        if not template_row:
            raise ValueError(
                "No email template found for "
                f"audience_type={audience_type}, template_type={template_type}, "
                f"course_id={course_id}"
            )

        rendered = self.render_service.render(
            outing_id=outing_id,
            template_row=template_row,
            extra_context=extra_context,
        )

        self.repo.upsert_draft(
            outing_id=outing_id,
            audience_type=audience_type,
            template_type=template_type,
            subject_text=rendered["subject_text"],
            body_text=rendered["body_text"],
            body_html=rendered["body_html"],
            status="draft",
            sent_at=None,
        )

        return self.repo.get_draft(outing_id, audience_type, template_type)

    def _validate_types(self, audience_type: str, template_type: str) -> None:
        if audience_type not in self.VALID_AUDIENCE_TYPES:
            raise ValueError(f"Invalid audience_type: {audience_type}")

        if template_type not in self.VALID_TEMPLATE_TYPES:
            raise ValueError(f"Invalid template_type: {template_type}")

    def send_draft(
        self,
        *,
        outing_id: int,
        audience_type: str,
        template_type: str,
    ) -> int:
        self._validate_types(audience_type, template_type)

        draft = self.repo.get_draft(outing_id, audience_type, template_type)
        if not draft:
            raise ValueError(
                "No saved draft exists for this outing, audience, and template type."
            )

        outing = self.outing_service.get_outing(outing_id)
        if not outing:
            raise ValueError(f"Outing not found: {outing_id}")

        sent_count = 0

        if audience_type == "member":
            members = self.member_repo.list_all(active_only=True)

            for member in members:
                to_email = str(member["email"] or "").strip()
                if not to_email:
                    continue

                self.email_service.send_email(
                    outing_id=outing_id,
                    to_email=to_email,
                    subject=str(draft["subject_text"]),
                    body_text=str(draft["body_text"]),
                    body_html=draft["body_html"],
                    attachments=[],
                    recipient_type="member",
                )
                sent_count += 1

        elif audience_type == "course":
            course_id = int(outing["course_id"])
            course = self.course_repo.get(course_id)
            if not course:
                raise ValueError(f"Course not found: {course_id}")

            to_email = str(course["contact_email"] or "").strip()
            if not to_email:
                raise ValueError("Selected course does not have a contact email.")

            self.email_service.send_email(
                outing_id=outing_id,
                to_email=to_email,
                subject=str(draft["subject_text"]),
                body_text=str(draft["body_text"]),
                body_html=draft["body_html"],
                attachments=[],
                recipient_type="course",
            )
            sent_count = 1

        else:
            raise ValueError(f"Unsupported audience_type: {audience_type}")

        self.repo.mark_sent(outing_id, audience_type, template_type)
        return sent_count
