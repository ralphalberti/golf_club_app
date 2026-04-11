from PyQt5.QtGui import QBrush
from ui.shared.forms import GuestFormDialog
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtWidgets import (
    QAbstractItemView,
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
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

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

RSVP_STATUSES = ["invited", "yes"]

MEMBER_EMAIL_TEMPLATES = [
    ("Invitation", "invitation"),
    ("Pairings", "pairings"),
    ("Revised Pairings", "revised_pairings"),
]


class OutingRSVPDialog(QDialog):
    def __init__(
        self,
        outing_id: int,
        outing_service,
        rsvp_service,
        guest_service,
        email_send_service,
        parent=None,
    ):
        super().__init__(parent)
        self.outing_id = outing_id
        self.outing_service = outing_service
        self.rsvp_service = rsvp_service
        self.guest_service = guest_service
        self.email_send_service = email_send_service
        self.settings = QSettings("GolfClubApp", "OutingManager")

        self.setWindowTitle("Manage RSVP")
        self.resize(1200, 760)

        self.stage_combo = QComboBox()
        for stage in WORKFLOW_STAGES:
            self.stage_combo.addItem(stage, stage)

        self.save_stage_button = QPushButton("Save Stage")
        self.save_stage_button.clicked.connect(self.save_workflow_stage)

        self.invite_all_button = QPushButton("Invite All Active Members")
        self.invite_selected_button = QPushButton("Invite Selected")
        self.remove_invite_button = QPushButton("Remove Invite")
        self.send_selected_email_button = QPushButton("Send Email to Selected")

        self.mark_member_invited_button = QPushButton("Reset to Pending")
        self.mark_member_yes_button = QPushButton("Mark Confirmed")

        self.add_guest_button = QPushButton("Add Guest to Outing")
        self.edit_guest_button = QPushButton("Edit Guest")
        self.remove_guest_button = QPushButton("Remove Guest")
        self.mark_guest_invited_button = QPushButton("Guest Pending")
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
        self.available_members_list.itemDoubleClicked.connect(
            self.invite_double_clicked_member
        )

        self.member_rsvp_table = QTableWidget()
        self.member_rsvp_table.setSelectionBehavior(SelectionBehavior.SelectRows)
        self.member_rsvp_table.setSelectionMode(SelectionMode.ExtendedSelection)
        self.member_rsvp_table.setEditTriggers(EditTrigger.NoEditTriggers)

        self.guest_table = QTableWidget()
        self.guest_table.setSelectionBehavior(SelectionBehavior.SelectRows)
        self.guest_table.setSelectionMode(SelectionMode.ExtendedSelection)
        self.guest_table.setEditTriggers(EditTrigger.NoEditTriggers)

        self.eligible_summary_label = QLabel("RSVP Summary: --")

        main_layout = QVBoxLayout(self)

        stage_box = QGroupBox("Workflow Stage")
        stage_layout = QHBoxLayout(stage_box)
        stage_layout.addWidget(QLabel("Current Stage"))
        stage_layout.addWidget(self.stage_combo)
        stage_layout.addWidget(self.save_stage_button)
        stage_layout.addStretch()

        member_box = QGroupBox("Member RSVP Management")
        member_layout = QGridLayout(member_box)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Active Members Not Yet Invited"))
        left_layout.addWidget(self.available_members_list)

        left_button_row = QHBoxLayout()
        left_button_row.addWidget(self.invite_selected_button)
        left_button_row.addWidget(self.invite_all_button)
        left_layout.addLayout(left_button_row)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("Invited / Confirmed Members"))
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
        main_layout.addWidget(member_box, 3)
        main_layout.addWidget(guest_box, 2)
        main_layout.addLayout(footer_row)

        self.load_data()

    def load_data(self):
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
            QMessageBox.information(self, "Stage Saved", "Workflow stage updated.")
        except Exception as exc:
            QMessageBox.warning(
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
            f"Pending: {pending_count}  |  "
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
            QMessageBox.warning(
                self,
                "Invite Failed",
                f"Could not invite active members.\n\n{exc}",
            )

    def invite_selected_members(self):
        items = self.available_members_list.selectedItems()
        if not items:
            QMessageBox.warning(
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
            QMessageBox.warning(
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
            QMessageBox.warning(
                self,
                "Invite Failed",
                f"Could not invite member.\n\n{exc}",
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

    def update_selected_member_rsvps(self, status: str):
        member_ids = self._selected_member_rsvp_ids()
        if not member_ids:
            QMessageBox.warning(
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
            QMessageBox.warning(
                self,
                "Update Failed",
                f"Could not update member RSVP status.\n\n{exc}",
            )

    def remove_selected_member_rsvps(self):
        member_ids = self._selected_member_rsvp_ids()
        if not member_ids:
            QMessageBox.warning(
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
            QMessageBox.warning(
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
            QMessageBox.warning(
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
                QMessageBox.warning(
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
            QMessageBox.warning(
                self,
                "Guest Add Failed",
                f"Could not add guest to outing.\n\n{exc}",
            )

    def update_selected_guest_statuses(self, status: str):
        guest_ids = self._selected_guest_ids()
        if not guest_ids:
            QMessageBox.warning(
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
            QMessageBox.warning(
                self,
                "Update Failed",
                f"Could not update guest status.\n\n{exc}",
            )

    def remove_selected_guests(self):
        guest_ids = self._selected_guest_ids()
        if not guest_ids:
            QMessageBox.warning(
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
            QMessageBox.warning(
                self,
                "Remove Failed",
                f"Could not remove guest(s) from outing.\n\n{exc}",
            )

    def edit_selected_guest(self):
        guest_ids = self._selected_guest_ids()
        if not guest_ids:
            QMessageBox.warning(
                self,
                "No Selection",
                "Select one guest row first.",
            )
            return

        if len(guest_ids) > 1:
            QMessageBox.warning(
                self,
                "Multiple Guests Selected",
                "Select only one guest to edit.",
            )
            return

        guest_id = guest_ids[0]
        guest = self.guest_service.get_guest(guest_id)
        if not guest:
            QMessageBox.warning(
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

            QMessageBox.warning(
                self,
                "Schedule Needs Revision",
                "This guest change makes the current schedule invalid.\n\n"
                "Please regenerate or revise the schedule.\n\n"
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
            elif is_yes:
                schedule_state = "Waitlist"
                waitlist_position = str(
                    waitlist_position_by_member_id.get(member_id, "")
                )

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

    def send_email_to_selected_members(self):
        member_ids = self._selected_member_rsvp_ids()
        if not member_ids:
            QMessageBox.warning(
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
            result = self.email_send_service.send_draft_to_member_ids(
                outing_id=self.outing_id,
                template_type=template_type,
                member_ids=member_ids,
            )

            sent_count = int(result.get("sent_count", 0))
            skipped_count = len(result.get("skipped", []))
            failed_count = len(result.get("failed", []))

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

            QMessageBox.information(
                self,
                "Selected Email Send Complete",
                message,
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Send Failed",
                f"Could not send email to selected members.\n\n{exc}",
            )
