from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SendConfirmationDialog(QDialog):
    def __init__(
        self,
        *,
        audience_label: str,
        template_label: str,
        recipients: list[dict],
        subject: str,
        body_text: str,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle("Preview / Confirm Send")
        self.resize(850, 700)

        self.recipients = recipients
        self.recipient_checkboxes: list[tuple[QCheckBox, dict]] = []

        layout = QVBoxLayout(self)

        summary = QLabel(
            f"<strong>Audience:</strong> {audience_label}<br>"
            f"<strong>Communication:</strong> {template_label}<br>"
            f"<strong>Subject:</strong> {subject}"
        )
        layout.addWidget(summary)

        recipient_box = QGroupBox("Recipients")
        recipient_layout = QVBoxLayout(recipient_box)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        for recipient in recipients:
            label = recipient.get("label", "")
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)
            scroll_layout.addWidget(checkbox)
            self.recipient_checkboxes.append((checkbox, recipient))

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)

        recipient_layout.addWidget(scroll)
        layout.addWidget(recipient_box, 1)

        body_box = QGroupBox("Email Body Preview")
        body_layout = QVBoxLayout(body_box)

        self.body_preview = QTextEdit()
        self.body_preview.setReadOnly(True)
        self.body_preview.setPlainText(body_text)

        body_layout.addWidget(self.body_preview)
        layout.addWidget(body_box, 2)

        button_row = QHBoxLayout()

        self.send_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

        self.send_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_row.addStretch()
        button_row.addWidget(self.send_button)
        button_row.addWidget(self.cancel_button)

        layout.addLayout(button_row)

    def selected_recipients(self) -> list[dict]:
        return [
            recipient
            for checkbox, recipient in self.recipient_checkboxes
            if checkbox.isChecked()
        ]
