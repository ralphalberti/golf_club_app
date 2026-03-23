from dataclasses import dataclass

@dataclass
class Course:
    id: int | None
    name: str
    address: str = ""
    active: int = 1
    notes: str = ""
    contact_name: str = ""
    contact_email: str = ""
    preferred_format: str = "both"
