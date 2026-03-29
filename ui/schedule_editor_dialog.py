from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


class AssignmentsTreeWidget(QTreeWidget):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog

        self.setHeaderLabels(["Tee Time / Player"])
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropOverwriteMode(False)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setRootIsDecorated(False)
        self.setExpandsOnDoubleClick(False)

    def dropEvent(self, event):
        dragged_item = self.currentItem()
        if not dragged_item or dragged_item.parent() is None:
            event.ignore()
            return

        target_item = self.itemAt(event.pos())
        if target_item is None:
            event.ignore()
            return

        source_group = dragged_item.parent()
        target_group = (
            target_item if target_item.parent() is None else target_item.parent()
        )

        if target_group is None:
            event.ignore()
            return

        max_players = int(target_group.data(0, Qt.UserRole + 1))

        if target_group != source_group and target_group.childCount() >= max_players:
            QMessageBox.warning(
                self,
                "Tee Time Full",
                "That tee time is full. Remove a player first or move to a tee time with an open slot.",
            )
            event.ignore()
            return

        super().dropEvent(event)

        if not self.dialog.validate_tree_state(show_message=True):
            self.dialog.load_assignments_tree()
            return

        self.dialog.persist_tree_structure()


class ScheduleEditorDialog(QDialog):
    def __init__(self, outing_id, outing_service, parent=None):
        super().__init__(parent)
        self.outing_id = outing_id
        self.outing_service = outing_service

        self.setWindowTitle("Edit Schedule")
        self.resize(1000, 650)

        self.available_members_list = QListWidget()
        self.available_members_list.setSelectionMode(
            QAbstractItemView.ExtendedSelection
        )
        self.assignments_tree = AssignmentsTreeWidget(self)

        self.add_button = QPushButton("Add Selected Player(s)")
        self.remove_button = QPushButton("Remove Selected Player(s)")
        self.close_button = QPushButton("Close")
        self.reshuffle_button = QPushButton("Reshuffle Schedule")

        self.add_button.clicked.connect(self.add_selected_member)
        self.remove_button.clicked.connect(self.remove_selected_assignment)
        self.close_button.clicked.connect(self.accept)
        self.reshuffle_button.clicked.connect(self.handle_reshuffle)

        self.available_members_list.itemDoubleClicked.connect(
            self.add_double_clicked_member
        )
        self.assignments_tree.itemDoubleClicked.connect(
            self.handle_assignment_double_click
        )

        main_layout = QVBoxLayout(self)
        content_layout = QHBoxLayout()
        button_layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Available Members - double-click to add"))
        left_layout.addWidget(self.available_members_list)

        right_layout = QVBoxLayout()
        right_layout.addWidget(
            QLabel("Current Groups - drag to move, double-click to remove")
        )
        right_layout.addWidget(self.assignments_tree)

        content_layout.addLayout(left_layout, 2)
        content_layout.addLayout(right_layout, 3)

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addWidget(self.reshuffle_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(content_layout)
        main_layout.addLayout(button_layout)

        self.load_data()

    def load_data(self):
        self.load_available_members()
        self.load_assignments_tree()

    def load_available_members(self):
        self.available_members_list.clear()
        members = self.outing_service.get_unassigned_members_for_outing(self.outing_id)

        for row in members:
            text = f"{row['first_name']} {row['last_name']}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, int(row["id"]))
            self.available_members_list.addItem(item)

    def load_assignments_tree(self):
        self.assignments_tree.clear()

        tee_times = self.outing_service.get_tee_times(self.outing_id)
        rows = self.outing_service.get_assignments(self.outing_id)

        assignments_by_tee_time = {}
        for row in rows:
            tee_time_id = int(row["tee_time_id"])
            assignments_by_tee_time.setdefault(tee_time_id, []).append(row)

        for tee_time in tee_times:
            tee_time_id = int(tee_time["id"])
            tee_time_text = str(tee_time["tee_time"])
            max_players = int(tee_time["max_players"])

            group_item = QTreeWidgetItem()
            group_item.setData(0, Qt.UserRole, tee_time_id)
            group_item.setData(0, Qt.UserRole + 1, max_players)
            group_item.setData(0, Qt.UserRole + 2, tee_time_text)
            group_item.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDropEnabled
            )

            self.assignments_tree.addTopLevelItem(group_item)

            for row in assignments_by_tee_time.get(tee_time_id, []):
                child = QTreeWidgetItem([f"{row['first_name']} {row['last_name']}"])
                child.setData(0, Qt.UserRole, int(row["id"]))  # assignment id
                child.setData(0, Qt.UserRole + 1, int(row["member_id"]))  # member id
                child.setFlags(
                    Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
                )
                group_item.addChild(child)

            self.update_group_label(group_item)

        self.assignments_tree.expandAll()

    def update_group_label(self, group_item):
        tee_time_text = group_item.data(0, Qt.UserRole + 2)
        max_players = int(group_item.data(0, Qt.UserRole + 1))
        current_players = group_item.childCount()
        group_item.setText(0, f"{tee_time_text} ({current_players}/{max_players})")

    def get_selected_group_item(self):
        current_item = self.assignments_tree.currentItem()
        if not current_item:
            return None

        if current_item.parent() is None:
            return current_item

        return current_item.parent()

    def validate_tree_state(self, show_message=False):
        seen_member_ids = set()

        for i in range(self.assignments_tree.topLevelItemCount()):
            group_item = self.assignments_tree.topLevelItem(i)
            max_players = int(group_item.data(0, Qt.UserRole + 1))

            if group_item.childCount() > max_players:
                if show_message:
                    QMessageBox.warning(
                        self,
                        "Too Many Players",
                        "A tee time has more players than allowed.",
                    )
                return False

            for j in range(group_item.childCount()):
                child = group_item.child(j)
                member_id = int(child.data(0, Qt.UserRole + 1))
                if member_id in seen_member_ids:
                    if show_message:
                        QMessageBox.warning(
                            self,
                            "Duplicate Player",
                            "The same player appears more than once in the outing.",
                        )
                    return False
                seen_member_ids.add(member_id)

        return True

    def persist_tree_structure(self):
        grouped_member_ids = []

        for i in range(self.assignments_tree.topLevelItemCount()):
            group_item = self.assignments_tree.topLevelItem(i)
            member_ids = []

            for j in range(group_item.childCount()):
                child = group_item.child(j)
                member_ids.append(int(child.data(0, Qt.UserRole + 1)))

            grouped_member_ids.append(member_ids)

        try:
            self.outing_service.replace_assignments(self.outing_id, grouped_member_ids)
            self.load_available_members()
            self.load_assignments_tree()
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Save Failed",
                f"Could not save the updated schedule.\n\n{exc}",
            )
            self.load_assignments_tree()

    def add_selected_member(self):
        member_items = self.available_members_list.selectedItems()
        group_item = self.get_selected_group_item()

        if not member_items:
            QMessageBox.warning(
                self, "No Member Selected", "Select one or more members to add."
            )
            return

        if not group_item:
            QMessageBox.warning(
                self,
                "No Tee Time Selected",
                "Select a tee time group on the right.",
            )
            return

        max_players = int(group_item.data(0, Qt.UserRole + 1))
        available_slots = max_players - group_item.childCount()

        if available_slots <= 0:
            QMessageBox.warning(
                self,
                "Tee Time Full",
                "That tee time is already full.",
            )
            return

        selected_tee_time_id = int(group_item.data(0, Qt.UserRole))
        member_ids_to_add = []
        member_names_to_add = []

        for item in member_items[:available_slots]:
            member_ids_to_add.append(int(item.data(Qt.UserRole)))
            member_names_to_add.append(item.text())

        if len(member_items) > available_slots:
            QMessageBox.information(
                self,
                "Tee Time Full",
                f"Only {available_slots} player(s) could be added because that tee time does not have enough open slots.",
            )

        for member_id, member_name in zip(member_ids_to_add, member_names_to_add):
            child = QTreeWidgetItem([member_name])
            child.setData(0, Qt.UserRole, -1)  # temp assignment id
            child.setData(0, Qt.UserRole + 1, member_id)  # member id
            child.setFlags(
                Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
            )
            group_item.addChild(child)

        self.update_group_label(group_item)

        if not self.validate_tree_state(show_message=True):
            self.load_assignments_tree()
            return

        self.persist_tree_structure()

        # Re-select the same tee time after reload
        self.select_group_by_tee_time_id(selected_tee_time_id)

    def remove_selected_assignment(self):
        selected_items = self.assignments_tree.selectedItems()
        player_items = [item for item in selected_items if item.parent() is not None]

        if not player_items:
            QMessageBox.warning(
                self,
                "No Player Selected",
                "Select one or more assigned players to remove.",
            )
            return

        parent_group_ids = {
            int(item.parent().data(0, Qt.UserRole)) for item in player_items
        }

        if len(parent_group_ids) != 1:
            QMessageBox.warning(
                self,
                "Mixed Tee Times Selected",
                "Select players from only one tee time at a time.",
            )
            return

        parent = player_items[0].parent()
        selected_tee_time_id = int(parent.data(0, Qt.UserRole))

        confirm = QMessageBox.question(
            self,
            "Remove Player(s)",
            f"Remove {len(player_items)} selected player(s) from the outing?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        for item in player_items:
            parent.removeChild(item)

        self.update_group_label(parent)

        if not self.validate_tree_state(show_message=True):
            self.load_assignments_tree()
            return

        self.persist_tree_structure()
        self.select_group_by_tee_time_id(selected_tee_time_id)

    def select_group_by_tee_time_id(self, tee_time_id: int):
        for i in range(self.assignments_tree.topLevelItemCount()):
            group_item = self.assignments_tree.topLevelItem(i)
            current_id = group_item.data(0, Qt.UserRole)
            if current_id is not None and int(current_id) == int(tee_time_id):
                self.assignments_tree.setCurrentItem(group_item)
                self.assignments_tree.scrollToItem(group_item)
                return

    def add_double_clicked_member(self, item):
        if not item:
            return

        group_item = self.get_selected_group_item()
        if not group_item:
            QMessageBox.warning(
                self,
                "No Tee Time Selected",
                "Select a tee time group on the right.",
            )
            return

        max_players = int(group_item.data(0, Qt.UserRole + 1))
        if group_item.childCount() >= max_players:
            QMessageBox.warning(
                self,
                "Tee Time Full",
                "That tee time is already full.",
            )
            return

        selected_tee_time_id = int(group_item.data(0, Qt.UserRole))
        member_id = int(item.data(Qt.UserRole))
        member_name = item.text()

        child = QTreeWidgetItem([member_name])
        child.setData(0, Qt.UserRole, -1)  # temp assignment id
        child.setData(0, Qt.UserRole + 1, member_id)  # member id
        child.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)

        group_item.addChild(child)
        self.update_group_label(group_item)

        if not self.validate_tree_state(show_message=True):
            self.load_assignments_tree()
            return

        self.persist_tree_structure()
        self.select_group_by_tee_time_id(selected_tee_time_id)

    def handle_assignment_double_click(self, item, column):
        if not item or item.parent() is None:
            return

        parent = item.parent()
        selected_tee_time_id = int(parent.data(0, Qt.UserRole))

        confirm = QMessageBox.question(
            self,
            "Remove Player",
            f"Remove {item.text(0)} from the outing?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        parent.removeChild(item)
        self.update_group_label(parent)

        if not self.validate_tree_state(show_message=True):
            self.load_assignments_tree()
            return

        self.persist_tree_structure()
        self.select_group_by_tee_time_id(selected_tee_time_id)

    def handle_reshuffle(self):
        try:
            self.outing_service.reshuffle_schedule(self.outing_id)
            self.load_available_members()
            self.load_assignments_tree()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Reshuffle Failed",
                f"Could not reshuffle the schedule.\n\n{exc}",
            )
