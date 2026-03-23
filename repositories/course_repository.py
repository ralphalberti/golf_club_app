from repositories.base_repository import BaseRepository

class CourseRepository(BaseRepository):
    def list_all(self):
        with self.db.get_conn() as conn:
            return conn.execute("SELECT * FROM courses ORDER BY name").fetchall()

    def create(self, data: dict) -> int:
        with self.db.get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO courses (name, address, active, notes, contact_name, contact_email, preferred_format)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["name"], data.get("address", ""), data.get("active", 1),
                    data.get("notes", ""), data.get("contact_name", ""),
                    data.get("contact_email", ""), data.get("preferred_format", "both"),
                ),
            )
            return cur.lastrowid

    def update(self, course_id: int, data: dict) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE courses
                SET name=?, address=?, active=?, notes=?, contact_name=?, contact_email=?, preferred_format=?
                WHERE id=?
                """,
                (
                    data["name"], data.get("address", ""), data.get("active", 1),
                    data.get("notes", ""), data.get("contact_name", ""),
                    data.get("contact_email", ""), data.get("preferred_format", "both"), course_id,
                ),
            )

    def delete(self, course_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute("DELETE FROM courses WHERE id=?", (course_id,))

    def get(self, course_id: int):
        with self.db.get_conn() as conn:
            return conn.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
