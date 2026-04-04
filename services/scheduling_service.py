from __future__ import annotations

import random
from collections.abc import Mapping

from repositories.member_repository import MemberRepository
from repositories.outing_repository import OutingRepository
from services.pairing_service import PairingService
from services.rotation_service import RotationService
from services.scheduler_units import SchedulingUnit, SchedulingUnitService
from services.settings_service import SettingsService


class SchedulingService:
    def __init__(self, db):
        self.db = db
        self.member_repo = MemberRepository(db)
        self.outing_repo = OutingRepository(db)
        self.pairing_service = PairingService(db)
        self.rotation_service = RotationService(db)
        self.settings_service = SettingsService(db)
        self.unit_service = SchedulingUnitService(db)

    def generate_schedule(
        self,
        outing_id: int,
        member_ids: list[int] | None = None,
    ) -> list[list[int]]:
        """
        Native unit-aware behavior:
        - if member_ids is omitted, schedule all RSVP=yes sponsor members
        - build/score/place sponsor-linked units during schedule construction
        - persist sponsor member assignments only
        """
        tee_times = self.outing_repo.get_tee_times(outing_id)
        if not tee_times:
            raise ValueError("No tee times found for outing.")

        if member_ids is None:
            member_ids = self.unit_service.sponsor_member_ids_for_outing(outing_id)

        member_ids = self._normalize_member_ids(member_ids)
        if not member_ids:
            raise ValueError("No members provided for scheduling.")

        member_map = self._get_member_map(member_ids)

        groups = self._build_best_groups(
            outing_id=outing_id,
            tee_times=tee_times,
            member_ids=member_ids,
            member_map=member_map,
            randomized=True,
            attempts=60,
            current_groups=None,
            mode="moderate",
            enforce_units=True,
            enforced_member_ids=None,
        )

        groups = self._order_groups_for_tee_times(
            outing_id=outing_id,
            groups=groups,
            enforced_member_ids=None,
        )

        self.unit_service.validate_expanded_groups(outing_id, groups)

        self.outing_repo.replace_assignments(outing_id, groups)
        self.outing_repo.increment_version(outing_id)
        return groups

    def reshuffle_schedule(self, outing_id: int) -> list[list[int]]:
        assignments = self.outing_repo.get_assignments(outing_id)
        if not assignments:
            raise ValueError("No assigned players found for outing.")

        member_ids: list[int] = []
        seen: set[int] = set()

        for row in assignments:
            member_id = int(row["member_id"])
            if member_id not in seen:
                seen.add(member_id)
                member_ids.append(member_id)

        if not member_ids:
            raise ValueError("No assigned players found for outing.")

        tee_times = self.outing_repo.get_tee_times(outing_id)
        if not tee_times:
            raise ValueError("No tee times found for outing.")

        member_map = self._get_member_map(member_ids)
        current_groups = self._groups_from_assignments(assignments, tee_times)

        reshuffle_mode = self.settings_service.get_reshuffle_mode()
        attempts = self._get_attempt_count_for_mode(reshuffle_mode)

        groups = self._build_best_groups(
            outing_id=outing_id,
            tee_times=tee_times,
            member_ids=member_ids,
            member_map=member_map,
            randomized=True,
            attempts=attempts,
            current_groups=current_groups,
            mode=reshuffle_mode,
            enforce_units=True,
            enforced_member_ids=member_ids,
        )

        groups = self._order_groups_for_tee_times(
            outing_id=outing_id,
            groups=groups,
            enforced_member_ids=member_ids,
        )

        self.unit_service.validate_expanded_groups_for_member_ids(
            outing_id,
            groups,
            member_ids,
        )

        self.outing_repo.replace_assignments(outing_id, groups)
        self.outing_repo.increment_version(outing_id)
        return groups

    def _build_best_groups(
        self,
        outing_id: int,
        tee_times,
        member_ids: list[int],
        member_map: dict[int, dict],
        randomized: bool,
        attempts: int,
        current_groups: list[list[int]] | None,
        mode: str,
        enforce_units: bool = False,
        enforced_member_ids: list[int] | None = None,
    ) -> list[list[int]]:
        best_groups: list[list[int]] | None = None
        best_score = float("inf")

        for _ in range(max(1, attempts)):
            candidate_groups = self._build_single_schedule(
                outing_id=outing_id,
                tee_times=tee_times,
                member_ids=member_ids,
                member_map=member_map,
                randomized=randomized,
                mode=mode,
                enforced_member_ids=enforced_member_ids,
            )

            if candidate_groups is None:
                continue

            if enforce_units:
                try:
                    if enforced_member_ids is None:
                        self.unit_service.validate_expanded_groups(
                            outing_id,
                            candidate_groups,
                        )
                    else:
                        self.unit_service.validate_expanded_groups_for_member_ids(
                            outing_id,
                            candidate_groups,
                            enforced_member_ids,
                        )
                except ValueError:
                    continue

            candidate_score = self._schedule_score(
                outing_id=outing_id,
                groups=candidate_groups,
                member_ids=member_ids,
                member_map=member_map,
                current_groups=current_groups,
                mode=mode,
                enforced_member_ids=enforced_member_ids,
            )

            if enforce_units:
                candidate_score += self._expanded_group_shape_penalty(
                    outing_id,
                    candidate_groups,
                    enforced_member_ids=enforced_member_ids,
                )

            if candidate_score < best_score:
                best_score = candidate_score
                best_groups = candidate_groups

        if best_groups is None:
            if enforce_units:
                raise ValueError(
                    "Unable to build a valid schedule with the current tier "
                    "constraints, tee-time capacity, and sponsor-guest unit sizes."
                )
            raise ValueError(
                "Unable to build a valid schedule with the current tier constraints "
                "and tee-time capacity."
            )

        return best_groups

    def _build_single_schedule(
        self,
        outing_id: int,
        tee_times,
        member_ids: list[int],
        member_map: dict[int, dict],
        randomized: bool,
        mode: str,
        enforced_member_ids: list[int] | None = None,
    ) -> list[list[int]] | None:
        pairing_counts = self.pairing_service.get_pairing_counts(member_ids)
        rotation_stats = self.rotation_service.get_stats(member_ids)

        if enforced_member_ids is None:
            unit_map = self.unit_service.build_unit_map_for_outing(outing_id)
        else:
            unit_map = self.unit_service.build_unit_map_for_member_ids(
                outing_id,
                enforced_member_ids,
            )

        groups: list[list[int]] = [[] for _ in tee_times]
        max_index = max(0, len(groups) - 1)

        base_order = sorted(
            member_ids,
            key=lambda mid: (
                -self._unit_size_for_member(mid, unit_map),
                rotation_stats.get(mid, {}).get("total_rounds", 0),
                rotation_stats.get(mid, {}).get("average_tee_index", 0),
                mid,
            ),
            reverse=False,
        )

        if randomized:
            ordered_members = self._shuffle_preserving_unit_size_priority(
                base_order,
                unit_map,
            )
        else:
            ordered_members = base_order

        for member_id in ordered_members:
            candidate_options: list[tuple[float, int]] = []

            tee_indexes = list(range(len(groups)))
            if randomized:
                random.shuffle(tee_indexes)

            candidate_unit_size = self._unit_size_for_member(member_id, unit_map)

            for tee_index in tee_indexes:
                group = groups[tee_index]
                max_players = int(tee_times[tee_index]["max_players"])
                current_size = self._expanded_group_size(group, unit_map)

                if current_size + candidate_unit_size > max_players:
                    continue

                candidate_group = group + [member_id]
                if not self._valid_group(candidate_group, member_map):
                    continue

                projected_size = current_size + candidate_unit_size

                score = 0.0
                score += self.pairing_service.pairing_penalty(
                    member_id,
                    group,
                    pairing_counts,
                )
                score += self.rotation_service.fairness_penalty(
                    member_id,
                    tee_index,
                    max_index,
                    rotation_stats,
                )
                score += current_size * 0.5
                score += self._tier_balance_penalty(candidate_group, member_map)
                score += self._projected_group_shape_penalty(
                    projected_size,
                    max_players,
                )

                if randomized:
                    score += random.uniform(
                        0.0,
                        self._get_randomness_strength_for_mode(mode),
                    )

                candidate_options.append((score, tee_index))

            if not candidate_options:
                return None

            candidate_options.sort(key=lambda item: item[0])
            best_idx = candidate_options[0][1]
            groups[best_idx].append(member_id)

        groups = self._improve_by_swaps(
            outing_id=outing_id,
            groups=groups,
            pairing_counts=pairing_counts,
            member_map=member_map,
            randomized=randomized,
            mode=mode,
            enforced_member_ids=enforced_member_ids,
        )

        self._validate_final_groups(
            outing_id=outing_id,
            groups=groups,
            tee_times=tee_times,
            member_map=member_map,
            expected_member_ids=member_ids,
            enforced_member_ids=enforced_member_ids,
        )

        return groups

    def _get_attempt_count_for_mode(self, mode: str) -> int:
        if mode == "conservative":
            return 12
        if mode == "aggressive":
            return 90
        return 50

    def _get_randomness_strength_for_mode(self, mode: str) -> float:
        if mode == "conservative":
            return 0.12
        if mode == "aggressive":
            return 0.60
        return 0.35

    def _groups_from_assignments(self, assignments, tee_times) -> list[list[int]]:
        tee_time_id_to_index = {
            int(row["id"]): idx for idx, row in enumerate(tee_times)
        }
        groups: list[list[int]] = [[] for _ in tee_times]

        sorted_rows = sorted(
            assignments,
            key=lambda row: (
                tee_time_id_to_index.get(int(row["tee_time_id"]), 9999),
                int(row["player_order_in_group"]),
                int(row["member_id"]),
            ),
        )

        for row in sorted_rows:
            tee_time_id = int(row["tee_time_id"])
            member_id = int(row["member_id"])
            idx = tee_time_id_to_index.get(tee_time_id)
            if idx is not None:
                groups[idx].append(member_id)

        return groups

    def _schedule_score(
        self,
        outing_id: int,
        groups: list[list[int]],
        member_ids: list[int],
        member_map: dict[int, dict],
        current_groups: list[list[int]] | None,
        mode: str,
        enforced_member_ids: list[int] | None = None,
    ) -> float:
        pairing_counts = self.pairing_service.get_pairing_counts(member_ids)

        if enforced_member_ids is None:
            unit_map = self.unit_service.build_unit_map_for_outing(outing_id)
        else:
            unit_map = self.unit_service.build_unit_map_for_member_ids(
                outing_id,
                enforced_member_ids,
            )

        score = 0.0

        for group in groups:
            score += self._group_pairing_score(group, pairing_counts)
            score += self._tier_balance_penalty(group, member_map)
            score += self._per_group_fill_penalty(group, unit_map)

        if current_groups is not None:
            score += self._stability_penalty(groups, current_groups, mode)
            score += self._pair_retention_penalty(groups, current_groups, mode)

        return score

    def _expanded_group_shape_penalty(
        self,
        outing_id: int,
        groups: list[list[int]],
        enforced_member_ids: list[int] | None = None,
    ) -> float:
        """
        Lower is better.
        - prefer foursomes over smaller expanded groups
        - prefer smaller expanded groups earlier in the tee sheet
        """
        if enforced_member_ids is None:
            expanded_sizes = self.unit_service.expanded_group_sizes(outing_id, groups)
        else:
            expanded_sizes = self.unit_service.expanded_group_sizes_for_member_ids(
                outing_id,
                groups,
                enforced_member_ids,
            )

        score = 0.0

        for size in expanded_sizes:
            if size == 4:
                score -= 3.0
            elif size == 3:
                score -= 1.0
            elif size == 2:
                score += 2.0
            elif size == 1:
                score += 6.0

        for idx in range(len(expanded_sizes) - 1):
            if expanded_sizes[idx] > expanded_sizes[idx + 1]:
                score += 1.5

        return score

    def _stability_penalty(
        self,
        groups: list[list[int]],
        current_groups: list[list[int]],
        mode: str,
    ) -> float:
        if not current_groups:
            return 0.0

        current_group_index_by_member = {}
        for group_idx, group in enumerate(current_groups):
            for member_id in group:
                current_group_index_by_member[member_id] = group_idx

        moved_count = 0
        for group_idx, group in enumerate(groups):
            for member_id in group:
                if current_group_index_by_member.get(member_id) != group_idx:
                    moved_count += 1

        if mode == "conservative":
            return moved_count * 8.0
        if mode == "aggressive":
            return moved_count * 0.5
        return moved_count * 3.0

    def _pair_retention_penalty(
        self,
        groups: list[list[int]],
        current_groups: list[list[int]],
        mode: str,
    ) -> float:
        if not current_groups:
            return 0.0

        current_pairs = self._extract_pairs(current_groups)
        new_pairs = self._extract_pairs(groups)

        preserved_pairs = len(current_pairs & new_pairs)

        if mode == "conservative":
            return preserved_pairs * -4.0
        if mode == "aggressive":
            return preserved_pairs * 3.0
        return preserved_pairs * 0.5

    def _extract_pairs(self, groups: list[list[int]]) -> set[tuple[int, int]]:
        pairs = set()

        for group in groups:
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a = min(group[i], group[j])
                    b = max(group[i], group[j])
                    pairs.add((a, b))

        return pairs

    def _normalize_member_ids(self, member_ids: list[int]) -> list[int]:
        seen: set[int] = set()
        normalized: list[int] = []

        for member_id in member_ids:
            member_id = int(member_id)
            if member_id not in seen:
                seen.add(member_id)
                normalized.append(member_id)

        return normalized

    def _get_member_map(self, member_ids: list[int]) -> dict[int, dict]:
        rows = self.member_repo.get_by_ids(member_ids)
        member_map = {int(row["id"]): row for row in rows}

        missing_ids = [mid for mid in member_ids if mid not in member_map]
        if missing_ids:
            raise ValueError(f"Member records not found for ids: {missing_ids}")

        inactive_ids = [
            mid for mid, row in member_map.items() if int(row["active"]) != 1
        ]
        if inactive_ids:
            raise ValueError(
                f"Inactive members cannot be scheduled. Inactive member ids: {inactive_ids}"
            )

        return member_map

    def _valid_group(self, group: list[int], member_map: dict[int, dict]) -> bool:
        tiers = set()

        for member_id in group:
            row = member_map.get(member_id)
            if row is None:
                continue

            tier = row["skill_tier"]
            if tier is None:
                continue

            tiers.add(int(tier))

        return not (1 in tiers and 3 in tiers)

    def _tier_balance_penalty(
        self,
        group: list[int],
        member_map: dict[int, dict],
    ) -> float:
        tiers: list[int] = []

        for member_id in group:
            row = member_map.get(member_id)
            if row is None:
                continue

            tier = row["skill_tier"]
            if tier is not None:
                tiers.append(int(tier))

        if not tiers:
            return 0.0

        unique_tiers = set(tiers)

        if unique_tiers == {2}:
            return 0.1
        if unique_tiers == {1} or unique_tiers == {3}:
            return 1.0
        if unique_tiers == {1, 2} or unique_tiers == {2, 3}:
            return 0.25

        return 0.0

    def _group_pairing_score(self, group: list[int], pairing_counts: dict) -> float:
        score = 0.0

        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                key = (min(group[i], group[j]), max(group[i], group[j]))
                pair = pairing_counts.get(key)
                if not pair:
                    continue

                score += pair.get("times_paired", 0) * 10
                if pair.get("last_paired_date"):
                    score += 5

        return score

    def _validate_final_groups(
        self,
        outing_id: int,
        groups: list[list[int]],
        tee_times,
        member_map: dict[int, dict],
        expected_member_ids: list[int],
        enforced_member_ids: list[int] | None = None,
    ) -> None:
        seen: set[int] = set()

        if enforced_member_ids is None:
            unit_map = self.unit_service.build_unit_map_for_outing(outing_id)
        else:
            unit_map = self.unit_service.build_unit_map_for_member_ids(
                outing_id,
                enforced_member_ids,
            )

        for idx, group in enumerate(groups):
            max_players = int(tee_times[idx]["max_players"])

            if self._expanded_group_size(group, unit_map) > max_players:
                raise ValueError("A generated group exceeds the tee-time maximum.")

            if not self._valid_group(group, member_map):
                raise ValueError(
                    "A generated group violates the skill tier constraint."
                )

            for member_id in group:
                if member_id in seen:
                    raise ValueError("A member was assigned more than once.")
                seen.add(member_id)

        expected_set = set(expected_member_ids)
        if seen != expected_set:
            missing = sorted(expected_set - seen)
            extras = sorted(seen - expected_set)

            details = []
            if missing:
                details.append(f"missing member ids: {missing}")
            if extras:
                details.append(f"unexpected member ids: {extras}")

            raise ValueError("Final schedule validation failed: " + ", ".join(details))

    def _improve_by_swaps(
        self,
        outing_id: int,
        groups: list[list[int]],
        pairing_counts: dict,
        member_map: dict[int, dict],
        randomized: bool,
        mode: str,
        enforced_member_ids: list[int] | None = None,
    ) -> list[list[int]]:
        if enforced_member_ids is None:
            unit_map = self.unit_service.build_unit_map_for_outing(outing_id)
        else:
            unit_map = self.unit_service.build_unit_map_for_member_ids(
                outing_id,
                enforced_member_ids,
            )

        improved = True

        while improved:
            improved = False

            for i in range(len(groups)):
                for j in range(i + 1, len(groups)):
                    current_score = (
                        self._group_pairing_score(groups[i], pairing_counts)
                        + self._group_pairing_score(groups[j], pairing_counts)
                        + self._tier_balance_penalty(groups[i], member_map)
                        + self._tier_balance_penalty(groups[j], member_map)
                        + self._per_group_fill_penalty(groups[i], unit_map)
                        + self._per_group_fill_penalty(groups[j], unit_map)
                    )

                    swap_candidates = [
                        (a_idx, b_idx)
                        for a_idx in range(len(groups[i]))
                        for b_idx in range(len(groups[j]))
                    ]

                    if randomized:
                        random.shuffle(swap_candidates)

                    for a_idx, b_idx in swap_candidates:
                        a = groups[i][a_idx]
                        b = groups[j][b_idx]

                        new_i = groups[i][:]
                        new_j = groups[j][:]

                        new_i[a_idx], new_j[b_idx] = b, a

                        if not self._valid_group(new_i, member_map):
                            continue
                        if not self._valid_group(new_j, member_map):
                            continue

                        # Capacity checks must be unit-aware.
                        max_players_i = 4
                        max_players_j = 4
                        # The final validate step uses actual tee max, but swap improvement
                        # should at least reject impossible 4-ball expansions here.
                        if self._expanded_group_size(new_i, unit_map) > max_players_i:
                            continue
                        if self._expanded_group_size(new_j, unit_map) > max_players_j:
                            continue

                        swapped_score = (
                            self._group_pairing_score(new_i, pairing_counts)
                            + self._group_pairing_score(new_j, pairing_counts)
                            + self._tier_balance_penalty(new_i, member_map)
                            + self._tier_balance_penalty(new_j, member_map)
                            + self._per_group_fill_penalty(new_i, unit_map)
                            + self._per_group_fill_penalty(new_j, unit_map)
                        )

                        if randomized:
                            swapped_score += random.uniform(
                                0.0,
                                self._get_randomness_strength_for_mode(mode) / 2.0,
                            )

                        if swapped_score < current_score:
                            groups[i], groups[j] = new_i, new_j
                            improved = True
                            break

                    if improved:
                        break
                if improved:
                    break

        return groups

    def _order_groups_for_tee_times(
        self,
        outing_id: int,
        groups: list[list[int]],
        enforced_member_ids: list[int] | None = None,
    ) -> list[list[int]]:
        """
        Prefer smaller expanded groups earlier in the tee sheet.
        Stable sort preserves relative order among equal-sized groups.
        """
        if enforced_member_ids is None:
            expanded_sizes = self.unit_service.expanded_group_sizes(outing_id, groups)
        else:
            expanded_sizes = self.unit_service.expanded_group_sizes_for_member_ids(
                outing_id,
                groups,
                enforced_member_ids,
            )

        indexed_groups = list(enumerate(groups))
        indexed_groups.sort(key=lambda item: (expanded_sizes[item[0]], item[0]))
        return [group for _, group in indexed_groups]

    def _unit_size_for_member(
        self,
        member_id: int,
        unit_map: Mapping[int, SchedulingUnit],
    ) -> int:
        unit = unit_map.get(int(member_id))
        if unit is None:
            return 1
        return int(unit.size)

    def _expanded_group_size(
        self,
        group: list[int],
        unit_map: Mapping[int, SchedulingUnit],
    ) -> int:
        return sum(
            self._unit_size_for_member(member_id, unit_map) for member_id in group
        )

    def _projected_group_shape_penalty(
        self,
        projected_size: int,
        max_players: int,
    ) -> float:
        if projected_size == max_players:
            return -2.0
        if projected_size == max_players - 1:
            return -0.75
        if projected_size <= 1:
            return 2.0
        return 0.0

    def _per_group_fill_penalty(
        self,
        group: list[int],
        unit_map: Mapping[int, SchedulingUnit],
    ) -> float:
        size = self._expanded_group_size(group, unit_map)

        if size == 4:
            return -2.0
        if size == 3:
            return -0.75
        if size == 2:
            return 1.0
        if size == 1:
            return 3.0
        return 0.0

    def _shuffle_preserving_unit_size_priority(
        self,
        ordered_members: list[int],
        unit_map: Mapping[int, SchedulingUnit],
    ) -> list[int]:
        buckets: dict[int, list[int]] = {}

        for member_id in ordered_members:
            size = self._unit_size_for_member(member_id, unit_map)
            buckets.setdefault(size, []).append(member_id)

        shuffled: list[int] = []
        for size in sorted(buckets.keys(), reverse=True):
            bucket = buckets[size][:]
            random.shuffle(bucket)
            shuffled.extend(bucket)

        return shuffled

    def validate_existing_schedule(self, outing_id: int) -> None:
        """
        Validate the currently saved schedule for an outing against:
        - current member activity
        - tier constraints
        - duplicate assignments
        - expanded sponsor+guest unit sizes

        Raises ValueError if the saved schedule is no longer valid.
        """
        assignments = self.outing_repo.get_assignments(outing_id)
        if not assignments:
            return

        tee_times = self.outing_repo.get_tee_times(outing_id)
        if not tee_times:
            raise ValueError("No tee times found for outing.")

        member_ids: list[int] = []
        seen: set[int] = set()

        for row in assignments:
            member_id = int(row["member_id"])
            if member_id not in seen:
                seen.add(member_id)
                member_ids.append(member_id)

        if not member_ids:
            return

        member_map = self._get_member_map(member_ids)
        current_groups = self._groups_from_assignments(assignments, tee_times)

        self._validate_final_groups(
            outing_id=outing_id,
            groups=current_groups,
            tee_times=tee_times,
            member_map=member_map,
            expected_member_ids=member_ids,
            enforced_member_ids=member_ids,
        )

        self.unit_service.validate_expanded_groups_for_member_ids(
            outing_id=outing_id,
            sponsor_groups=current_groups,
            sponsor_member_ids=member_ids,
        )
