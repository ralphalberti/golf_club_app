from PyQt5.QtGui import QBrush
from datetime import datetime
from ui.shared.forms import GuestFormDialog
from ui.email_draft_dialog import EmailDraftDialog
from PyQt5.QtCore import Qt, QSettings, QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from services.outing_workflow_service import OutingWorkflowService
from ui.shared.messages import show_error, show_info, show_warning

DataRole = Qt.ItemDataRole
SelectionBehavior = QTableWidget.SelectionBehavior
SelectionMode = QTableWidget.SelectionMode
EditTrigger = QTableWidget.EditTrigger
ListSelectionMode = QAbstractItemView.SelectionMode

WORKFLOW_STAGES = [
    "draft",
    "invites_prepared",
    "invites_sent",
    "rsvp_in_progress",
    "schedule_generated",
    "course_hold_sent",
    "players_notified",
    "schedule_revised",
    "final_sent_to_course",
    "completed",
]

RSVP_STATUSES = ["selected", "invited", "yes"]

MEMBER_EMAIL_TEMPLATES = [
    ("Invitation", "invitation"),
    ("Pairings", "pairings"),
    ("Revised Pairings", "revised_pairings"),
]


class EmailSendWorker(QObject):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, email_send_service, outing_id, template_type, member_ids):
        super().__init__()
        self.email_send_service = email_send_service
        self.outing_id = outing_id
        self.template_type = template_type
        self.member_ids = member_ids

    def run(self):
        try:
            result = self.email_send_service.send_draft_to_member_ids(
                outing_id=self.outing_id,
                template_type=self.template_type,
                member_ids=self.member_ids,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class OutingRSVPDialog(QDialog):
    def __init__(
        self,
        outing_id: int,
        outing,
        outing_service,
        rsvp_service,
        guest_service,
        email_send_service,
        draft_service,
        member_service,
        parent=None,
    ):
        super().__init__(parent)
        self.outing_id = outing_id
        self.outing = outing
        self.outing_service = outing_service
        self.rsvp_service = rsvp_service
        self.guest_service = guest_service
        self.email_send_service = email_send_service
        self.draft_service = draft_service
        self.member_service = member_service
        self.settings = QSettings("GolfClubApp", "OutingManager")
        self.workflow_service = OutingWorkflowService(
            self.email_send_service.draft_service.repo.db
        )

        self.setWindowTitle("Manage RSVP")
        self.resize(1500, 950)
        self.setWindowState(self.windowState() | Qt.WindowMaximized)

        self.stage_combo = QComboBox()
        for stage in WORKFLOW_STAGES:
            self.stage_combo.addItem(stage, stage)

        self.save_stage_button = QPushButton("Save Stage")
        self.save_stage_button.clicked.connect(self.save_workflow_stage)

        # Eventually clean up the hidden buttons. Maybe include via setup function
        self.invite_all_button = QPushButton("Invite All Active Members")
        self.invite_selected_button = QPushButton("Invite Selected")
        self.invite_all_button.hide()
        self.invite_selected_button.hide()
        self.remove_invite_button = QPushButton("Remove Invite")
        self.remove_invite_button.hide()
        self.send_selected_email_button = QPushButton("Send Selected Members Email")

        self.mark_member_invited_button = QPushButton("Mark Pending")
        self.mark_member_yes_button = QPushButton("Mark Confirmed")

        self.add_guest_button = QPushButton("Add Guest to Outing")
        self.edit_guest_button = QPushButton("Edit Guest")
        self.remove_guest_button = QPushButton("Remove Guest")
        self.mark_guest_invited_button = QPushButton("Mark Guest Pending")
        self.mark_guest_yes_button = QPushButton("Guest Confirmed")

        self.member_email_template_combo = QComboBox()
        for label, value in MEMBER_EMAIL_TEMPLATES:
            self.member_email_template_combo.addItem(label, value)
        self._restore_member_email_template()
        self.member_email_template_combo.currentIndexChanged.connect(
            self._save_member_email_template
        )

        self.invite_all_button.clicked.connect(self.invite_all_active_members)
        self.invite_selected_button.clicked.connect(self.invite_selected_members)
        self.remove_invite_button.clicked.connect(self.remove_selected_member_rsvps)
        self.send_selected_email_button.clicked.connect(
            self.send_email_to_selected_members
        )

        self.mark_member_invited_button.clicked.connect(
            lambda: self.update_selected_member_rsvps("invited")
        )
        self.mark_member_yes_button.clicked.connect(
            lambda: self.update_selected_member_rsvps("yes")
        )

        self.add_guest_button.clicked.connect(self.add_guest_to_outing)
        self.edit_guest_button.clicked.connect(self.edit_selected_guest)
        self.remove_guest_button.clicked.connect(self.remove_selected_guests)
        self.mark_guest_invited_button.clicked.connect(
            lambda: self.update_selected_guest_statuses("invited")
        )
        self.mark_guest_yes_button.clicked.connect(
            lambda: self.update_selected_guest_statuses("yes")
        )

        self.available_members_list = QListWidget()
        self.available_members_list.setSelectionMode(
            ListSelectionMode.ExtendedSelection
        )
        # self.available_members_list.itemDoubleClicked.connect(
        #     self.invite_double_clicked_member
        # )

        self.member_rsvp_table = QTableWidget()
        self.member_rsvp_table.setSelectionBehavior(SelectionBehavior.SelectRows)
        self.member_rsvp_table.setSelectionMode(SelectionMode.ExtendedSelection)
        self.member_rsvp_table.setEditTriggers(EditTrigger.NoEditTriggers)

        self.guest_table = QTableWidget()
        self.guest_table.setSelectionBehavior(SelectionBehavior.SelectRows)
        self.guest_table.setSelectionMode(SelectionMode.ExtendedSelection)
        self.guest_table.setEditTriggers(EditTrigger.NoEditTriggers)

        self.eligible_summary_label = QLabel("RSVP Summary: --")
        self.recommended_next_step_label = QLabel("Recommended Next Step: --")
        self.current_stage_value_label = QLabel("--")
        self.outing_date_value_label = QLabel("--")
        self.schedule_status_value_label = QLabel("--")
        self.recommended_template_value_label = QLabel("--")
        self.outing_summary_label = QLabel("--")

        self.invitation_draft_status_value_label = QLabel("--")
        self.pairings_draft_status_value_label = QLabel("--")
        self.revised_pairings_draft_status_value_label = QLabel("--")
        self.course_hold_draft_status_value_label = QLabel("--")
        self.course_final_draft_status_value_label = QLabel("--")
        self.revised_needed_status_value_label = QLabel("--")

        # workflow_value_style = "font-weight: 600; color: #e6c65b;"
        workflow_value_style = "font-weight: 600; color: #f5d76e;"
        # workflow_value_style = "font-weight: 600; color: #ffd84d;"

        for label in (
            self.outing_summary_label,
            self.current_stage_value_label,
            self.outing_date_value_label,
            self.schedule_status_value_label,
            self.recommended_template_value_label,
            self.recommended_next_step_label,
            self.invitation_draft_status_value_label,
            self.pairings_draft_status_value_label,
            self.revised_pairings_draft_status_value_label,
            self.course_hold_draft_status_value_label,
            self.course_final_draft_status_value_label,
            self.revised_needed_status_value_label,
        ):
            label.setStyleSheet(workflow_value_style)

        self.open_draft_editor_button = QPushButton("Open Draft Editor")
        self.generate_schedule_button = QPushButton("Generate Schedule")
        self.send_recommended_template_button = QPushButton("Send Email")

        self.open_draft_editor_button.clicked.connect(self.open_draft_editor)
        self.generate_schedule_button.clicked.connect(self.generate_schedule_from_rsvp)
        # Temporarily hide the Generate Schedule button
        self.generate_schedule_button.setVisible(False)
        self.generate_schedule_button.setEnabled(False)
        self.send_recommended_template_button.clicked.connect(
            self.send_recommended_template
        )

        main_layout = QVBoxLayout(self)

        stage_box = QGroupBox("Workflow Stage")
        stage_layout = QHBoxLayout(stage_box)
        stage_layout.addWidget(QLabel("Current Stage"))
        stage_layout.addWidget(self.stage_combo)
        stage_layout.addWidget(self.save_stage_button)
        stage_layout.addStretch()

        workflow_summary_box = QGroupBox("Workflow Summary")
        workflow_summary_layout = QVBoxLayout(workflow_summary_box)

        def summary_row(label_text, value_widget):
            layout = QHBoxLayout()

            label = QLabel(label_text + ":")
            label.setStyleSheet("color: #aaaaaa;")

            layout.addWidget(label)
            layout.addSpacing(8)
            layout.addWidget(value_widget)
            layout.addStretch()

            return layout

        workflow_summary_layout.addLayout(
            summary_row("Outing", self.outing_summary_label)
        )
        workflow_summary_layout.addLayout(
            summary_row("Current Stage", self.current_stage_value_label)
        )
        workflow_summary_layout.addLayout(
            summary_row("Schedule Status", self.schedule_status_value_label)
        )
        workflow_summary_layout.addLayout(
            summary_row("Recommended Template", self.recommended_template_value_label)
        )
        workflow_summary_layout.addLayout(
            summary_row("Recommended Next Step", self.recommended_next_step_label)
        )

        communication_box = QGroupBox("Communication Status")
        outer_communication_layout = QVBoxLayout(communication_box)

        status_columns_layout = QHBoxLayout()
        left_column = QVBoxLayout()
        right_column = QVBoxLayout()

        def status_row(label_text, value_widget):
            layout = QHBoxLayout()

            label = QLabel(label_text + ":")
            label.setStyleSheet("color: #aaaaaa;")

            layout.addWidget(label)
            layout.addSpacing(8)
            layout.addWidget(value_widget)
            layout.addStretch()

            return layout

        left_column.addLayout(
            status_row("Invitation Draft", self.invitation_draft_status_value_label)
        )
        left_column.addLayout(
            status_row("Pairings Draft", self.pairings_draft_status_value_label)
        )
        left_column.addLayout(
            status_row(
                "Revised Pairings Draft",
                self.revised_pairings_draft_status_value_label,
            )
        )

        right_column.addLayout(
            status_row("Course Hold Draft", self.course_hold_draft_status_value_label)
        )
        right_column.addLayout(
            status_row("Course Final Draft", self.course_final_draft_status_value_label)
        )
        right_column.addLayout(
            status_row(
                "Revised Pairings Needed", self.revised_needed_status_value_label
            )
        )

        status_columns_layout.addLayout(left_column, 1)
        status_columns_layout.addSpacing(24)
        status_columns_layout.addLayout(right_column, 1)

        communication_button_row = QHBoxLayout()
        communication_button_row.addWidget(self.open_draft_editor_button)
        communication_button_row.addWidget(self.send_recommended_template_button)
        # communication_button_row.addWidget(self.generate_schedule_button)
        communication_button_row.addStretch()

        outer_communication_layout.addLayout(status_columns_layout)
        outer_communication_layout.addLayout(communication_button_row)

        top_dashboard_row = QHBoxLayout()
        top_dashboard_row.addWidget(workflow_summary_box, 1)
        top_dashboard_row.addWidget(communication_box, 1)

        member_box = QGroupBox("Member RSVP Management")
        member_layout = QGridLayout(member_box)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Active Members"))
        left_layout.addWidget(self.available_members_list)

        left_button_row = QHBoxLayout()
        left_button_row.addWidget(self.invite_selected_button)
        left_button_row.addWidget(self.invite_all_button)
        left_layout.addLayout(left_button_row)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Selected / Pending / Confirmed Members"))
        right_layout.addWidget(self.member_rsvp_table)

        email_template_row = QHBoxLayout()
        email_template_row.addWidget(QLabel("Member Email Template"))
        email_template_row.addWidget(self.member_email_template_combo)
        email_template_row.addStretch()
        right_layout.addLayout(email_template_row)

        rsvp_button_row = QHBoxLayout()
        rsvp_button_row.addWidget(self.mark_member_invited_button)
        rsvp_button_row.addWidget(self.mark_member_yes_button)
        rsvp_button_row.addWidget(self.send_selected_email_button)
        rsvp_button_row.addWidget(self.remove_invite_button)
        right_layout.addLayout(rsvp_button_row)

        member_layout.addWidget(left_panel, 0, 0)
        member_layout.addWidget(right_panel, 0, 1)

        guest_box = QGroupBox("Guest Participation")
        guest_layout = QVBoxLayout(guest_box)
        guest_layout.addWidget(self.guest_table)

        guest_button_row = QHBoxLayout()
        guest_button_row.addWidget(self.add_guest_button)
        guest_button_row.addWidget(self.edit_guest_button)
        guest_button_row.addWidget(self.mark_guest_invited_button)
        guest_button_row.addWidget(self.mark_guest_yes_button)
        guest_button_row.addWidget(self.remove_guest_button)
        guest_button_row.addStretch()
        guest_layout.addLayout(guest_button_row)

        footer_row = QHBoxLayout()
        footer_row.addWidget(self.eligible_summary_label)
        footer_row.addStretch()

        main_layout.addWidget(stage_box)
        main_layout.addLayout(top_dashboard_row)
        main_layout.addWidget(member_box, 3)
        main_layout.addWidget(guest_box, 2)
        main_layout.addLayout(footer_row)

        self.load_data()

    def load_data(self):
        self._refresh_workflow_guidance()
        self.load_workflow_stage()
        self.load_available_members()
        self.load_member_rsvps()
        self.load_guests()
        self.refresh_eligible_summary()

    def load_workflow_stage(self):
        current_stage = self.rsvp_service.get_outing_workflow_stage(self.outing_id)
        for index in range(self.stage_combo.count()):
            if self.stage_combo.itemData(index) == current_stage:
                self.stage_combo.setCurrentIndex(index)
                break

    def save_workflow_stage(self):
        try:
            self.rsvp_service.set_outing_workflow_stage(
                self.outing_id,
                self.stage_combo.currentData(),
            )
            show_info(self, "Stage Saved", "Workflow stage updated.")
        except Exception as exc:
            show_warning(
                self,
                "Save Failed",
                f"Could not update workflow stage.\n\n{exc}",
            )

    def load_available_members(self):
        self.available_members_list.clear()
        rows = self.rsvp_service.list_uninvited_active_members_for_outing(
            self.outing_id
        )

        for row in rows:
            item = QListWidgetItem(f"{row['first_name']} {row['last_name']}")
            item.setData(DataRole.UserRole, int(row["id"]))
            self.available_members_list.addItem(item)

    def load_member_rsvps(self):
        rows = self._build_dashboard_rows()

        self.member_rsvp_table.clear()
        self.member_rsvp_table.setRowCount(0)
        self.member_rsvp_table.setColumnCount(8)
        self.member_rsvp_table.setHorizontalHeaderLabels(
            [
                "Member",
                "Email",
                "Status",
                "Responded",
                "Schedule State",
                "Tee Time",
                "Waitlist",
                "Note",
            ]
        )

        for row_idx, row in enumerate(rows):
            self.member_rsvp_table.insertRow(row_idx)

            member_item = QTableWidgetItem(row["member_name"])
            member_item.setData(DataRole.UserRole, int(row["member_id"]))

            email_item = QTableWidgetItem(row["email"])
            status_item = QTableWidgetItem(row["rsvp_status"])
            responded_item = QTableWidgetItem(row["responded_at"])
            scheduled_item = QTableWidgetItem(row["scheduled"])
            tee_time_item = QTableWidgetItem(row["tee_time"])
            waitlist_item = QTableWidgetItem(row["waitlist_position"])
            note_item = QTableWidgetItem(row["note"])

            self.member_rsvp_table.setItem(row_idx, 0, member_item)
            self.member_rsvp_table.setItem(row_idx, 1, email_item)
            self.member_rsvp_table.setItem(row_idx, 2, status_item)
            self.member_rsvp_table.setItem(row_idx, 3, responded_item)
            self.member_rsvp_table.setItem(row_idx, 4, scheduled_item)
            self.member_rsvp_table.setItem(row_idx, 5, tee_time_item)
            self.member_rsvp_table.setItem(row_idx, 6, waitlist_item)
            self.member_rsvp_table.setItem(row_idx, 7, note_item)

            self._apply_member_row_styling(row_idx, row)

        self.member_rsvp_table.resizeColumnsToContents()
        self.member_rsvp_table.horizontalHeader().setStretchLastSection(True)

    def _apply_member_row_styling(self, row_idx: int, row: dict):
        status = row["rsvp_status"]
        schedule_state = row["scheduled"]

        default_text_color = self.member_rsvp_table.palette().color(
            self.member_rsvp_table.foregroundRole()
        )

        if schedule_state == "Scheduled":
            foreground = QBrush(Qt.GlobalColor.darkGreen)
        elif status == "yes":
            foreground = QBrush(Qt.GlobalColor.darkYellow)
        else:
            foreground = QBrush(default_text_color)

        for col_idx in range(self.member_rsvp_table.columnCount()):
            item = self.member_rsvp_table.item(row_idx, col_idx)
            if item is not None:
                item.setForeground(foreground)

    def load_guests(self):
        rows = self.guest_service.list_outing_guests(self.outing_id)

        self.guest_table.clear()
        self.guest_table.setRowCount(0)
        self.guest_table.setColumnCount(4)
        self.guest_table.setHorizontalHeaderLabels(
            ["Guest", "Sponsor", "Status", "Responded"]
        )

        for row_idx, row in enumerate(rows):
            self.guest_table.insertRow(row_idx)

            guest_item = QTableWidgetItem(f"{row['first_name']} {row['last_name']}")
            guest_item.setData(DataRole.UserRole, int(row["guest_id"]))

            sponsor_item = QTableWidgetItem(
                f"{row['sponsor_first_name']} {row['sponsor_last_name']}"
            )
            status_item = QTableWidgetItem(str(row["status"] or ""))
            responded_item = QTableWidgetItem(str(row["responded_at"] or ""))

            self.guest_table.setItem(row_idx, 0, guest_item)
            self.guest_table.setItem(row_idx, 1, sponsor_item)
            self.guest_table.setItem(row_idx, 2, status_item)
            self.guest_table.setItem(row_idx, 3, responded_item)

        self.guest_table.resizeColumnsToContents()
        self.guest_table.horizontalHeader().setStretchLastSection(True)

    def refresh_eligible_summary(self):
        dashboard_rows = self._build_dashboard_rows()
        tee_times = self.outing_service.get_tee_times(self.outing_id)

        invited_count = len(dashboard_rows)
        confirmed_count = sum(
            1 for row in dashboard_rows if row["rsvp_status"] == "yes"
        )
        pending_count = invited_count - confirmed_count
        scheduled_count = sum(
            1 for row in dashboard_rows if row["scheduled"] == "Scheduled"
        )
        waitlist_count = sum(
            1 for row in dashboard_rows if row["scheduled"] == "Waitlist"
        )

        guest_rows = self.guest_service.list_schedulable_outing_guests(self.outing_id)
        guest_confirmed_count = len(guest_rows)

        capacity = sum(int(row["max_players"]) for row in tee_times)
        open_spots = max(0, capacity - scheduled_count)

        self.eligible_summary_label.setText(
            f"Pending Invitation Response: {pending_count}  |  "
            f"Confirmed: {confirmed_count}  |  "
            f"Scheduled: {scheduled_count}  |  "
            f"Waitlist: {waitlist_count}  |  "
            f"Guests Confirmed: {guest_confirmed_count}  |  "
            f"Open Spots: {open_spots}"
        )

    def invite_all_active_members(self):
        try:
            self.rsvp_service.invite_all_active_members(self.outing_id)
            self.load_data()
        except Exception as exc:
            show_warning(
                self,
                "Invite Failed",
                f"Could not invite active members.\n\n{exc}",
            )

    def invite_selected_members(self):
        items = self.available_members_list.selectedItems()
        if not items:
            show_warning(
                self,
                "No Selection",
                "Select one or more members to invite.",
            )
            return

        member_ids = [int(item.data(DataRole.UserRole)) for item in items]

        try:
            self.rsvp_service.invite_members(self.outing_id, member_ids)
            self.load_data()
        except Exception as exc:
            show_warning(
                self,
                "Invite Failed",
                f"Could not invite selected members.\n\n{exc}",
            )

    def invite_double_clicked_member(self, item):
        if not item:
            return

        member_id = int(item.data(DataRole.UserRole))
        try:
            self.rsvp_service.invite_members(self.outing_id, [member_id])
            self.load_data()
        except Exception as exc:
            show_warning(
                self,
                "Member Not Invited",
                f"The member could not be invited. Please try again.\n\n{exc}",
            )

    def _selected_member_rsvp_ids(self):
        ids = []
        seen = set()

        for item in self.member_rsvp_table.selectedItems():
            row = item.row()
            member_item = self.member_rsvp_table.item(row, 0)
            if member_item is None:
                continue

            member_id = int(member_item.data(DataRole.UserRole))
            if member_id not in seen:
                seen.add(member_id)
                ids.append(member_id)

        return ids

    def _selected_member_email_template(self) -> str:
        return str(self.member_email_template_combo.currentData() or "invitation")

    def _member_email_template_settings_key(self) -> str:
        return "outing_rsvp/member_email_template"

    def _restore_member_email_template(self):
        saved_value = self.settings.value(
            self._member_email_template_settings_key(),
            "invitation",
            type=str,
        )

        for index in range(self.member_email_template_combo.count()):
            if self.member_email_template_combo.itemData(index) == saved_value:
                self.member_email_template_combo.setCurrentIndex(index)
                return

        self.member_email_template_combo.setCurrentIndex(0)

    def _save_member_email_template(self):
        self.settings.setValue(
            self._member_email_template_settings_key(),
            self._selected_member_email_template(),
        )

    def _force_member_email_template(self, template_type: str):
        for index in range(self.member_email_template_combo.count()):
            if self.member_email_template_combo.itemData(index) == template_type:
                self.member_email_template_combo.setCurrentIndex(index)
                return

    def _refresh_workflow_guidance(self):
        try:
            snapshot = self.workflow_service.get_workflow_snapshot(self.outing_id)
        except Exception:
            self.current_stage_value_label.setText("--")
            # self.outing_date_value_label.setText("--")
            self.schedule_status_value_label.setText("--")
            self.recommended_template_value_label.setText("--")
            self.recommended_next_step_label.setText("--")

            self.invitation_draft_status_value_label.setText("--")
            self.pairings_draft_status_value_label.setText("--")
            self.revised_pairings_draft_status_value_label.setText("--")
            self.course_hold_draft_status_value_label.setText("--")
            self.course_final_draft_status_value_label.setText("--")
            self.revised_needed_status_value_label.setText("--")
            self.send_recommended_template_button.setEnabled(False)
            return

        self._update_workflow_summary_labels(snapshot)
        self._update_communication_status_labels(snapshot)
        self._update_shortcut_buttons(snapshot)

        recommended_template = str(
            snapshot.get("recommended_member_template", "invitation")
        )
        self._force_member_email_template(recommended_template)

        next_step = str(snapshot.get("recommended_next_step", "")).strip() or "--"
        self.recommended_next_step_label.setText(next_step)

    def _set_member_email_template_if_available(self, template_type: str):
        current_value = self._selected_member_email_template()

        should_override = (
            current_value == "invitation" or template_type == "revised_pairings"
        )

        if not should_override:
            return

        for index in range(self.member_email_template_combo.count()):
            if self.member_email_template_combo.itemData(index) == template_type:
                self.member_email_template_combo.setCurrentIndex(index)
                return

    def _format_draft_status(self, status: str, sent_at: str) -> str:
        status = str(status or "").strip()
        sent_at = str(sent_at or "").strip()

        if not status:
            return "Missing"

        if status == "sent":
            if sent_at:
                formatted_sent_at = self._format_datetime_mmddyyyy_ampm(sent_at)
                return f"Sent ({formatted_sent_at})"
            return "Sent"

        return "Draft"

    def _format_datetime_mmddyyyy_ampm(self, value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return "--"

        try:
            dt = datetime.fromisoformat(raw.replace(" ", "T"))
            return dt.strftime("%m-%d-%Y @ %I:%M %p")
        except ValueError:
            return raw

    def _update_workflow_summary_labels(self, snapshot: dict):
        current_stage = str(snapshot.get("current_stage", "")).strip() or "--"
        outing_date_raw = str(snapshot.get("outing_date", "")).strip()
        outing_date = self._format_mmddyyyy(outing_date_raw)
        has_assignments = bool(snapshot.get("schedule_generated", False))
        schedule_status = "Generated" if has_assignments else "Not Generated"
        recommended_template = (
            str(snapshot.get("recommended_member_template", "")).strip() or "--"
        )

        course_name = ""
        if self.outing is not None:
            try:
                course_name = str(self.outing["course_name"] or "").strip()
            except Exception:
                course_name = ""

        if course_name and outing_date != "--":
            outing_summary = f"{course_name} — {outing_date}"
        elif outing_date != "--":
            outing_summary = outing_date
        else:
            outing_summary = "--"

        self.outing_summary_label.setText(outing_summary)
        self.current_stage_value_label.setText(current_stage)
        self.outing_date_value_label.setText(outing_date)
        self.schedule_status_value_label.setText(schedule_status)
        self.recommended_template_value_label.setText(recommended_template)

    def _update_communication_status_labels(self, snapshot: dict):
        self.invitation_draft_status_value_label.setText(
            self._format_draft_status(
                snapshot.get("invitation_draft_status", ""),
                snapshot.get("invitation_sent_at", ""),
            )
        )

        self.pairings_draft_status_value_label.setText(
            self._format_draft_status(
                snapshot.get("pairings_draft_status", ""),
                snapshot.get("pairings_sent_at", ""),
            )
        )

        self.revised_pairings_draft_status_value_label.setText(
            self._format_draft_status(
                snapshot.get("revised_pairings_draft_status", ""),
                snapshot.get("revised_pairings_sent_at", ""),
            )
        )

        self.course_hold_draft_status_value_label.setText(
            self._format_draft_status(
                snapshot.get("course_hold_draft_status", ""),
                snapshot.get("course_hold_sent_at", ""),
            )
        )

        self.course_final_draft_status_value_label.setText(
            self._format_draft_status(
                snapshot.get("course_final_draft_status", ""),
                snapshot.get("course_final_sent_at", ""),
            )
        )

        self.revised_needed_status_value_label.setText(
            "Yes" if bool(snapshot.get("schedule_revision_detected", False)) else "No"
        )

    def open_draft_editor(self):
        try:
            self.outing = self.outing_service.get_outing(self.outing_id)
            snapshot = self.workflow_service.get_workflow_snapshot(self.outing_id)
        except Exception as exc:
            show_warning(
                self,
                "Open Draft Editor Failed",
                f"Could not reload outing.\n\n{exc}",
            )
            return

        if not self.outing:
            show_warning(
                self,
                "Outing Not Found",
                "Could not load the selected outing.",
            )
            return

        recommended_template = (
            str(snapshot.get("recommended_member_template", "invitation")).strip()
            or "invitation"
        )

        dialog = EmailDraftDialog(
            self.outing,
            self.draft_service,
            email_send_service=self.email_send_service,
            parent=self,
        )
        dialog.audience_combo.setCurrentText("member")

        for index in range(dialog.template_combo.count()):
            if dialog.template_combo.itemText(index) == recommended_template:
                dialog.template_combo.setCurrentIndex(index)
                break

        dialog.exec_()
        self.load_data()

    def update_selected_member_rsvps(self, status: str):
        member_ids = self._selected_member_rsvp_ids()
        if not member_ids:
            show_warning(
                self,
                "No Selection",
                "Select one or more RSVP rows first.",
            )
            return

        try:
            for member_id in member_ids:
                self.rsvp_service.set_member_rsvp_status(
                    self.outing_id,
                    member_id,
                    status,
                )
            self.load_data()
            self._warn_if_schedule_invalid_after_guest_change()
        except Exception as exc:
            show_warning(
                self,
                "RSVP Not Updated",
                f"The member’s RSVP status could not be updated. Please try again.\n\n{exc}",
            )

    def remove_selected_member_rsvps(self):
        member_ids = self._selected_member_rsvp_ids()
        if not member_ids:
            show_warning(
                self,
                "No Selection",
                "Select one or more RSVP rows first.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Remove Invite(s)",
            f"Remove {len(member_ids)} member invite(s) from this outing?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            for member_id in member_ids:
                self.rsvp_service.remove_member_rsvp(self.outing_id, member_id)
            self.load_data()
            self._warn_if_schedule_invalid_after_guest_change()
        except Exception as exc:
            show_warning(
                self,
                "Remove Failed",
                f"Could not remove selected invite(s).\n\n{exc}",
            )

    def _selected_guest_ids(self):
        ids = []
        seen = set()

        for item in self.guest_table.selectedItems():
            row = item.row()
            guest_item = self.guest_table.item(row, 0)
            if guest_item is None:
                continue

            guest_id = int(guest_item.data(DataRole.UserRole))
            if guest_id not in seen:
                seen.add(guest_id)
                ids.append(guest_id)

        return ids

    def add_guest_to_outing(self):
        member_rsvp_rows = self.rsvp_service.list_member_rsvps_for_outing(
            self.outing_id
        )
        if not member_rsvp_rows:
            show_warning(
                self,
                "No Sponsors Available",
                "Invite at least one member before adding a guest.",
            )
            return

        sponsor_lookup = {}
        sponsor_labels = []
        for row in member_rsvp_rows:
            member_id = int(row["member_id"])
            label = f"{row['first_name']} {row['last_name']}"
            sponsor_lookup[label] = member_id
            sponsor_labels.append(label)

        sponsor_label, ok = QInputDialog.getItem(
            self,
            "Select Sponsor",
            "Sponsoring Member",
            sponsor_labels,
            0,
            False,
        )
        if not ok or not sponsor_label:
            return

        sponsor_member_id = sponsor_lookup[sponsor_label]

        existing_guests = self.guest_service.list_guests(active_only=True)
        guest_choices = ["<Create New Guest>"] + [
            f"{row['first_name']} {row['last_name']} (id:{row['id']})"
            for row in existing_guests
        ]

        guest_choice, ok = QInputDialog.getItem(
            self,
            "Select Guest",
            "Guest",
            guest_choices,
            0,
            False,
        )
        if not ok or not guest_choice:
            return

        if guest_choice == "<Create New Guest>":
            dlg = GuestFormDialog(parent=self)
            if not dlg.exec_():
                return

            values = dlg.values()
            guest_id = self.guest_service.create_guest(values)
        else:
            try:
                guest_id = int(guest_choice.rsplit("(id:", 1)[1].rstrip(")"))
            except (IndexError, ValueError):
                show_warning(
                    self,
                    "Invalid Guest Selection",
                    "Could not determine the selected guest.",
                )
                return

        status, ok = QInputDialog.getItem(
            self,
            "Guest Status",
            "Initial RSVP Status",
            RSVP_STATUSES,
            0,
            False,
        )
        if not ok or not status:
            return

        try:
            self.guest_service.add_guest_to_outing(
                outing_id=self.outing_id,
                guest_id=guest_id,
                sponsoring_member_id=sponsor_member_id,
                status=status,
            )
            self.load_data()
            self._warn_if_schedule_invalid_after_guest_change()
        except Exception as exc:
            show_warning(
                self,
                "Guest Add Failed",
                f"Could not add guest to outing.\n\n{exc}",
            )

    def update_selected_guest_statuses(self, status: str):
        guest_ids = self._selected_guest_ids()
        if not guest_ids:
            show_warning(
                self,
                "No Selection",
                "Select one or more guest rows first.",
            )
            return

        try:
            for guest_id in guest_ids:
                self.guest_service.set_outing_guest_status(
                    self.outing_id,
                    guest_id,
                    status,
                )
            self.load_data()
            self._warn_if_schedule_invalid_after_guest_change()
        except Exception as exc:
            show_warning(
                self,
                "Update Failed",
                f"Could not update guest status.\n\n{exc}",
            )

    def remove_selected_guests(self):
        guest_ids = self._selected_guest_ids()
        if not guest_ids:
            show_warning(
                self,
                "No Selection",
                "Select one or more guest rows first.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Remove Guest(s)",
            f"Remove {len(guest_ids)} guest(s) from this outing?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            for guest_id in guest_ids:
                self.guest_service.remove_guest_from_outing(self.outing_id, guest_id)
            self.load_data()
            self._warn_if_schedule_invalid_after_guest_change()
        except Exception as exc:
            show_warning(
                self,
                "Remove Failed",
                f"Could not remove guest(s) from outing.\n\n{exc}",
            )

    def edit_selected_guest(self):
        guest_ids = self._selected_guest_ids()
        if not guest_ids:
            show_warning(
                self,
                "No Selection",
                "Select one guest row first.",
            )
            return

        if len(guest_ids) > 1:
            show_warning(
                self,
                "Multiple Guests Selected",
                "Select only one guest to edit.",
            )
            return

        guest_id = guest_ids[0]
        guest = self.guest_service.get_guest(guest_id)
        if not guest:
            show_warning(
                self,
                "Guest Not Found",
                "The selected guest record could not be found.",
            )
            return

        dlg = GuestFormDialog(guest, self)
        if not dlg.exec_():
            return

        self.guest_service.update_guest(guest_id, dlg.values())
        self.load_data()
        self._warn_if_schedule_invalid_after_guest_change()

    def _warn_if_schedule_invalid_after_guest_change(self):
        try:
            self.outing_service.validate_existing_schedule(self.outing_id)
        except Exception as exc:
            try:
                self.rsvp_service.set_outing_workflow_stage(
                    self.outing_id,
                    "schedule_revised",
                )
            except Exception:
                pass

            show_warning(
                self,
                "Schedule Needs Review",
                "This change may affect the current schedule.\n\n"
                "Please review the schedule before sending updated pairings.\n\n"
                f"Details: {exc}",
            )

    def _build_dashboard_rows(self):
        rsvp_rows = self.rsvp_service.list_member_rsvps_for_outing(self.outing_id)
        assignment_rows = self.outing_service.get_assignments(self.outing_id)

        assigned_by_member_id: dict[int, str] = {}
        for row in assignment_rows:
            assigned_by_member_id[int(row["member_id"])] = str(row["tee_time"] or "")

        yes_unassigned_member_ids = [
            int(row["member_id"])
            for row in rsvp_rows
            if str(row["status"] or "") == "yes"
            and int(row["member_id"]) not in assigned_by_member_id
        ]

        waitlist_position_by_member_id = {
            member_id: index + 1
            for index, member_id in enumerate(yes_unassigned_member_ids)
        }

        dashboard_rows = []

        for row in rsvp_rows:
            member_id = int(row["member_id"])
            assigned_tee_time = assigned_by_member_id.get(member_id, "")
            is_scheduled = member_id in assigned_by_member_id
            is_yes = str(row["status"] or "") == "yes"

            waitlist_position = ""
            schedule_state = ""

            if is_scheduled:
                schedule_state = "Scheduled"
            elif is_yes and assignment_rows:
                schedule_state = "Waitlist"
                waitlist_position = str(
                    waitlist_position_by_member_id.get(member_id, "")
                )
            elif is_yes:
                schedule_state = "Confirmed"

            dashboard_rows.append(
                {
                    "member_id": member_id,
                    "member_name": f"{row['first_name']} {row['last_name']}".strip(),
                    "email": str(row["email"] or ""),
                    "rsvp_status": str(row["status"] or ""),
                    "responded_at": str(row["responded_at"] or ""),
                    "scheduled": schedule_state,
                    "tee_time": assigned_tee_time,
                    "waitlist_position": waitlist_position,
                    "note": str(row["note"] or ""),
                }
            )

        def sort_key(row):
            status = row["rsvp_status"]
            schedule_state = row["scheduled"]

            if schedule_state == "Scheduled":
                return (0, row["tee_time"])
            if status == "yes":
                return (1, int(row["waitlist_position"] or 9999))
            return (2, row["member_name"].lower())

        return sorted(dashboard_rows, key=sort_key)

    def _format_mmddyyyy(self, value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return "--"

        parts = raw.split("-")
        if len(parts) == 3:
            year, month, day = parts
            if len(year) == 4:
                return f"{month}-{day}-{year}"

        return raw

    def send_email_to_selected_members(self):
        member_ids = self._selected_member_rsvp_ids()
        if not member_ids:
            show_warning(
                self,
                "No Selection",
                "Select one or more member RSVP rows first.",
            )
            return

        template_type = self._selected_member_email_template()

        confirm = QMessageBox.question(
            self,
            "Send Email to Selected Members",
            f"Send the saved '{template_type}' draft to {len(member_ids)} selected member(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            progress = QProgressDialog(
                "Sending email to members...",
                None,
                0,
                0,
                self,
            )
            progress.setWindowTitle("Sending Email")
            progress.setMinimumDuration(0)
            progress.setCancelButton(None)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()

            QApplication.processEvents()

            result = self.email_send_service.send_draft_to_member_ids(
                outing_id=self.outing_id,
                template_type=template_type,
                member_ids=member_ids,
            )
            progress.close()

            sent_count = int(result.get("sent_count", 0))
            skipped_count = len(result.get("skipped", []))
            failed_count = len(result.get("failed", []))

            # Trying out the new block
            if template_type == "invitation" and sent_count > 0:
                successfully_sent_member_ids = []
                failed_member_ids = {
                    int(row["member_id"])
                    for row in result.get("failed", [])
                    if "member_id" in row
                }
                skipped_member_ids = {
                    int(row["member_id"])
                    for row in result.get("skipped", [])
                    if "member_id" in row
                }

                for member_id in member_ids:
                    member_id = int(member_id)
                    if member_id in failed_member_ids:
                        continue
                    if member_id in skipped_member_ids:
                        continue
                    successfully_sent_member_ids.append(member_id)

                if successfully_sent_member_ids:
                    self.rsvp_service.invite_members(
                        self.outing_id,
                        successfully_sent_member_ids,
                    )

            message = (
                f"SMTP accepted {sent_count} email(s).\n\n"
                f"Skipped: {skipped_count}\n"
                f"Failed: {failed_count}"
            )

            if skipped_count:
                skipped_lines = [
                    f"- Member {row['member_id']}: {row['reason']}"
                    for row in result["skipped"][:10]
                ]
                message += "\n\nSkipped details:\n" + "\n".join(skipped_lines)

            if failed_count:
                failed_lines = [
                    f"- Member {row['member_id']} ({row.get('email', '')}): {row['error']}"
                    for row in result["failed"][:10]
                ]
                message += "\n\nFailed details:\n" + "\n".join(failed_lines)

            show_info(
                self,
                "Selected Email Send Complete",
                message,
            )

        except Exception as exc:
            try:
                progress.close()
            except Exception:
                pass

            show_warning(
                self,
                "Send Failed",
                f"Could not send email to selected members.\n\n{exc}",
            )

    def _all_member_rsvp_ids(self):
        member_ids = []

        for row in range(self.member_rsvp_table.rowCount()):
            member_item = self.member_rsvp_table.item(row, 0)
            if member_item is None:
                continue

            member_id = member_item.data(DataRole.UserRole)
            if member_id is None:
                continue

            member_ids.append(int(member_id))

        seen = set()
        unique_ids = []
        for member_id in member_ids:
            if member_id not in seen:
                seen.add(member_id)
                unique_ids.append(member_id)

        return unique_ids

    def _all_available_member_ids(self):
        member_ids = []

        for row in range(self.available_members_list.count()):
            item = self.available_members_list.item(row)
            if item is None:
                continue

            member_id = item.data(DataRole.UserRole)
            if member_id is None:
                continue

            member_ids.append(int(member_id))

        seen = set()
        unique_ids = []

        for member_id in member_ids:
            if member_id not in seen:
                seen.add(member_id)
                unique_ids.append(member_id)

        return unique_ids

    def _all_active_member_ids(self):
        rows = self.member_service.list_members(active_only=True)

        member_ids = []
        seen = set()

        for row in rows:
            member_id = int(row["id"])
            if member_id not in seen:
                seen.add(member_id)
                member_ids.append(member_id)

        return member_ids

    def send_recommended_template(self):
        try:
            snapshot = self.workflow_service.get_workflow_snapshot(self.outing_id)
        except Exception as exc:
            show_warning(
                self,
                "Workflow Unavailable",
                f"Could not determine the recommended template.\n\n{exc}",
            )
            return

        template_type = (
            str(snapshot.get("recommended_member_template", "invitation")).strip()
            or "invitation"
        )

        draft = self.draft_service.get_draft(
            self.outing_id,
            "member",
            template_type,
        )

        if not draft:
            show_warning(
                self,
                "Draft Required",
                f"No saved '{template_type}' draft exists yet.\n\n"
                "Open Draft Editor and save a draft before sending email.",
            )
            return

        if template_type == "invitation":
            member_ids = self._all_available_member_ids()
        elif template_type in {"pairings", "revised_pairings"}:
            member_ids = self._all_active_member_ids()
        else:
            member_ids = []

        if not member_ids:
            show_warning(
                self,
                "No Members Available",
                "There are no members available to email.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Send Email",
            f"Send the saved '{template_type}' draft to {len(member_ids)} member(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            # 🔽 Create progress dialog
            self.progress = QProgressDialog(
                "Sending email to members...",
                None,
                0,
                0,
                self,
            )
            self.progress.setWindowTitle("Sending Email")
            self.progress.setCancelButton(None)
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.show()

            # 🔽 Setup thread + worker
            self.thread = QThread()
            self.worker = EmailSendWorker(
                self.email_send_service,
                self.outing_id,
                template_type,
                member_ids,
            )

            self.worker.moveToThread(self.thread)

            # 🔽 Wire signals
            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self._on_email_send_complete)
            self.worker.error.connect(self._on_email_send_error)

            # Cleanup
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            self._last_send_member_ids = list(member_ids)
            self._last_send_template_type = template_type

            self.thread.start()

        except Exception as exc:
            show_warning(
                self,
                "Send Failed",
                f"Could not send email.\n\n{exc}",
            )

    def _update_shortcut_buttons(self, snapshot: dict):
        recommended_template = str(
            snapshot.get("recommended_member_template", "")
        ).strip()

        available_member_count = self.available_members_list.count()
        active_member_count = len(self.member_service.list_members(active_only=True))
        schedule_generated = bool(snapshot.get("schedule_generated", False))
        should_generate_schedule_now = bool(
            snapshot.get("should_generate_schedule_now", False)
        )
        confirmed_count = int(snapshot.get("yes_count", 0) or 0)

        enable_send = False

        if recommended_template == "invitation":
            enable_send = available_member_count > 0
        elif recommended_template in {"pairings", "revised_pairings"}:
            enable_send = active_member_count > 0 and schedule_generated

        self.send_recommended_template_button.setEnabled(enable_send)
        self.generate_schedule_button.setEnabled(
            (not schedule_generated)
            and (should_generate_schedule_now or confirmed_count > 0)
        )

    def _on_email_send_complete(self, result: dict):
        self.progress.close()

        sent_count = int(result.get("sent_count", 0))
        skipped_count = len(result.get("skipped", []))
        failed_count = len(result.get("failed", []))

        template_type = getattr(self, "_last_send_template_type", "")

        if template_type == "invitation" and sent_count > 0:
            attempted_member_ids = getattr(self, "_last_send_member_ids", [])
            failed_ids = {
                int(r["member_id"])
                for r in result.get("failed", [])
                if "member_id" in r
            }
            skipped_ids = {
                int(r["member_id"])
                for r in result.get("skipped", [])
                if "member_id" in r
            }

            successful_ids = [
                int(member_id)
                for member_id in attempted_member_ids
                if int(member_id) not in failed_ids
                and int(member_id) not in skipped_ids
            ]

            if successful_ids:
                self.rsvp_service.invite_members(self.outing_id, successful_ids)

        message = (
            f"SMTP accepted {sent_count} email(s).\n\n"
            f"Skipped: {skipped_count}\n"
            f"Failed: {failed_count}"
        )

        if skipped_count:
            skipped_lines = [
                f"- Member {row['member_id']}: {row['reason']}"
                for row in result["skipped"][:10]
            ]
            message += "\n\nSkipped details:\n" + "\n".join(skipped_lines)

        if failed_count:
            failed_lines = [
                f"- Member {row['member_id']} ({row.get('email', '')}): {row['error']}"
                for row in result["failed"][:10]
            ]
            message += "\n\nFailed details:\n" + "\n".join(failed_lines)

        show_info(
            self,
            "Email Send Complete",
            message,
        )

        self.load_data()

    def _on_email_send_error(self, error_msg: str):
        self.progress.close()

        show_warning(
            self,
            "Send Failed",
            f"Could not send email.\n\n{error_msg}",
        )

    def generate_schedule_from_rsvp(self):
        try:
            parent = self.parent()

            if parent is not None and hasattr(parent, "generate_schedule"):
                parent.generate_schedule()
            else:
                raise RuntimeError("Main window does not expose generate_schedule().")

            self.outing = self.outing_service.get_outing(self.outing_id)
            self.load_data()

        except Exception as exc:
            show_warning(
                self,
                "Generate Schedule Failed",
                f"Could not generate schedule.\n\n{exc}",
            )
