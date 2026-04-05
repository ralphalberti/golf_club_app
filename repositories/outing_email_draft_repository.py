from repositories.base_repository import BaseRepository
from app.utils import now_iso


class OutingEmailDraftRepository(BaseRepository):
    VALID_AUDIENCE_TYPES = {"member", "course"}
    VALID_TEMPLATE_TYPES = {
        "invitation",
        "pairings",
        "revised_pairings",
        "course_hold_request",
        "course_final_schedule",
    }
    VALID_STATUSES = {"draft", "sent"}

    def get_draft(
        self,
        outing_id: int,
        audience_type: str,
        template_type: str,
    ):
        self._validate_types(audience_type, template_type)

        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM outing_email_drafts
                WHERE outing_id = ?
                  AND audience_type = ?
                  AND template_type = ?
                """,
                (outing_id, audience_type, template_type),
            ).fetchone()

    def upsert_draft(
        self,
        *,
        outing_id: int,
        audience_type: str,
        template_type: str,
        subject_text: str,
        body_text: str,
        body_html: str | None = None,
        status: str = "draft",
        sent_at: str | None = None,
    ) -> int:
        self._validate_types(audience_type, template_type)

        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid draft status: {status}")

        now = now_iso()

        with self.db.get_conn() as conn:
            existing = conn.execute(
                """
                SELECT id
                FROM outing_email_drafts
                WHERE outing_id = ?
                  AND audience_type = ?
                  AND template_type = ?
                """,
                (outing_id, audience_type, template_type),
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE outing_email_drafts
                    SET subject_text = ?,
                        body_text = ?,
                        body_html = ?,
                        status = ?,
                        sent_at = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        subject_text,
                        body_text,
                        body_html,
                        status,
                        sent_at,
                        now,
                        int(existing["id"]),
                    ),
                )
                return int(existing["id"])

            cur = conn.execute(
                """
                INSERT INTO outing_email_drafts (
                    outing_id,
                    audience_type,
                    template_type,
                    subject_text,
                    body_text,
                    body_html,
                    status,
                    sent_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outing_id,
                    audience_type,
                    template_type,
                    subject_text,
                    body_text,
                    body_html,
                    status,
                    sent_at,
                    now,
                    now,
                ),
            )
            return int(cur.lastrowid)

    def mark_sent(
        self,
        outing_id: int,
        audience_type: str,
        template_type: str,
    ) -> None:
        self._validate_types(audience_type, template_type)

        now = now_iso()

        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE outing_email_drafts
                SET status = 'sent',
                    sent_at = ?,
                    updated_at = ?
                WHERE outing_id = ?
                  AND audience_type = ?
                  AND template_type = ?
                """,
                (now, now, outing_id, audience_type, template_type),
            )

    def delete_draft(
        self,
        outing_id: int,
        audience_type: str,
        template_type: str,
    ) -> None:
        self._validate_types(audience_type, template_type)

        with self.db.get_conn() as conn:
            conn.execute(
                """
                DELETE FROM outing_email_drafts
                WHERE outing_id = ?
                  AND audience_type = ?
                  AND template_type = ?
                """,
                (outing_id, audience_type, template_type),
            )

    def _validate_types(self, audience_type: str, template_type: str) -> None:
        if audience_type not in self.VALID_AUDIENCE_TYPES:
            raise ValueError(f"Invalid audience_type: {audience_type}")

        if template_type not in self.VALID_TEMPLATE_TYPES:
            raise ValueError(f"Invalid template_type: {template_type}")
