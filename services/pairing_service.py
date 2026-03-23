from __future__ import annotations

from collections import defaultdict

class PairingService:
    def __init__(self, db):
        self.db = db

    def get_pairing_counts(self, member_ids: list[int]) -> dict[tuple[int, int], dict]:
        if not member_ids:
            return {}
        placeholders = ",".join("?" for _ in member_ids)
        with self.db.get_conn() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM pairing_history
                WHERE member_a_id IN ({placeholders}) AND member_b_id IN ({placeholders})
                """,
                tuple(member_ids) + tuple(member_ids),
            ).fetchall()
        result = defaultdict(lambda: {"times_paired": 0, "last_paired_date": None})
        for row in rows:
            result[(row["member_a_id"], row["member_b_id"])] = dict(row)
        return result

    def pairing_penalty(self, candidate_member_id: int, group_member_ids: list[int], pairing_counts: dict) -> float:
        penalty = 0.0
        for other_id in group_member_ids:
            key = (min(candidate_member_id, other_id), max(candidate_member_id, other_id))
            pair = pairing_counts.get(key)
            if not pair:
                continue
            penalty += pair.get("times_paired", 0) * 10
            if pair.get("last_paired_date"):
                penalty += 5
        return penalty

    def update_history_for_outing(self, outing_id: int) -> None:
        with self.db.get_conn() as conn:
            rows = conn.execute(
                """
                SELECT t.outing_id, o.outing_date, t.id AS tee_time_id, a.member_id
                FROM tee_time_assignments a
                JOIN tee_times t ON t.id = a.tee_time_id
                JOIN outings o ON o.id = t.outing_id
                WHERE t.outing_id = ? AND a.status = 'scheduled'
                ORDER BY t.position_index, a.player_order_in_group
                """,
                (outing_id,),
            ).fetchall()
            grouped = {}
            outing_date = None
            for row in rows:
                outing_date = row["outing_date"]
                grouped.setdefault(row["tee_time_id"], []).append(row["member_id"])
            for group in grouped.values():
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        a = min(group[i], group[j])
                        b = max(group[i], group[j])
                        existing = conn.execute(
                            "SELECT id, times_paired FROM pairing_history WHERE member_a_id=? AND member_b_id=?",
                            (a, b),
                        ).fetchone()
                        if existing:
                            conn.execute(
                                "UPDATE pairing_history SET times_paired=?, last_paired_date=? WHERE id=?",
                                (existing["times_paired"] + 1, outing_date, existing["id"]),
                            )
                        else:
                            conn.execute(
                                """
                                INSERT INTO pairing_history (member_a_id, member_b_id, times_paired, last_paired_date)
                                VALUES (?, ?, 1, ?)
                                """,
                                (a, b, outing_date),
                            )
