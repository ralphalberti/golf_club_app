from collections import defaultdict


class RotationService:
    def __init__(self, db):
        self.db = db

    def get_stats(self, member_ids: list[int]) -> dict[int, dict]:
        if not member_ids:
            return {}

        placeholders = ",".join("?" for _ in member_ids)

        with self.db.get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM member_tee_order WHERE member_id IN ({placeholders})",
                tuple(member_ids),
            ).fetchall()

        stats = defaultdict(
            lambda: {
                "average_tee_index": 0.0,
                "total_rounds": 0,
                "total_first_slots": 0,
                "total_last_slots": 0,
                "last_tee_index": None,
            }
        )

        for row in rows:
            stats[row["member_id"]] = dict(row)

        return stats

    def fairness_penalty(
        self,
        member_id: int,
        tee_index: int,
        max_index: int,
        stats: dict[int, dict],
    ) -> float:
        member_stats = stats.get(member_id, {})
        avg = member_stats.get("average_tee_index", 0.0)
        total_first = member_stats.get("total_first_slots", 0)
        total_last = member_stats.get("total_last_slots", 0)

        penalty = 0.0

        if tee_index == 0:
            penalty += total_first * 4
        if tee_index == max_index:
            penalty += total_last * 4

        target = max_index / 2 if max_index else 0
        penalty += abs((avg or 0) - target) if tee_index < target else 0

        return penalty
