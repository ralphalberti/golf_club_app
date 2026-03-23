from __future__ import annotations

from db.connection import Database

class BaseRepository:
    def __init__(self, db: Database):
        self.db = db
