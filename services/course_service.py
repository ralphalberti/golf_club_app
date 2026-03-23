from repositories.course_repository import CourseRepository

class CourseService:
    def __init__(self, db):
        self.repo = CourseRepository(db)

    def list_courses(self):
        return self.repo.list_all()

    def create_course(self, data: dict) -> int:
        return self.repo.create(data)

    def update_course(self, course_id: int, data: dict) -> None:
        self.repo.update(course_id, data)

    def delete_course(self, course_id: int) -> None:
        self.repo.delete(course_id)

    def get_course(self, course_id: int):
        return self.repo.get(course_id)
