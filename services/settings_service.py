from __future__ import annotations

from repositories.app_settings_repository import AppSettingsRepository


class SettingsService:
    VALID_SCHEDULER_ALGORITHMS = {
        "balanced",
        "pairing_priority",
        "rotation_priority",
    }

    VALID_RESHUFFLE_MODES = {
        "conservative",
        "moderate",
        "aggressive",
    }

    def __init__(self, db):
        self.repo = AppSettingsRepository(db)

    def get_all(self) -> dict:
        row = self.repo.get()
        return {
            "club_name": row["club_name"],
            "default_start_time": row["default_start_time"],
            "default_tee_interval": int(row["default_tee_interval"]),
            "smtp_host": row["smtp_host"],
            "smtp_port": row["smtp_port"],
            "smtp_username": row["smtp_username"],
            "smtp_password": row["smtp_password"],
            "smtp_from_name": row["smtp_from_name"],
            "smtp_from_email": row["smtp_from_email"],
            "scheduler_algorithm": row["scheduler_algorithm"],
            "reshuffle_mode": row["reshuffle_mode"],
            "show_tier_colors": bool(row["show_tier_colors"]),
            "show_tier_summary": bool(row["show_tier_summary"]),
        }

    def get_scheduler_algorithm(self) -> str:
        return self.get_all()["scheduler_algorithm"]

    def set_scheduler_algorithm(self, value: str) -> None:
        if value not in self.VALID_SCHEDULER_ALGORITHMS:
            raise ValueError(
                f"Invalid scheduler_algorithm: {value}. "
                f"Expected one of: {sorted(self.VALID_SCHEDULER_ALGORITHMS)}"
            )
        self.repo.update({"scheduler_algorithm": value})

    def get_reshuffle_mode(self) -> str:
        return self.get_all()["reshuffle_mode"]

    def set_reshuffle_mode(self, value: str) -> None:
        if value not in self.VALID_RESHUFFLE_MODES:
            raise ValueError(
                f"Invalid reshuffle_mode: {value}. "
                f"Expected one of: {sorted(self.VALID_RESHUFFLE_MODES)}"
            )
        self.repo.update({"reshuffle_mode": value})

    def get_show_tier_colors(self) -> bool:
        return self.get_all()["show_tier_colors"]

    def set_show_tier_colors(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError("show_tier_colors must be a bool.")
        self.repo.update({"show_tier_colors": 1 if value else 0})

    def get_show_tier_summary(self) -> bool:
        return self.get_all()["show_tier_summary"]

    def set_show_tier_summary(self, value: bool) -> None:
        if not isinstance(value, bool):
            raise ValueError("show_tier_summary must be a bool.")
        self.repo.update({"show_tier_summary": 1 if value else 0})

    def update_display_settings(
        self,
        *,
        show_tier_colors: bool,
        show_tier_summary: bool,
    ) -> None:
        if not isinstance(show_tier_colors, bool):
            raise ValueError("show_tier_colors must be a bool.")
        if not isinstance(show_tier_summary, bool):
            raise ValueError("show_tier_summary must be a bool.")

        self.repo.update(
            {
                "show_tier_colors": 1 if show_tier_colors else 0,
                "show_tier_summary": 1 if show_tier_summary else 0,
            }
        )

    def update_scheduler_settings(
        self,
        *,
        scheduler_algorithm: str,
        reshuffle_mode: str,
    ) -> None:
        if scheduler_algorithm not in self.VALID_SCHEDULER_ALGORITHMS:
            raise ValueError(
                f"Invalid scheduler_algorithm: {scheduler_algorithm}. "
                f"Expected one of: {sorted(self.VALID_SCHEDULER_ALGORITHMS)}"
            )

        if reshuffle_mode not in self.VALID_RESHUFFLE_MODES:
            raise ValueError(
                f"Invalid reshuffle_mode: {reshuffle_mode}. "
                f"Expected one of: {sorted(self.VALID_RESHUFFLE_MODES)}"
            )

        self.repo.update(
            {
                "scheduler_algorithm": scheduler_algorithm,
                "reshuffle_mode": reshuffle_mode,
            }
        )
