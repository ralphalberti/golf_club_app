from __future__ import annotations

class DistributionService:
    def __init__(self, db, pdf_service, export_service, email_service):
        self.db = db
        self.pdf_service = pdf_service
        self.export_service = export_service
        self.email_service = email_service

    def build_outputs(self, outing: dict, tee_times: list[dict], assignments: list[dict]):
        pdf_path = self.pdf_service.export_master_schedule_pdf(outing, tee_times, assignments)
        csv_path = self.export_service.export_course_csv(outing, tee_times, assignments)
        return pdf_path, csv_path
