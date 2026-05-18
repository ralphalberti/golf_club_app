from dataclasses import dataclass


@dataclass
class Facility:
    id: int | None

    name: str

    address: str = ""
    phone: str = ""
    website: str = ""

    notes: str = ""

    active: int = 1
