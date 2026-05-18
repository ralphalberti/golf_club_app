from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ui.shared.messages import show_error


class FacilityContactDialog(QDialog):
    def __init__(self, contact=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Course Contact")
        self.resize(500, 450)

        self.contact = contact or {}

        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout()

        form = QFormLayout()

        self.first_name_input = QLineEdit()
        self.last_name_input = QLineEdit()

        self.title_input = QLineEdit()

        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()

        self.notes_input = QTextEdit()

        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(True)

        self.hold_requests_checkbox = QCheckBox("Receives Hold Requests")
        self.hold_requests_checkbox.setChecked(True)

        self.final_schedule_checkbox = QCheckBox("Receives Final Schedule")
        self.final_schedule_checkbox.setChecked(True)

        form.addRow("First Name *", self.first_name_input)
        form.addRow("Last Name *", self.last_name_input)

        form.addRow("Title", self.title_input)

        form.addRow("Email", self.email_input)
        form.addRow("Phone", self.phone_input)

        form.addRow("Notes", self.notes_input)

        form.addRow("", self.active_checkbox)
        form.addRow("", self.hold_requests_checkbox)
        form.addRow("", self.final_schedule_checkbox)

        layout.addLayout(form)

        help_label = QLabel("* indicates required fields")
        help_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(help_label)

        buttons = QHBoxLayout()

        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)

        layout.addLayout(buttons)

        self.setLayout(layout)

    def _load_values(self):
        if not self.contact:
            return

        if not hasattr(self.contact, "get"):
            self.contact = dict(self.contact)

        self.first_name_input.setText(str(self.contact.get("first_name", "")))

        # self.first_name_input.setText(str(self.contact.get("first_name", "")))

        self.last_name_input.setText(str(self.contact.get("last_name", "")))

        self.title_input.setText(str(self.contact.get("title", "")))

        self.email_input.setText(str(self.contact.get("email", "")))

        self.phone_input.setText(str(self.contact.get("phone", "")))

        self.notes_input.setPlainText(str(self.contact.get("notes", "")))

        self.active_checkbox.setChecked(int(self.contact.get("active", 1)) == 1)

        self.hold_requests_checkbox.setChecked(
            int(self.contact.get("receives_hold_requests", 1)) == 1
        )

        self.final_schedule_checkbox.setChecked(
            int(self.contact.get("receives_final_schedule", 1)) == 1
        )

    def values(self) -> dict:
        return {
            "first_name": self.first_name_input.text().strip(),
            "last_name": self.last_name_input.text().strip(),
            "title": self.title_input.text().strip(),
            "email": self.email_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip(),
            "active": 1 if self.active_checkbox.isChecked() else 0,
            "receives_hold_requests": (
                1 if self.hold_requests_checkbox.isChecked() else 0
            ),
            "receives_final_schedule": (
                1 if self.final_schedule_checkbox.isChecked() else 0
            ),
        }

    def accept(self):
        values = self.values()

        if not values["first_name"]:
            show_error(
                self,
                "Validation Error",
                "First name is required.",
            )
            return

        if not values["last_name"]:
            show_error(
                self,
                "Validation Error",
                "Last name is required.",
            )
            return

        super().accept()
