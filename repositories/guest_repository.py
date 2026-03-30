from repositories.base_repository import BaseRepository
from app.utils import now_iso


class GuestRepository(BaseRepository):
    VALID_STATUSES = {"invited", "yes", "no", "maybe"}

    def list_all_guests(self, active_only: bool = True):
        with self.db.get_conn() as conn:
            if active_only:
                return conn.execute("""
                    SELECT *
                    FROM guests
                    WHERE active = 1
                    ORDER BY last_name, first_name
                    """).fetchall()

            return conn.execute("""
                SELECT *
                FROM guests
                ORDER BY last_name, first_name
                """).fetchall()

    def create_guest(self, data: dict) -> int:
        now = now_iso()
        with self.db.get_conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO guests (
                    first_name,
                    last_name,
                    email,
                    phone,
                    notes,
                    active,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["first_name"],
                    data["last_name"],
                    data.get("email", ""),
                    data.get("phone", ""),
                    data.get("notes", ""),
                    data.get("active", 1),
                    now,
                    now,
                ),
            )
            return cur.lastrowid

    def update_guest(self, guest_id: int, data: dict) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE guests
                SET first_name = ?,
                    last_name = ?,
                    email = ?,
                    phone = ?,
                    notes = ?,
                    active = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    data["first_name"],
                    data["last_name"],
                    data.get("email", ""),
                    data.get("phone", ""),
                    data.get("notes", ""),
                    data.get("active", 1),
                    now_iso(),
                    guest_id,
                ),
            )

    def get_guest(self, guest_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT *
                FROM guests
                WHERE id = ?
                """,
                (guest_id,),
            ).fetchone()

    def delete_guest(self, guest_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                DELETE FROM guests
                WHERE id = ?
                """,
                (guest_id,),
            )

    def list_outing_guests(self, outing_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT
                    og.id,
                    og.outing_id,
                    og.guest_id,
                    og.sponsoring_member_id,
                    og.status,
                    og.responded_at,
                    og.note,
                    g.first_name,
                    g.last_name,
                    g.email,
                    g.phone,
                    sponsor.first_name AS sponsor_first_name,
                    sponsor.last_name AS sponsor_last_name
                FROM outing_guests og
                JOIN guests g ON g.id = og.guest_id
                JOIN members sponsor ON sponsor.id = og.sponsoring_member_id
                WHERE og.outing_id = ?
                ORDER BY g.last_name, g.first_name
                """,
                (outing_id,),
            ).fetchall()

    def add_guest_to_outing(
        self,
        outing_id: int,
        guest_id: int,
        sponsoring_member_id: int,
        status: str = "invited",
        note: str = "",
    ) -> None:
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid guest RSVP status: {status}")

        now = now_iso()
        responded_at = now if status in {"yes", "no", "maybe"} else None

        with self.db.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO outing_guests (
                    outing_id,
                    guest_id,
                    sponsoring_member_id,
                    status,
                    responded_at,
                    note,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(outing_id, guest_id)
                DO UPDATE SET
                    sponsoring_member_id = excluded.sponsoring_member_id,
                    status = excluded.status,
                    responded_at = excluded.responded_at,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (
                    outing_id,
                    guest_id,
                    sponsoring_member_id,
                    status,
                    responded_at,
                    note,
                    now,
                    now,
                ),
            )

    def set_outing_guest_status(
        self,
        outing_id: int,
        guest_id: int,
        status: str,
        note: str = "",
    ) -> None:
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid guest RSVP status: {status}")

        now = now_iso()
        responded_at = now if status in {"yes", "no", "maybe"} else None

        with self.db.get_conn() as conn:
            conn.execute(
                """
                UPDATE outing_guests
                SET status = ?,
                    responded_at = ?,
                    note = ?,
                    updated_at = ?
                WHERE outing_id = ? AND guest_id = ?
                """,
                (status, responded_at, note, now, outing_id, guest_id),
            )

    def remove_guest_from_outing(self, outing_id: int, guest_id: int) -> None:
        with self.db.get_conn() as conn:
            conn.execute(
                """
                DELETE FROM outing_guests
                WHERE outing_id = ? AND guest_id = ?
                """,
                (outing_id, guest_id),
            )

    def list_schedulable_outing_guests(self, outing_id: int):
        with self.db.get_conn() as conn:
            return conn.execute(
                """
                SELECT
                    og.outing_id,
                    og.guest_id,
                    og.sponsoring_member_id,
                    og.status,
                    g.first_name,
                    g.last_name
                FROM outing_guests og
                JOIN guests g ON g.id = og.guest_id
                WHERE og.outing_id = ? AND og.status = 'yes'
                ORDER BY g.last_name, g.first_name
                """,
                (outing_id,),
            ).fetchall()
