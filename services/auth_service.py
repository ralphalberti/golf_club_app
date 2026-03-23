from repositories.user_repository import UserRepository
from app.utils import verify_password

class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def authenticate(self, username: str, password: str):
        user = self.user_repository.get_by_username(username)
        if not user or not user.active:
            return None
        return user if verify_password(password, user.password_hash) else None
