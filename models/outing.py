from dataclasses import dataclass

@dataclass
class Outing:
    id: int | None
    outing_date: str
    course_id: int
    start_time: str = "10:00"
    tee_interval_minutes: int = 9
    tee_time_count: int = 4
    max_players_per_tee_time: int = 4
    status: str = "draft"
    version: int = 1
    notes: str = ""
    created_by: int | None = None
    updated_by: int | None = None
