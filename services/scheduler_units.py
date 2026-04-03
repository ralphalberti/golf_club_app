from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from repositories.guest_repository import GuestRepository
from repositories.member_repository import MemberRepository
from repositories.outing_repository import OutingRepository
from repositories.rsvp_repository import RSVPRepository

ParticipantKind = Literal["member", "guest"]


@dataclass(frozen=True)
class Participant:
    kind: ParticipantKind
    id: int
    display_name: str
    sponsor_member_id: int | None = None
    skill_tier: int | None = None
    handicap: float | None = None


@dataclass(frozen=True)
class SchedulingUnit:
    sponsor_member_id: int
    participants: tuple[Participant, ...]

    @property
    def size(self) -> int:
        return len(self.participants)

    @property
    def sponsor(self) -> Participant:
        for participant in self.participants:
            if (
                participant.kind == "member"
                and participant.id == self.sponsor_member_id
            ):
                return participant
        raise ValueError(
            f"Scheduling unit is missing sponsor member {self.sponsor_member_id}."
        )

    @property
    def member_ids(self) -> tuple[int, ...]:
        return tuple(
            participant.id
            for participant in self.participants
            if participant.kind == "member"
        )

    @property
    def guest_ids(self) -> tuple[int, ...]:
        return tuple(
            participant.id
            for participant in self.participants
            if participant.kind == "guest"
        )


