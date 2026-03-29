from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME
from app.constants import APP_VERSION
from ui.outing_assignment_dialog import OutingAssignmentDialog
from ui.schedule_editor_dialog import ScheduleEditorDialog
from ui.shared.forms import MemberFormDialog, CourseFormDialog, OutingFormDialog


class MainWindow(QMainWindow):
    def __init__(
        self,
        current_user,
        member_service,
        course_service,
        outing_service,
        reporting_service,
        scheduling_service,
        distribution_service,
    ):
        super().__init__()

        # Services / state
        self.current_user = current_user
        self.member_service = member_service
        self.course_service = course_service
        self.outing_service = outing_service
        self.reporting_service = reporting_service
        self.scheduling_service = scheduling_service
        self.distribution_service = distribution_service

        # Window setup
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 720)

        # Core widgets
        self.tabs = QTabWidget()
        self.members_table = QTableWidget()
        self.courses_table = QTableWidget()
        self.outings_table = QTableWidget()
        self.assignments_table = QTableWidget()

        # Table behavior
        self.members_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.members_table.setSelectionMode(QTableWidget.SingleSelection)

        self.courses_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.courses_table.setSelectionMode(QTableWidget.SingleSelection)

        self.outings_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.outings_table.setSelectionMode(QTableWidget.SingleSelection)

        self.assignments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.assignments_table.setSelectionMode(QTableWidget.SingleSelection)

        # Tabs
        self.tabs.addTab(self._build_members_tab(), "Members")
        self.tabs.addTab(self._build_courses_tab(), "Courses")
        self.tabs.addTab(self._build_outings_tab(), "Outings / Schedules")

        # Signals
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.outings_table.itemSelectionChanged.connect(self.refresh_assignments)

        # Central layout
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.tabs)
        self.setCentralWidget(container)

        # Final setup
        self._build_menu_bar()
        self.refresh_all()

    def _build_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        help_menu = menu_bar.addMenu("Help")

        import_members_action = QAction("Import Member CSV", self)
        import_members_action.triggered.connect(self.import_member_csv)
        file_menu.addAction(import_members_action)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def _build_members_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        buttons = QHBoxLayout()

        add_btn = QPushButton("Add Member")
        edit_btn = QPushButton("Edit Member")
        delete_btn = QPushButton("Delete Member")

        add_btn.clicked.connect(self.add_member)
        edit_btn.clicked.connect(self.edit_member)
        delete_btn.clicked.connect(self.delete_member)

        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()

        layout.addLayout(buttons)
        layout.addWidget(self.members_table)
        return widget

    def _build_courses_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        buttons = QHBoxLayout()

        add_btn = QPushButton("Add Course")
        edit_btn = QPushButton("Edit Course")
        delete_btn = QPushButton("Delete Course")

        add_btn.clicked.connect(self.add_course)
        edit_btn.clicked.connect(self.edit_course)
        delete_btn.clicked.connect(self.delete_course)

        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()

        layout.addLayout(buttons)
        layout.addWidget(self.courses_table)
        return widget

    def _build_outings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        buttons = QHBoxLayout()

        create_btn = QPushButton("Create Outing")
        edit_btn = QPushButton("Edit Outing")
        delete_btn = QPushButton("Delete Outing")
        gen_btn = QPushButton("Generate Schedule")
        edit_schedule_btn = QPushButton("Edit Schedule")
        remove_player_btn = QPushButton("Remove Selected Player")
        refresh_btn = QPushButton("Refresh Assignments")
        export_btn = QPushButton("Export PDF / CSV")

        create_btn.clicked.connect(self.add_outing)
        edit_btn.clicked.connect(self.edit_outing)
        delete_btn.clicked.connect(self.delete_outing)
        gen_btn.clicked.connect(self.generate_schedule)
        edit_schedule_btn.clicked.connect(self.edit_schedule)
        remove_player_btn.clicked.connect(self.remove_selected_assignment)
        refresh_btn.clicked.connect(self.refresh_assignments)
        export_btn.clicked.connect(self.export_outputs)

        buttons.addWidget(create_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addWidget(gen_btn)
        buttons.addWidget(edit_schedule_btn)
        buttons.addWidget(remove_player_btn)
        buttons.addWidget(refresh_btn)
        buttons.addWidget(export_btn)
        buttons.addStretch()

        layout.addLayout(buttons)
        layout.addWidget(self.outings_table)
        layout.addWidget(self.assignments_table)
        return widget

    def refresh_all(self):
        self.load_members()
        self.load_courses()
        self.load_outings()
        self.refresh_assignments()

    def _populate_table(self, table, rows):
        if not rows:
            table.clear()
            table.setRowCount(0)
            table.setColumnCount(0)
            return

        columns = list(rows[0].keys())
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            for c, col in enumerate(columns):
                value = row[col]
                item = QTableWidgetItem("" if value is None else str(value))
                if c == 0 and "id" in row.keys():
                    item.setData(Qt.UserRole, row["id"])
                table.setItem(r, c, item)

        table.resizeColumnsToContents()

    def selected_row_id(self, table):
        row = table.currentRow()
        if row < 0:
            return None

        item = table.item(row, 0)
        if not item:
            return None

        hidden_id = item.data(Qt.UserRole)
        if hidden_id is not None:
            return int(hidden_id)

        text = item.text().strip()
        if text.isdigit():
            return int(text)

        return None

    def load_members(self):
        rows = self.member_service.list_members(active_only=False)

        self.members_table.clear()
        self.members_table.setRowCount(0)
        self.members_table.setColumnCount(9)
        self.members_table.setHorizontalHeaderLabels(
            [
                "First Name",
                "Last Name",
                "Email",
                "Phone",
                "Handicap",
                "Skill Tier",
                "Joined",
                "Active",
                "Notes",
            ]
        )

        tier_map = {
            1: "Tier I",
            2: "Tier II",
            3: "Tier III",
        }

        for row_idx, row in enumerate(rows):
            self.members_table.insertRow(row_idx)

            first_name_item = QTableWidgetItem(str(row["first_name"] or ""))
            first_name_item.setData(Qt.UserRole, row["id"])  # hidden member id
            first_name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            last_name_item = QTableWidgetItem(str(row["last_name"] or ""))
            last_name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            email_item = QTableWidgetItem(str(row["email"] or ""))
            email_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            phone_item = QTableWidgetItem(str(row["phone"] or ""))
            phone_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            handicap_value = "" if row["handicap"] is None else str(row["handicap"])
            handicap_item = QTableWidgetItem(handicap_value)
            handicap_item.setTextAlignment(Qt.AlignCenter)

            skill_tier_value = row["skill_tier"]
            skill_tier_text = tier_map.get(skill_tier_value, "")
            skill_tier_item = QTableWidgetItem(skill_tier_text)
            skill_tier_item.setTextAlignment(Qt.AlignCenter)

            joined_item = QTableWidgetItem(str(row["joined_date"] or ""))
            joined_item.setTextAlignment(Qt.AlignCenter)

            active_text = "Yes" if int(row["active"]) == 1 else "No"
            active_item = QTableWidgetItem(active_text)
            active_item.setTextAlignment(Qt.AlignCenter)

            notes_item = QTableWidgetItem(str(row["notes"] or ""))
            notes_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            self.members_table.setItem(row_idx, 0, first_name_item)
            self.members_table.setItem(row_idx, 1, last_name_item)
            self.members_table.setItem(row_idx, 2, email_item)
            self.members_table.setItem(row_idx, 3, phone_item)
            self.members_table.setItem(row_idx, 4, handicap_item)
            self.members_table.setItem(row_idx, 5, skill_tier_item)
            self.members_table.setItem(row_idx, 6, joined_item)
            self.members_table.setItem(row_idx, 7, active_item)
            self.members_table.setItem(row_idx, 8, notes_item)

        self.members_table.resizeColumnsToContents()
        self.members_table.horizontalHeader().setStretchLastSection(True)

    def load_courses(self):
        rows = self.course_service.list_courses()

        self.courses_table.clear()
        self.courses_table.setRowCount(0)
        self.courses_table.setColumnCount(7)
        self.courses_table.setHorizontalHeaderLabels(
            [
                "Course",
                "Address",
                "Active",
                "Notes",
                "Contact Name",
                "Contact Email",
                "Preferred Format",
            ]
        )

        for row_idx, row in enumerate(rows):
            self.courses_table.insertRow(row_idx)

            course_item = QTableWidgetItem(str(row["name"] or ""))
            course_item.setData(Qt.UserRole, row["id"])  # hidden course id
            course_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            address_item = QTableWidgetItem(str(row["address"] or ""))
            address_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            active_value = (
                row["active"]
                if "active" in row.keys()
                else row.get("default_active", 1)
            )
            active_text = "Yes" if int(active_value) == 1 else "No"
            active_item = QTableWidgetItem(active_text)
            active_item.setTextAlignment(Qt.AlignCenter)

            notes_item = QTableWidgetItem(str(row["notes"] or ""))
            notes_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            contact_name_item = QTableWidgetItem(str(row["contact_name"] or ""))
            contact_name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            contact_email_item = QTableWidgetItem(str(row["contact_email"] or ""))
            contact_email_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            preferred_format_item = QTableWidgetItem(str(row["preferred_format"] or ""))
            preferred_format_item.setTextAlignment(Qt.AlignCenter)

            self.courses_table.setItem(row_idx, 0, course_item)
            self.courses_table.setItem(row_idx, 1, address_item)
            self.courses_table.setItem(row_idx, 2, active_item)
            self.courses_table.setItem(row_idx, 3, notes_item)
            self.courses_table.setItem(row_idx, 4, contact_name_item)
            self.courses_table.setItem(row_idx, 5, contact_email_item)
            self.courses_table.setItem(row_idx, 6, preferred_format_item)

        self.courses_table.resizeColumnsToContents()
        self.courses_table.horizontalHeader().setStretchLastSection(True)

    def load_outings(self):
        outings = self.outing_service.list_outings()

        self.outings_table.clear()
        self.outings_table.setRowCount(0)
        self.outings_table.setColumnCount(5)
        self.outings_table.setHorizontalHeaderLabels(
            ["Outing Date", "Course", "Start Time", "Status", "Notes"]
        )

        for row_idx, row in enumerate(outings):
            self.outings_table.insertRow(row_idx)

            row_keys = set(row.keys())

            outing_date = (
                row["outing_date"]
                if "outing_date" in row_keys and row["outing_date"] is not None
                else ""
            )
            course_name = (
                row["course_name"]
                if "course_name" in row_keys and row["course_name"] is not None
                else ""
            )
            start_time = (
                row["start_time"]
                if "start_time" in row_keys and row["start_time"] is not None
                else ""
            )
            status = (
                row["status"]
                if "status" in row_keys and row["status"] is not None
                else ""
            )
            notes = (
                row["notes"] if "notes" in row_keys and row["notes"] is not None else ""
            )

            outing_date_item = QTableWidgetItem(str(outing_date))
            outing_date_item.setData(Qt.UserRole, row["id"])
            outing_date_item.setTextAlignment(Qt.AlignCenter)

            course_item = QTableWidgetItem(str(course_name))
            course_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            start_time_item = QTableWidgetItem(str(start_time))
            start_time_item.setTextAlignment(Qt.AlignCenter)

            status_item = QTableWidgetItem(str(status))
            status_item.setTextAlignment(Qt.AlignCenter)

            notes_item = QTableWidgetItem(str(notes))
            notes_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            self.outings_table.setItem(row_idx, 0, outing_date_item)
            self.outings_table.setItem(row_idx, 1, course_item)
            self.outings_table.setItem(row_idx, 2, start_time_item)
            self.outings_table.setItem(row_idx, 3, status_item)
            self.outings_table.setItem(row_idx, 4, notes_item)

        self._resize_outings_table_columns()

        # Run once more after Qt finishes laying out the table
        QTimer.singleShot(0, self._resize_outings_table_columns)

    def refresh_assignments(self):
        outing_id = self.selected_row_id(self.outings_table)
        rows = self.outing_service.get_assignments(outing_id) if outing_id else []

        self.assignments_table.clear()
        self.assignments_table.setRowCount(0)
        self.assignments_table.setColumnCount(5)
        self.assignments_table.setHorizontalHeaderLabels(
            ["Tee Time", "First Name", "Last Name", "Email", "Handicap"]
        )

        previous_tee_time = None

        for row_idx, row in enumerate(rows):
            self.assignments_table.insertRow(row_idx)

            current_tee_time = str(row["tee_time"] or "")
            show_tee_time = current_tee_time != previous_tee_time

            tee_time_item = QTableWidgetItem(current_tee_time if show_tee_time else "")
            tee_time_item.setData(Qt.UserRole, row["id"])  # hidden assignment id
            tee_time_item.setTextAlignment(Qt.AlignCenter)

            first_name_item = QTableWidgetItem(str(row["first_name"] or ""))
            first_name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            last_name_item = QTableWidgetItem(str(row["last_name"] or ""))
            last_name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            email_item = QTableWidgetItem(str(row["email"] or ""))
            email_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            handicap_value = "" if row["handicap"] is None else str(row["handicap"])
            handicap_item = QTableWidgetItem(handicap_value)
            handicap_item.setTextAlignment(Qt.AlignCenter)

            items = [
                tee_time_item,
                first_name_item,
                last_name_item,
                email_item,
                handicap_item,
            ]

            # Subtle separator effect: first row has date plus bold font
            if show_tee_time:
                font = QFont()
                font.setBold(True)
                tee_time_item.setFont(font)

            self.assignments_table.setItem(row_idx, 0, tee_time_item)
            self.assignments_table.setItem(row_idx, 1, first_name_item)
            self.assignments_table.setItem(row_idx, 2, last_name_item)
            self.assignments_table.setItem(row_idx, 3, email_item)
            self.assignments_table.setItem(row_idx, 4, handicap_item)

            previous_tee_time = current_tee_time

        self.assignments_table.resizeColumnsToContents()
        self.assignments_table.horizontalHeader().setStretchLastSection(True)

    def add_member(self):
        dlg = MemberFormDialog()
        if dlg.exec_():
            member_id = self.member_service.create_member(dlg.values())
            self.load_members()
            self.select_member_row_by_id(member_id)

    def edit_member(self):
        member_id = self.selected_row_id(self.members_table)
        if not member_id:
            QMessageBox.warning(self, "No selection", "Select a member first.")
            return

        member, _ = self.member_service.get_member(member_id)
        dlg = MemberFormDialog(member)

        if dlg.exec_():
            self.member_service.update_member(member_id, dlg.values())
            self.load_members()

    def delete_member(self):
        member_id = self.selected_row_id(self.members_table)
        if not member_id:
            QMessageBox.warning(self, "No selection", "Select a member first.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Member",
            "Are you sure you want to delete this member?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.member_service.delete_member(member_id)
            self.load_members()
            QMessageBox.information(
                self, "Member Deleted", "Member deleted successfully."
            )
        except Exception as exc:
            error_text = str(exc)

            if "FOREIGN KEY constraint failed" in error_text:
                QMessageBox.critical(
                    self,
                    "Delete Failed",
                    "Member cannot be deleted while participating in a currently scheduled outing.",
                )
            else:
                QMessageBox.critical(
                    self,
                    "Delete Failed",
                    f"Could not delete member.\n\n{exc}",
                )

    def add_course(self):
        dlg = CourseFormDialog()
        if dlg.exec_():
            course_id = self.course_service.create_course(dlg.values())
            self.load_courses()
            self.select_course_row_by_id(course_id)

    def edit_course(self):
        course_id = self.selected_row_id(self.courses_table)
        if not course_id:
            QMessageBox.warning(self, "No selection", "Select a course first.")
            return

        course = self.course_service.get_course(course_id)
        dlg = CourseFormDialog(course)

        if dlg.exec_():
            self.course_service.update_course(course_id, dlg.values())
            self.load_courses()

    def delete_course(self):
        course_id = self.selected_row_id(self.courses_table)
        if not course_id:
            QMessageBox.warning(self, "No selection", "Select a course first.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Course",
            "Are you sure you want to delete this course?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.course_service.delete_course(course_id)
            self.load_courses()
            QMessageBox.information(
                self, "Course Deleted", "Course deleted successfully."
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Delete Failed",
                f"Could not delete course.\n\n{exc}",
            )

    def add_outing(self):
        courses = self.course_service.list_courses()
        if not courses:
            QMessageBox.warning(self, "No courses", "Create at least one course first.")
            return

        dlg = OutingFormDialog(courses)
        if dlg.exec_():
            values = dlg.values()
            values["created_by"] = self.current_user.id
            values["updated_by"] = self.current_user.id
            self.outing_service.create_outing(values)
            self.load_outings()

    def edit_outing(self):
        outing_id = self.selected_row_id(self.outings_table)
        if not outing_id:
            QMessageBox.warning(self, "No selection", "Select an outing first.")
            return

        outing = self.outing_service.get_outing(outing_id)
        courses = self.course_service.list_courses()
        dlg = OutingFormDialog(courses, outing)

        if dlg.exec_():
            values = dlg.values()
            values["updated_by"] = self.current_user.id
            values["version"] = outing["version"]
            self.outing_service.update_outing(outing_id, values)
            self.load_outings()
            self.refresh_assignments()

    def delete_outing(self):
        outing_id = self.selected_row_id(self.outings_table)
        if not outing_id:
            QMessageBox.warning(self, "No selection", "Select an outing first.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Outing",
            "Delete this outing and all of its assignments?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.outing_service.delete_outing(outing_id)
            self.load_outings()
            self.refresh_assignments()
            QMessageBox.information(
                self,
                "Outing Deleted",
                "The outing was deleted successfully.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Delete Failed",
                f"Could not delete outing.\n\n{exc}",
            )

    def generate_schedule(self):
        outing_id = self.selected_row_id(self.outings_table)
        if not outing_id:
            QMessageBox.warning(self, "No outing selected", "Select an outing first.")
            return

        members = self.member_service.list_members(active_only=True)
        dlg = OutingAssignmentDialog(members, self)
        if not dlg.exec_():
            return

        member_ids = dlg.selected_member_ids()
        if not member_ids:
            QMessageBox.warning(self, "No players", "Select at least one player.")
            return

        self.scheduling_service.generate_schedule(outing_id, member_ids)
        self.outing_service.increment_version(outing_id)

        self.load_outings()
        self.select_outing_row_by_id(outing_id)
        self.refresh_assignments()
        self.assignments_table.setFocus()

        QMessageBox.information(
            self,
            "Schedule generated",
            "The outing schedule has been generated.",
        )

    def edit_schedule(self):
        outing_id = self.selected_row_id(self.outings_table)
        if not outing_id:
            QMessageBox.warning(self, "No selection", "Select an outing first.")
            return

        dlg = ScheduleEditorDialog(
            outing_id=outing_id,
            outing_service=self.outing_service,
            parent=self,
        )
        dlg.exec_()
        self.refresh_assignments()

    def remove_selected_assignment(self):
        assignment_id = self.selected_row_id(self.assignments_table)
        if not assignment_id:
            QMessageBox.warning(
                self,
                "No selection",
                "Select an assigned player first.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Remove Player",
            "Remove this player from the selected outing?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.outing_service.remove_assignment(assignment_id)
            self.refresh_assignments()
            QMessageBox.information(
                self,
                "Player Removed",
                "The player was removed from the outing.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Remove Failed",
                f"Could not remove player from outing.\n\n{exc}",
            )

    def export_outputs(self):
        outing_id = self.selected_row_id(self.outings_table)
        if not outing_id:
            QMessageBox.warning(self, "No selection", "Select an outing first.")
            return

        outing = self.outing_service.get_outing(outing_id)
        tee_times = self.outing_service.get_tee_times(outing_id)
        assignments = self.outing_service.get_assignments(outing_id)

        if not assignments:
            QMessageBox.warning(
                self,
                "No schedule",
                "Generate or edit a schedule first.",
            )
            return

        pdf_path, csv_path = self.distribution_service.build_outputs(
            outing,
            tee_times,
            assignments,
        )

        QMessageBox.information(
            self,
            "Export complete",
            f"Saved:\n{pdf_path}\n{csv_path}",
        )

    def import_member_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Member CSV",
            "",
            "CSV Files (*.csv)",
        )

        if not file_path:
            return

        try:
            result = self.member_service.import_members_from_csv(file_path)

            message = (
                f"Import complete.\n\n"
                f"Imported: {result['imported']}\n"
                f"Updated: {result.get('updated', 0)}\n"
                f"Skipped: {result['skipped']}"
            )

            if result["errors"]:
                preview = "\n".join(result["errors"][:10])
                message += f"\n\nErrors:\n{preview}"
                if len(result["errors"]) > 10:
                    message += "\n..."

            QMessageBox.information(self, "Member Import", message)
            self.load_members()

        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", str(exc))

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "About",
            f"{APP_NAME}\nVersion: {APP_VERSION}",
        )

    def _resize_outings_table_columns(self):
        table = self.outings_table
        if table.columnCount() != 5:
            return

        total_width = table.viewport().width()
        if total_width <= 0:
            return

        notes_width = int(total_width * 0.32)
        other_width = int((total_width - notes_width) / 4)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)

        table.setColumnWidth(0, other_width)  # Outing Date
        table.setColumnWidth(1, other_width)  # Course
        table.setColumnWidth(2, other_width)  # Start Time
        table.setColumnWidth(3, other_width)  # Status
        table.setColumnWidth(4, notes_width)  # Notes

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_outings_table_columns()

    def _on_tab_changed(self, index):
        # Assuming outings tab is index 2
        if index == 2:
            QTimer.singleShot(0, self._resize_outings_table_columns)

    def select_outing_row_by_id(self, outing_id: int):
        for row in range(self.outings_table.rowCount()):
            item = self.outings_table.item(row, 0)
            if not item:
                continue

            hidden_id = item.data(Qt.UserRole)
            if hidden_id is not None and int(hidden_id) == int(outing_id):
                self.outings_table.selectRow(row)
                self.outings_table.setCurrentCell(row, 0)
                return

    def select_member_row_by_id(self, member_id: int):
        for row in range(self.members_table.rowCount()):
            item = self.members_table.item(row, 0)
            if not item:
                continue

            hidden_id = item.data(Qt.UserRole)
            if hidden_id is not None and int(hidden_id) == int(member_id):
                self.members_table.selectRow(row)
                self.members_table.setCurrentCell(row, 0)
                self.members_table.scrollToItem(
                    item,
                    QTableWidget.PositionAtCenter,
                )
                return

    def select_course_row_by_id(self, course_id: int):
        for row in range(self.courses_table.rowCount()):
            item = self.courses_table.item(row, 0)
            if not item:
                continue

            hidden_id = item.data(Qt.UserRole)
            if hidden_id is not None and int(hidden_id) == int(course_id):
                self.courses_table.selectRow(row)
                self.courses_table.setCurrentCell(row, 0)
                self.courses_table.scrollToItem(
                    item,
                    QTableWidget.PositionAtCenter,
                )
                return
