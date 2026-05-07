from repositories.rsvp_repository import RSVPRepository


class RSVPService:
    VALID_WORKFLOW_STAGES = {
        "draft",
        "invites_prepared",
        "invites_sent",
        "rsvp_in_progress",
        "schedule_generated",
        "course_hold_sent",
        "players_notified",
        "schedule_revised",
        "final_sent_to_course",
        "completed",
    }

    def __init__(self, db):
        self.repo = RSVPRepository(db)

    def list_member_rsvps_for_outing(self, outing_id: int):
        return self.repo.list_member_rsvps_for_outing(outing_id)

    def list_uninvited_active_members_for_outing(self, outing_id: int):
        return self.repo.list_uninvited_active_members_for_outing(outing_id)

    def invite_members(self, outing_id: int, member_ids: list[int]) -> None:
        self.repo.invite_members(outing_id, member_ids)

    def invite_all_active_members(self, outing_id: int) -> None:
        rows = self.repo.list_uninvited_active_members_for_outing(outing_id)
        member_ids = [int(row["id"]) for row in rows]
        self.repo.invite_members(outing_id, member_ids)

    def set_member_rsvp_status(
        self,
        outing_id: int,
        member_id: int,
        status: str,
        note: str = "",
    ) -> None:
        self.repo.set_member_rsvp_status(outing_id, member_id, status, note)

    def remove_member_rsvp(self, outing_id: int, member_id: int) -> None:
        self.repo.remove_member_rsvp(outing_id, member_id)

    def get_schedulable_member_ids(self, outing_id: int) -> list[int]:
        return self.repo.get_schedulable_member_ids(outing_id)

    def get_outing_workflow_stage(self, outing_id: int):
        return self.repo.get_outing_workflow_stage(outing_id)

    def set_outing_workflow_stage(self, outing_id: int, workflow_stage: str) -> None:
        if workflow_stage not in self.VALID_WORKFLOW_STAGES:
            raise ValueError(f"Invalid workflow stage: {workflow_stage}")
        self.repo.update_outing_workflow_stage(outing_id, workflow_stage)
