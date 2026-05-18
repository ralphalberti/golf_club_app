from __future__ import annotations

from repositories.base_repository import BaseRepository
from app.utils import build_tee_times, now_iso


class OutingRepository(BaseRepository):
    def list_all(self):
        with self.db.get_conn() as conn:
            return conn.execute("""
                SELECT
                    o.id,
                    o.outing_date,
                    c.name AS course_name,
                    o.start_time,
                    o.notes,
                    o.status
                FROM outings o
                JOIN courses c ON c.id = o.course_id
                ORDER BY o.outing_date, o.start_time
                """).fetchall()

    def create(self, data: dict) -> int:
        now = now_iso()
        with self.db.get_conn() as conn:
            fee_value = data.get("fee")
            if fee_value in (None, ""):
                fee_value = self._lookup_fee_snapshot(
                    conn,
                    data["course_id"],
                    data["outing_date"],
                )

            cur = conn.execute(
                """
                INSERT INTO outings
                (outing_date, course_id, start_time, tee_interval_minutes, tee_time_count,
                 max_players_per_tee_time, status, version, notes, fee, created_by, updated_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["outing_date"],
                    data["course_id"],
                    data.get("start_time", "10:00"),
                    data.get("tee_interval_minutes", 9),
                    data.get("tee_time_count", 4),
                    data.get("max_players_per_tee_time", 4),
                    data.get("status", "draft"),
                    data.get("version", 1),
                    data.get("notes", ""),
                    fee_value,
                    data.get("created_by"),
                    data.get("updated_by"),
                    now,
                    now,
                ),
            )
            outing_id = cur.lastrowid
            if outing_id is None:
                raise RuntimeError("Failed to create outing.")

            self._rebuild_tee_times(conn, int(outing_id))
            return int(outing_id)

    def update(self, outing_id: int, data: dict) -> None:
        with self.db.get_conn() as conn:
            fee_value = data.get("fee")
            if fee_value in (None, ""):
                fee_value = self._lookup_fee_snapshot(
                    conn,
                    data["course_id"],
                    data["outing_date"],
                )

            conn.execute(
                """
                UPDATE outings
                SET outing_date=?, course_id=?, start_time=?, tee_interval_minutes=?, tee_time_count=?,
                    max_players_per_tee_time=?, status=?, version=?, notes=?, fee=?, updated_by=?, updated_at=?
                WHERE id=?
                """,
                (
                    data["outing_date"],
                    data["course_id"],
                    data.get("start_time", "10:00"),
                    data.get("tee_interval_minutes", 9),
                    data.get("tee_time_count", 4),
                    data.get("max_players_per_tee_time", 4),
                    data.get("status", "draft"),
                    data.get("version", 1),
                    data.get("notes", ""),
                    fee_value,
                    data.get("updated_by"),
                    now_iso(),
                    outing_id,
                ),
            )
            self._rebuild_tee_times(conn, outing_id)

    def _lookup_fee_snapshot(self, conn, course_id: int, outing_date: str):
        row = conn.execute(
            """
            SELECT fee
            FROM course_fee_schedules
            WHERE course_id = ?
              AND effective_start_date <= ?
              AND effective_end_date >= ?
            ORDER BY effective_start_date DESC, effective_end_date DESC
            LIMIT 1
            """,
            (course_id, outing_date, outing_date),
        ).fetchone()

        return row["fee"] if row else None

    def _rebuild_tee_times(self, conn, outing_id: int) -> None:
        outing = conn.execute(
            "SELECT * FROM outings WHERE id=?", (outing_id,)
        ).fetchone()
        existing = conn.execute(
            "SELECT COUNT(*) AS count FROM tee_time_assignments a JOIN tee_times t ON t.id=a.tee_time_id WHERE t.outing_id=?",
            (outing_id,),
        ).fetchone()["count"]
        if existing:
            return
        conn.execute("DELETE FROM tee_times WHERE outing_id=?", (outing_id,))
        tee_times = build_tee_times(
            outing["start_time"],
            outing["tee_interval_minutes"],
            outing["tee_time_count"],
        )
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
                SELECT
                    tta.id,
                    tta.tee_time_id,
                    tta.player_order_in_group,
                    tt.tee_time,
                    tt.position_index,
                    m.id AS member_id,
                    m.first_name,
                    m.last_name,
                    m.email,
                    m.handicap,
                    m.skill_tier
                FROM tee_time_assignments tta
                JOIN tee_times tt ON tt.id = tta.tee_time_id
                JOIN members m ON m.id = tta.member_id
                WHERE tt.outing_id = ?
                ORDER BY tt.position_index, tta.player_order_in_group, m.last_name, m.first_name
                """,
                (outing_id,),
            ).fetchall()

    def replace_assignments(
        self, outing_id: int, grouped_member_ids: list[list[int]]
    ) -> None:
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

    def delete_assignment(self, assignment_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                "DELETE FROM tee_time_assignments WHERE id = ?",
                (assignment_id,),
            )

    def delete_assignments_by_outing(self, outing_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                DELETE FROM tee_time_assignments
                WHERE tee_time_id IN (
                    SELECT id FROM tee_times WHERE outing_id = ?
                )
                """,
                (outing_id,),
            )

    def delete_tee_times_by_outing(self, outing_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                "DELETE FROM tee_times WHERE outing_id = ?",
                (outing_id,),
            )

    def delete_outing(self, outing_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                "DELETE FROM outings WHERE id = ?",
                (outing_id,),
            )

    def get_unassigned_members_for_outing(self, outing_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM members
                WHERE active = 1
                  AND id NOT IN (
                      SELECT tta.member_id
                      FROM tee_time_assignments tta
                      JOIN tee_times tt ON tt.id = tta.tee_time_id
                      WHERE tt.outing_id = ?
                  )
                ORDER BY last_name, first_name
                """,
                (outing_id,),
            ).fetchall()

    def add_assignment(
        self,
        tee_time_id: int,
        member_id: int,
        player_order_in_group: int,
    ) -> int:
        with self.db.get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO tee_time_assignments
                (tee_time_id, member_id, player_order_in_group, status, checked_in)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tee_time_id, member_id, player_order_in_group, "scheduled", 0),
            )
            assignment_id = cur.lastrowid
            if assignment_id is None:
                raise RuntimeError("Failed to add assignment.")
            return int(assignment_id)

    def delete_rounds_by_outing(self, outing_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                "DELETE FROM rounds WHERE outing_id = ?",
                (outing_id,),
            )

    def delete_email_logs_by_outing(self, outing_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                "DELETE FROM email_logs WHERE outing_id = ?",
                (outing_id,),
            )

    def is_member_assigned_for_outing(self, outing_id: int, member_id: int) -> bool:
        with self.db.get_conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM tee_time_assignments a
                JOIN tee_times t ON t.id = a.tee_time_id
                WHERE t.outing_id = ? AND a.member_id = ?
                """,
                (outing_id, member_id),
            ).fetchone()

        return int(row["count"]) > 0

    def get_tee_time_by_id(self, tee_time_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM tee_times
                WHERE id = ?
                """,
                (tee_time_id,),
            ).fetchone()

    def get_tee_time_player_count(self, tee_time_id: int) -> int:
        with self.db.get_conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM tee_time_assignments
                WHERE tee_time_id = ?
                """,
                (tee_time_id,),
            ).fetchone()

        return int(row["count"])

    def remove_member_from_schedule(self, outing_id: int, member_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                DELETE FROM tee_time_assignments
                WHERE member_id = ?
                  AND tee_time_id IN (
                      SELECT id FROM tee_times WHERE outing_id = ?
                  )
                """,
                (member_id, outing_id),
            )

    # NOTE:
    # This is guest-aware but still implemented at the repository layer.
    # Future refactor target:
    # move waitlist promotion into a service that uses SchedulingUnitService,
    # so guest sizing logic is not duplicated here.
    def auto_promote_waitlist(self, outing_id: int) -> None:
        with self.db.get_conn() as conn:
            row = conn.execute(
                """
                SELECT member_id
                FROM outing_rsvps
                WHERE outing_id = ?
                  AND status = 'yes'
                  AND member_id NOT IN (
                      SELECT tta.member_id
                      FROM tee_time_assignments tta
                      JOIN tee_times tt ON tt.id = tta.tee_time_id
                      WHERE tt.outing_id = ?
                  )
                ORDER BY responded_at ASC
                LIMIT 1
                """,
                (outing_id, outing_id),
            ).fetchone()

            if not row:
                return

            candidate_member_id = int(row["member_id"])
            candidate_size = self._guest_aware_member_size(
                conn,
                outing_id,
                candidate_member_id,
            )

            tee_times = conn.execute(
                """
                SELECT id, max_players
                FROM tee_times
                WHERE outing_id = ?
                ORDER BY position_index
                """,
                (outing_id,),
            ).fetchall()

            for tee_time in tee_times:
                tee_time_id = int(tee_time["id"])
                max_players = int(tee_time["max_players"])

                current_size = self._guest_aware_tee_time_size(
                    conn,
                    outing_id,
                    tee_time_id,
                )

                if current_size + candidate_size > max_players:
                    continue

                member_count = self._tee_time_assignment_count(conn, tee_time_id)

                conn.execute(
                    """
                    INSERT INTO tee_time_assignments (
                        tee_time_id,
                        member_id,
                        player_order_in_group,
                        status,
                        locked,
                        checked_in
                    )
                    VALUES (?, ?, ?, 'scheduled', 0, 0)
                    """,
                    (tee_time_id, candidate_member_id, member_count + 1),
                )
                return

    # NOTE:
    # This promotes only the first waitlisted RSVP-yes member.
    # If that member's sponsor+guest unit does not fit, no later member is promoted.
    # This preserves RSVP priority while preventing guests from creating fivesomes.
    def auto_promote_waitlist_to_tee_time(
        self,
        outing_id: int,
        tee_time_id: int,
    ) -> None:
        with self.db.get_conn() as conn:

            # 1. Get next waitlist member
            row = conn.execute(
                """
                SELECT member_id
                FROM outing_rsvps
                WHERE outing_id = ?
                  AND status = 'yes'
                  AND member_id NOT IN (
                      SELECT tta.member_id
                      FROM tee_time_assignments tta
                      JOIN tee_times tt ON tt.id = tta.tee_time_id
                      WHERE tt.outing_id = ?
                  )
                ORDER BY responded_at ASC
                LIMIT 1
                """,
                (outing_id, outing_id),
            ).fetchone()

            if not row:
                return

            candidate_member_id = int(row["member_id"])

            # 2. Get max players for tee time
            tee_time = conn.execute(
                """
                SELECT max_players
                FROM tee_times
                WHERE id = ?
                """,
                (tee_time_id,),
            ).fetchone()

            if not tee_time:
                return

            max_players = int(tee_time["max_players"])

            # 3. Count current players INCLUDING guests
            rows = conn.execute(
                """
                SELECT m.id AS member_id
                FROM tee_time_assignments tta
                JOIN members m ON m.id = tta.member_id
                WHERE tta.tee_time_id = ?
                """,
                (tee_time_id,),
            ).fetchall()

            total_players = 0

            for r in rows:
                sponsor_id = int(r["member_id"])

                # count sponsor
                total_players += 1

                # count sponsor guests
                guest_count = conn.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM outing_guests
                    WHERE outing_id = ?
                      AND sponsoring_member_id = ?
                      AND status = 'yes'
                    """,
                    (outing_id, sponsor_id),
                ).fetchone()["count"]

                total_players += int(guest_count)

            # 4. Count candidate size
            candidate_guest_count = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM outing_guests
                WHERE outing_id = ?
                  AND sponsoring_member_id = ?
                  AND status = 'yes'
                """,
                (outing_id, candidate_member_id),
            ).fetchone()["count"]

            candidate_size = 1 + int(candidate_guest_count)

            # 5. Check capacity
            if total_players + candidate_size > max_players:
                return  # cannot fit — do nothing

            # 6. Insert into THIS tee time
            conn.execute(
                """
                INSERT INTO tee_time_assignments (
                    tee_time_id,
                    member_id,
                    player_order_in_group,
                    status,
                    locked,
                    checked_in
                )
                VALUES (?, ?, ?, 'scheduled', 0, 0)
                """,
                (
                    tee_time_id,
                    candidate_member_id,
                    len(rows) + 1,
                ),
            )

    def _guest_aware_member_size(self, conn, outing_id: int, member_id: int) -> int:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM outing_guests
            WHERE outing_id = ?
              AND sponsoring_member_id = ?
              AND status = 'yes'
            """,
            (outing_id, member_id),
        ).fetchone()

        return 1 + int(row["count"] or 0)

    def _guest_aware_tee_time_size(self, conn, outing_id: int, tee_time_id: int) -> int:
        rows = conn.execute(
            """
            SELECT member_id
            FROM tee_time_assignments
            WHERE tee_time_id = ?
              AND status = 'scheduled'
            """,
            (tee_time_id,),
        ).fetchall()

        total = 0
        for row in rows:
            total += self._guest_aware_member_size(
                conn,
                outing_id,
                int(row["member_id"]),
            )

        return total

    def _tee_time_assignment_count(self, conn, tee_time_id: int) -> int:
        row = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM tee_time_assignments
            WHERE tee_time_id = ?
              AND status = 'scheduled'
            """,
            (tee_time_id,),
        ).fetchone()

        return int(row["count"] or 0)

    def get_member_tee_time_id_for_outing(
        self,
        outing_id: int,
        member_id: int,
    ) -> int | None:
        with self.db.get_conn() as conn:
            row = conn.execute(
                """
                SELECT tta.tee_time_id
                FROM tee_time_assignments tta
                JOIN tee_times tt ON tt.id = tta.tee_time_id
                WHERE tt.outing_id = ?
                  AND tta.member_id = ?
                LIMIT 1
                """,
                (outing_id, member_id),
            ).fetchone()

        return int(row["tee_time_id"]) if row else None

    def get_email_delivery_summary(self, outing_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT
                    recipient_type,
                    subject,
                    status,
                    COUNT(*) AS count,
                    MAX(sent_at) AS last_at
                FROM email_logs
                WHERE outing_id = ?
                GROUP BY recipient_type, subject, status
                ORDER BY last_at DESC
                """,
                (outing_id,),
            ).fetchall()
