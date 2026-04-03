from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush, QFont
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

DataRole = Qt.ItemDataRole
DropAction = Qt.DropAction
ItemFlag = Qt.ItemFlag

SelectionMode = QAbstractItemView.SelectionMode
DragDropMode = QAbstractItemView.DragDropMode
EditTrigger = QAbstractItemView.EditTrigger


class AssignmentsTreeWidget(QTreeWidget):
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog

        self.setHeaderLabels(["Tee Time / Player"])
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(DragDropMode.DragDrop)
        self.setDefaultDropAction(DropAction.MoveAction)
        self.setDragDropOverwriteMode(False)
        self.setSelectionMode(SelectionMode.ExtendedSelection)
        self.setEditTriggers(EditTrigger.NoEditTriggers)
        self.setRootIsDecorated(False)
        self.setExpandsOnDoubleClick(False)

    def dropEvent(self, event):
        dragged_item = self.currentItem()
        if not dragged_item or dragged_item.parent() is None:
            event.ignore()
            return

        # Guests are read-only display rows; only sponsors/members are draggable.
        if bool(dragged_item.data(0, DataRole.UserRole + 3)):
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

        max_players = int(target_group.data(0, DataRole.UserRole + 1))
        projected_size = self.dialog._projected_group_size_after_drop(
            source_group=source_group,
            target_group=target_group,
            dragged_item=dragged_item,
        )

        if projected_size > max_players:
            QMessageBox.warning(
                self,
                "Tee Time Full",
                "That move would exceed the tee time capacity once sponsor guests are included.",
            )
            event.ignore()
            return

        super().dropEvent(event)

        if not self.dialog.validate_tree_state(show_message=True):
            self.dialog.load_assignments_tree()
            return

        self.dialog.persist_tree_structure()


