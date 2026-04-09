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

    def render_html(
        self,
        *,
        outing_id: int,
        tee_times: list,
        assignments: list,
        max_players_per_group: int = 4,
    ) -> str:
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

        html_parts: list[str] = []
        html_parts.append('<table style="border-collapse: collapse; width: 100%;">')
        html_parts.append("<tbody>")

        for tee in tee_times:
            tee_time = str(tee["tee_time"] or "").strip()
            max_players = int(tee["max_players"] or max_players_per_group)

            players = list(grouped.get(tee_time, []))
            open_slots = max(0, max_players - len(players))
            players.extend(["OPEN"] * open_slots)

            rendered_players: list[str] = []
            for player in players:
                if player == "OPEN":
                    rendered_players.append(
                        '<span style="color: red; font-weight: bold;">OPEN</span>'
                    )
                else:
                    rendered_players.append(player)

            player_html = ", ".join(rendered_players)

            html_parts.append(
                "<tr>"
                f'<td style="padding: 6px 12px 6px 0; vertical-align: top; white-space: nowrap;"><strong>{tee_time}</strong></td>'
                f'<td style="padding: 6px 0; vertical-align: top;">{player_html}</td>'
                "</tr>"
            )

        html_parts.append("</tbody>")
        html_parts.append("</table>")

        return "".join(html_parts)

    def render_member_claim_html(
        self,
        *,
        outing_id: int,
        member_id: int,
        tee_times: list,
        assignments: list,
        build_claim_link,
        max_players_per_group: int = 4,
    ) -> str:
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

        html_parts: list[str] = []
        html_parts.append('<table style="border-collapse: collapse; width: 100%;">')
        html_parts.append("<tbody>")

        for tee in tee_times:
            tee_time_id = int(tee["id"])
            tee_time = str(tee["tee_time"] or "").strip()
            max_players = int(tee["max_players"] or max_players_per_group)

            players = list(grouped.get(tee_time, []))
            open_slots = max(0, max_players - len(players))

            rendered_players: list[str] = list(players)

            for _ in range(open_slots):
                claim_link = build_claim_link(outing_id, member_id, tee_time_id)
                rendered_players.append(
                    f'<a href="{claim_link}" '
                    'style="color: red; font-weight: bold; text-decoration: underline;">'
                    "OPEN</a>"
                )

            player_html = ", ".join(rendered_players)

            html_parts.append(
                "<tr>"
                f'<td style="padding: 6px 12px 6px 0; vertical-align: top; white-space: nowrap;"><strong>{tee_time}</strong></td>'
                f'<td style="padding: 6px 0; vertical-align: top;">{player_html}</td>'
                "</tr>"
            )

        html_parts.append("</tbody>")
        html_parts.append("</table>")

        return "".join(html_parts)
