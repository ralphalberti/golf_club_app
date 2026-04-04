from __future__ import annotations

import csv
from pathlib import Path
from app.config import EXPORT_DIR


class ExportService:
    def __init__(self, db):
        self.db = db

    def export_course_csv(
        self, outing: dict, tee_times: list[dict], assignments: list[dict]
    ) -> Path:
        from repositories.guest_repository import GuestRepository

        export_dir = EXPORT_DIR / "csv"
        export_dir.mkdir(parents=True, exist_ok=True)
        path = export_dir / f"outing_{outing['id']}_v{outing['version']}.csv"

        repo = GuestRepository(self.db)

        # Group sponsors by tee time
        grouped = {tt["id"]: [] for tt in tee_times}
        for row in assignments:
            grouped.setdefault(row["tee_time_id"], []).append(
                {
                    "member_id": row["member_id"],
                    "name": f"{row['first_name']} {row['last_name']}",
                }
            )

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            writer.writerow(["outing_date", "course_name", "tee_time", "role", "name"])

            for tt in tee_times:
                tee_time_label = tt["tee_time"]

                for entry in grouped.get(tt["id"], []):
                    member_id = entry["member_id"]
                    sponsor_name = entry["name"]

                    # Sponsor row
                    writer.writerow(
                        [
                            outing["outing_date"],
                            outing["course_name"],
                            tee_time_label,
                            "Sponsor",
                            sponsor_name,
                        ]
                    )

                    # Guests
                    guests = repo.get_guests_for_outing_and_sponsor(
                        outing_id=outing["id"],
                        sponsoring_member_id=member_id,
                    )

                    for guest in guests:
                        guest_name = f"{guest['first_name']} {guest['last_name']}"
                        writer.writerow(
                            [
                                outing["outing_date"],
                                outing["course_name"],
                                tee_time_label,
                                "Guest",
                                guest_name,
                            ]
                        )

        return path
