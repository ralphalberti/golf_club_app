from repositories.base_repository import BaseRepository
from app.utils import now_iso


class FacilityRepository(BaseRepository):
    def list_all(self, active_only: bool = False):
        with self.db.get_conn() as conn:
            sql = """
                SELECT *
                FROM facilities
            """

            if active_only:
                sql += " WHERE active = 1"

            sql += " ORDER BY name"

            return conn.execute(sql).fetchall()

    def get(self, facility_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM facilities
                WHERE id = ?
                """,
                (facility_id,),
            ).fetchone()

    def create(self, data: dict) -> int:
        now = now_iso()

        with self.db.get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO facilities (
                    name,
                    address,
                    phone,
                    website,
                    notes,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["name"].strip(),
                    data.get("address", "").strip(),
                    data.get("phone", "").strip(),
                    data.get("website", "").strip(),
                    data.get("notes", "").strip(),
                    int(data.get("active", 1)),
                    now,
                    now,
                ),
            )

            return int(cur.lastrowid)

    def update(self, facility_id: int, data: dict) -> None:
        now = now_iso()

        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE facilities
                SET
                    name = ?,
                    address = ?,
                    phone = ?,
                    website = ?,
                    notes = ?,
                    active = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    data["name"].strip(),
                    data.get("address", "").strip(),
                    data.get("phone", "").strip(),
                    data.get("website", "").strip(),
                    data.get("notes", "").strip(),
                    int(data.get("active", 1)),
                    now,
                    facility_id,
                ),
            )

    def delete(self, facility_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                DELETE FROM facilities
                WHERE id = ?
                """,
                (facility_id,),
            )
