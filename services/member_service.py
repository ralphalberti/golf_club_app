import csv
from datetime import datetime
from repositories.member_repository import MemberRepository
from repositories.reporting_repository import ReportingRepository


class MemberService:
    def __init__(self, member_repository, reporting_repository):
        self.member_repository = member_repository
        self.reporting_repo = reporting_repository

    def list_members(self):
        return self.member_repository.list_all()

    def create_member(self, data: dict) -> int:
        return self.member_repository.create(data)

    def update_member(self, member_id: int, data: dict) -> None:
        self.member_repository.update(member_id, data)

    def delete_member(self, member_id: int) -> None:
        self.member_repository.delete(member_id)

    def get_member(self, member_id: int):
        member = self.member_repository.get(member_id)
        stats = self.reporting_repo.member_summary(member_id)
        return member, stats

    def import_members_from_csv(self, csv_path: str) -> dict:
        imported = 0
        updated = 0
        skipped = 0
        errors = []

        today_str = datetime.today().strftime("%Y-%m-%d")

        with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)

            required_columns = {"first_name", "last_name", "email", "phone"}
            missing = required_columns - set(reader.fieldnames or [])
            if missing:
                raise ValueError(
                    f"Missing required column(s): {', '.join(sorted(missing))}"
                )

            for row_number, row in enumerate(reader, start=2):
                try:
                    first_name = (row.get("first_name") or "").strip()
                    last_name = (row.get("last_name") or "").strip()
                    email = (row.get("email") or "").strip().lower()
                    phone = (row.get("phone") or "").strip()
                    handicap_raw = (row.get("handicap") or "").strip()
                    joined_date = (row.get("joined_date") or "").strip()
                    active_raw = (row.get("active") or "1").strip()
                    notes = (row.get("notes") or "").strip()

                    if not first_name or not last_name or not email or not phone:
                        raise ValueError(
                            "first_name, last_name, email, and phone are required"
                        )

                    if joined_date:
                        datetime.strptime(joined_date, "%Y-%m-%d")

                    handicap = None
                    if handicap_raw:
                        try:
                            handicap = float(handicap_raw)
                        except ValueError:
                            raise ValueError(f"invalid handicap: {handicap_raw}")

                    active = (
                        1
                        if active_raw not in {"0", "false", "False", "no", "NO"}
                        else 0
                    )

                    existing = self.member_repository.get_by_email(email)

                    if existing:
                        update_data = {
                            "first_name": first_name,
                            "last_name": last_name,
                            "email": email,
                            "phone": phone,
                            "handicap": handicap,
                            "joined_date": joined_date or existing["joined_date"],
                            "active": active,
                            "notes": notes,
                        }
                        self.member_repository.update(existing["id"], update_data)
                        updated += 1
                    else:
                        create_data = {
                            "first_name": first_name,
                            "last_name": last_name,
                            "email": email,
                            "phone": phone,
                            "handicap": handicap,
                            "joined_date": joined_date or today_str,
                            "active": active,
                            "notes": notes,
                        }
                        self.member_repository.create(create_data)
                        imported += 1

                except Exception as exc:
                    skipped += 1
                    errors.append(f"Row {row_number}: {exc}")

        return {
            "imported": imported,
            "updated": updated,
            "skipped": skipped,
            "errors": errors,
        }
