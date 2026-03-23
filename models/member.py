from dataclasses import dataclass

@dataclass
class Member:
    id: int | None
    first_name: str
    last_name: str
    email: str = ""
    phone: str = ""
    handicap: float = 0.0
    joined_date: str = ""
    active: int = 1
    notes: str = ""
