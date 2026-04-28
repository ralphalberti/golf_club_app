from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScheduleResult:
    outing_id: int
    schedule_version_id: int
    scheduled_unit_count: int
    waitlisted_unit_count: int
    assigned_player_count: int
    open_slot_count: int
    message: str


class SchedulerService:
    def __init__(self, db_path: Path | str = "app.db") -> None:
        self.db_path = Path(db_path)

    def generate_schedule(self, outing_id: int) -> ScheduleResult:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")

            outing = self._load_outing(conn, outing_id)
            if outing["workflow_state"] in {"completed", "cancelled"}:
                raise ValueError(
                    "Cannot generate a schedule for a completed or cancelled outing."
                )

            tee_times = self._load_tee_times(conn, outing_id)
            if not tee_times:
                raise ValueError("Cannot generate a schedule without tee times.")

            self._clear_existing_assignments(conn, outing_id)
            self._reset_units_for_rerun(conn, outing_id)

            units = self._load_pending_units(conn, outing_id)

            scheduled_unit_count = 0
            waitlisted_unit_count = 0
            assigned_player_count = 0

            for unit in units:
                players = self._load_unit_players(conn, unit["id"])

                if not players or len(players) > 4:
                    self._mark_unit_ineligible(
                        conn,
                        unit_id=unit["id"],
                        reason="invalid_unit_size",
                    )
                    continue

                assigned = self._try_assign_unit_to_tee_time(
                    conn,
                    tee_times=tee_times,
                    players=players,
                )

                if assigned:
                    self._mark_unit_scheduled(conn, unit["id"])
                    scheduled_unit_count += 1
                    assigned_player_count += len(players)
                else:
                    self._mark_unit_waitlisted(conn, unit["id"])
                    waitlisted_unit_count += 1

            schedule_version_id = self._create_schedule_version(conn, outing_id)
            open_slot_count = self._count_open_slots(conn, outing_id)

            conn.commit()

            return ScheduleResult(
                outing_id=outing_id,
                schedule_version_id=schedule_version_id,
                scheduled_unit_count=scheduled_unit_count,
                waitlisted_unit_count=waitlisted_unit_count,
                assigned_player_count=assigned_player_count,
                open_slot_count=open_slot_count,
                message="Schedule generated successfully.",
            )

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

    def _load_tee_times(
        self,
        conn: sqlite3.Connection,
        outing_id: int,
    ) -> list[sqlite3.Row]:
        return conn.execute(
            """
            SELECT *
            FROM tee_times
            WHERE outing_id = ?
            ORDER BY sequence_number ASC
            """,
            (outing_id,),
        ).fetchall()

    def _clear_existing_assignments(
        self,
        conn: sqlite3.Connection,
        outing_id: int,
    ) -> None:
        conn.execute(
            """
            DELETE FROM tee_time_assignments
            WHERE tee_time_id IN (
                SELECT id
                FROM tee_times
                WHERE outing_id = ?
            )
            """,
            (outing_id,),
        )

    def _reset_units_for_rerun(
        self,
        conn: sqlite3.Connection,
        outing_id: int,
    ) -> None:
        conn.execute(
            """
            UPDATE scheduling_units
            SET status = 'pending'
            WHERE outing_id = ?
              AND status IN ('scheduled', 'waitlisted')
            """,
            (outing_id,),
        )

    def _load_pending_units(
        self,
        conn: sqlite3.Connection,
        outing_id: int,
    ) -> list[sqlite3.Row]:
        return conn.execute(
            """
            SELECT *
            FROM scheduling_units
            WHERE outing_id = ?
              AND status = 'pending'
            ORDER BY priority_at ASC, id ASC
            """,
            (outing_id,),
        ).fetchall()

    def _load_unit_players(
        self,
        conn: sqlite3.Connection,
        scheduling_unit_id: int,
    ) -> list[sqlite3.Row]:
        return conn.execute(
            """
            SELECT *
            FROM scheduling_unit_players
            WHERE scheduling_unit_id = ?
            ORDER BY id ASC
            """,
            (scheduling_unit_id,),
        ).fetchall()

    def _try_assign_unit_to_tee_time(
        self,
        conn: sqlite3.Connection,
        *,
        tee_times: list[sqlite3.Row],
        players: list[sqlite3.Row],
    ) -> bool:
        for tee_time in tee_times:
            open_slots = self._get_open_slots(conn, tee_time["id"])

            if len(open_slots) < len(players):
                continue

            for player, slot_number in zip(players, open_slots):
                conn.execute(
                    """
                    INSERT INTO tee_time_assignments (
                        tee_time_id,
                        scheduling_unit_player_id,
                        slot_number
                    )
                    VALUES (?, ?, ?)
                    """,
                    (tee_time["id"], player["id"], slot_number),
                )

            return True

        return False

    def _get_open_slots(
        self,
        conn: sqlite3.Connection,
        tee_time_id: int,
    ) -> list[int]:
        taken_slots = conn.execute(
            """
            SELECT slot_number
            FROM tee_time_assignments
            WHERE tee_time_id = ?
            ORDER BY slot_number ASC
            """,
            (tee_time_id,),
        ).fetchall()

        taken = {int(row["slot_number"]) for row in taken_slots}
        return [slot for slot in range(1, 5) if slot not in taken]

    def _mark_unit_scheduled(
        self,
        conn: sqlite3.Connection,
        unit_id: int,
    ) -> None:
        conn.execute(
            """
            UPDATE scheduling_units
            SET status = 'scheduled',
                ineligibility_reason = NULL
            WHERE id = ?
            """,
            (unit_id,),
        )

    def _mark_unit_waitlisted(
        self,
        conn: sqlite3.Connection,
        unit_id: int,
    ) -> None:
        conn.execute(
            """
            UPDATE scheduling_units
            SET status = 'waitlisted',
                ineligibility_reason = NULL
            WHERE id = ?
            """,
            (unit_id,),
        )

    def _mark_unit_ineligible(
        self,
        conn: sqlite3.Connection,
        *,
        unit_id: int,
        reason: str,
    ) -> None:
        conn.execute(
            """
            UPDATE scheduling_units
            SET status = 'ineligible',
                ineligibility_reason = ?
            WHERE id = ?
            """,
            (reason, unit_id),
        )

    def _create_schedule_version(
        self,
        conn: sqlite3.Connection,
        outing_id: int,
    ) -> int:
        row = conn.execute(
            """
            SELECT COALESCE(MAX(version_number), 0) + 1 AS next_version
            FROM schedule_versions
            WHERE outing_id = ?
            """,
            (outing_id,),
        ).fetchone()

        next_version = int(row["next_version"])

        cursor = conn.execute(
            """
            INSERT INTO schedule_versions (
                outing_id,
                version_number,
                status,
                notes
            )
            VALUES (?, ?, 'draft', 'Generated by SchedulerService')
            """,
            (outing_id, next_version),
        )

        return int(cursor.lastrowid)

    def _count_open_slots(
        self,
        conn: sqlite3.Connection,
        outing_id: int,
    ) -> int:
        row = conn.execute(
            """
            SELECT
                (COUNT(tt.id) * 4) - COUNT(tta.id) AS open_slot_count
            FROM tee_times tt
            LEFT JOIN tee_time_assignments tta
                ON tta.tee_time_id = tt.id
            WHERE tt.outing_id = ?
            """,
            (outing_id,),
        ).fetchone()

        return int(row["open_slot_count"] or 0)
