from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QDateEdit,
    QMessageBox,
)
from PyQt5.QtCore import QDate


class MemberFormDialog(QDialog):
    def __init__(self, member=None):
        super().__init__()
        self.setWindowTitle("Member")

        self.first_name = QLineEdit(member["first_name"] if member else "")
        self.last_name = QLineEdit(member["last_name"] if member else "")
        self.email = QLineEdit(member["email"] if member else "")
        self.phone = QLineEdit(member["phone"] if member else "")

        self.handicap = QDoubleSpinBox()
        self.handicap.setRange(-10, 54)
        self.handicap.setDecimals(1)

        handicap_value = 0.0
        if member and member["handicap"] is not None:
            handicap_value = float(member["handicap"])
        self.handicap.setValue(handicap_value)

        self.joined_date = QDateEdit()
        self.joined_date.setCalendarPopup(True)
        if member and member["joined_date"]:
            y, m, d = [int(x) for x in member["joined_date"].split("-")]
            self.joined_date.setDate(QDate(y, m, d))
        else:
            self.joined_date.setDate(QDate.currentDate())

        self.notes = QTextEdit(member["notes"] if member else "")

        form = QFormLayout(self)
        form.addRow("First name", self.first_name)
        form.addRow("Last name", self.last_name)
        form.addRow("Email", self.email)
        form.addRow("Phone", self.phone)
        form.addRow("Handicap", self.handicap)
        form.addRow("Joined date", self.joined_date)
        form.addRow("Notes", self.notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def accept(self):
        first_name = self.first_name.text().strip()
        last_name = self.last_name.text().strip()
        email = self.email.text().strip()
        phone = self.phone.text().strip()

        if not first_name or not last_name or not email or not phone:
            QMessageBox.warning(
                self,
                "Missing Required Fields",
                "First name, last name, email, and phone are required.",
            )
            return

        super().accept()

    def values(self):
        handicap_value = float(self.handicap.value())
        handicap = None if handicap_value == 0.0 else handicap_value

        return {
            "first_name": self.first_name.text().strip(),
            "last_name": self.last_name.text().strip(),
            "email": self.email.text().strip().lower(),
            "phone": self.phone.text().strip(),
            "handicap": handicap,
            "joined_date": self.joined_date.date().toString("yyyy-MM-dd"),
            "notes": self.notes.toPlainText().strip(),
            "active": 1,
        }


class CourseFormDialog(QDialog):
    def __init__(self, course=None):
        super().__init__()
        self.setWindowTitle("Course")
        self.name = QLineEdit(course["name"] if course else "")
        self.address = QLineEdit(course["address"] if course else "")
        self.contact_name = QLineEdit(course["contact_name"] if course else "")
        self.contact_email = QLineEdit(course["contact_email"] if course else "")
        self.notes = QTextEdit(course["notes"] if course else "")
        self.preferred_format = QComboBox()
        self.preferred_format.addItems(["both", "pdf", "csv"])
        if course:
            idx = self.preferred_format.findText(course["preferred_format"])
            if idx >= 0:
                self.preferred_format.setCurrentIndex(idx)

        form = QFormLayout(self)
        form.addRow("Name", self.name)
        form.addRow("Address", self.address)
        form.addRow("Course contact", self.contact_name)
        form.addRow("Course email", self.contact_email)
        form.addRow("Preferred format", self.preferred_format)
        form.addRow("Notes", self.notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return {
            "name": self.name.text().strip(),
            "address": self.address.text().strip(),
            "contact_name": self.contact_name.text().strip(),
            "contact_email": self.contact_email.text().strip(),
            "preferred_format": self.preferred_format.currentText(),
            "notes": self.notes.toPlainText().strip(),
            "active": 1,
        }


class OutingFormDialog(QDialog):
    def __init__(self, courses, outing=None):
        super().__init__()
        self.setWindowTitle("Outing")
        self.course = QComboBox()
        self.course_map = {}
        for row in courses:
            label = row["name"]
            self.course.addItem(label, row["id"])
            self.course_map[row["id"]] = row["name"]

        self.outing_date = QDateEdit()
        self.outing_date.setCalendarPopup(True)
        self.outing_date.setDate(QDate.currentDate())

        self.start_time = QLineEdit(outing["start_time"] if outing else "10:00")

        self.interval = QSpinBox()
        self.interval.setRange(1, 30)
        self.interval.setValue(int(outing["tee_interval_minutes"]) if outing else 9)

        self.tee_count = QSpinBox()
        self.tee_count.setRange(1, 20)
        self.tee_count.setValue(int(outing["tee_time_count"]) if outing else 4)

        self.max_players = QSpinBox()
        self.max_players.setRange(2, 4)
        self.max_players.setValue(
            int(outing["max_players_per_tee_time"]) if outing else 4
        )

        self.status = QComboBox()
        self.status.addItems(["draft", "published", "completed", "cancelled"])

        self.notes = QTextEdit(outing["notes"] if outing else "")

        if outing:
            y, m, d = [int(x) for x in outing["outing_date"].split("-")]
            self.outing_date.setDate(QDate(y, m, d))
            idx = self.course.findData(outing["course_id"])
            if idx >= 0:
                self.course.setCurrentIndex(idx)
            self.status.setCurrentText(outing["status"])

        form = QFormLayout(self)
        form.addRow("Date", self.outing_date)
        form.addRow("Course", self.course)
        form.addRow("First tee time", self.start_time)
        form.addRow("Interval minutes", self.interval)
        form.addRow("Number of tee times", self.tee_count)
        form.addRow("Players per tee time", self.max_players)
        form.addRow("Status", self.status)
        form.addRow("Notes", self.notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        return {
            "outing_date": self.outing_date.date().toString("yyyy-MM-dd"),
            "course_id": self.course.currentData(),
            "start_time": self.start_time.text().strip() or "10:00",
            "tee_interval_minutes": int(self.interval.value()),
            "tee_time_count": int(self.tee_count.value()),
            "max_players_per_tee_time": int(self.max_players.value()),
            "status": self.status.currentText(),
            "notes": self.notes.toPlainText().strip(),
            "version": 1,
        }
