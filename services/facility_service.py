from repositories.facility_repository import FacilityRepository


class FacilityService:
    def __init__(self, db):
        self.repo = FacilityRepository(db)

    def list_facilities(self, active_only: bool = False):
        return self.repo.list_all(active_only=active_only)

    def get_facility(self, facility_id: int):
        return self.repo.get(facility_id)

    def create_facility(self, data: dict) -> int:
        self._validate(data)
        return self.repo.create(data)

    def update_facility(self, facility_id: int, data: dict) -> None:
        self._validate(data)
        self.repo.update(facility_id, data)

    def delete_facility(self, facility_id: int) -> None:
        self.repo.delete(facility_id)

    def _validate(self, data: dict):
        if not str(data.get("name", "")).strip():
            raise ValueError("Facility name is required.")
