from PyQt5.QtWidgets import QDialog, QTextEdit, QVBoxLayout


class ActivityLogDialog(QDialog):
    def __init__(self, *, outing_id, outing_service, formatter, parent=None):
        super().__init__(parent)

        self.outing_id = outing_id
        self.outing_service = outing_service
        self.formatter = formatter

        self.setWindowTitle("Activity Log")
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        self.activity_text = QTextEdit()
        self.activity_text.setReadOnly(True)

        layout.addWidget(self.activity_text)

        self.load_activity()

    def load_activity(self):
        try:
            rows = self.outing_service.get_recent_workflow_activity(
                self.outing_id,
                limit=25,
            )
        except Exception:
            self.activity_text.setPlainText("Recent activity unavailable.")
            return

        if not rows:
            self.activity_text.setPlainText("No recent workflow activity.")
            return

        lines = []

        for row in rows:
            activity_type = str(row["activity_type"] or "")
            status = str(row["status"] or "")
            subject = str(row["subject"] or "")
            count = int(row["count"] or 0)
            activity_at = self.formatter(str(row["activity_at"] or ""))

            if activity_type == "email":
                icon = "🟢" if status == "sent" else "🔴"
                lines.append(f"{icon} Email {status}: {count} recipient(s)")
                lines.append(f"   {subject}")
                lines.append(f"   {activity_at}")
            else:
                lines.append(f"🔵 Audit: {subject}")
                lines.append(f"   {activity_at}")

            lines.append("")

        self.activity_text.setPlainText("\n".join(lines).strip())
