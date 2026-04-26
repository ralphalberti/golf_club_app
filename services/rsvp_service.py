from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Response = Literal["yes", "no"]


@dataclass(frozen=True)
class RsvpResult:
    outing_id: int
    member_id: int
    response: Response
    rsvp_id: int
    scheduling_unit_id: int | None
    status: str
    message: str


@dataclass(frozen=True)
class RsvpGuest:
    id: int
    name: str


@dataclass(frozen=True)
class RsvpContext:
    token: str
    invitation_id: int
    outing_id: int
    member_id: int
    member_name: str
    member_email: str
    play_date: str
    course_name: str
    green_fee_cents: int
    workflow_state: str
    current_response: str | None
    responded_at: str | None
    guests: list[RsvpGuest]
    can_rsvp: bool
    message: str


class RsvpService:
    def __init__(self, db_path: Path | str = "app.db") -> None:
        self.db_path = Path(db_path)

    def submit_rsvp(
        self,
        token: str,
        response: Response,
        guests: list[str] | None = None,
    ) -> RsvpResult:
        guests = [guest.strip() for guest in guests or [] if guest.strip()]

        if response not in {"yes", "no"}:
            raise ValueError("RSVP response must be 'yes' or 'no'.")

        if len(guests) > 3:
            raise ValueError("A member may bring at most 3 guests.")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")

            invitation = self._load_invitation(conn, token)
            outing = self._load_outing(conn, invitation["outing_id"])
            member = self._load_member(conn, invitation["member_id"])

            if outing["workflow_state"] in {"completed", "cancelled"}:
                raise ValueError("This outing is no longer accepting RSVPs.")

            if member["active"] != 1:
                raise ValueError("Inactive members cannot RSVP.")

            existing_rsvp = self._load_existing_rsvp(
                conn,
                outing_id=outing["id"],
                member_id=member["id"],
            )

            rsvp_id = self._upsert_rsvp(
                conn,
                outing_id=outing["id"],
                member_id=member["id"],
                response=response,
                existing_rsvp=existing_rsvp,
            )

            if response == "no":
                self._cancel_scheduling_unit(
                    conn,
                    outing_id=outing["id"],
                    member_id=member["id"],
                )

                conn.commit()

                return RsvpResult(
                    outing_id=outing["id"],
                    member_id=member["id"],
                    response="no",
                    rsvp_id=rsvp_id,
                    scheduling_unit_id=None,
                    status="not_scheduled",
                    message="RSVP recorded as no.",
                )

            self._replace_guests(
                conn,
                outing_id=outing["id"],
                sponsor_member_id=member["id"],
                guests=guests,
            )

            is_suspended = self._is_member_suspended(
                conn,
                member_id=member["id"],
                play_date=outing["play_date"],
            )

            unit_status = "ineligible" if is_suspended else "pending"
            ineligibility_reason = "suspended" if is_suspended else None

            scheduling_unit_id = self._upsert_scheduling_unit(
                conn,
                outing_id=outing["id"],
                sponsor_member_id=member["id"],
                rsvp_id=rsvp_id,
                unit_size=1 + len(guests),
                status=unit_status,
                ineligibility_reason=ineligibility_reason,
            )

            self._rebuild_scheduling_unit_players(
                conn,
                scheduling_unit_id=scheduling_unit_id,
                outing_id=outing["id"],
                sponsor_member_id=member["id"],
            )

            conn.commit()

            return RsvpResult(
                outing_id=outing["id"],
                member_id=member["id"],
                response="yes",
                rsvp_id=rsvp_id,
                scheduling_unit_id=scheduling_unit_id,
                status=unit_status,
                message=(
                    "RSVP recorded, but member is suspended for this outing."
                    if is_suspended
                    else "RSVP recorded successfully."
                ),
            )

    def _load_invitation(self, conn: sqlite3.Connection, token: str) -> sqlite3.Row:
        row = conn.execute(
            """
            SELECT *
            FROM outing_invitations
            WHERE rsvp_token = ?
            """,
            (token,),
        ).fetchone()

        if row is None:
            raise ValueError("Invalid RSVP token.")

        return row

    def _load_outing(self, conn: sqlite3.Connection, outing_id: int) -> sqlite3.Row:
        row = conn.execute(
            """
            SELECT *
            FROM outings
            WHERE id = ?
            """,
            (outing_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Outing not found.")

        return row

    def _load_member(self, conn: sqlite3.Connection, member_id: int) -> sqlite3.Row:
        row = conn.execute(
            """
            SELECT *
            FROM members
            WHERE id = ?
            """,
            (member_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Member not found.")

        return row

    def _load_existing_rsvp(
        self,
        conn: sqlite3.Connection,
        *,
        outing_id: int,
        member_id: int,
    ) -> sqlite3.Row | None:
        return conn.execute(
            """
            SELECT *
            FROM rsvps
            WHERE outing_id = ?
              AND member_id = ?
            """,
            (outing_id, member_id),
        ).fetchone()

    def _upsert_rsvp(
        self,
        conn: sqlite3.Connection,
        *,
        outing_id: int,
        member_id: int,
        response: Response,
        existing_rsvp: sqlite3.Row | None,
    ) -> int:
        if existing_rsvp is None:
            cursor = conn.execute(
                """
                INSERT INTO rsvps (
                    outing_id,
                    member_id,
                    response,
                    responded_at,
                    source
                )
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'link')
                """,
                (outing_id, member_id, response),
            )
            return int(cursor.lastrowid)

        if existing_rsvp["response"] == "yes" and response == "yes":
            return int(existing_rsvp["id"])

        conn.execute(
            """
            UPDATE rsvps
            SET response = ?,
                responded_at = CURRENT_TIMESTAMP,
                source = 'link'
            WHERE id = ?
            """,
            (response, existing_rsvp["id"]),
        )

        return int(existing_rsvp["id"])

    def _replace_guests(
        self,
        conn: sqlite3.Connection,
        *,
        outing_id: int,
        sponsor_member_id: int,
        guests: list[str],
    ) -> None:
        conn.execute(
            """
            DELETE FROM guests
            WHERE outing_id = ?
              AND sponsor_member_id = ?
            """,
            (outing_id, sponsor_member_id),
        )

        conn.executemany(
            """
            INSERT INTO guests (
                outing_id,
                sponsor_member_id,
                name
            )
            VALUES (?, ?, ?)
            """,
            [(outing_id, sponsor_member_id, guest) for guest in guests],
        )

    def _is_member_suspended(
        self,
        conn: sqlite3.Connection,
        *,
        member_id: int,
        play_date: str,
    ) -> bool:
        row = conn.execute(
            """
            SELECT id
            FROM member_suspensions
            WHERE member_id = ?
              AND status = 'active'
              AND starts_on <= ?
              AND ends_on >= ?
            LIMIT 1
            """,
            (member_id, play_date, play_date),
        ).fetchone()

        return row is not None

    def _upsert_scheduling_unit(
        self,
        conn: sqlite3.Connection,
        *,
        outing_id: int,
        sponsor_member_id: int,
        rsvp_id: int,
        unit_size: int,
        status: str,
        ineligibility_reason: str | None,
    ) -> int:
        existing = conn.execute(
            """
            SELECT id
            FROM scheduling_units
            WHERE outing_id = ?
              AND sponsor_member_id = ?
            """,
            (outing_id, sponsor_member_id),
        ).fetchone()

        if existing is None:
            cursor = conn.execute(
                """
                INSERT INTO scheduling_units (
                    outing_id,
                    sponsor_member_id,
                    rsvp_id,
                    unit_size,
                    priority_at,
                    status,
                    ineligibility_reason
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    (SELECT responded_at FROM rsvps WHERE id = ?),
                    ?,
                    ?
                )
                """,
                (
                    outing_id,
                    sponsor_member_id,
                    rsvp_id,
                    unit_size,
                    rsvp_id,
                    status,
                    ineligibility_reason,
                ),
            )
            return int(cursor.lastrowid)

        conn.execute(
            """
            UPDATE scheduling_units
            SET rsvp_id = ?,
                unit_size = ?,
                status = ?,
                ineligibility_reason = ?,
                priority_at = COALESCE(
                    priority_at,
                    (SELECT responded_at FROM rsvps WHERE id = ?)
                )
            WHERE id = ?
            """,
            (
                rsvp_id,
                unit_size,
                status,
                ineligibility_reason,
                rsvp_id,
                existing["id"],
            ),
        )

        return int(existing["id"])

    def _cancel_scheduling_unit(
        self,
        conn: sqlite3.Connection,
        *,
        outing_id: int,
        member_id: int,
    ) -> None:
        conn.execute(
            """
            UPDATE scheduling_units
            SET status = 'cancelled',
                ineligibility_reason = NULL
            WHERE outing_id = ?
              AND sponsor_member_id = ?
            """,
            (outing_id, member_id),
        )

    def _rebuild_scheduling_unit_players(
        self,
        conn: sqlite3.Connection,
        *,
        scheduling_unit_id: int,
        outing_id: int,
        sponsor_member_id: int,
    ) -> None:
        member = conn.execute(
            """
            SELECT first_name || ' ' || last_name AS display_name
            FROM members
            WHERE id = ?
            """,
            (sponsor_member_id,),
        ).fetchone()

        if member is None:
            raise ValueError("Sponsor member not found.")

        conn.execute(
            """
            DELETE FROM scheduling_unit_players
            WHERE scheduling_unit_id = ?
            """,
            (scheduling_unit_id,),
        )

        conn.execute(
            """
            INSERT INTO scheduling_unit_players (
                scheduling_unit_id,
                member_id,
                guest_id,
                player_type,
                display_name
            )
            VALUES (?, ?, NULL, 'member', ?)
            """,
            (scheduling_unit_id, sponsor_member_id, member["display_name"]),
        )

        guests = conn.execute(
            """
            SELECT id, name
            FROM guests
            WHERE outing_id = ?
              AND sponsor_member_id = ?
            ORDER BY id
            """,
            (outing_id, sponsor_member_id),
        ).fetchall()

        conn.executemany(
            """
            INSERT INTO scheduling_unit_players (
                scheduling_unit_id,
                member_id,
                guest_id,
                player_type,
                display_name
            )
            VALUES (?, NULL, ?, 'guest', ?)
            """,
            [(scheduling_unit_id, guest["id"], guest["name"]) for guest in guests],
        )

    def get_rsvp_context(self, token: str) -> RsvpContext:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")

            invitation = self._load_invitation(conn, token)
            outing = self._load_outing(conn, invitation["outing_id"])
            member = self._load_member(conn, invitation["member_id"])

            existing_rsvp = self._load_existing_rsvp(
                conn,
                outing_id=outing["id"],
                member_id=member["id"],
            )

            guest_rows = conn.execute(
                """
                SELECT id, name
                FROM guests
                WHERE outing_id = ?
                  AND sponsor_member_id = ?
                ORDER BY id
                """,
                (outing["id"], member["id"]),
            ).fetchall()

            guests = [
                RsvpGuest(
                    id=int(row["id"]),
                    name=row["name"],
                )
                for row in guest_rows
            ]

            member_name = f"{member['first_name']} {member['last_name']}"

            can_rsvp = member["active"] == 1 and outing["workflow_state"] not in {
                "completed",
                "cancelled",
            }

            if member["active"] != 1:
                message = "Inactive members cannot RSVP."
            elif outing["workflow_state"] in {"completed", "cancelled"}:
                message = "This outing is no longer accepting RSVPs."
            else:
                message = "RSVP is available."

            return RsvpContext(
                token=token,
                invitation_id=int(invitation["id"]),
                outing_id=int(outing["id"]),
                member_id=int(member["id"]),
                member_name=member_name,
                member_email=member["email"],
                play_date=outing["play_date"],
                course_name=outing["course_name_snapshot"],
                green_fee_cents=int(outing["green_fee_cents_snapshot"]),
                workflow_state=outing["workflow_state"],
                current_response=(
                    existing_rsvp["response"] if existing_rsvp is not None else None
                ),
                responded_at=(
                    existing_rsvp["responded_at"] if existing_rsvp is not None else None
                ),
                guests=guests,
                can_rsvp=can_rsvp,
                message=message,
            )
