from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QMessageBox,
    QVBoxLayout,
)

from services.settings_service import SettingsService


class SettingsDialog(QDialog):
    def __init__(self, settings_service, parent=None):
        super().__init__(parent)
        self.settings_service = settings_service

        self.setWindowTitle("Settings")
        self.resize(420, 220)

        self.scheduler_algorithm_combo = QComboBox()
        self.scheduler_algorithm_combo.addItem("Balanced", "balanced")
        self.scheduler_algorithm_combo.addItem("Pairing Priority", "pairing_priority")
        self.scheduler_algorithm_combo.addItem("Rotation Priority", "rotation_priority")

        self.reshuffle_mode_combo = QComboBox()
        self.reshuffle_mode_combo.addItem("Conservative", "conservative")
        self.reshuffle_mode_combo.addItem("Moderate", "moderate")
        self.reshuffle_mode_combo.addItem("Aggressive", "aggressive")

        self.show_tier_colors_checkbox = QCheckBox(
            "Enable colored player names by tier"
        )
        self.show_tier_summary_checkbox = QCheckBox(
            "Show tier counts in tee-time headers"
        )

        form_layout = QFormLayout()
        form_layout.addRow("Scheduler Algorithm", self.scheduler_algorithm_combo)
        form_layout.addRow("Reshuffle Mode", self.reshuffle_mode_combo)
        form_layout.addRow("", self.show_tier_colors_checkbox)
        form_layout.addRow("", self.show_tier_summary_checkbox)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(self.button_box)

        self.load_settings()

    def load_settings(self) -> None:
        settings = self.settings_service.get_all()

        self._set_combo_value(
            self.scheduler_algorithm_combo,
            settings["scheduler_algorithm"],
        )
        self._set_combo_value(
            self.reshuffle_mode_combo,
            settings["reshuffle_mode"],
        )

        self.show_tier_colors_checkbox.setChecked(settings["show_tier_colors"])
        self.show_tier_summary_checkbox.setChecked(settings["show_tier_summary"])

    def save_settings(self) -> None:
        try:
            self.settings_service.update_scheduler_settings(
                scheduler_algorithm=self.scheduler_algorithm_combo.currentData(),
                reshuffle_mode=self.reshuffle_mode_combo.currentData(),
            )

            self.settings_service.update_display_settings(
                show_tier_colors=self.show_tier_colors_checkbox.isChecked(),
                show_tier_summary=self.show_tier_summary_checkbox.isChecked(),
            )

            self.accept()

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Save Failed",
                f"Could not save settings.\n\n{exc}",
            )

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return
