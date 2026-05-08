from __future__ import annotations

from repositories.base_repository import BaseRepository


class OutingAuditRepository(BaseRepository):
    def log(
        self,
        *,
        outing_id: int,
        member_id: int | None,
        action: str,
        details: str = "",
    ) -> None:
        action = action.strip()
        if not action:
            raise ValueError("Audit action is required.")

        with self.db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO outing_audit_log (
                    outing_id,
                    member_id,
                    action,
                    details,
                    created_at
                )
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (outing_id, member_id, action, details),
            )

    def list_for_outing(self, outing_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT
                    a.id,
                    a.outing_id,
                    a.member_id,
                    a.action,
                    a.details,
                    a.created_at,
                    m.first_name,
                    m.last_name
                FROM outing_audit_log a
                LEFT JOIN members m ON m.id = a.member_id
                WHERE a.outing_id = ?
                ORDER BY a.created_at DESC, a.id DESC
                """,
                (outing_id,),
            ).fetchall()
