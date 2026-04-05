from pathlib import Path
import sys

from PyQt5.QtWidgets import QApplication

from app.config import APP_NAME, DATA_DIR, EXPORT_DIR
from db.connection import Database
from db.schema import create_schema
from db.seed import seed_defaults
from repositories.user_repository import UserRepository
from repositories.member_repository import MemberRepository
from repositories.reporting_repository import ReportingRepository
from services.auth_service import AuthService
from services.member_service import MemberService
from services.course_service import CourseService
from services.outing_service import OutingService
from services.reporting_service import ReportingService
from services.scheduling_service import SchedulingService
from services.settings_service import SettingsService
from services.rsvp_service import RSVPService
from services.guest_service import GuestService
from services.export_service import ExportService
from services.pdf_service import PdfService
from services.email_service import EmailService
from services.distribution_service import DistributionService
from services.outing_email_draft_service import OutingEmailDraftService
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow


def bootstrap_and_run() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    EXPORT_DIR.mkdir(exist_ok=True)

    db = Database()
    create_schema(db)
    seed_defaults(db)

    user_repo = UserRepository(db)
    auth_service = AuthService(user_repo)

    member_repo = MemberRepository(db)
    reporting_repo = ReportingRepository(db)
    member_service = MemberService(member_repo, reporting_repo)

    course_service = CourseService(db)
    outing_service = OutingService(db)
    reporting_service = ReportingService(db)
    scheduling_service = SchedulingService(db)
    settings_service = SettingsService(db)
    rsvp_service = RSVPService(db)
    guest_service = GuestService(db)
    pdf_service = PdfService(db)
    export_service = ExportService(db)
    email_service = EmailService(db)
    outing_email_draft_service = OutingEmailDraftService(db)

    distribution_service = DistributionService(
        db=db,
        pdf_service=pdf_service,
        export_service=export_service,
        email_service=email_service,
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    login = LoginDialog(auth_service)
    if login.exec_() != LoginDialog.Accepted:
        return

    user = login.authenticated_user
    window = MainWindow(
        current_user=user,
        member_service=member_service,
        course_service=course_service,
        outing_service=outing_service,
        reporting_service=reporting_service,
        scheduling_service=scheduling_service,
        distribution_service=distribution_service,
        settings_service=settings_service,
        rsvp_service=rsvp_service,
        guest_service=guest_service,
        outing_email_draft_service=outing_email_draft_service,
    )
    window.show()
    sys.exit(app.exec_())
