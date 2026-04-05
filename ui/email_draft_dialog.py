from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QMessageBox,
)

from services.outing_email_draft_service import OutingEmailDraftService


class EmailDraftDialog(QDialog):
    def __init__(self, outing_row, draft_service, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Email Draft Editor")
        self.resize(700, 600)

        self.outing = outing_row
        self.draft_service = draft_service

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()

        # --- Top selectors ---
        selector_layout = QHBoxLayout()

        selector_layout.addWidget(QLabel("Audience:"))
        self.audience_combo = QComboBox()
        self.audience_combo.addItems(["member", "course"])
        selector_layout.addWidget(self.audience_combo)

        selector_layout.addWidget(QLabel("Template:"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(
            [
                "invitation",
                "pairings",
                "revised_pairings",
                "course_hold_request",
                "course_final_schedule",
            ]
        )
        selector_layout.addWidget(self.template_combo)

        layout.addLayout(selector_layout)

        # --- Subject ---
        layout.addWidget(QLabel("Subject:"))
        self.subject_input = QLineEdit()
        layout.addWidget(self.subject_input)

        # --- Body ---
        layout.addWidget(QLabel("Body:"))
        self.body_input = QTextEdit()
        layout.addWidget(self.body_input)

        # --- Buttons ---
        button_layout = QHBoxLayout()

        self.load_btn = QPushButton("Load / Generate")
        self.load_btn.clicked.connect(self.load_or_generate)
        button_layout.addWidget(self.load_btn)

        self.regen_btn = QPushButton("Regenerate")
        self.regen_btn.clicked.connect(self.regenerate)
        button_layout.addWidget(self.regen_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_draft)
        button_layout.addWidget(self.save_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    # -------------------------
    # Actions
    # -------------------------

    def load_or_generate(self):
        try:
            draft = self.draft_service.get_or_create_draft(
                outing_id=int(self.outing["id"]),
                course_id=int(self.outing["course_id"]),
                audience_type=self.audience_combo.currentText(),
                template_type=self.template_combo.currentText(),
                extra_context={
                    "sender_name": "Ralph",
                    "rsvp_link": "http://localhost:8000/rsvp/yes?token=test",
                },
            )

            self.subject_input.setText(draft["subject_text"])
            self.body_input.setPlainText(draft["body_text"])

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def regenerate(self):
        try:
            draft = self.draft_service.regenerate_draft_from_template(
                outing_id=int(self.outing["id"]),
                course_id=int(self.outing["course_id"]),
                audience_type=self.audience_combo.currentText(),
                template_type=self.template_combo.currentText(),
                extra_context={
                    "sender_name": "Ralph",
                    "rsvp_link": "http://localhost:8000/rsvp/yes?token=test",
                },
            )

            self.subject_input.setText(draft["subject_text"])
            self.body_input.setPlainText(draft["body_text"])

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_draft(self):
        try:
            self.draft_service.save_draft(
                outing_id=int(self.outing["id"]),
                audience_type=self.audience_combo.currentText(),
                template_type=self.template_combo.currentText(),
                subject_text=self.subject_input.text(),
                body_text=self.body_input.toPlainText(),
            )

            QMessageBox.information(self, "Saved", "Draft saved successfully")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
