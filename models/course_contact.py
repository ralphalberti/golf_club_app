from dataclasses import dataclass


@dataclass
class CourseContact:
    id: int | None
    course_id: int

    first_name: str
    last_name: str

    title: str = ""
    email: str = ""
    phone: str = ""

    notes: str = ""

    active: int = 1

    receives_hold_requests: int = 1
    receives_final_schedule: int = 1
