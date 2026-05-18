from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ui.facility_contact_dialog import FacilityContactDialog
from ui.shared.messages import show_error, show_info, show_warning


class FacilityContactsDialog(QDialog):
    def __init__(self, *, course, contact_service, parent=None):
        super().__init__(parent)

        self.course = course
        self.contact_service = contact_service

        self.setWindowTitle(f"Facility Contacts - {course['name']}")
        self.resize(900, 500)

        self._build_ui()
        self.load_contacts()

    def _build_ui(self):
        layout = QVBoxLayout()
        buttons = QHBoxLayout()

        add_btn = QPushButton("Add Contact")
        edit_btn = QPushButton("Edit Contact")
        delete_btn = QPushButton("Delete Contact")

        add_btn.clicked.connect(self.add_contact)
        edit_btn.clicked.connect(self.edit_contact)
        delete_btn.clicked.connect(self.delete_contact)

        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()

        self.table = QTableWidget()

        layout.addLayout(buttons)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load_contacts(self):
        rows = self.contact_service.list_for_facility(
            int(self.course["id"]),
            active_only=False,
        )

        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "First Name",
                "Last Name",
                "Title",
                "Email",
                "Phone",
                "Active",
                "Hold Requests",
                "Final Schedule",
            ]
        )

        for row_idx, row in enumerate(rows):
            self.table.insertRow(row_idx)

            values = [
                row["first_name"],
                row["last_name"],
                row["title"],
                row["email"],
                row["phone"],
                "Yes" if int(row["active"]) == 1 else "No",
                "Yes" if int(row["receives_hold_requests"]) == 1 else "No",
                "Yes" if int(row["receives_final_schedule"]) == 1 else "No",
            ]

            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))

                if col_idx == 0:
                    item.setData(Qt.UserRole, int(row["id"]))

                self.table.setItem(row_idx, col_idx, item)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

    def selected_contact_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None

        item = self.table.item(row, 0)
        if not item:
            return None

        return item.data(Qt.UserRole)

    def add_contact(self):
        dlg = FacilityContactDialog(parent=self)

        if dlg.exec_():
            values = dlg.values()
            values["facility_id"] = int(self.course["id"])
            values["course_id"] = None

            self.contact_service.create_contact(values)
            self.load_contacts()

            show_info(self, "Contact Added", "Course contact added successfully.")

    def edit_contact(self):
        contact_id = self.selected_contact_id()

        if not contact_id:
            show_warning(self, "No Selection", "Select a contact first.")
            return

        contact = self.contact_service.get_contact(contact_id)
        dlg = FacilityContactDialog(contact, self)

        if dlg.exec_():
            values = dlg.values()
            values["facility_id"] = int(self.course["id"])
            values["course_id"] = None

            self.contact_service.update_contact(contact_id, values)
            self.load_contacts()

            show_info(self, "Contact Updated", "Course contact updated successfully.")

    def delete_contact(self):
        contact_id = self.selected_contact_id()

        if not contact_id:
            show_warning(self, "No Selection", "Select a contact first.")
            return

        confirm = QMessageBox.question(
            self,
            "Delete Contact",
            "Are you sure you want to delete this contact?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if confirm != QMessageBox.Yes:
            return

        try:
            self.contact_service.delete_contact(contact_id)
            self.load_contacts()
            show_info(self, "Contact Deleted", "Course contact deleted successfully.")

        except Exception as exc:
            show_error(self, "Delete Failed", str(exc))
