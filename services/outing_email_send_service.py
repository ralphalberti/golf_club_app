from __future__ import annotations

from app.config import RSVP_SERVER_HOST, RSVP_SERVER_PORT
from services.outing_workflow_service import OutingWorkflowService
from services.rsvp_token_service import RSVPTokenService
import html


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
        self.workflow_service = OutingWorkflowService(draft_service.repo.db)
        self.token_service = RSVPTokenService()

    def _cancel_link(self, outing_id: int, member_id: int) -> str:
        token = self.token_service.create_token(outing_id, member_id)
        return f"http://{RSVP_SERVER_HOST}:{RSVP_SERVER_PORT}/rsvp/cancel?token={token}"

    def _inject_cancel_link(
        self,
        *,
        outing_id: int,
        member_id: int,
        body_text: str,
        body_html: str | None,
    ) -> tuple[str, str | None]:
        cancel_link = self._cancel_link(outing_id, member_id)

        if "{{cancel_link}}" in body_text:
            body_text = body_text.replace("{{cancel_link}}", cancel_link)
        else:
            body_text = (
                f"{body_text.rstrip()}\n\n" "Need to cancel?\n" f"{cancel_link}\n"
            )

        if body_html is not None:
            if "{{cancel_link}}" in body_html:
                body_html = body_html.replace("{{cancel_link}}", cancel_link)
            else:
                body_html = (
                    f"{body_html}"
                    "<hr>"
                    "<p><strong>Need to cancel?</strong><br>"
                    f'<a href="{cancel_link}">Cancel your spot</a></p>'
                )

        return body_text, body_html

    def _inject_rsvp_link(
        self,
        *,
        body_text: str,
        body_html: str | None,
        rsvp_link: str,
    ) -> tuple[str, str | None]:
        text_cta = "Want to play?\n" "Yes, I'd like to play\n" f"{rsvp_link}"

        html_cta = (
            "<p><strong>Want to play?</strong><br>"
            f'<a href="{rsvp_link}">Yes, I&apos;d like to play</a></p>'
        )

        if "{{rsvp_link}}" in body_text:
            body_text = body_text.replace("{{rsvp_link}}", text_cta)
        elif rsvp_link in body_text:
            body_text = body_text.replace(rsvp_link, text_cta)
        else:
            body_text = f"{body_text.rstrip()}\n\n{text_cta}\n"

        if body_html:
            if "{{rsvp_link}}" in body_html:
                body_html = body_html.replace("{{rsvp_link}}", html_cta)
            elif rsvp_link in body_html:
                body_html = body_html.replace(rsvp_link, html_cta)
            else:
                body_html = f"{body_html.rstrip()}\n{html_cta}"

        return body_text, body_html

    def _plain_text_to_html(self, body_text: str) -> str:
        escaped = html.escape(body_text)
        return "<p>" + escaped.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"

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

                if body_html is None:
                    body_html = self._plain_text_to_html(body_text)

                token = RSVPTokenService().create_token(outing_id, member_id)
                rsvp_link = (
                    f"http://{RSVP_SERVER_HOST}:{RSVP_SERVER_PORT}"
                    f"/rsvp/yes?token={token}"
                )

                body_text, body_html = self._inject_rsvp_link(
                    body_text=body_text,
                    body_html=body_html,
                    rsvp_link=rsvp_link,
                )

            elif template_type in {"pairings", "revised_pairings"}:
                personalized_schedule_html = (
                    self.draft_service._apply_member_pairings_html(
                        draft=draft,
                        outing_id=outing_id,
                        member_id=member_id,
                    )
                )
                tee_times = self.outing_service.get_tee_times(outing_id)
                assignments = self.outing_service.get_assignments(outing_id)

                fresh_schedule_text = (
                    self.draft_service.schedule_render_service.render_text(
                        outing_id=outing_id,
                        tee_times=tee_times,
                        assignments=assignments,
                    )
                )

                body_lines = []
                for line in body_text.splitlines():
                    if not self.draft_service._is_schedule_line(line):
                        body_lines.append(line)

                body_text = "\n".join(body_lines).rstrip()
                body_text = f"{body_text}\n\n{fresh_schedule_text}"

                body_html = self.draft_service._build_pairings_html_from_body_text(
                    body_text=body_text,
                    schedule_html=personalized_schedule_html,
                )
                body_text, body_html = self._inject_cancel_link(
                    outing_id=outing_id,
                    member_id=member_id,
                    body_text=body_text,
                    body_html=body_html,
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

                    if body_html is None:
                        body_html = self._plain_text_to_html(body_text)

                    token = RSVPTokenService().create_token(outing_id, member_id)
                    rsvp_link = (
                        f"http://{RSVP_SERVER_HOST}:{RSVP_SERVER_PORT}"
                        f"/rsvp/yes?token={token}"
                    )

                    body_text, body_html = self._inject_rsvp_link(
                        body_text=body_text,
                        body_html=body_html,
                        rsvp_link=rsvp_link,
                    )

                elif template_type in {"pairings", "revised_pairings"}:
                    personalized_schedule_html = (
                        self.draft_service._apply_member_pairings_html(
                            draft=draft,
                            outing_id=outing_id,
                            member_id=member_id,
                        )
                    )

                    tee_times = self.outing_service.get_tee_times(outing_id)
                    assignments = self.outing_service.get_assignments(outing_id)

                    fresh_schedule_text = (
                        self.draft_service.schedule_render_service.render_text(
                            outing_id=outing_id,
                            tee_times=tee_times,
                            assignments=assignments,
                        )
                    )

                    body_lines = []
                    for line in body_text.splitlines():
                        if not self.draft_service._is_schedule_line(line):
                            body_lines.append(line)

                    body_text = "\n".join(body_lines).rstrip()
                    body_text = f"{body_text}\n\n{fresh_schedule_text}"

                    body_html = self.draft_service._build_pairings_html_from_body_text(
                        body_text=body_text,
                        schedule_html=personalized_schedule_html,
                    )
                    body_text, body_html = self._inject_cancel_link(
                        outing_id=outing_id,
                        member_id=member_id,
                        body_text=body_text,
                        body_html=body_html,
                    )

                subject_text = f"[TEST: {member['last_name']}] {subject_text}"

                test_header = (
                    "[TEST MODE]\n"
                    f"Generated for: {member['first_name']} {member['last_name']}\n"
                    f"Original email: {member['email'] or ''}\n\n"
                )
                body_text = test_header + body_text

                if body_html is not None:
                    test_html_header = (
                        "<div style='border:1px solid #ccc;padding:12px;margin-bottom:16px;'>"
                        "<strong>TEST MODE</strong><br>"
                        f"Generated for: {member['first_name']} {member['last_name']}<br>"
                        f"Original email: {member['email'] or ''}"
                        "</div>"
                    )
                    body_html = test_html_header + body_html

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

        if sent > 0:
            self.draft_service.mark_sent(
                outing_id,
                "member",
                template_type,
            )

            if hasattr(self, "workflow_service"):
                self.workflow_service.advance_after_member_email_send(
                    outing_id=outing_id,
                    template_type=template_type,
                    sent_count=sent,
                )

        return {
            "attempted": attempted,
            "sent_count": sent,
            "skipped": skipped,
            "failed": failed,
        }
