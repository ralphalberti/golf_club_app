from db.connection import Database
from app.utils import now_iso, hash_password

def seed_defaults(db: Database) -> None:
    with db.get_conn() as conn:
        now = now_iso()
        conn.execute(
            """
            INSERT OR IGNORE INTO app_settings
            (id, club_name, default_start_time, default_tee_interval, updated_at)
            VALUES (1, 'Community Golf Club', '10:00', 9, ?)
            """,
            (now,),
        )
        exists = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        if exists == 0:
            conn.execute(
                """
                INSERT INTO users
                (username, password_hash, role, member_id, active, created_at, updated_at)
                VALUES (?, ?, 'admin', NULL, 1, ?, ?)
                """,
                ("admin", hash_password("admin123"), now, now),
            )
