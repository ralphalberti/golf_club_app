from repositories.reporting_repository import ReportingRepository

class ReportingService:
    def __init__(self, db):
        self.repo = ReportingRepository(db)
