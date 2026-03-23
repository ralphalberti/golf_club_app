from repositories.outing_repository import OutingRepository

class OutingService:
    def __init__(self, db):
        self.repo = OutingRepository(db)

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

    def replace_assignments(self, outing_id: int, grouped_member_ids: list[list[int]]) -> None:
        self.repo.replace_assignments(outing_id, grouped_member_ids)

    def increment_version(self, outing_id: int) -> None:
        self.repo.increment_version(outing_id)
