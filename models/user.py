from dataclasses import dataclass


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    role: str
    member_id: int | None = None
    active: int = 1
    created_at: str = ""
    updated_at: str = ""
