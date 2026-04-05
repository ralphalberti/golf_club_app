from collections import defaultdict

from services.guest_service import GuestService


class ScheduleRenderService:
    def __init__(self, db):
        self.db = db
        self.guest_service = GuestService(db)

    def render_text(
        self,
        *,
        outing_id: int,
        tee_times: list,
        assignments: list,
        max_players_per_group: int = 4,
    ) -> str:
        """
        Render schedule as one line per tee time, e.g.

        10:00 AM    John Smith, Mike Doe, Bob Jones (G), OPEN
        10:09 AM    Ralph Alberti, Stuart Feinberg, Jeff Yeager, Jim Simons
        """

        guest_rows = self.guest_service.list_schedulable_outing_guests(outing_id)

        guests_by_sponsor: dict[int, list[str]] = defaultdict(list)
        for guest_row in guest_rows:
            sponsor_id = int(guest_row["sponsoring_member_id"])
            first_name = str(guest_row["first_name"] or "").strip()
            last_name = str(guest_row["last_name"] or "").strip()
            guest_name = f"{first_name} {last_name} (G)".strip()

            if guest_name:
                guests_by_sponsor[sponsor_id].append(guest_name)

        grouped: dict[str, list[str]] = defaultdict(list)

        for row in assignments:
            tee_time = str(row["tee_time"] or "").strip()
            sponsor_id = int(row["member_id"])

            first_name = str(row["first_name"] or "").strip()
            last_name = str(row["last_name"] or "").strip()
            sponsor_name = f"{first_name} {last_name}".strip()

            if tee_time and sponsor_name:
                grouped[tee_time].append(sponsor_name)

            for guest_name in guests_by_sponsor.get(sponsor_id, []):
                grouped[tee_time].append(guest_name)

        lines: list[str] = []

        for tee in tee_times:
            tee_time = str(tee["tee_time"] or "").strip()
            max_players = int(tee["max_players"] or max_players_per_group)

            players = list(grouped.get(tee_time, []))
            open_slots = max(0, max_players - len(players))
            players.extend(["OPEN"] * open_slots)

            player_text = ", ".join(players)
            lines.append(f"{tee_time}    {player_text}")
            lines.append("")

        return "\n".join(lines).strip()
