from repositories.base_repository import BaseRepository
from app.utils import now_iso


class CourseFeeScheduleRepository(BaseRepository):
    def list_for_course(self, course_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM course_fee_schedules
                WHERE course_id = ?
                ORDER BY effective_start_date DESC, effective_end_date DESC
                """,
                (course_id,),
            ).fetchall()

    def get(self, fee_schedule_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM course_fee_schedules
                WHERE id = ?
                """,
                (fee_schedule_id,),
            ).fetchone()

    def create(self, data: dict) -> int:
        now = now_iso()
        with self.db.get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO course_fee_schedules (
                    course_id,
                    fee,
                    effective_start_date,
                    effective_end_date,
                    notes,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["course_id"],
                    data["fee"],
                    data["effective_start_date"],
                    data["effective_end_date"],
                    data.get("notes", ""),
                    now,
                    now,
                ),
            )
            fee_schedule_id = cur.lastrowid
            if fee_schedule_id is None:
                raise RuntimeError("Failed to create course fee schedule.")
            return int(fee_schedule_id)

    def update(self, fee_schedule_id: int, data: dict) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE course_fee_schedules
                SET course_id = ?,
                    fee = ?,
                    effective_start_date = ?,
                    effective_end_date = ?,
                    notes = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    data["course_id"],
                    data["fee"],
                    data["effective_start_date"],
                    data["effective_end_date"],
                    data.get("notes", ""),
                    now_iso(),
                    fee_schedule_id,
                ),
            )

    def delete(self, fee_schedule_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                "DELETE FROM course_fee_schedules WHERE id = ?",
                (fee_schedule_id,),
            )

    def get_active_fee_for_date(self, course_id: int, outing_date: str):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM course_fee_schedules
                WHERE course_id = ?
                  AND effective_start_date <= ?
                  AND effective_end_date >= ?
                ORDER BY effective_start_date DESC, effective_end_date DESC
                LIMIT 1
                """,
                (course_id, outing_date, outing_date),
            ).fetchone()
