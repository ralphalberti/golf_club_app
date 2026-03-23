from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QListWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
)

class OutingAssignmentDialog(QDialog):
    def __init__(self, members, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Players for Schedule Generation")
        self.resize(700, 400)

        self.available = QListWidget()
        self.selected = QListWidget()
        for member in members:
            self.available.addItem(f"{member['id']} - {member['first_name']} {member['last_name']}")

        move_right = QPushButton(">>")
        move_left = QPushButton("<<")
        move_right.clicked.connect(self.add_member)
        move_left.clicked.connect(self.remove_member)

        controls = QVBoxLayout()
        controls.addStretch()
        controls.addWidget(move_right)
        controls.addWidget(move_left)
        controls.addStretch()

        left = QVBoxLayout()
        left.addWidget(QLabel("Available members"))
        left.addWidget(self.available)

        right = QVBoxLayout()
        right.addWidget(QLabel("Selected members"))
        right.addWidget(self.selected)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("Generate")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)

        top = QHBoxLayout()
        top.addLayout(left)
        top.addLayout(controls)
        top.addLayout(right)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(buttons)

    def add_member(self):
        item = self.available.currentItem()
        if item:
            self.selected.addItem(self.available.takeItem(self.available.row(item)))

    def remove_member(self):
        item = self.selected.currentItem()
        if item:
            self.available.addItem(self.selected.takeItem(self.selected.row(item)))

    def selected_member_ids(self):
        ids = []
        for i in range(self.selected.count()):
            text = self.selected.item(i).text()
            ids.append(int(text.split(" - ")[0]))
        return ids
