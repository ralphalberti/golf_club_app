from __future__ import annotations

from repositories.member_repository import MemberRepository
from repositories.outing_repository import OutingRepository
from services.pairing_service import PairingService
from services.rotation_service import RotationService

class SchedulingService:
    def __init__(self, db):
        self.db = db
        self.member_repo = MemberRepository(db)
        self.outing_repo = OutingRepository(db)
        self.pairing_service = PairingService(db)
        self.rotation_service = RotationService(db)

    def generate_schedule(self, outing_id: int, member_ids: list[int]) -> list[list[int]]:
        tee_times = self.outing_repo.get_tee_times(outing_id)
        if not tee_times:
            raise ValueError("No tee times found for outing.")
        max_group_size = tee_times[0]["max_players"]
        groups: list[list[int]] = [[] for _ in tee_times]

        pairing_counts = self.pairing_service.get_pairing_counts(member_ids)
        rotation_stats = self.rotation_service.get_stats(member_ids)
        max_index = max(0, len(groups) - 1)

        ordered_members = sorted(
            member_ids,
            key=lambda mid: (
                rotation_stats.get(mid, {}).get("total_rounds", 0),
                rotation_stats.get(mid, {}).get("average_tee_index", 0),
            ),
            reverse=True,
        )

        for member_id in ordered_members:
            best_idx = None
            best_score = float("inf")
            for tee_index, group in enumerate(groups):
                if len(group) >= max_group_size:
                    continue
                score = self.pairing_service.pairing_penalty(member_id, group, pairing_counts)
                score += self.rotation_service.fairness_penalty(member_id, tee_index, max_index, rotation_stats)
                score += len(group) * 0.5
                if score < best_score:
                    best_score = score
                    best_idx = tee_index
            if best_idx is None:
                break
            groups[best_idx].append(member_id)

        groups = self._improve_by_swaps(groups, pairing_counts)
        self.outing_repo.replace_assignments(outing_id, groups)
        return groups

    def _improve_by_swaps(self, groups: list[list[int]], pairing_counts: dict) -> list[list[int]]:
        def group_score(group: list[int]) -> float:
            score = 0.0
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    key = (min(group[i], group[j]), max(group[i], group[j]))
                    pair = pairing_counts.get(key)
                    if pair:
                        score += pair.get("times_paired", 0) * 10
            return score

        improved = True
        while improved:
            improved = False
            for i in range(len(groups)):
                for j in range(i + 1, len(groups)):
                    for a_idx, a in enumerate(groups[i]):
                        for b_idx, b in enumerate(groups[j]):
                            current = group_score(groups[i]) + group_score(groups[j])
                            new_i = groups[i][:]
                            new_j = groups[j][:]
                            new_i[a_idx], new_j[b_idx] = b, a
                            swapped = group_score(new_i) + group_score(new_j)
                            if swapped < current:
                                groups[i], groups[j] = new_i, new_j
                                improved = True
        return groups
