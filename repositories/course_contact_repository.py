from repositories.base_repository import BaseRepository
from app.utils import now_iso


class CourseContactRepository(BaseRepository):
    def list_for_course(self, course_id: int, active_only: bool = False):
        with self.db.get_conn() as conn:
            sql = """
                SELECT *
                FROM course_contacts
                WHERE course_id = ?
            """
            params: list = [course_id]

            if active_only:
                sql += " AND active = 1"

            sql += " ORDER BY last_name, first_name"

            return conn.execute(sql, params).fetchall()

    def list_for_facility(self, facility_id: int, active_only: bool = False):
        with self.db.get_conn() as conn:
            sql = """
                SELECT *
                FROM course_contacts
                WHERE facility_id = ?
            """
            params: list = [facility_id]

            if active_only:
                sql += " AND active = 1"

            sql += " ORDER BY last_name, first_name"

            return conn.execute(sql, params).fetchall()

    def list_email_recipients_for_facility_template(
        self,
        facility_id: int,
        template_type: str,
    ):
        if template_type not in {"course_hold_request", "course_final_schedule"}:
            raise ValueError(f"Unsupported course template_type: {template_type}")

        flag_column = (
            "receives_hold_requests"
            if template_type == "course_hold_request"
            else "receives_final_schedule"
        )

        with self.db.get_conn() as conn:
            return conn.execute(
                f"""
                SELECT *
                FROM course_contacts
                WHERE facility_id = ?
                  AND active = 1
                  AND {flag_column} = 1
                  AND email IS NOT NULL
                  AND TRIM(email) != ''
                ORDER BY last_name, first_name
                """,
                (facility_id,),
            ).fetchall()

    def get(self, contact_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM course_contacts
                WHERE id = ?
                """,
                (contact_id,),
            ).fetchone()

    def create(self, data: dict) -> int:
        now = now_iso()

        with self.db.get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO course_contacts (
                    facility_id,
                    course_id,
                    first_name,
                    last_name,
                    title,
                    email,
                    phone,
                    notes,
                    active,
                    receives_hold_requests,
                    receives_final_schedule,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    # int(data["course_id"]),
                    data.get("facility_id"),
                    data.get("course_id"),
                    data["first_name"].strip(),
                    data["last_name"].strip(),
                    data.get("title", "").strip(),
                    data.get("email", "").strip(),
                    data.get("phone", "").strip(),
                    data.get("notes", "").strip(),
                    int(data.get("active", 1)),
                    int(data.get("receives_hold_requests", 1)),
                    int(data.get("receives_final_schedule", 1)),
                    now,
                    now,
                ),
            )
            return int(cur.lastrowid)

    def update(self, contact_id: int, data: dict) -> None:
        now = now_iso()

        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE course_contacts
                SET facility_id = ?,
                    course_id = ?,
                    first_name = ?,
                    last_name = ?,
                    title = ?,
                    email = ?,
                    phone = ?,
                    notes = ?,
                    active = ?,
                    receives_hold_requests = ?,
                    receives_final_schedule = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    data.get("facility_id"),
                    data.get("course_id"),
                    data["first_name"].strip(),
                    data["last_name"].strip(),
                    data.get("title", "").strip(),
                    data.get("email", "").strip(),
                    data.get("phone", "").strip(),
                    data.get("notes", "").strip(),
                    int(data.get("active", 1)),
                    int(data.get("receives_hold_requests", 1)),
                    int(data.get("receives_final_schedule", 1)),
                    now,
                    contact_id,
                ),
            )

    def delete(self, contact_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                DELETE FROM course_contacts
                WHERE id = ?
                """,
                (contact_id,),
            )
