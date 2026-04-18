from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from services.outing_email_draft_service import OutingEmailDraftService
from services.outing_service import OutingService
from services.rsvp_service import RSVPService


@dataclass(frozen=True)
class WorkflowTimingRules:
    """
    Centralized timing rules for the club's current workflow.

    These are intentionally isolated here so they can later be moved into
    settings/admin configuration without changing the rest of the workflow code.
    """

    invitation_to_schedule_days: int = 2
    course_hold_lead_days: int = 5
    course_final_schedule_lead_days: int = 2


class OutingWorkflowService:
    """
    Coordinates outing workflow decisions across:
    - RSVP stage
    - email draft/sent state
    - schedule/assignment state

    This service is intentionally read-heavy and side-effect-light, except for
    stage transition helpers that are explicitly called after known events.
    """

    VALID_MEMBER_TEMPLATE_TYPES = {
        "invitation",
        "pairings",
        "revised_pairings",
    }

    VALID_COURSE_TEMPLATE_TYPES = {
        "course_hold_request",
        "course_final_schedule",
    }

    def __init__(self, db):
        self.db = db
        self.rsvp_service = RSVPService(db)
        self.draft_service = OutingEmailDraftService(db)
        self.outing_service = OutingService(db)
        self.rules = WorkflowTimingRules()

    # -------------------------------------------------------------------------
    # Public summary / recommendation methods
    # -------------------------------------------------------------------------

    def get_workflow_snapshot(self, outing_id: int) -> dict[str, Any]:
        """
        Returns a single summary payload that UI code can use to drive labels,
        default template selection, and next-step hints.
        """
        outing = self.outing_service.get_outing(outing_id)
        if not outing:
            raise ValueError(f"Outing not found: {outing_id}")

        current_stage = self.sync_stage_with_current_state(outing_id)
        assignments = self.outing_service.get_assignments(outing_id)
        tee_times = self.outing_service.get_tee_times(outing_id)
        rsvp_rows = self.rsvp_service.list_member_rsvps_for_outing(outing_id)

        invited_count = len(rsvp_rows)
        yes_count = sum(1 for row in rsvp_rows if str(row["status"] or "") == "yes")
        no_count = sum(1 for row in rsvp_rows if str(row["status"] or "") == "no")
        maybe_count = sum(1 for row in rsvp_rows if str(row["status"] or "") == "maybe")
        pending_count = sum(
            1 for row in rsvp_rows if str(row["status"] or "") == "invited"
        )

        capacity = sum(int(row["max_players"]) for row in tee_times)
        assigned_count = len(assignments)

        invitation_draft = self._get_member_draft(outing_id, "invitation")
        pairings_draft = self._get_member_draft(outing_id, "pairings")
        revised_pairings_draft = self._get_member_draft(outing_id, "revised_pairings")
        course_hold_draft = self._get_course_draft(outing_id, "course_hold_request")
        course_final_draft = self._get_course_draft(
            outing_id,
            "course_final_schedule",
        )

        recommended_member_template = self.get_recommended_member_template(outing_id)
        recommended_course_template = self.get_recommended_course_template(outing_id)
        recommended_next_step = self.get_recommended_next_step(outing_id)

        return {
            "outing_id": outing_id,
            "outing_date": str(outing["outing_date"]),
            "current_stage": str(current_stage or ""),
            "invited_count": invited_count,
            "yes_count": yes_count,
            "no_count": no_count,
            "maybe_count": maybe_count,
            "pending_count": pending_count,
            "capacity": capacity,
            "assigned_count": assigned_count,
            "has_assignments": bool(assignments),
            "schedule_generated": bool(assignments),
            "schedule_revision_detected": self.is_revised_pairings_needed(outing_id),
            "should_generate_schedule_now": self.should_generate_schedule_now(
                outing_id
            ),
            "should_send_course_hold_now": self.should_send_course_hold_now(outing_id),
            "should_send_course_final_now": self.should_send_course_final_now(
                outing_id
            ),
            "recommended_member_template": recommended_member_template,
            "recommended_course_template": recommended_course_template,
            "recommended_next_step": recommended_next_step,
            "invitation_draft_status": self._draft_status(invitation_draft),
            "pairings_draft_status": self._draft_status(pairings_draft),
            "revised_pairings_draft_status": self._draft_status(revised_pairings_draft),
            "course_hold_draft_status": self._draft_status(course_hold_draft),
            "course_final_draft_status": self._draft_status(course_final_draft),
            "invitation_sent_at": self._draft_sent_at(invitation_draft),
            "pairings_sent_at": self._draft_sent_at(pairings_draft),
            "revised_pairings_sent_at": self._draft_sent_at(revised_pairings_draft),
            "course_hold_sent_at": self._draft_sent_at(course_hold_draft),
            "course_final_sent_at": self._draft_sent_at(course_final_draft),
        }

    def get_recommended_member_template(self, outing_id: int) -> str:
        """
        Determine which member-facing template is the best default for the UI.
        """
        assignments = self.outing_service.get_assignments(outing_id)
        if not assignments:
            return "invitation"

        if self.is_revised_pairings_needed(outing_id):
            return "revised_pairings"

        pairings_draft = self._get_member_draft(outing_id, "pairings")
        if self._is_sent(pairings_draft):
            return "pairings"

        return "pairings"

    def get_recommended_course_template(self, outing_id: int) -> str:
        """
        Determine which course-facing template is most relevant now.
        """
        if self.should_send_course_final_now(outing_id):
            return "course_final_schedule"

        return "course_hold_request"

    def get_recommended_next_step(self, outing_id: int) -> str:
        outing = self.outing_service.get_outing(outing_id)
        if not outing:
            return "Outing not found"

        assignments = self.outing_service.get_assignments(outing_id)
        rsvp_rows = self.rsvp_service.list_member_rsvps_for_outing(outing_id)

        invitation_draft = self._get_member_draft(outing_id, "invitation")
        pairings_draft = self._get_member_draft(outing_id, "pairings")
        revised_pairings_draft = self._get_member_draft(outing_id, "revised_pairings")

        has_invited = bool(rsvp_rows)
        has_yes = any(str(r["status"] or "") == "yes" for r in rsvp_rows)

        # --- Start of workflow ---
        if not self._exists(invitation_draft):
            return "Prepare invitation draft"

        if not self._is_sent(invitation_draft):
            return "Send invitation email to members"

        # --- RSVP phase ---
        if not has_invited:
            return "Invite members to outing"

        if not has_yes:
            return "Wait for members to RSVP"

        # --- Scheduling ---
        if not assignments:
            return "Generate schedule"

        # --- Pairings ---
        if not self._is_sent(pairings_draft):
            return "Send pairings email to members"

        # --- Revised ---
        if self.is_revised_pairings_needed(outing_id):
            if not self._exists(revised_pairings_draft):
                return "Prepare revised pairings draft"
            if not self._is_sent(revised_pairings_draft):
                return "Send revised pairings email to members"

        return "Workflow looks current"

    # -------------------------------------------------------------------------
    # Timing / deadline logic
    # -------------------------------------------------------------------------

    def should_generate_schedule_now(self, outing_id: int) -> bool:
        """
        Business rule:
        schedule generation is eligible once invitations were sent at least
        N days ago.
        """
        invitation_draft = self._get_member_draft(outing_id, "invitation")
        invitation_sent_at = self._draft_sent_at(invitation_draft)
        if not invitation_sent_at:
            return False

        sent_dt = self._parse_iso_datetime(invitation_sent_at)
        if sent_dt is None:
            return False

        return self._now() >= sent_dt + timedelta(
            days=self.rules.invitation_to_schedule_days
        )

    def should_send_course_hold_now(self, outing_id: int) -> bool:
        """
        Course should know roughly how many tee times are needed at least
        X days before the outing date.
        """
        outing = self.outing_service.get_outing(outing_id)
        if not outing:
            return False

        outing_date = self._parse_iso_date(str(outing["outing_date"]))
        if outing_date is None:
            return False

        threshold = outing_date - timedelta(days=self.rules.course_hold_lead_days)
        return self._today() >= threshold

    def should_send_course_final_now(self, outing_id: int) -> bool:
        """
        Final pairings/revised pairings info to course should be ready at least
        Y days before play date.
        """
        outing = self.outing_service.get_outing(outing_id)
        if not outing:
            return False

        if not self.outing_service.get_assignments(outing_id):
            return False

        outing_date = self._parse_iso_date(str(outing["outing_date"]))
        if outing_date is None:
            return False

        threshold = outing_date - timedelta(
            days=self.rules.course_final_schedule_lead_days
        )
        return self._today() >= threshold

    # -------------------------------------------------------------------------
    # Schedule revision detection
    # -------------------------------------------------------------------------

    def is_revised_pairings_needed(self, outing_id: int) -> bool:
        """
        Revised pairings is only relevant if:
        - initial pairings were already sent
        - the schedule changed afterward

        Current implementation uses outing.version as a lightweight signal.
        Because version is incremented when schedules are generated/reshuffled,
        this method provides a good first pass without requiring schema changes.

        For a later refinement, store the outing version at send time in an
        email log table or metadata field for exact change detection.
        """
        pairings_draft = self._get_member_draft(outing_id, "pairings")
        if not self._is_sent(pairings_draft):
            return False

        outing = self.outing_service.get_outing(outing_id)
        if not outing:
            return False

        assignments = self.outing_service.get_assignments(outing_id)
        if not assignments:
            return False

        version = int(outing["version"] or 1)

        # Conservative first-pass rule:
        # - version 1 generally means original outing state
        # - once scheduling / reshuffling changes increment version further,
        #   pairings may need revision if the first pairings email was already sent.
        return version > 1

    # -------------------------------------------------------------------------
    # Stage transitions
    # -------------------------------------------------------------------------

    def advance_after_member_email_send(
        self,
        outing_id: int,
        template_type: str,
        sent_count: int,
    ) -> None:
        """
        Advance stage after a successful member email send.
        """
        if template_type not in self.VALID_MEMBER_TEMPLATE_TYPES:
            raise ValueError(f"Unsupported member template_type: {template_type}")

        if sent_count <= 0:
            return

        if template_type == "invitation":
            self.rsvp_service.set_outing_workflow_stage(outing_id, "invites_sent")
            return

        if template_type == "pairings":
            self.rsvp_service.set_outing_workflow_stage(outing_id, "players_notified")
            return

        if template_type == "revised_pairings":
            self.rsvp_service.set_outing_workflow_stage(outing_id, "schedule_revised")
            return

    def advance_after_course_email_send(
        self,
        outing_id: int,
        template_type: str,
        sent_count: int,
    ) -> None:
        """
        Advance stage after a successful course email send.
        """
        if template_type not in self.VALID_COURSE_TEMPLATE_TYPES:
            raise ValueError(f"Unsupported course template_type: {template_type}")

        if sent_count <= 0:
            return

        if template_type == "course_hold_request":
            self.rsvp_service.set_outing_workflow_stage(outing_id, "course_hold_sent")
            return

        if template_type == "course_final_schedule":
            self.rsvp_service.set_outing_workflow_stage(
                outing_id,
                "final_sent_to_course",
            )
            return

    def sync_stage_with_current_state(self, outing_id: int) -> str:
        """
        Compute the best-fit workflow stage from the currently known state and
        persist it if needed.

        This is useful when UI opens, after scheduling, or after edits.
        """
        target_stage = self._determine_best_stage(outing_id)
        current_stage = self.rsvp_service.get_outing_workflow_stage(outing_id)

        if target_stage and target_stage != current_stage:
            self.rsvp_service.set_outing_workflow_stage(outing_id, target_stage)

        return str(target_stage or current_stage or "")

    def mark_schedule_changed_after_pairings_if_needed(self, outing_id: int) -> str:
        """
        If pairings were already sent and the schedule now appears revised,
        move the outing into schedule_revised.
        """
        if self.is_revised_pairings_needed(outing_id):
            self.rsvp_service.set_outing_workflow_stage(outing_id, "schedule_revised")
            return "schedule_revised"

        return str(self.rsvp_service.get_outing_workflow_stage(outing_id) or "")

    # -------------------------------------------------------------------------
    # Internal stage logic
    # -------------------------------------------------------------------------

    def _determine_best_stage(self, outing_id: int) -> str:
        invitation_draft = self._get_member_draft(outing_id, "invitation")
        pairings_draft = self._get_member_draft(outing_id, "pairings")
        revised_pairings_draft = self._get_member_draft(outing_id, "revised_pairings")
        course_hold_draft = self._get_course_draft(outing_id, "course_hold_request")
        course_final_draft = self._get_course_draft(outing_id, "course_final_schedule")

        rsvp_rows = self.rsvp_service.list_member_rsvps_for_outing(outing_id)
        assignments = self.outing_service.get_assignments(outing_id)

        has_yes = any(str(row["status"] or "") == "yes" for row in rsvp_rows)
        has_invited = bool(rsvp_rows)

        if self._is_sent(course_final_draft):
            return "final_sent_to_course"

        if self.is_revised_pairings_needed(outing_id):
            return "schedule_revised"

        if self._is_sent(pairings_draft):
            return "players_notified"

        if assignments:
            return "schedule_generated"

        if has_invited:
            return "rsvp_in_progress"

        if self._is_sent(invitation_draft):
            return "invites_sent"

        if self._exists(invitation_draft):
            return "invites_prepared"

        return "draft"

    # -------------------------------------------------------------------------
    # Draft helpers
    # -------------------------------------------------------------------------

    def _get_member_draft(self, outing_id: int, template_type: str):
        return self.draft_service.get_draft(outing_id, "member", template_type)

    def _get_course_draft(self, outing_id: int, template_type: str):
        return self.draft_service.get_draft(outing_id, "course", template_type)

    def _exists(self, draft) -> bool:
        return draft is not None

    def _is_sent(self, draft) -> bool:
        if not draft:
            return False
        return str(draft["status"] or "") == "sent" and bool(draft["sent_at"])

    def _draft_status(self, draft) -> str:
        if not draft:
            return ""
        return str(draft["status"] or "")

    def _draft_sent_at(self, draft) -> str:
        if not draft or not draft["sent_at"]:
            return ""
        return str(draft["sent_at"])

    # -------------------------------------------------------------------------
    # Date / time helpers
    # -------------------------------------------------------------------------

    def _now(self) -> datetime:
        return datetime.now()

    def _today(self):
        return self._now().date()

    def _parse_iso_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None

        raw = str(value).strip()
        if not raw:
            return None

        # Handles common SQLite-ish values like:
        # 2026-04-11T10:30:00
        # 2026-04-11 10:30:00
        try:
            return datetime.fromisoformat(raw.replace(" ", "T"))
        except ValueError:
            return None

    def _parse_iso_date(self, value: str | None):
        if not value:
            return None

        raw = str(value).strip()
        if not raw:
            return None

        try:
            return datetime.fromisoformat(raw).date()
        except ValueError:
            pass

        try:
            return datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return None
