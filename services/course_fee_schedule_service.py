from repositories.course_fee_schedule_repository import CourseFeeScheduleRepository


class CourseFeeScheduleService:
    def __init__(self, db):
        self.repo = CourseFeeScheduleRepository(db)

    def list_fee_schedules_for_course(self, course_id: int):
        return self.repo.list_for_course(course_id)

    def get_fee_schedule(self, fee_schedule_id: int):
        return self.repo.get(fee_schedule_id)

    def create_fee_schedule(self, data: dict) -> int:
        return self.repo.create(data)

    def update_fee_schedule(self, fee_schedule_id: int, data: dict) -> None:
        self.repo.update(fee_schedule_id, data)

    def delete_fee_schedule(self, fee_schedule_id: int) -> None:
        self.repo.delete(fee_schedule_id)

    def get_active_fee_for_date(self, course_id: int, outing_date: str):
        return self.repo.get_active_fee_for_date(course_id, outing_date)
