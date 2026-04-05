from repositories.base_repository import BaseRepository
from app.utils import now_iso


class EmailTemplateRepository(BaseRepository):
    VALID_AUDIENCE_TYPES = {"member", "course"}
    VALID_TEMPLATE_TYPES = {
        "invitation",
        "pairings",
        "revised_pairings",
        "course_hold_request",
        "course_final_schedule",
    }

    def list_all(self):
        with self.db.get_conn() as conn:
            return conn.execute("""
                SELECT *
                FROM email_templates
                ORDER BY
                    CASE WHEN course_id IS NULL THEN 0 ELSE 1 END,
                    course_id,
                    audience_type,
                    template_type
                """).fetchall()

    def list_for_course(self, course_id: int | None):
        with self.db.get_conn() as conn:
            if course_id is None:
                return conn.execute("""
                    SELECT *
                    FROM email_templates
                    WHERE course_id IS NULL
                    ORDER BY audience_type, template_type
                    """).fetchall()

            return conn.execute(
                """
                SELECT *
                FROM email_templates
                WHERE course_id = ?
                ORDER BY audience_type, template_type
                """,
                (course_id,),
            ).fetchall()

    def get_by_id(self, template_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM email_templates
                WHERE id = ?
                """,
                (template_id,),
            ).fetchone()

    def get_exact_match(
        self,
        course_id: int | None,
        audience_type: str,
        template_type: str,
    ):
        self._validate_types(audience_type, template_type)

        with self.db.get_conn() as conn:
            if course_id is None:
                return conn.execute(
                    """
                    SELECT *
                    FROM email_templates
                    WHERE course_id IS NULL
                      AND audience_type = ?
                      AND template_type = ?
                      AND active = 1
                    """,
                    (audience_type, template_type),
                ).fetchone()

            return conn.execute(
                """
                SELECT *
                FROM email_templates
                WHERE course_id = ?
                  AND audience_type = ?
                  AND template_type = ?
                  AND active = 1
                """,
                (course_id, audience_type, template_type),
            ).fetchone()

    def get_best_match(
        self,
        course_id: int | None,
        audience_type: str,
        template_type: str,
    ):
        self._validate_types(audience_type, template_type)

        with self.db.get_conn() as conn:
            if course_id is not None:
                row = conn.execute(
                    """
                    SELECT *
                    FROM email_templates
                    WHERE course_id = ?
                      AND audience_type = ?
                      AND template_type = ?
                      AND active = 1
                    """,
                    (course_id, audience_type, template_type),
                ).fetchone()

                if row:
                    return row

            return conn.execute(
                """
                SELECT *
                FROM email_templates
                WHERE course_id IS NULL
                  AND audience_type = ?
                  AND template_type = ?
                  AND active = 1
                """,
                (audience_type, template_type),
            ).fetchone()

    def upsert_template(
        self,
        *,
        course_id: int | None,
        audience_type: str,
        template_type: str,
        subject_template: str,
        body_text_template: str,
        body_html_template: str | None = None,
        active: int = 1,
    ) -> int:
        self._validate_types(audience_type, template_type)

        now = now_iso()

        with self.db.get_conn() as conn:
            existing = self.get_exact_match(course_id, audience_type, template_type)

            if existing:
                conn.execute(
                    """
                    UPDATE email_templates
                    SET subject_template = ?,
                        body_text_template = ?,
                        body_html_template = ?,
                        active = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        subject_template,
                        body_text_template,
                        body_html_template,
                        active,
                        now,
                        int(existing["id"]),
                    ),
                )
                return int(existing["id"])

            cur = conn.execute(
                """
                INSERT INTO email_templates (
                    course_id,
                    audience_type,
                    template_type,
                    subject_template,
                    body_text_template,
                    body_html_template,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    course_id,
                    audience_type,
                    template_type,
                    subject_template,
                    body_text_template,
                    body_html_template,
                    active,
                    now,
                    now,
                ),
            )
            return int(cur.lastrowid)

    def delete(self, template_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                "DELETE FROM email_templates WHERE id = ?",
                (template_id,),
            )

    def _validate_types(self, audience_type: str, template_type: str) -> None:
        if audience_type not in self.VALID_AUDIENCE_TYPES:
            raise ValueError(f"Invalid audience_type: {audience_type}")

        if template_type not in self.VALID_TEMPLATE_TYPES:
            raise ValueError(f"Invalid template_type: {template_type}")
