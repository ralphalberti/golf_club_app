from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
)


class ScheduleEditorDialog(QDialog):
    def __init__(self, outing_id, outing_service, parent=None):
        super().__init__(parent)
        self.outing_id = outing_id
        self.outing_service = outing_service

        self.setWindowTitle("Edit Schedule")
        self.resize(1000, 600)

        self.available_members_list = QListWidget()
        self.tee_times_list = QListWidget()
        self.assignments_list = QListWidget()

        self.add_button = QPushButton("Add To Selected Tee Time")
        self.remove_button = QPushButton("Remove Selected Assignment")
        self.close_button = QPushButton("Close")

        self.add_button.clicked.connect(self.add_selected_member)
        self.remove_button.clicked.connect(self.remove_selected_assignment)
        self.close_button.clicked.connect(self.accept)

        main_layout = QVBoxLayout(self)
        content_layout = QHBoxLayout()
        button_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Available Members"))
        left_layout.addWidget(self.available_members_list)

        middle_layout = QVBoxLayout()
        middle_layout.addWidget(QLabel("Tee Times"))
        middle_layout.addWidget(self.tee_times_list)

        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Current Assignments"))
        right_layout.addWidget(self.assignments_list)

        content_layout.addLayout(left_layout, 2)
        content_layout.addLayout(middle_layout, 1)
        content_layout.addLayout(right_layout, 3)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(content_layout)
        main_layout.addLayout(button_layout)

        self.tee_times_list.currentRowChanged.connect(
            self.load_assignments_for_selected_tee_time
        )

        self.load_data()

    def load_data(self):
        self.load_available_members()
        self.load_tee_times()
        self.load_all_assignments()

    def load_available_members(self):
        self.available_members_list.clear()
        members = self.outing_service.get_unassigned_members_for_outing(self.outing_id)

        for row in members:
            text = f"{row['first_name']} {row['last_name']}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, row["id"])
            self.available_members_list.addItem(item)

    def load_tee_times(self):
        self.tee_times_list.clear()
        tee_times = self.outing_service.get_tee_times(self.outing_id)

        for row in tee_times:
            label = f"{row['tee_time']} (max {row['max_players']})"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, row["id"])
            self.tee_times_list.addItem(item)

        if self.tee_times_list.count() > 0:
            self.tee_times_list.setCurrentRow(0)

    def load_all_assignments(self):
        self.assignments_list.clear()
        rows = self.outing_service.get_assignments(self.outing_id)

        for row in rows:
            text = f"{row['tee_time']} - {row['first_name']} {row['last_name']}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, row["id"])  # assignment id
            item.setData(Qt.UserRole + 1, row["tee_time_id"])  # tee time id
            self.assignments_list.addItem(item)

    def load_assignments_for_selected_tee_time(self):
        selected_item = self.tee_times_list.currentItem()
        if not selected_item:
            self.assignments_list.clear()
            return

        selected_tee_time_id = selected_item.data(Qt.UserRole)

        self.assignments_list.clear()
        rows = self.outing_service.get_assignments(self.outing_id)

        for row in rows:
            if int(row["tee_time_id"]) != int(selected_tee_time_id):
                continue

            text = f"{row['first_name']} {row['last_name']}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, row["id"])  # assignment id
            item.setData(Qt.UserRole + 1, row["tee_time_id"])  # tee time id
            self.assignments_list.addItem(item)

    def add_selected_member(self):
        member_item = self.available_members_list.currentItem()
        tee_time_item = self.tee_times_list.currentItem()

        if not member_item:
            QMessageBox.warning(self, "No Member Selected", "Select a member to add.")
            return

        if not tee_time_item:
            QMessageBox.warning(self, "No Tee Time Selected", "Select a tee time.")
            return

        member_id = member_item.data(Qt.UserRole)
        tee_time_id = tee_time_item.data(Qt.UserRole)

        try:
            self.outing_service.add_member_to_tee_time(
                outing_id=self.outing_id,
                tee_time_id=tee_time_id,
                member_id=member_id,
            )
            self.load_available_members()
            self.load_assignments_for_selected_tee_time()
        except Exception as exc:
            QMessageBox.critical(self, "Add Failed", str(exc))

    def remove_selected_assignment(self):
        assignment_item = self.assignments_list.currentItem()
        if not assignment_item:
            QMessageBox.warning(
                self,
                "No Assignment Selected",
                "Select an assigned player to remove.",
            )
            return

        assignment_id = assignment_item.data(Qt.UserRole)

        confirm = QMessageBox.question(
            self,
            "Remove Player",
            "Remove this player from the outing?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self.outing_service.remove_assignment(assignment_id)
            self.load_available_members()
            self.load_assignments_for_selected_tee_time()
        except Exception as exc:
            QMessageBox.critical(self, "Remove Failed", str(exc))