class SchedulingUnitService:
    """
    Builds sponsor-linked scheduling units for an outing.

    Wrapper-phase behavior:
    - the scheduler still places sponsor member IDs only
    - this service lets us validate whether the sponsor-only schedule is
      actually legal once sponsor guests are expanded back in
    """

    def __init__(self, db):
        self.db = db
        self.member_repo = MemberRepository(db)
        self.outing_repo = OutingRepository(db)
        self.rsvp_repo = RSVPRepository(db)
        self.guest_repo = GuestRepository(db)

    def build_units_for_outing(self, outing_id: int) -> list[SchedulingUnit]:
        outing = self.outing_repo.get(outing_id)
        if outing is None:
            raise ValueError(f"Outing {outing_id} not found.")

        max_group_size = int(outing["max_players_per_tee_time"])

        sponsor_member_ids = self.rsvp_repo.get_schedulable_member_ids(outing_id)
        if not sponsor_member_ids:
            return []

        member_rows = self.member_repo.get_by_ids(sponsor_member_ids)
        member_map = {int(row["id"]): row for row in member_rows}

        missing_member_ids = [
            member_id for member_id in sponsor_member_ids if member_id not in member_map
        ]
        if missing_member_ids:
            raise ValueError(
                "Member records not found for schedulable RSVP-yes members: "
                f"{missing_member_ids}"
            )

        inactive_member_ids = [
            member_id
            for member_id, row in member_map.items()
            if int(row["active"]) != 1
        ]
        if inactive_member_ids:
            raise ValueError(
                "Inactive members cannot be scheduled. "
                f"Inactive member ids: {inactive_member_ids}"
            )

        guest_rows = self.guest_repo.list_schedulable_outing_guests(outing_id)
        guests_by_sponsor: dict[int, list] = {}

        for row in guest_rows:
            sponsor_member_id = int(row["sponsoring_member_id"])
            guests_by_sponsor.setdefault(sponsor_member_id, []).append(row)

        orphan_sponsor_ids = sorted(
            sponsor_member_id
            for sponsor_member_id in guests_by_sponsor
            if sponsor_member_id not in member_map
        )
        if orphan_sponsor_ids:
            raise ValueError(
                "Guest RSVP yes records exist for sponsors who are not schedulable "
                f"members in this outing: {orphan_sponsor_ids}"
            )

        units: list[SchedulingUnit] = []

        for sponsor_member_id in sponsor_member_ids:
            sponsor_row = member_map[sponsor_member_id]

            participants: list[Participant] = [
                Participant(
                    kind="member",
                    id=sponsor_member_id,
                    display_name=self._member_display_name(sponsor_row),
                    sponsor_member_id=None,
                    skill_tier=self._int_or_none(sponsor_row["skill_tier"]),
                    handicap=self._float_or_none(sponsor_row["handicap"]),
                )
            ]

            sponsor_guest_rows = guests_by_sponsor.get(sponsor_member_id, [])
            for guest_row in sponsor_guest_rows:
                participants.append(
                    Participant(
                        kind="guest",
                        id=int(guest_row["guest_id"]),
                        display_name=self._guest_display_name(guest_row),
                        sponsor_member_id=sponsor_member_id,
                        skill_tier=None,
                        handicap=None,
                    )
                )

            unit = SchedulingUnit(
                sponsor_member_id=sponsor_member_id,
                participants=tuple(participants),
            )

            if unit.size > max_group_size:
                raise ValueError(
                    "Scheduling unit exceeds max tee-time capacity. "
                    f"Sponsor member id {sponsor_member_id} has unit size {unit.size}, "
                    f"max group size is {max_group_size}."
                )

            units.append(unit)

        return units

    def sponsor_member_ids_for_outing(self, outing_id: int) -> list[int]:
        units = self.build_units_for_outing(outing_id)
        return [unit.sponsor_member_id for unit in units]

    def build_unit_map_for_outing(self, outing_id: int) -> dict[int, SchedulingUnit]:
        units = self.build_units_for_outing(outing_id)
        return {unit.sponsor_member_id: unit for unit in units}

    def validate_expanded_groups(
        self,
        outing_id: int,
        sponsor_groups: list[list[int]],
    ) -> None:
        tee_times = self.outing_repo.get_tee_times(outing_id)
        unit_map = self.build_unit_map_for_outing(outing_id)

        if len(sponsor_groups) > len(tee_times):
            raise ValueError("Generated more sponsor groups than available tee times.")

        seen_sponsors: set[int] = set()

        for idx, sponsor_group in enumerate(sponsor_groups):
            if idx >= len(tee_times):
                raise ValueError("Generated group index exceeds tee times.")

            tee_time = tee_times[idx]
            max_players = int(tee_time["max_players"])

            expanded_size = 0
            for sponsor_member_id in sponsor_group:
                if sponsor_member_id in seen_sponsors:
                    raise ValueError(
                        "A sponsor member was assigned more than once in the schedule."
                    )
                seen_sponsors.add(sponsor_member_id)

                unit = unit_map.get(sponsor_member_id)
                if unit is None:
                    raise ValueError(
                        "Generated schedule contains a sponsor member not present in "
                        f"the schedulable unit set: {sponsor_member_id}"
                    )

                expanded_size += unit.size

            if expanded_size > max_players:
                raise ValueError(
                    "Expanded unit group exceeds tee-time capacity. "
                    f"Tee index {idx}, expanded size {expanded_size}, "
                    f"max players {max_players}."
                )

        expected_sponsors = set(unit_map.keys())
        if seen_sponsors != expected_sponsors:
            missing = sorted(expected_sponsors - seen_sponsors)
            extras = sorted(seen_sponsors - expected_sponsors)

            details: list[str] = []
            if missing:
                details.append(f"missing sponsor member ids: {missing}")
            if extras:
                details.append(f"unexpected sponsor member ids: {extras}")

            raise ValueError(
                "Expanded sponsor-unit schedule validation failed: "
                + ", ".join(details)
            )

    def expanded_group_sizes(
        self,
        outing_id: int,
        sponsor_groups: list[list[int]],
    ) -> list[int]:
        unit_map = self.build_unit_map_for_outing(outing_id)
        sizes: list[int] = []

        for sponsor_group in sponsor_groups:
            expanded_size = 0
            for sponsor_member_id in sponsor_group:
                unit = unit_map.get(sponsor_member_id)
                if unit is None:
                    raise ValueError(
                        f"Unknown sponsor member id in schedule: {sponsor_member_id}"
                    )
                expanded_size += unit.size
            sizes.append(expanded_size)

        return sizes

    def _member_display_name(self, row) -> str:
        first_name = str(row["first_name"]).strip()
        last_name = str(row["last_name"]).strip()
        return f"{first_name} {last_name}".strip()

    def _guest_display_name(self, row) -> str:
        first_name = str(row["first_name"]).strip()
        last_name = str(row["last_name"]).strip()
        return f"{first_name} {last_name}".strip()

    def _int_or_none(self, value) -> int | None:
        return None if value is None else int(value)

    def _float_or_none(self, value) -> float | None:
        return None if value is None else float(value)

    def build_unit_map_for_member_ids(
        self,
        outing_id: int,
        sponsor_member_ids: list[int],
    ) -> dict[int, SchedulingUnit]:
        all_units = self.build_units_for_outing(outing_id)
        all_unit_map = {unit.sponsor_member_id: unit for unit in all_units}

        requested_ids = {int(member_id) for member_id in sponsor_member_ids}
        missing_ids = sorted(requested_ids - set(all_unit_map.keys()))
        if missing_ids:
            raise ValueError(
                "Some sponsor members are assigned but are not valid schedulable "
                f"units for this outing: {missing_ids}"
            )

        return {
            sponsor_member_id: all_unit_map[sponsor_member_id]
            for sponsor_member_id in sponsor_member_ids
        }

    def validate_expanded_groups_for_member_ids(
        self,
        outing_id: int,
        sponsor_groups: list[list[int]],
        sponsor_member_ids: list[int],
    ) -> None:
        tee_times = self.outing_repo.get_tee_times(outing_id)
        unit_map = self.build_unit_map_for_member_ids(outing_id, sponsor_member_ids)

        if len(sponsor_groups) > len(tee_times):
            raise ValueError("Generated more sponsor groups than available tee times.")

        seen_sponsors: set[int] = set()

        for idx, sponsor_group in enumerate(sponsor_groups):
            if idx >= len(tee_times):
                raise ValueError("Generated group index exceeds tee times.")

            tee_time = tee_times[idx]
            max_players = int(tee_time["max_players"])

            expanded_size = 0
            for sponsor_member_id in sponsor_group:
                if sponsor_member_id in seen_sponsors:
                    raise ValueError(
                        "A sponsor member was assigned more than once in the schedule."
                    )
                seen_sponsors.add(sponsor_member_id)

                unit = unit_map.get(sponsor_member_id)
                if unit is None:
                    raise ValueError(
                        "Generated schedule contains a sponsor member not present in "
                        f"the requested reshuffle set: {sponsor_member_id}"
                    )

                expanded_size += unit.size

            if expanded_size > max_players:
                raise ValueError(
                    "Expanded unit group exceeds tee-time capacity. "
                    f"Tee index {idx}, expanded size {expanded_size}, "
                    f"max players {max_players}."
                )

        expected_sponsors = set(unit_map.keys())
        if seen_sponsors != expected_sponsors:
            missing = sorted(expected_sponsors - seen_sponsors)
            extras = sorted(seen_sponsors - expected_sponsors)

            details: list[str] = []
            if missing:
                details.append(f"missing sponsor member ids: {missing}")
            if extras:
                details.append(f"unexpected sponsor member ids: {extras}")

            raise ValueError(
                "Expanded sponsor-unit schedule validation failed: "
                + ", ".join(details)
            )

    def expanded_group_sizes_for_member_ids(
        self,
        outing_id: int,
        sponsor_groups: list[list[int]],
        sponsor_member_ids: list[int],
    ) -> list[int]:
        unit_map = self.build_unit_map_for_member_ids(outing_id, sponsor_member_ids)
        sizes: list[int] = []

        for sponsor_group in sponsor_groups:
            expanded_size = 0
            for sponsor_member_id in sponsor_group:
                unit = unit_map.get(sponsor_member_id)
                if unit is None:
                    raise ValueError(
                        f"Unknown sponsor member id in schedule: {sponsor_member_id}"
                    )
                expanded_size += unit.size
            sizes.append(expanded_size)

        return sizes
