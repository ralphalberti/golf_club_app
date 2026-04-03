# DEPRECATED: OutingAssignmentDialog
# This dialog supported manual member selection for scheduling.
# Scheduling is now driven by RSVP-yes members and sponsor-linked guest units.
# Safe to remove once no rollback is needed.
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLineEdit,
    QMessageBox,
)

DataRole = Qt.ItemDataRole
SelectionMode = QAbstractItemView.SelectionMode


class OutingAssignmentDialog(QDialog):
    def __init__(self, members, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Players for Schedule Generation")
        self.resize(950, 600)

        self.all_members = list(members)
        self.selected_member_ids_set = set()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search members by name...")

        self.available_label = QLabel("Available Members")
        self.selected_label = QLabel("Selected Players: 0")
        self.capacity_label = QLabel("Capacity: --   Selected: 0   Remaining: --")

        self.available_list = QListWidget()
        self.selected_list = QListWidget()

        self.available_list.setSelectionMode(SelectionMode.ExtendedSelection)
        self.selected_list.setSelectionMode(SelectionMode.ExtendedSelection)

        self.add_button = QPushButton("Add →")
        self.remove_button = QPushButton("← Remove")
        self.select_all_button = QPushButton("Select All Visible")
        self.clear_button = QPushButton("Clear Selection")
        self.ok_button = QPushButton("Generate Schedule")
        self.cancel_button = QPushButton("Cancel")

        self.add_button.clicked.connect(self.add_selected_members)
        self.remove_button.clicked.connect(self.remove_selected_members)
        self.select_all_button.clicked.connect(self.select_all_visible)
        self.clear_button.clicked.connect(self.clear_selection)
        self.ok_button.clicked.connect(self.accept_with_validation)
        self.cancel_button.clicked.connect(self.reject)
        self.search_edit.textChanged.connect(self.refresh_available_members)

        self.available_list.itemDoubleClicked.connect(self.add_double_clicked_member)
        self.selected_list.itemDoubleClicked.connect(self.remove_double_clicked_member)

        main_layout = QVBoxLayout(self)

        top_layout = QVBoxLayout()
        top_layout.addWidget(self.capacity_label)
        top_layout.addWidget(self.search_edit)

        content_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.available_label)
        left_layout.addWidget(self.available_list)

        middle_layout = QVBoxLayout()
        middle_layout.addStretch()
        middle_layout.addWidget(self.add_button)
        middle_layout.addWidget(self.remove_button)
        middle_layout.addWidget(self.select_all_button)
        middle_layout.addWidget(self.clear_button)
        middle_layout.addStretch()

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.selected_label)
        right_layout.addWidget(self.selected_list)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        content_layout.addLayout(left_layout, 3)
        content_layout.addLayout(middle_layout, 1)
        content_layout.addLayout(right_layout, 3)

        main_layout.addLayout(top_layout)
        main_layout.addLayout(content_layout)
        main_layout.addLayout(button_layout)

        self._refresh_capacity_summary()
        self.refresh_available_members()
        self.refresh_selected_members()

    def _member_display_name(self, row):
        return f"{row['first_name']} {row['last_name']}".strip()

    def _member_sort_key(self, row):
        return (
            str(row["last_name"]).lower(),
            str(row["first_name"]).lower(),
            int(row["id"]),
        )

    def _get_capacity(self):
        parent = self.parent()
        if parent is None:
            return None

        outing_id = parent.selected_row_id(parent.outings_table)
        if not outing_id:
            return None

        tee_times = parent.outing_service.get_tee_times(outing_id)
        if not tee_times:
            return None

        return sum(int(row["max_players"]) for row in tee_times)

    def _refresh_capacity_summary(self):
        capacity = self._get_capacity()
        selected = len(self.selected_member_ids_set)

        if capacity is None:
            self.capacity_label.setText(
                f"Capacity: --   Selected: {selected}   Remaining: --"
            )
            return

        remaining = capacity - selected
        self.capacity_label.setText(
            f"Capacity: {capacity}   Selected: {selected}   Remaining: {remaining}"
        )

    def refresh_available_members(self):
        self.available_list.clear()

        search_text = self.search_edit.text().strip().lower()
        filtered = []

        for row in sorted(self.all_members, key=self._member_sort_key):
            member_id = int(row["id"])
            if member_id in self.selected_member_ids_set:
                continue

            full_name = self._member_display_name(row)
            if search_text and search_text not in full_name.lower():
                continue

            filtered.append(row)

        for row in filtered:
            item = QListWidgetItem(self._member_display_name(row))
            item.setData(DataRole.UserRole, int(row["id"]))
            self.available_list.addItem(item)

    def refresh_selected_members(self):
        self.selected_list.clear()

        selected_rows = [
            row
            for row in self.all_members
            if int(row["id"]) in self.selected_member_ids_set
        ]
        selected_rows = sorted(selected_rows, key=self._member_sort_key)

        for idx, row in enumerate(selected_rows, start=1):
            item = QListWidgetItem(f"{idx}. {self._member_display_name(row)}")
            item.setData(DataRole.UserRole, int(row["id"]))
            self.selected_list.addItem(item)

        self.selected_label.setText(f"Selected Players: {len(selected_rows)}")
        self._refresh_capacity_summary()

    def add_selected_members(self):
        items = self.available_list.selectedItems()
        if not items:
            return

        capacity = self._get_capacity()
        current_selected = len(self.selected_member_ids_set)
        added_count = 0

        for item in items:
            member_id = int(item.data(DataRole.UserRole))

            if capacity is not None and current_selected >= capacity:
                if added_count == 0:
                    QMessageBox.warning(
                        self,
                        "Capacity Reached",
                        f"You cannot select more than {capacity} players for this outing.",
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Capacity Reached",
                        f"Only {added_count} player(s) were added because the outing capacity is {capacity}.",
                    )
                break

            if member_id not in self.selected_member_ids_set:
                self.selected_member_ids_set.add(member_id)
                current_selected += 1
                added_count += 1

        self.refresh_available_members()
        self.refresh_selected_members()

    def remove_selected_members(self):
        items = self.selected_list.selectedItems()
        if not items:
            return

        for item in items:
            member_id = int(item.data(DataRole.UserRole))
            self.selected_member_ids_set.discard(member_id)

        self.refresh_available_members()
        self.refresh_selected_members()

    def add_double_clicked_member(self, item):
        if not item:
            return

        capacity = self._get_capacity()
        current_selected = len(self.selected_member_ids_set)
        member_id = int(item.data(DataRole.UserRole))

        if capacity is not None and current_selected >= capacity:
            QMessageBox.warning(
                self,
                "Capacity Reached",
                f"You cannot select more than {capacity} players for this outing.",
            )
            return

        if member_id not in self.selected_member_ids_set:
            self.selected_member_ids_set.add(member_id)

        self.refresh_available_members()
        self.refresh_selected_members()

    def remove_double_clicked_member(self, item):
        if not item:
            return

        member_id = int(item.data(DataRole.UserRole))
        self.selected_member_ids_set.discard(member_id)

        self.refresh_available_members()
        self.refresh_selected_members()

    def select_all_visible(self):
        capacity = self._get_capacity()
        current_selected = len(self.selected_member_ids_set)
        added_count = 0

        for i in range(self.available_list.count()):
            item = self.available_list.item(i)
            member_id = int(item.data(DataRole.UserRole))

            if capacity is not None and current_selected >= capacity:
                break

            if member_id not in self.selected_member_ids_set:
                self.selected_member_ids_set.add(member_id)
                current_selected += 1
                added_count += 1

        if (
            capacity is not None
            and self.available_list.count() > 0
            and current_selected >= capacity
            and added_count < self.available_list.count()
        ):
            QMessageBox.information(
                self,
                "Capacity Reached",
                f"Only {added_count} visible player(s) were added because the outing capacity is {capacity}.",
            )

        self.refresh_available_members()
        self.refresh_selected_members()

    def clear_selection(self):
        self.selected_member_ids_set.clear()
        self.refresh_available_members()
        self.refresh_selected_members()

    def selected_member_ids(self):
        selected_rows = [
            row
            for row in self.all_members
            if int(row["id"]) in self.selected_member_ids_set
        ]
        selected_rows = sorted(selected_rows, key=self._member_sort_key)
        return [int(row["id"]) for row in selected_rows]

    def accept_with_validation(self):
        selected_ids = self.selected_member_ids()
        if not selected_ids:
            QMessageBox.warning(
                self, "No Players Selected", "Select at least one player."
            )
            return

        capacity = self._get_capacity()
        if capacity is not None and len(selected_ids) > capacity:
            QMessageBox.warning(
                self,
                "Too Many Players",
                f"You selected {len(selected_ids)} players, but the outing capacity is {capacity}.",
            )
            return

        self.accept()
