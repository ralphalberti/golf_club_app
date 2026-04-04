from __future__ import annotations

from pathlib import Path
from app.config import EXPORT_DIR


class PdfService:
    def __init__(self, db):
        self.db = db

    def export_master_schedule_pdf(
        self, outing: dict, tee_times: list[dict], assignments: list[dict]
    ) -> Path:
        # def export_master_schedule_pdf(
        #     self, outing: dict, tee_times: list[dict], assignments: list[dict]
        # ) -> Path:
        export_dir = EXPORT_DIR / "pdf"
        export_dir.mkdir(parents=True, exist_ok=True)
        base = export_dir / f"outing_{outing['id']}_v{outing['version']}"
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            path = base.with_suffix(".pdf")
            c = canvas.Canvas(str(path), pagesize=letter)
            width, height = letter
            y = height - 50
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, y, "Community Golf Club Schedule")
            y -= 25
            c.setFont("Helvetica", 11)
            header = f"Date: {outing['outing_date']}   Course: {outing['course_name']}   Start: {outing['start_time']}   Interval: {outing['tee_interval_minutes']} min   Version: {outing['version']}"
            c.drawString(50, y, header[:110])
            y -= 30
            grouped = {tt["id"]: [] for tt in tee_times}

            for row in assignments:
                grouped.setdefault(row["tee_time_id"], []).append(
                    {
                        "member_id": row["member_id"],
                        "name": f"{row['first_name']} {row['last_name']}",
                    }
                )
            for tt in tee_times:
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y, tt["tee_time"])
                y -= 18
                c.setFont("Helvetica", 11)
                # for player in grouped.get(tt["id"], []):
                #     c.drawString(70, y, f"- {player}")
                #     y -= 16
                #     if y < 60:
                #         c.showPage()
                #         y = height - 50
                # y -= 8
                for entry in grouped.get(tt["id"], []):
                    sponsor_name = entry["name"]
                    member_id = entry["member_id"]

                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(70, y, sponsor_name)
                    y -= 16

                    guests = self._get_guests_for_member(outing["id"], member_id)

                    c.setFont("Helvetica-Oblique", 10)
                    for guest in guests:
                        guest_name = f"{guest['first_name']} {guest['last_name']}"
                        c.drawString(90, y, f"- {guest_name}")
                        y -= 14

                        if y < 60:
                            c.showPage()
                            y = height - 50
                            c.setFont("Helvetica-Oblique", 10)

                    if y < 60:
                        c.showPage()
                        y = height - 50

                    y -= 8
            c.save()
            return path
        except Exception:
            path = base.with_suffix(".pdf.txt")
            with path.open("w", encoding="utf-8") as f:
                f.write("Community Golf Club Schedule\n")
                f.write(
                    f"Date: {outing['outing_date']}\nCourse: {outing['course_name']}\n"
                )
                f.write(
                    f"Start: {outing['start_time']}\nInterval: {outing['tee_interval_minutes']} min\nVersion: {outing['version']}\n\n"
                )
                grouped = {tt["id"]: [] for tt in tee_times}

                for row in assignments:
                    grouped.setdefault(row["tee_time_id"], []).append(
                        {
                            "member_id": row["member_id"],
                            "name": f"{row['first_name']} {row['last_name']}",
                        }
                    )
                for tt in tee_times:
                    f.write(f"{tt['tee_time']}\n")
                    # for player in grouped.get(tt["id"], []):
                    #     f.write(f"  - {player}\n")
                    # f.write("\n")
                    for entry in grouped.get(tt["id"], []):
                        sponsor_name = entry["name"]
                        member_id = entry["member_id"]

                        f.write(f"  {sponsor_name}\n")

                        guests = self._get_guests_for_member(outing["id"], member_id)

                        for guest in guests:
                            guest_name = f"{guest['first_name']} {guest['last_name']}"
                            f.write(f"    - {guest_name}\n")
            return path

    def _get_guests_for_member(self, outing_id: int, member_id: int):
        from repositories.guest_repository import GuestRepository

        repo = GuestRepository(self.db)

        return repo.get_guests_for_outing_and_sponsor(
            outing_id=outing_id,
            sponsoring_member_id=member_id,
        )
