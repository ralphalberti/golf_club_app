from repositories.base_repository import BaseRepository
from app.utils import now_iso


class RSVPRepository(BaseRepository):
    VALID_STATUSES = {"invited", "yes", "no", "maybe"}

    def list_member_rsvps_for_outing(self, outing_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT
                    r.id,
                    r.outing_id,
                    r.member_id,
                    r.status,
                    r.responded_at,
                    r.note,
                    m.first_name,
                    m.last_name,
                    m.email,
                    m.phone,
                    m.skill_tier,
                    m.active
                FROM outing_rsvps r
                JOIN members m ON m.id = r.member_id
                WHERE r.outing_id = ?
                ORDER BY m.last_name, m.first_name
                """,
                (outing_id,),
            ).fetchall()

    def list_uninvited_active_members_for_outing(self, outing_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM members
                WHERE active = 1
                  AND id NOT IN (
                      SELECT member_id
                      FROM outing_rsvps
                      WHERE outing_id = ?
                  )
                ORDER BY last_name, first_name
                """,
                (outing_id,),
            ).fetchall()

    def invite_members(self, outing_id: int, member_ids: list[int]) -> None:
        if not member_ids:
            return

        now = now_iso()
        with self.db.get_conn() as conn:
            for member_id in member_ids:
                conn.execute(
                    """
                    INSERT INTO outing_rsvps (
                        outing_id,
                        member_id,
                        status,
                        responded_at,
                        note,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, 'invited', NULL, '', ?, ?)
                    ON CONFLICT(outing_id, member_id) DO NOTHING
                    """,
                    (outing_id, member_id, now, now),
                )

    def set_member_rsvp_status(
        self,
        outing_id: int,
        member_id: int,
        status: str,
        note: str = "",
    ) -> None:
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid RSVP status: {status}")

        now = now_iso()
        responded_at = now if status in {"yes", "no", "maybe"} else None

        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE outing_rsvps
                SET status = ?, responded_at = ?, note = ?, updated_at = ?
                WHERE outing_id = ? AND member_id = ?
                """,
                (status, responded_at, note, now, outing_id, member_id),
            )

    def remove_member_rsvp(self, outing_id: int, member_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                DELETE FROM outing_rsvps
                WHERE outing_id = ? AND member_id = ?
                """,
                (outing_id, member_id),
            )

    def get_schedulable_member_ids(self, outing_id: int) -> list[int]:
        with self.db.get_conn() as conn:
            rows = conn.execute(
                """
                SELECT member_id
                FROM outing_rsvps
                WHERE outing_id = ? AND status = 'yes'
                ORDER BY member_id
                """,
                (outing_id,),
            ).fetchall()

        return [int(row["member_id"]) for row in rows]

    def update_outing_workflow_stage(self, outing_id: int, workflow_stage: str) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE outings
                SET workflow_stage = ?
                WHERE id = ?
                """,
                (workflow_stage, outing_id),
            )

    def get_outing_workflow_stage(self, outing_id: int):
        with self.db.get_conn() as conn:
            row = conn.execute(
                """
                SELECT workflow_stage
                FROM outings
                WHERE id = ?
                """,
                (outing_id,),
            ).fetchone()

        return row["workflow_stage"] if row else None
