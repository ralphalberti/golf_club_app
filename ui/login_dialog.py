from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QLabel, QMessageBox
)

class LoginDialog(QDialog):
    def __init__(self, auth_service):
        super().__init__()
        self.auth_service = auth_service
        self.authenticated_user = None
        self.setWindowTitle("Login")
        self.resize(360, 160)

        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Username", self.username_edit)
        form.addRow("Password", self.password_edit)

        self.info = QLabel("Default admin login: admin / admin123")
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.handle_login)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.info)
        layout.addWidget(self.login_button)
        self.setLayout(layout)

    def handle_login(self):
        user = self.auth_service.authenticate(self.username_edit.text().strip(), self.password_edit.text())
        if not user:
            QMessageBox.warning(self, "Login failed", "Invalid credentials.")
            return
        self.authenticated_user = user
        self.accept()