class ScheduleEditorDialog(QDialog):
    def __init__(self, outing_id, outing_service, settings_service, parent=None):
        super().__init__(parent)
        self.outing_id = outing_id
        self.outing_service = outing_service
        self.settings_service = settings_service
        self.settings = self.settings_service.get_all()

        self.guest_rows_by_sponsor_id: dict[int, list] = {}

        self.setWindowTitle("Edit Schedule")
        self.resize(1000, 650)

        self.available_members_list = QListWidget()
        self.available_members_list.setSelectionMode(SelectionMode.ExtendedSelection)
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
            QLabel(
                "Current Groups - drag sponsors to move, double-click sponsor to remove"
            )
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
        self.settings = self.settings_service.get_all()
        self._load_guest_lookup()
        self.load_available_members()
        self.load_assignments_tree()

    def _load_guest_lookup(self):
        self.guest_rows_by_sponsor_id = {}

        parent = self.parent()
        if parent is None or not hasattr(parent, "guest_service"):
            return

        guest_rows = parent.guest_service.list_schedulable_outing_guests(self.outing_id)
        for row in guest_rows:
            sponsor_id = int(row["sponsoring_member_id"])
            self.guest_rows_by_sponsor_id.setdefault(sponsor_id, []).append(row)

    def _guest_count_for_member(self, member_id: int) -> int:
        return len(self.guest_rows_by_sponsor_id.get(int(member_id), []))

    def _unit_size_for_member(self, member_id: int) -> int:
        return 1 + self._guest_count_for_member(member_id)

    def _member_display_name(self, first_name, last_name) -> str:
        return f"{str(first_name or '')} {str(last_name or '')}".strip()

    def _guest_display_name(self, guest_row) -> str:
        return self._member_display_name(
            guest_row["first_name"],
            guest_row["last_name"],
        )

    def _group_expanded_player_count(self, group_item) -> int:
        total = 0

        for i in range(group_item.childCount()):
            child = group_item.child(i)
            is_guest_row = bool(child.data(0, DataRole.UserRole + 3))
            if is_guest_row:
                continue

            member_id = int(child.data(0, DataRole.UserRole + 1))
            total += self._unit_size_for_member(member_id)

        return total

    def _projected_group_size_after_drop(
        self,
        source_group,
        target_group,
        dragged_item,
    ) -> int:
        member_id = int(dragged_item.data(0, DataRole.UserRole + 1))
        dragged_unit_size = self._unit_size_for_member(member_id)

        if source_group == target_group:
            return self._group_expanded_player_count(target_group)

        return self._group_expanded_player_count(target_group) + dragged_unit_size

    def load_available_members(self):
        self.available_members_list.clear()

        parent = self.parent()
        if parent is None or not hasattr(parent, "rsvp_service"):
            return

        schedulable_member_ids = set(
            parent.rsvp_service.get_schedulable_member_ids(self.outing_id)
        )
        if not schedulable_member_ids:
            return

        assigned_member_ids = set()
        assigned_rows = self.outing_service.get_assignments(self.outing_id)
        for row in assigned_rows:
            assigned_member_ids.add(int(row["member_id"]))

        members = self.outing_service.get_unassigned_members_for_outing(self.outing_id)

        for row in members:
            member_id = int(row["id"])

            if member_id not in schedulable_member_ids:
                continue

            if member_id in assigned_member_ids:
                continue

            guest_count = self._guest_count_for_member(member_id)
            text = f"{row['first_name']} {row['last_name']}"
            if guest_count > 0:
                text += f" (+{guest_count} guest{'s' if guest_count != 1 else ''})"

            item = QListWidgetItem(text)
            item.setData(DataRole.UserRole, member_id)
            item.setData(DataRole.UserRole + 1, row["skill_tier"])

            self._apply_tier_color_to_list_item(item, row["skill_tier"])
            self.available_members_list.addItem(item)

    def load_assignments_tree(self):
        self.settings = self.settings_service.get_all()
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
            group_item.setData(0, DataRole.UserRole, tee_time_id)
            group_item.setData(0, DataRole.UserRole + 1, max_players)
            group_item.setData(0, DataRole.UserRole + 2, tee_time_text)
            group_item.setFlags(
                ItemFlag.ItemIsEnabled
                | ItemFlag.ItemIsSelectable
                | ItemFlag.ItemIsDropEnabled
            )

            self.assignments_tree.addTopLevelItem(group_item)

            for row in assignments_by_tee_time.get(tee_time_id, []):
                member_id = int(row["member_id"])
                guest_count = self._guest_count_for_member(member_id)

                sponsor_text = f"{row['first_name']} {row['last_name']}"
                if guest_count > 0:
                    sponsor_text += f" (+{guest_count})"

                child = QTreeWidgetItem([sponsor_text])
                child.setData(0, DataRole.UserRole, int(row["id"]))  # assignment id
                child.setData(0, DataRole.UserRole + 1, member_id)  # member id
                child.setData(0, DataRole.UserRole + 2, row["skill_tier"])  # skill tier
                child.setData(0, DataRole.UserRole + 3, False)  # is_guest_row
                child.setFlags(
                    ItemFlag.ItemIsEnabled
                    | ItemFlag.ItemIsSelectable
                    | ItemFlag.ItemIsDragEnabled
                )

                self._apply_tier_color_to_tree_item(child, row["skill_tier"])
                group_item.addChild(child)

                for guest_row in self.guest_rows_by_sponsor_id.get(member_id, []):
                    guest_child = QTreeWidgetItem(
                        [f"    ↳ {self._guest_display_name(guest_row)}"]
                    )
                    guest_child.setData(0, DataRole.UserRole, None)
                    guest_child.setData(0, DataRole.UserRole + 1, None)
                    guest_child.setData(0, DataRole.UserRole + 2, None)
                    guest_child.setData(0, DataRole.UserRole + 3, True)  # is_guest_row
                    guest_child.setFlags(
                        ItemFlag.ItemIsEnabled | ItemFlag.ItemIsSelectable
                    )
                    self._apply_guest_style_to_tree_item(guest_child)
                    group_item.addChild(guest_child)

            self.update_group_label(group_item)

        self.assignments_tree.expandAll()

    def update_group_label(self, group_item):
        tee_time_text = group_item.data(0, DataRole.UserRole + 2)
        max_players = int(group_item.data(0, DataRole.UserRole + 1))
        current_players = self._group_expanded_player_count(group_item)

        label = f"{tee_time_text} ({current_players}/{max_players})"

        if self.settings.get("show_tier_summary", True):
            tier_counts = {1: 0, 2: 0, 3: 0}

            for i in range(group_item.childCount()):
                child = group_item.child(i)
                is_guest_row = bool(child.data(0, DataRole.UserRole + 3))
                if is_guest_row:
                    continue

                tier = child.data(0, DataRole.UserRole + 2)
                if tier is None:
                    continue

                tier = int(tier)
                if tier in tier_counts:
                    tier_counts[tier] += 1

            tier_summary = f"1:{tier_counts[1]}  2:{tier_counts[2]}  3:{tier_counts[3]}"
            label = f"{label}    |    {tier_summary}"

        group_item.setText(0, label)

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
            max_players = int(group_item.data(0, DataRole.UserRole + 1))
            expanded_count = self._group_expanded_player_count(group_item)

            if expanded_count > max_players:
                if show_message:
                    QMessageBox.warning(
                        self,
                        "Too Many Players",
                        "A tee time exceeds capacity once sponsor guests are included.",
                    )
                return False

            for j in range(group_item.childCount()):
                child = group_item.child(j)
                is_guest_row = bool(child.data(0, DataRole.UserRole + 3))
                if is_guest_row:
                    continue

                member_id = int(child.data(0, DataRole.UserRole + 1))
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
                is_guest_row = bool(child.data(0, DataRole.UserRole + 3))
                if is_guest_row:
                    continue

                member_ids.append(int(child.data(0, DataRole.UserRole + 1)))

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

        max_players = int(group_item.data(0, DataRole.UserRole + 1))
        current_size = self._group_expanded_player_count(group_item)
        available_slots = max_players - current_size

        if available_slots <= 0:
            QMessageBox.warning(
                self,
                "Tee Time Full",
                "That tee time is already full.",
            )
            return

        selected_tee_time_id = int(group_item.data(0, DataRole.UserRole))
        members_to_add = []
        skipped_members = []

        for item in member_items:
            member_id = int(item.data(DataRole.UserRole))
            skill_tier = item.data(DataRole.UserRole + 1)
            member_name = item.text()
            unit_size = self._unit_size_for_member(member_id)

            if unit_size <= available_slots:
                members_to_add.append((member_id, member_name, skill_tier))
                available_slots -= unit_size
            else:
                skipped_members.append(member_name)

        if not members_to_add:
            QMessageBox.warning(
                self,
                "Tee Time Full",
                "None of the selected players fit once sponsor guests are included.",
            )
            return

        if skipped_members:
            QMessageBox.information(
                self,
                "Some Players Not Added",
                "Some selected players could not be added because the tee time "
                "does not have enough open slots once sponsor guests are included.",
            )

        for member_id, member_name, skill_tier in members_to_add:
            guest_count = self._guest_count_for_member(member_id)
            display_name = member_name
            if guest_count > 0:
                display_name += f" (+{guest_count})"

            child = QTreeWidgetItem([display_name])
            child.setData(0, DataRole.UserRole, -1)  # temp assignment id
            child.setData(0, DataRole.UserRole + 1, member_id)  # member id
            child.setData(0, DataRole.UserRole + 2, skill_tier)  # skill tier
            child.setData(0, DataRole.UserRole + 3, False)  # is_guest_row
            child.setFlags(
                ItemFlag.ItemIsEnabled
                | ItemFlag.ItemIsSelectable
                | ItemFlag.ItemIsDragEnabled
            )

            self._apply_tier_color_to_tree_item(child, skill_tier)
            group_item.addChild(child)

            for guest_row in self.guest_rows_by_sponsor_id.get(member_id, []):
                guest_child = QTreeWidgetItem(
                    [f"    ↳ {self._guest_display_name(guest_row)}"]
                )
                guest_child.setData(0, DataRole.UserRole, None)
                guest_child.setData(0, DataRole.UserRole + 1, None)
                guest_child.setData(0, DataRole.UserRole + 2, None)
                guest_child.setData(0, DataRole.UserRole + 3, True)
                guest_child.setFlags(ItemFlag.ItemIsEnabled | ItemFlag.ItemIsSelectable)
                self._apply_guest_style_to_tree_item(guest_child)
                group_item.addChild(guest_child)

        self.update_group_label(group_item)

        if not self.validate_tree_state(show_message=True):
            self.load_assignments_tree()
            return

        self.persist_tree_structure()
        self.select_group_by_tee_time_id(selected_tee_time_id)

    def remove_selected_assignment(self):
        selected_items = self.assignments_tree.selectedItems()
        player_items = []

        for item in selected_items:
            if item.parent() is None:
                continue
            if bool(item.data(0, DataRole.UserRole + 3)):
                continue
            player_items.append(item)

        if not player_items:
            QMessageBox.warning(
                self,
                "No Player Selected",
                "Select one or more assigned sponsor/member rows to remove.",
            )
            return

        parent_group_ids = {
            int(item.parent().data(0, DataRole.UserRole)) for item in player_items
        }

        if len(parent_group_ids) != 1:
            QMessageBox.warning(
                self,
                "Mixed Tee Times Selected",
                "Select players from only one tee time at a time.",
            )
            return

        parent = player_items[0].parent()
        selected_tee_time_id = int(parent.data(0, DataRole.UserRole))

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
            member_id = int(item.data(0, DataRole.UserRole + 1))
            self._remove_sponsor_and_guest_rows(parent, member_id)

        self.update_group_label(parent)

        if not self.validate_tree_state(show_message=True):
            self.load_assignments_tree()
            return

        self.persist_tree_structure()
        self.select_group_by_tee_time_id(selected_tee_time_id)

    def _remove_sponsor_and_guest_rows(self, group_item, member_id: int):
        indices_to_remove = []

        for i in range(group_item.childCount()):
            child = group_item.child(i)
            is_guest_row = bool(child.data(0, DataRole.UserRole + 3))

            if not is_guest_row:
                child_member_id = child.data(0, DataRole.UserRole + 1)
                if child_member_id is not None and int(child_member_id) == int(
                    member_id
                ):
                    indices_to_remove.append(i)
            else:
                # guest rows immediately follow sponsor rows in the tree
                pass

        if not indices_to_remove:
            return

        sponsor_index = indices_to_remove[0]
        remove_count = 1 + self._guest_count_for_member(member_id)

        for idx in reversed(range(sponsor_index, sponsor_index + remove_count)):
            if 0 <= idx < group_item.childCount():
                group_item.removeChild(group_item.child(idx))

    def select_group_by_tee_time_id(self, tee_time_id: int):
        for i in range(self.assignments_tree.topLevelItemCount()):
            group_item = self.assignments_tree.topLevelItem(i)
            current_id = group_item.data(0, DataRole.UserRole)
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

        max_players = int(group_item.data(0, DataRole.UserRole + 1))
        current_size = self._group_expanded_player_count(group_item)

        member_id = int(item.data(DataRole.UserRole))
        unit_size = self._unit_size_for_member(member_id)

        if current_size + unit_size > max_players:
            QMessageBox.warning(
                self,
                "Tee Time Full",
                "That player does not fit once sponsor guests are included.",
            )
            return

        selected_tee_time_id = int(group_item.data(0, DataRole.UserRole))
        member_name = item.text()
        skill_tier = item.data(DataRole.UserRole + 1)
        guest_count = self._guest_count_for_member(member_id)

        display_name = member_name
        if guest_count > 0:
            display_name += f" (+{guest_count})"

        child = QTreeWidgetItem([display_name])
        child.setData(0, DataRole.UserRole, -1)  # temp assignment id
        child.setData(0, DataRole.UserRole + 1, member_id)  # member id
        child.setData(0, DataRole.UserRole + 2, skill_tier)  # skill tier
        child.setData(0, DataRole.UserRole + 3, False)  # is_guest_row
        child.setFlags(
            ItemFlag.ItemIsEnabled
            | ItemFlag.ItemIsSelectable
            | ItemFlag.ItemIsDragEnabled
        )

        self._apply_tier_color_to_tree_item(child, skill_tier)
        group_item.addChild(child)

        for guest_row in self.guest_rows_by_sponsor_id.get(member_id, []):
            guest_child = QTreeWidgetItem(
                [f"    ↳ {self._guest_display_name(guest_row)}"]
            )
            guest_child.setData(0, DataRole.UserRole, None)
            guest_child.setData(0, DataRole.UserRole + 1, None)
            guest_child.setData(0, DataRole.UserRole + 2, None)
            guest_child.setData(0, DataRole.UserRole + 3, True)
            guest_child.setFlags(ItemFlag.ItemIsEnabled | ItemFlag.ItemIsSelectable)
            self._apply_guest_style_to_tree_item(guest_child)
            group_item.addChild(guest_child)

        self.update_group_label(group_item)

        if not self.validate_tree_state(show_message=True):
            self.load_assignments_tree()
            return

        self.persist_tree_structure()
        self.select_group_by_tee_time_id(selected_tee_time_id)

    def handle_assignment_double_click(self, item, column):
        if not item or item.parent() is None:
            return

        if bool(item.data(0, DataRole.UserRole + 3)):
            return

        parent = item.parent()
        selected_tee_time_id = int(parent.data(0, DataRole.UserRole))
        member_id = int(item.data(0, DataRole.UserRole + 1))

        confirm = QMessageBox.question(
            self,
            "Remove Player",
            f"Remove {item.text(0)} from the outing?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        self._remove_sponsor_and_guest_rows(parent, member_id)
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

    def _apply_tier_color_to_tree_item(self, item, skill_tier):
        if not self.settings.get("show_tier_colors", True):
            return

        if skill_tier is None:
            return

        skill_tier = int(skill_tier)

        if skill_tier == 1:
            item.setForeground(0, QBrush(QColor("#2e8b57")))
        elif skill_tier == 3:
            item.setForeground(0, QBrush(QColor("#c9a000")))

    def _apply_tier_color_to_list_item(self, item, skill_tier):
        if not self.settings.get("show_tier_colors", True):
            return

        if skill_tier is None:
            return

        skill_tier = int(skill_tier)

        if skill_tier == 1:
            item.setForeground(QBrush(QColor("#2e8b57")))
        elif skill_tier == 3:
            item.setForeground(QBrush(QColor("#c9a000")))

    def _apply_guest_style_to_tree_item(self, item):
        guest_font = QFont()
        guest_font.setItalic(True)
        guest_brush = QBrush(QColor("#1e90ff"))

        item.setFont(0, guest_font)
        item.setForeground(0, guest_brush)
