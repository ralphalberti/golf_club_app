from __future__ import annotations

from pathlib import Path
from app.config import EXPORT_DIR

class PdfService:
    def export_master_schedule_pdf(self, outing: dict, tee_times: list[dict], assignments: list[dict]) -> Path:
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
                grouped.setdefault(row["tee_time_id"], []).append(f"{row['first_name']} {row['last_name']}")
            for tt in tee_times:
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y, tt["tee_time"])
                y -= 18
                c.setFont("Helvetica", 11)
                for player in grouped.get(tt["id"], []):
                    c.drawString(70, y, f"- {player}")
                    y -= 16
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
                f.write(f"Date: {outing['outing_date']}\nCourse: {outing['course_name']}\n")
                f.write(f"Start: {outing['start_time']}\nInterval: {outing['tee_interval_minutes']} min\nVersion: {outing['version']}\n\n")
                grouped = {tt["id"]: [] for tt in tee_times}
                for row in assignments:
                    grouped.setdefault(row["tee_time_id"], []).append(f"{row['first_name']} {row['last_name']}")
                for tt in tee_times:
                    f.write(f"{tt['tee_time']}\n")
                    for player in grouped.get(tt["id"], []):
                        f.write(f"  - {player}\n")
                    f.write("\n")
            return path
