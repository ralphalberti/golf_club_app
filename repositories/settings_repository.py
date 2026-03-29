from repositories.base_repository import BaseRepository


class SettingsRepository(BaseRepository):
    def get(self, key: str):
        with self.db.get_conn() as conn:
            row = conn.execute(
                """
                SELECT value
                FROM settings
                WHERE key = ?
                """,
                (key,),
            ).fetchone()

        if row is None:
            return None

        return row["value"]

    def set(self, key: str, value: str) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def get_all(self) -> dict[str, str]:
        with self.db.get_conn() as conn:
            rows = conn.execute("""
                SELECT key, value
                FROM settings
                ORDER BY key
                """).fetchall()

        return {row["key"]: row["value"] for row in rows}

    def set_many(self, values: dict[str, str]) -> None:
        if not values:
            return

        with self.db.get_conn() as conn:
            conn.executemany(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                [(key, value) for key, value in values.items()],
            )
