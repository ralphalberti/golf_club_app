from repositories.member_repository import MemberRepository
from repositories.reporting_repository import ReportingRepository

class MemberService:
    def __init__(self, db):
        self.repo = MemberRepository(db)
        self.reporting_repo = ReportingRepository(db)

    def list_members(self):
        return self.repo.list_all()

    def create_member(self, data: dict) -> int:
        return self.repo.create(data)

    def update_member(self, member_id: int, data: dict) -> None:
        self.repo.update(member_id, data)

    def delete_member(self, member_id: int) -> None:
        self.repo.delete(member_id)

    def get_member(self, member_id: int):
        member = self.repo.get(member_id)
        stats = self.reporting_repo.member_summary(member_id)
        return member, stats
