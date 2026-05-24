from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QApplication,
    QProgressDialog,
)
from repositories.member_repository import MemberRepository
from repositories.course_repository import CourseRepository
from ui.email_draft_dialog import EmailDraftDialog
from ui.send_confirmation_dialog import SendConfirmationDialog
from services.outing_email_send_service import OutingEmailSendService

MEMBER_TEMPLATE_OPTIONS = [
    ("Invitation", "invitation"),
    ("Pairings", "pairings"),
    ("Revised Pairings", "revised_pairings"),
]

COURSE_TEMPLATE_OPTIONS = [
    ("Hold Request", "course_hold_request"),
    ("Schedule", "course_final_schedule"),
    ("Revised Schedule", "course_revised_schedule"),
]


class SendCommunicationDialog(QDialog):
    def __init__(
        self,
        *,
        outing_id,
        outing_service,
        contact_service,
        draft_service,
        workflow_service,
        parent=None,
    ):
        super().__init__(parent)

        self.outing_id = outing_id
        self.outing_service = outing_service
        self.contact_service = contact_service
        self.draft_service = draft_service
        self.workflow_service = workflow_service
        self.member_repo = MemberRepository(workflow_service.db)
        self.course_repo = CourseRepository(workflow_service.db)

        self.setWindowTitle("Send Communication")
        self.resize(900, 650)

        self._build_ui()
        self.load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        #
        # Audience selection
        #
        audience_box = QGroupBox("Audience")
        audience_layout = QHBoxLayout(audience_box)

        self.audience_combo = QComboBox()
        self.audience_combo.setMinimumWidth(180)
        self.audience_combo.addItem("Members", "member")
        self.audience_combo.addItem("Facility Contacts", "course")

        audience_layout.addWidget(QLabel("Audience"))
        audience_layout.addWidget(self.audience_combo)
        audience_layout.addStretch()

        #
        # Template selection
        #
        template_box = QGroupBox("Communication Type")
        template_layout = QHBoxLayout(template_box)

        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(260)

        template_layout.addWidget(QLabel("Template"))
        template_layout.addWidget(self.template_combo)
        template_layout.addStretch()

        #
        # Recipients
        #
        recipients_box = QGroupBox("Recipients")
        recipients_layout = QVBoxLayout(recipients_box)

        self.recipient_list = QListWidget()

        recipients_layout.addWidget(self.recipient_list)

        #
        # Draft status
        #
        draft_box = QGroupBox("Draft Status")
        draft_layout = QVBoxLayout(draft_box)

        self.draft_status_label = QLabel("--")
        self.draft_preview = QTextEdit()
        self.draft_preview.setReadOnly(True)

        draft_layout.addWidget(self.draft_status_label)
        draft_layout.addWidget(self.draft_preview)

        #
        # Buttons
        #
        button_row = QHBoxLayout()

        self.open_draft_button = QPushButton("Open/Edit Draft")
        self.preview_button = QPushButton("Preview")
        self.send_button = QPushButton("Send")
        self.close_button = QPushButton("Close")

        button_row.addWidget(self.open_draft_button)
        button_row.addWidget(self.preview_button)
        button_row.addStretch()
        button_row.addWidget(self.send_button)
        button_row.addWidget(self.close_button)

        #
        # Layout
        #
        layout.addWidget(audience_box)
        layout.addWidget(recipients_box, 1)
        layout.addWidget(template_box)
        layout.addWidget(draft_box, 1)
        layout.addLayout(button_row)

        #
        # Signals
        #
        self.audience_combo.currentIndexChanged.connect(self._reload_template_options)
        self.template_combo.currentIndexChanged.connect(self.load_data)
        self.close_button.clicked.connect(self.reject)
        self.preview_button.clicked.connect(self.open_preview_dialog)
        self.open_draft_button.clicked.connect(self.open_draft_editor)
        self.send_button.clicked.connect(self.send_communication)

        self._reload_template_options()

    def _reload_template_options(self):
        self.template_combo.blockSignals(True)

        self.template_combo.clear()

        audience_type = self.current_audience_type()

        options = (
            MEMBER_TEMPLATE_OPTIONS
            if audience_type == "member"
            else COURSE_TEMPLATE_OPTIONS
        )

        for label, value in options:
            self.template_combo.addItem(label, value)

        self.template_combo.blockSignals(False)

        self.load_data()

    def current_audience_type(self) -> str:
        return str(self.audience_combo.currentData() or "member")

    def current_template_type(self) -> str:
        return str(self.template_combo.currentData() or "")

    def load_data(self):
        self._reload_recipients()
        self._reload_draft_status()

    def _reload_recipients(self):
        self.recipient_list.clear()

        audience_type = self.current_audience_type()
        template_type = self.current_template_type()

        if audience_type == "member":
            members = self.member_repo.list_all(active_only=True)

            for member in members:
                name = (f"{member['first_name']} " f"{member['last_name']}").strip()

                email = str(member["email"] or "").strip()

                self.recipient_list.addItem(f"{name} <{email}>")

            self.recipient_list.insertItem(
                0,
                f"Active Members: {len(members)}",
            )

            return

        #
        # Facility contacts
        #
        outing = self.outing_service.get_outing(self.outing_id)

        if not outing:
            self.recipient_list.addItem("Outing not found.")
            return

        course_id = int(outing["course_id"])
        course = self.course_repo.get(course_id)

        if not course:
            self.recipient_list.addItem("Course not found.")
            return

        facility_id = course["facility_id"]

        if not facility_id:
            self.recipient_list.addItem("Course has no assigned facility.")
            return

        contacts = self.contact_service.list_email_recipients_for_facility_template(
            int(facility_id),
            template_type,
        )

        if not contacts:
            self.recipient_list.addItem("No matching facility contacts.")
            return

        self.recipient_list.addItem(f"Facility Contacts: {len(contacts)}")

        for contact in contacts:
            name = (f"{contact['first_name']} " f"{contact['last_name']}").strip()

            title = str(contact["title"] or "").strip()
            email = str(contact["email"] or "").strip()

            line = f"{name}"

            if title:
                line += f" ({title})"

            line += f" <{email}>"

            self.recipient_list.addItem(line)

    def _reload_draft_status(self):
        audience_type = self.current_audience_type()
        template_type = self.current_template_type()

        try:
            draft = self.draft_service.get_draft(
                self.outing_id,
                audience_type,
                template_type,
            )
        except Exception as exc:
            self.draft_status_label.setText(str(exc))
            self.draft_preview.clear()
            return

        if not draft:
            self.draft_status_label.setText("No saved draft")
            self.draft_preview.clear()
            return

        self.draft_status_label.setText(f"Draft status: {draft['status']}")

        preview_text = (
            f"Subject:\n{draft['subject_text']}\n\n"
            f"Body:\n{draft['body_text'][:1500]}"
        )

        self.draft_preview.setPlainText(preview_text)

    def _current_recipient_dicts(self) -> list[dict]:
        audience_type = self.current_audience_type()
        template_type = self.current_template_type()

        recipients: list[dict] = []

        if audience_type == "member":
            members = self.member_repo.list_all(active_only=True)

            for member in members:
                name = (f"{member['first_name']} " f"{member['last_name']}").strip()

                email = str(member["email"] or "").strip()

                recipients.append(
                    {
                        "member_id": int(member["id"]),
                        "email": email,
                        "label": f"{name} <{email}>",
                    }
                )

            return recipients

        #
        # Facility contacts
        #
        outing = self.outing_service.get_outing(self.outing_id)

        if not outing:
            return []

        course_id = int(outing["course_id"])
        course = self.course_repo.get(course_id)

        if not course:
            return []

        facility_id = course["facility_id"]

        if not facility_id:
            return []

        contacts = self.contact_service.list_email_recipients_for_facility_template(
            int(facility_id),
            template_type,
        )

        for contact in contacts:
            name = (f"{contact['first_name']} " f"{contact['last_name']}").strip()

            title = str(contact["title"] or "").strip()
            email = str(contact["email"] or "").strip()

            label = name

            if title:
                label += f" ({title})"

            label += f" <{email}>"

            recipients.append(
                {
                    "contact_id": int(contact["id"]),
                    "email": email,
                    "label": label,
                }
            )

        return recipients

    def _replace_recipient_list_with_selected(self, selected: list[dict]):
        self.recipient_list.clear()
        self.recipient_list.addItem(f"Selected Recipients: {len(selected)}")

        for recipient in selected:
            self.recipient_list.addItem(recipient.get("label", ""))

    def _sent_count_from_result(self, result: dict) -> int:
        return int(result.get("sent_count", result.get("sent", 0)) or 0)

    def open_draft_editor(self):
        outing = self.outing_service.get_outing(self.outing_id)

        if not outing:
            self.draft_status_label.setText("Outing not found.")
            return

        dialog = EmailDraftDialog(
            outing,
            self.draft_service,
            parent=self,
        )

        dialog.audience_combo.setCurrentText(self.current_audience_type())

        template_type = self.current_template_type()
        for index in range(dialog.template_combo.count()):
            if dialog.template_combo.itemText(index) == template_type:
                dialog.template_combo.setCurrentIndex(index)
                break

        dialog.exec_()

        self.load_data()

    def open_preview_dialog(self):
        audience_type = self.current_audience_type()
        template_type = self.current_template_type()

        draft = self.draft_service.get_draft(
            self.outing_id,
            audience_type,
            template_type,
        )

        if not draft:
            self.draft_status_label.setText("No saved draft to preview.")
            return

        recipients = self._current_recipient_dicts()

        dialog = SendConfirmationDialog(
            audience_label=self.audience_combo.currentText(),
            template_label=self.template_combo.currentText(),
            recipients=recipients,
            subject=str(draft["subject_text"]),
            body_text=str(draft["body_text"]),
            parent=self,
        )

        # if dialog.exec_():
        #     selected = dialog.selected_recipients()
        #     self._replace_recipient_list_with_selected(selected)
        #     self.draft_status_label.setText(
        #         f"Preview confirmed. Selected recipients: {len(selected)}"
        #     )
        dialog.exec_()

    def send_communication(self):
        audience_type = self.current_audience_type()
        template_type = self.current_template_type()

        draft = self.draft_service.get_draft(
            self.outing_id,
            audience_type,
            template_type,
        )

        if not draft:
            QMessageBox.warning(
                self,
                "No Draft",
                "Please create and save a draft before sending.",
            )
            return

        recipients = self._current_recipient_dicts()

        if not recipients:
            QMessageBox.warning(
                self,
                "No Recipients",
                "There are no recipients available for this communication.",
            )
            return

        dialog = SendConfirmationDialog(
            audience_label=self.audience_combo.currentText(),
            template_label=self.template_combo.currentText(),
            recipients=recipients,
            subject=str(draft["subject_text"]),
            body_text=str(draft["body_text"]),
            parent=self,
        )

        if not dialog.exec_():
            return

        selected = dialog.selected_recipients()

        if not selected:
            QMessageBox.information(
                self,
                "No Recipients Selected",
                "No recipients were selected.",
            )
            return

        progress = QProgressDialog(
            "Sending communication...",
            None,
            0,
            0,
            self,
        )
        progress.setWindowTitle("Sending")
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setCancelButton(None)
        progress.show()

        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            send_service = OutingEmailSendService(self.draft_service)

            if audience_type == "member":
                member_ids = [int(r["member_id"]) for r in selected if "member_id" in r]

                result = send_service.send_draft_to_member_ids(
                    outing_id=self.outing_id,
                    template_type=template_type,
                    member_ids=member_ids,
                )

            else:
                to_emails = [
                    str(r["email"]).strip() for r in selected if r.get("email")
                ]

                result = send_service.send_test_email(
                    outing_id=self.outing_id,
                    audience_type="course",
                    template_type=template_type,
                    to_emails=to_emails,
                )

            sent_count = self._sent_count_from_result(result)
            skipped_count = len(result.get("skipped", []))
            failed_count = len(result.get("failed", []))

            progress.close()
            QApplication.restoreOverrideCursor()

            QMessageBox.information(
                self,
                "Send Complete",
                (
                    f"Sent: {sent_count}\n"
                    f"Skipped: {skipped_count}\n"
                    f"Failed: {failed_count}"
                ),
            )

            self.accept()

        except Exception as exc:
            progress.close()
            QApplication.restoreOverrideCursor()

            QMessageBox.critical(
                self,
                "Send Failed",
                str(exc),
            )
