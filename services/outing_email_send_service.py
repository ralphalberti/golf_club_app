class OutingEmailSendService:
    VALID_MEMBER_TEMPLATE_TYPES = {
        "invitation",
        "pairings",
        "revised_pairings",
    }

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

        if audience_type == "member":
            members = self.member_repo.list_all(active_only=True)
            if not members:
                raise ValueError("No members available for test rendering.")

            sample_member = members[0]
            member_id = int(sample_member["id"])

            subject_text = str(draft["subject_text"])
            body_text = str(draft["body_text"])
            body_html = draft["body_html"]

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

        if audience_type == "course":
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

        raise ValueError(f"Unsupported audience_type: {audience_type}")

    def send_draft_to_member_ids(
        self,
        *,
        outing_id: int,
        template_type: str,
        member_ids: list[int],
    ) -> dict:
        if template_type not in self.VALID_MEMBER_TEMPLATE_TYPES:
            raise ValueError(
                f"Unsupported member template_type for targeted send: {template_type}"
            )

        if not member_ids:
            raise ValueError("No member IDs provided.")

        draft = self.draft_service.get_draft(
            outing_id,
            "member",
            template_type,
        )
        if not draft:
            raise ValueError(
                "No saved member draft exists for this outing and template type."
            )

        outing = self.outing_service.get_outing(outing_id)
        if not outing:
            raise ValueError(f"Outing not found: {outing_id}")

        member_lookup = {
            int(row["id"]): row for row in self.member_repo.list_all(active_only=False)
        }

        attempted = 0
        sent = 0
        skipped: list[dict] = []
        failed: list[dict] = []

        seen_member_ids: set[int] = set()

        for member_id in member_ids:
            member_id = int(member_id)
            if member_id in seen_member_ids:
                continue
            seen_member_ids.add(member_id)

            member = member_lookup.get(member_id)
            if not member:
                skipped.append({"member_id": member_id, "reason": "Member not found"})
                continue

            to_email = str(member["email"] or "").strip()
            if not to_email:
                skipped.append({"member_id": member_id, "reason": "No email address"})
                continue

            attempted += 1

            subject_text = str(draft["subject_text"])
            body_text = str(draft["body_text"])
            body_html = draft["body_html"]

            try:
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

                self.email_service.send_email(
                    outing_id=outing_id,
                    to_email=to_email,
                    subject=subject_text,
                    body_text=body_text,
                    body_html=body_html,
                    attachments=[],
                    recipient_type="member",
                )
                sent += 1

            except Exception as exc:
                failed.append(
                    {
                        "member_id": member_id,
                        "email": to_email,
                        "error": str(exc),
                    }
                )

        return {
            "attempted": attempted,
            "sent_count": sent,
            "skipped": skipped,
            "failed": failed,
        }
