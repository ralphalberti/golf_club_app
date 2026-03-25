from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QFileDialog,
    QAction,
)

from app.config import APP_NAME
from app.constants import APP_VERSION
from ui.shared.forms import MemberFormDialog, CourseFormDialog, OutingFormDialog
from ui.outing_assignment_dialog import OutingAssignmentDialog
from ui.schedule_editor_dialog import ScheduleEditorDialog


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
        self.current_user = current_user
        self.member_service = member_service
        self.course_service = course_service
        self.outing_service = outing_service
        self.reporting_service = reporting_service
        self.scheduling_service = scheduling_service
        self.distribution_service = distribution_service

        self.setWindowTitle(APP_NAME)
        self.resize(1200, 720)

        self.tabs = QTabWidget()
        self.members_table = QTableWidget()
        self.courses_table = QTableWidget()
        self.outings_table = QTableWidget()
        self.assignments_table = QTableWidget()

        self.tabs.addTab(self._build_members_tab(), "Members")
        self.tabs.addTab(self._build_courses_tab(), "Courses")
        self.tabs.addTab(self._build_outings_tab(), "Outings / Schedules")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(self.tabs)
        self.setCentralWidget(container)

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
                table.setItem(
                    r,
                    c,
                    QTableWidgetItem("" if value is None else str(value)),
                )

        table.resizeColumnsToContents()

    def selected_row_id(self, table):
        row = table.currentRow()
        if row < 0 or table.columnCount() == 0:
            return None
        return int(table.item(row, 0).text())

    def load_members(self):
        self._populate_table(self.members_table, self.member_service.list_members())

    def load_courses(self):
        self._populate_table(self.courses_table, self.course_service.list_courses())

    def load_outings(self):
        self._populate_table(self.outings_table, self.outing_service.list_outings())

    def refresh_assignments(self):
        outing_id = self.selected_row_id(self.outings_table)
        rows = self.outing_service.get_assignments(outing_id) if outing_id else []
        self._populate_table(self.assignments_table, rows)

    def add_member(self):
        dlg = MemberFormDialog()
        if dlg.exec_():
            self.member_service.create_member(dlg.values())
            self.load_members()

    def edit_member(self):
        member_id = self.selected_row_id(self.members_table)
        if not member_id:
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
            QMessageBox.critical(
                self,
                "Delete Failed",
                f"Could not delete member.\n\n{exc}",
            )

    def add_course(self):
        dlg = CourseFormDialog()
        if dlg.exec_():
            self.course_service.create_course(dlg.values())
            self.load_courses()

    def edit_course(self):
        course_id = self.selected_row_id(self.courses_table)
        if not course_id:
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

    def generate_schedule(self):
        outing_id = self.selected_row_id(self.outings_table)
        if not outing_id:
            QMessageBox.warning(self, "No outing selected", "Select an outing first.")
            return

        members = self.member_service.list_members()
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
        self.refresh_assignments()

        QMessageBox.information(
            self,
            "Schedule generated",
            "The outing schedule has been generated.",
        )

    def export_outputs(self):
        outing_id = self.selected_row_id(self.outings_table)
        if not outing_id:
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

    def delete_outing(self):
        outing_id = self.selected_row_id(self.outings_table)
        if not outing_id:
            QMessageBox.warning(
                self,
                "No selection",
                "Select an outing first.",
            )
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

    def edit_schedule(self):
        outing_id = self.selected_row_id(self.outings_table)
        if not outing_id:
            QMessageBox.warning(
                self,
                "No selection",
                "Select an outing first.",
            )
            return

        dlg = ScheduleEditorDialog(
            outing_id=outing_id,
            outing_service=self.outing_service,
            parent=self,
        )
        dlg.exec_()
        self.refresh_assignments()
