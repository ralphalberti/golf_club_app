from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Iterable

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

def build_tee_times(start_time: str, interval_minutes: int, count: int) -> list[str]:
    start = datetime.strptime(start_time, "%H:%M")
    return [
        (start + timedelta(minutes=interval_minutes * i)).strftime("%H:%M")
        for i in range(count)
    ]

def fullname(first_name: str, last_name: str) -> str:
    return f"{first_name} {last_name}".strip()

def pairwise(values: Iterable[int]) -> list[tuple[int, int]]:
    vals = list(values)
    pairs: list[tuple[int, int]] = []
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            a, b = vals[i], vals[j]
            pairs.append((min(a, b), max(a, b)))
    return pairs
