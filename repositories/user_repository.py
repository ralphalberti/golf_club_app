from repositories.base_repository import BaseRepository
from models.user import User


class UserRepository(BaseRepository):
    USER_FIELDS = {
        "id",
        "username",
        "password_hash",
        "role",
        "member_id",
        "active",
        "created_at",
        "updated_at",
    }

    def get_by_username(self, username: str) -> User | None:
        with self.db.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND active = 1",
                (username,),
            ).fetchone()
            if not row:
                return None
            payload = {key: row[key] for key in row.keys() if key in self.USER_FIELDS}
            return User(**payload)
