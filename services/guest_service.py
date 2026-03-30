from repositories.guest_repository import GuestRepository


class GuestService:
    def __init__(self, db):
        self.repo = GuestRepository(db)

    def list_guests(self, active_only: bool = True):
        return self.repo.list_all_guests(active_only=active_only)

    def create_guest(self, data: dict) -> int:
        return self.repo.create_guest(data)

    def update_guest(self, guest_id: int, data: dict) -> None:
        self.repo.update_guest(guest_id, data)

    def get_guest(self, guest_id: int):
        return self.repo.get_guest(guest_id)

    def delete_guest(self, guest_id: int) -> None:
        self.repo.delete_guest(guest_id)

    def list_outing_guests(self, outing_id: int):
        return self.repo.list_outing_guests(outing_id)

    def add_guest_to_outing(
        self,
        outing_id: int,
        guest_id: int,
        sponsoring_member_id: int,
        status: str = "invited",
        note: str = "",
    ) -> None:
        self.repo.add_guest_to_outing(
            outing_id=outing_id,
            guest_id=guest_id,
            sponsoring_member_id=sponsoring_member_id,
            status=status,
            note=note,
        )

    def set_outing_guest_status(
        self,
        outing_id: int,
        guest_id: int,
        status: str,
        note: str = "",
    ) -> None:
        self.repo.set_outing_guest_status(
            outing_id=outing_id,
            guest_id=guest_id,
            status=status,
            note=note,
        )

    def remove_guest_from_outing(self, outing_id: int, guest_id: int) -> None:
        self.repo.remove_guest_from_outing(outing_id, guest_id)

    def list_schedulable_outing_guests(self, outing_id: int):
        return self.repo.list_schedulable_outing_guests(outing_id)
