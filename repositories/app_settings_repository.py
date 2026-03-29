from repositories.base_repository import BaseRepository
from app.utils import now_iso


class AppSettingsRepository(BaseRepository):
    def ensure_exists(self) -> None:
        with self.db.get_conn() as conn:
            row = conn.execute("SELECT id FROM app_settings WHERE id = 1").fetchone()

            if row is None:
                conn.execute(
                    """
                    INSERT INTO app_settings (
                        id,
                        club_name,
                        default_start_time,
                        default_tee_interval,
                        smtp_host,
                        smtp_port,
                        smtp_username,
                        smtp_password,
                        smtp_from_name,
                        smtp_from_email,
                        scheduler_algorithm,
                        reshuffle_mode,
                        show_tier_colors,
                        show_tier_summary,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        1,
                        "Community Golf Club",
                        "10:00",
                        9,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        "balanced",
                        "moderate",
                        1,
                        1,
                        now_iso(),
                    ),
                )

    def get(self):
        self.ensure_exists()

        with self.db.get_conn() as conn:
            return conn.execute("SELECT * FROM app_settings WHERE id = 1").fetchone()

    def update(self, data: dict) -> None:
        self.ensure_exists()

        allowed_fields = {
            "club_name",
            "default_start_time",
            "default_tee_interval",
            "smtp_host",
            "smtp_port",
            "smtp_username",
            "smtp_password",
            "smtp_from_name",
            "smtp_from_email",
            "scheduler_algorithm",
            "reshuffle_mode",
            "show_tier_colors",
            "show_tier_summary",
        }

        update_fields = []
        params = []

        for key, value in data.items():
            if key not in allowed_fields:
                raise KeyError(f"Unknown app setting field: {key}")
            update_fields.append(f"{key} = ?")
            params.append(value)

        if not update_fields:
            return

        update_fields.append("updated_at = ?")
        params.append(now_iso())
        params.append(1)

        sql = f"""
            UPDATE app_settings
            SET {", ".join(update_fields)}
            WHERE id = ?
        """

        with self.db.get_conn() as conn:
            conn.execute(sql, tuple(params))
