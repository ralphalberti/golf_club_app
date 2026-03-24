from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from app.constants import APP_NAME, APP_VERSION


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setMinimumWidth(320)

        layout = QVBoxLayout()

        title = QLabel(f"<h2>{APP_NAME}</h2>")
        version = QLabel(f"Version: {APP_VERSION}")
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(close_button)

        self.setLayout(layout)
