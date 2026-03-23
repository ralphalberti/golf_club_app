from __future__ import annotations

from repositories.base_repository import BaseRepository
from app.utils import build_tee_times, now_iso

class OutingRepository(BaseRepository):
    def list_all(self):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT o.*, c.name AS course_name
                FROM outings o
                JOIN courses c ON c.id = o.course_id
                ORDER BY o.outing_date DESC, o.start_time DESC
                """
            ).fetchall()

    def create(self, data: dict) -> int:
        now = now_iso()
        with self.db.get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO outings
                (outing_date, course_id, start_time, tee_interval_minutes, tee_time_count,
                 max_players_per_tee_time, status, version, notes, created_by, updated_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["outing_date"], data["course_id"], data.get("start_time", "10:00"),
                    data.get("tee_interval_minutes", 9), data.get("tee_time_count", 4),
                    data.get("max_players_per_tee_time", 4), data.get("status", "draft"),
                    data.get("version", 1), data.get("notes", ""), data.get("created_by"),
                    data.get("updated_by"), now, now,
                ),
            )
            outing_id = cur.lastrowid
            self._rebuild_tee_times(conn, outing_id)
            return outing_id

    def update(self, outing_id: int, data: dict) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE outings
                SET outing_date=?, course_id=?, start_time=?, tee_interval_minutes=?, tee_time_count=?,
                    max_players_per_tee_time=?, status=?, version=?, notes=?, updated_by=?, updated_at=?
                WHERE id=?
                """,
                (
                    data["outing_date"], data["course_id"], data.get("start_time", "10:00"),
                    data.get("tee_interval_minutes", 9), data.get("tee_time_count", 4),
                    data.get("max_players_per_tee_time", 4), data.get("status", "draft"),
                    data.get("version", 1), data.get("notes", ""), data.get("updated_by"),
                    now_iso(), outing_id,
                ),
            )
            self._rebuild_tee_times(conn, outing_id)

    def _rebuild_tee_times(self, conn, outing_id: int) -> None:
        outing = conn.execute("SELECT * FROM outings WHERE id=?", (outing_id,)).fetchone()
        existing = conn.execute(
            "SELECT COUNT(*) AS count FROM tee_time_assignments a JOIN tee_times t ON t.id=a.tee_time_id WHERE t.outing_id=?",
            (outing_id,),
        ).fetchone()["count"]
        if existing:
            return
        conn.execute("DELETE FROM tee_times WHERE outing_id=?", (outing_id,))
        tee_times = build_tee_times(outing["start_time"], outing["tee_interval_minutes"], outing["tee_time_count"])
        for idx, tee_time in enumerate(tee_times):
            conn.execute(
                "INSERT INTO tee_times (outing_id, tee_time, position_index, max_players, locked) VALUES (?, ?, ?, ?, 0)",
                (outing_id, tee_time, idx, outing["max_players_per_tee_time"]),
            )

    def get(self, outing_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT o.*, c.name AS course_name
                FROM outings o JOIN courses c ON c.id=o.course_id
                WHERE o.id=?
                """,
                (outing_id,),
            ).fetchone()

    def get_tee_times(self, outing_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                "SELECT * FROM tee_times WHERE outing_id=? ORDER BY position_index",
                (outing_id,),
            ).fetchall()

    def get_assignments(self, outing_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT a.*, t.tee_time, t.position_index,
                       m.first_name, m.last_name, m.email, m.handicap
                FROM tee_time_assignments a
                JOIN tee_times t ON t.id = a.tee_time_id
                JOIN members m ON m.id = a.member_id
                WHERE t.outing_id = ?
                ORDER BY t.position_index, a.player_order_in_group
                """,
                (outing_id,),
            ).fetchall()

    def replace_assignments(self, outing_id: int, grouped_member_ids: list[list[int]]) -> None:
        with self.db.get_conn() as conn:
            tee_times = conn.execute(
                "SELECT * FROM tee_times WHERE outing_id=? ORDER BY position_index",
                (outing_id,),
            ).fetchall()
            tee_time_ids = [row["id"] for row in tee_times]
            conn.execute(
                "DELETE FROM tee_time_assignments WHERE tee_time_id IN (SELECT id FROM tee_times WHERE outing_id=?)",
                (outing_id,),
            )
            for idx, members in enumerate(grouped_member_ids):
                if idx >= len(tee_time_ids):
                    break
                for order, member_id in enumerate(members, start=1):
                    conn.execute(
                        """
                        INSERT INTO tee_time_assignments (tee_time_id, member_id, player_order_in_group, status, locked, checked_in)
                        VALUES (?, ?, ?, 'scheduled', 0, 0)
                        """,
                        (tee_time_ids[idx], member_id, order),
                    )

    def increment_version(self, outing_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                "UPDATE outings SET version = version + 1, updated_at=? WHERE id=?",
                (now_iso(), outing_id),
            )
