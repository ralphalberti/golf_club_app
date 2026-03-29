from repositories.base_repository import BaseRepository
from app.utils import now_iso


class MemberRepository(BaseRepository):
    def list_all(self, active_only: bool = True):
        with self.db.get_conn() as conn:
            if active_only:
                return conn.execute("""
                    SELECT *
                    FROM members
                    WHERE active = 1
                    ORDER BY last_name, first_name
                    """).fetchall()

            return conn.execute("""
                SELECT *
                FROM members
                ORDER BY last_name, first_name
                """).fetchall()

    def create(self, data: dict) -> int:
        now = now_iso()
        with self.db.get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO members
                (
                    first_name,
                    last_name,
                    email,
                    phone,
                    handicap,
                    skill_tier,
                    joined_date,
                    active,
                    notes,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["first_name"],
                    data["last_name"],
                    data.get("email", ""),
                    data.get("phone", ""),
                    data.get("handicap"),
                    data.get("skill_tier"),
                    data["joined_date"],
                    data.get("active", 1),
                    data.get("notes", ""),
                    now,
                    now,
                ),
            )
            return cur.lastrowid

    def update(self, member_id: int, data: dict) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE members
                SET first_name=?,
                    last_name=?,
                    email=?,
                    phone=?,
                    handicap=?,
                    skill_tier=?,
                    joined_date=?,
                    active=?,
                    notes=?,
                    updated_at=?
                WHERE id=?
                """,
                (
                    data["first_name"],
                    data["last_name"],
                    data.get("email", ""),
                    data.get("phone", ""),
                    data.get("handicap"),
                    data.get("skill_tier"),
                    data["joined_date"],
                    data.get("active", 1),
                    data.get("notes", ""),
                    now_iso(),
                    member_id,
                ),
            )

    def get(self, member_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                "SELECT * FROM members WHERE id=?",
                (member_id,),
            ).fetchone()

    def get_by_email(self, email: str):
        with self.db.get_conn() as conn:
            return conn.execute(
                "SELECT * FROM members WHERE lower(email) = lower(?)",
                (email,),
            ).fetchone()

    def delete(self, member_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                "DELETE FROM members WHERE id=?",
                (member_id,),
            )

    def get_by_ids(self, member_ids: list[int]):
        normalized_ids = []
        seen = set()

        for member_id in member_ids:
            member_id = int(member_id)
            if member_id not in seen:
                seen.add(member_id)
                normalized_ids.append(member_id)

        if not normalized_ids:
            return []

        placeholders = ",".join("?" for _ in normalized_ids)

        with self.db.get_conn() as conn:
            return conn.execute(
                f"""
                SELECT *
                FROM members
                WHERE id IN ({placeholders})
                ORDER BY last_name, first_name
                """,
                tuple(normalized_ids),
            ).fetchall()
