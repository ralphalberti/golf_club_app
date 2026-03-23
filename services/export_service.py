from __future__ import annotations

import csv
from pathlib import Path
from app.config import EXPORT_DIR

class ExportService:
    def export_course_csv(self, outing: dict, tee_times: list[dict], assignments: list[dict]) -> Path:
        export_dir = EXPORT_DIR / "csv"
        export_dir.mkdir(parents=True, exist_ok=True)
        path = export_dir / f"outing_{outing['id']}_v{outing['version']}.csv"

        grouped = {tt["id"]: [] for tt in tee_times}
        for row in assignments:
            grouped.setdefault(row["tee_time_id"], []).append(f"{row['first_name']} {row['last_name']}")

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["outing_date", "course_name", "tee_time", "player_1", "player_2", "player_3", "player_4"])
            for tt in tee_times:
                players = grouped.get(tt["id"], [])
                padded = players + [""] * (4 - len(players))
                writer.writerow([outing["outing_date"], outing["course_name"], tt["tee_time"], *padded[:4]])
        return path
