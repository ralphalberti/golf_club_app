from repositories.outing_repository import OutingRepository
from services.scheduling_service import SchedulingService


class OutingService:
    def __init__(self, db):
        self.repo = OutingRepository(db)
        self.scheduling_service = SchedulingService(db)

    def list_outings(self):
        return self.repo.list_all()

    def create_outing(self, data: dict) -> int:
        return self.repo.create(data)

    def update_outing(self, outing_id: int, data: dict) -> None:
        self.repo.update(outing_id, data)

    def get_outing(self, outing_id: int):
        return self.repo.get(outing_id)

    def get_tee_times(self, outing_id: int):
        return self.repo.get_tee_times(outing_id)

    def get_assignments(self, outing_id: int):
        return self.repo.get_assignments(outing_id)

    def replace_assignments(
        self, outing_id: int, grouped_member_ids: list[list[int]]
    ) -> None:
        self.repo.replace_assignments(outing_id, grouped_member_ids)

    def increment_version(self, outing_id: int) -> None:
        self.repo.increment_version(outing_id)

    def remove_assignment(self, assignment_id: int) -> None:
        self.repo.delete_assignment(assignment_id)

    def delete_outing(self, outing_id: int) -> None:
        self.repo.delete_assignments_by_outing(outing_id)
        self.repo.delete_tee_times_by_outing(outing_id)
        self.repo.delete_outing(outing_id)

    def get_unassigned_members_for_outing(self, outing_id: int):
        return self.repo.get_unassigned_members_for_outing(outing_id)

    def add_member_to_tee_time(
        self, outing_id: int, tee_time_id: int, member_id: int
    ) -> int:
        tee_times = self.get_tee_times(outing_id)
        target_tee_time = None

        for row in tee_times:
            if int(row["id"]) == int(tee_time_id):
                target_tee_time = row
                break

        if not target_tee_time:
            raise ValueError("Selected tee time was not found.")

        max_players = int(target_tee_time["max_players"])
        current_count = self.repo.get_tee_time_player_count(tee_time_id)

        if current_count >= max_players:
            raise ValueError("Selected tee time is already full.")

        player_order_in_group = current_count + 1

        return self.repo.add_assignment(
            tee_time_id=tee_time_id,
            member_id=member_id,
            player_order_in_group=player_order_in_group,
        )

    def reshuffle_schedule(self, outing_id: int):
        return self.scheduling_service.reshuffle_schedule(outing_id)

    def validate_existing_schedule(self, outing_id: int) -> None:
        self.scheduling_service.validate_existing_schedule(outing_id)
