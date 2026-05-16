from repositories.course_contact_repository import CourseContactRepository


class CourseContactService:
    def __init__(self, db):
        self.repo = CourseContactRepository(db)

    def list_for_course(self, course_id: int, active_only: bool = False):
        return self.repo.list_for_course(course_id, active_only=active_only)

    def get_contact(self, contact_id: int):
        return self.repo.get(contact_id)

    def create_contact(self, data: dict) -> int:
        self._validate(data)
        return self.repo.create(data)

    def update_contact(self, contact_id: int, data: dict) -> None:
        self._validate(data)
        self.repo.update(contact_id, data)

    def delete_contact(self, contact_id: int) -> None:
        self.repo.delete(contact_id)

    def _validate(self, data: dict) -> None:
        if not str(data.get("first_name", "")).strip():
            raise ValueError("First name is required.")

        if not str(data.get("last_name", "")).strip():
            raise ValueError("Last name is required.")

        if not int(data.get("course_id", 0)):
            raise ValueError("Course is required.")
