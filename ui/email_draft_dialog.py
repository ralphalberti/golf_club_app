from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class EmailDraftDialog(QDialog):
    TEMPLATE_OPTIONS = {
        "member": [
            "invitation",
            "pairings",
            "revised_pairings",
        ],
        "course": [
            "course_hold_request",
            "course_final_schedule",
        ],
    }

    def __init__(
        self,
        outing_row,
        draft_service,
        email_send_service=None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Email Draft Editor")
        self.resize(700, 600)

        self.outing = outing_row
        self.draft_service = draft_service
        self.email_send_service = email_send_service

        self.current_body_html: str | None = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()

        selector_layout = QHBoxLayout()

        selector_layout.addWidget(QLabel("Audience:"))
        self.audience_combo = QComboBox()
        self.audience_combo.addItems(["member", "course"])
        self.audience_combo.currentTextChanged.connect(self._on_audience_changed)
        selector_layout.addWidget(self.audience_combo)

        selector_layout.addWidget(QLabel("Template:"))
        self.template_combo = QComboBox()
        self._update_template_options("member")
        selector_layout.addWidget(self.template_combo)

        layout.addLayout(selector_layout)

        layout.addWidget(QLabel("Subject:"))
        self.subject_input = QLineEdit()
        layout.addWidget(self.subject_input)

        layout.addWidget(QLabel("Body:"))
        self.body_input = QTextEdit()
        layout.addWidget(self.body_input)

        button_layout = QHBoxLayout()

        self.load_btn = QPushButton("Load Existing / Create New")
        self.load_btn.clicked.connect(self.load_or_generate)
        button_layout.addWidget(self.load_btn)

        self.regen_btn = QPushButton("Rebuild From Template")
        self.regen_btn.clicked.connect(self.regenerate)
        button_layout.addWidget(self.regen_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_draft)
        button_layout.addWidget(self.save_btn)

        self.test_send_btn = QPushButton("Send Test")
        self.test_send_btn.clicked.connect(self.send_test_email)
        button_layout.addWidget(self.test_send_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self._close_dialog)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _update_template_options(self, audience: str):
        self.template_combo.clear()
        options = self.TEMPLATE_OPTIONS.get(audience, [])
        self.template_combo.addItems(options)

    def _on_audience_changed(self, audience: str):
        self._update_template_options(audience)

    def load_or_generate(self):
        try:
            draft = self.draft_service.get_or_create_draft(
                outing_id=int(self.outing["id"]),
                course_id=int(self.outing["course_id"]),
                audience_type=self.audience_combo.currentText(),
                template_type=self.template_combo.currentText(),
                extra_context={
                    "sender_name": "Ralph",
                    "rsvp_link": "{{rsvp_link}}",
                },
            )

            self.subject_input.setText(draft["subject_text"])
            self.body_input.setPlainText(draft["body_text"])
            self.current_body_html = draft["body_html"]

        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def regenerate(self):
        try:
            draft = self.draft_service.regenerate_draft_from_template(
                outing_id=int(self.outing["id"]),
                course_id=int(self.outing["course_id"]),
                audience_type=self.audience_combo.currentText(),
                template_type=self.template_combo.currentText(),
                extra_context={
                    "sender_name": "Ralph",
                    "rsvp_link": "{{rsvp_link}}",
                },
            )

            self.subject_input.setText(draft["subject_text"])
            self.body_input.setPlainText(draft["body_text"])
            self.current_body_html = draft["body_html"]

        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def save_draft(self):
        try:
            self.draft_service.save_draft(
                outing_id=int(self.outing["id"]),
                audience_type=self.audience_combo.currentText(),
                template_type=self.template_combo.currentText(),
                subject_text=self.subject_input.text(),
                body_text=self.body_input.toPlainText(),
                body_html=self.current_body_html,
            )

            QMessageBox.information(self, "Saved", "Draft saved successfully")

        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def _save_draft_silently(self):
        self.draft_service.save_draft(
            outing_id=int(self.outing["id"]),
            audience_type=self.audience_combo.currentText(),
            template_type=self.template_combo.currentText(),
            subject_text=self.subject_input.text(),
            body_text=self.body_input.toPlainText(),
            body_html=self.current_body_html,
        )

    def _close_dialog(self) -> None:
        self.close()

    def send_test_email(self):
        raw_emails, ok = QInputDialog.getText(
            self,
            "Send Test Email",
            "Enter one or more email addresses (comma separated):",
        )
        if not ok or not raw_emails.strip():
            return

        to_emails = [part.strip() for part in raw_emails.split(",") if part.strip()]
        if not to_emails:
            QMessageBox.warning(
                self,
                "No Recipients",
                "Enter at least one test email address.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Send Test Email",
            f"Send a test email to {len(to_emails)} recipient(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self._save_draft_silently()

            if self.email_send_service is not None:
                result = self.email_send_service.send_test_email(
                    outing_id=int(self.outing["id"]),
                    audience_type=self.audience_combo.currentText(),
                    template_type=self.template_combo.currentText(),
                    to_emails=to_emails,
                )

                sent_count = int(result.get("sent_count", 0))
            elif hasattr(self.draft_service, "send_test_draft"):
                sent_count = int(
                    self.draft_service.send_test_draft(
                        outing_id=int(self.outing["id"]),
                        audience_type=self.audience_combo.currentText(),
                        template_type=self.template_combo.currentText(),
                        to_emails=to_emails,
                    )
                )
            else:
                raise RuntimeError(
                    "Test send is not wired up yet. "
                    "Provide email_send_service or implement "
                    "draft_service.send_test_draft(...)."
                )

            QMessageBox.information(
                self,
                "Test Email Sent",
                f"Sent {sent_count} test email(s) successfully.",
            )

        except Exception as exc:
            QMessageBox.critical(self, "Test Send Failed", str(exc))
