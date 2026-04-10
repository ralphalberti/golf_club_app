class OutingEmailSendService:
    def __init__(self, draft_service):
        self.draft_service = draft_service
        self.email_service = draft_service.email_service
        self.member_repo = draft_service.member_repo
        self.course_repo = draft_service.course_repo
        self.outing_service = draft_service.outing_service

    def send_test_email(
        self,
        *,
        outing_id: int,
        audience_type: str,
        template_type: str,
        to_emails: list[str],
    ) -> dict:
        if not to_emails:
            raise ValueError("No test email recipients provided.")

        draft = self.draft_service.get_draft(
            outing_id,
            audience_type,
            template_type,
        )
        if not draft:
            raise ValueError("No saved draft exists.")

        outing = self.outing_service.get_outing(outing_id)
        if not outing:
            raise ValueError(f"Outing not found: {outing_id}")

        # --- MEMBER TEST SEND ---
        if audience_type == "member":
            members = self.member_repo.list_all(active_only=True)
            if not members:
                raise ValueError("No members available for test rendering.")

            sample_member = members[0]
            member_id = int(sample_member["id"])

            subject_text = str(draft["subject_text"])
            body_text = str(draft["body_text"])
            body_html = draft["body_html"]

            # reuse SAME logic as send_draft
            if template_type == "invitation":
                subject_text, body_text, body_html = (
                    self.draft_service._apply_member_placeholders(
                        subject_text=subject_text,
                        body_text=body_text,
                        body_html=body_html,
                        outing_id=outing_id,
                        member_id=member_id,
                    )
                )

            elif template_type in {"pairings", "revised_pairings"}:
                personalized_schedule_html = (
                    self.draft_service._apply_member_pairings_html(
                        draft=draft,
                        outing_id=outing_id,
                        member_id=member_id,
                    )
                )

                body_html = self.draft_service._build_pairings_html_from_body_text(
                    body_text=body_text,
                    schedule_html=personalized_schedule_html,
                )

            sent_count = 0

            for email in to_emails:
                email = email.strip()
                if not email:
                    continue

                self.email_service.send_email(
                    outing_id=outing_id,
                    to_email=email,
                    subject=subject_text,
                    body_text=body_text,
                    body_html=body_html,
                    attachments=[],
                    recipient_type="test",
                )
                sent_count += 1

            return {
                "sent_count": sent_count,
                "sample_member_id": member_id,
            }

        # --- COURSE TEST SEND ---
        elif audience_type == "course":
            subject_text = str(draft["subject_text"])
            body_text = str(draft["body_text"])
            body_html = draft["body_html"]

            sent_count = 0

            for email in to_emails:
                email = email.strip()
                if not email:
                    continue

                self.email_service.send_email(
                    outing_id=outing_id,
                    to_email=email,
                    subject=subject_text,
                    body_text=body_text,
                    body_html=body_html,
                    attachments=[],
                    recipient_type="test",
                )
                sent_count += 1

            return {"sent_count": sent_count}

        else:
            raise ValueError(f"Unsupported audience_type: {audience_type}")
