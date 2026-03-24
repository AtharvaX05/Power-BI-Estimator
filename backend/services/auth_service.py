"""Authentication service — sits between routes and repository."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.models.user import User, UserCreate
from backend.repositories.base import UserRepository
from backend.utils.security import hash_password, verify_password, create_access_token


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self._repo = user_repo

    def register(self, data: UserCreate) -> User:
        """Register a new user. Raises ValueError if email already taken."""
        if self._repo.get_by_email(data.email):
            raise ValueError("Email already registered")

        user = User(
            id=uuid.uuid4().hex,
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
            created_at=datetime.now(timezone.utc),
        )
        return self._repo.create(user)

    def login(self, email: str, password: str) -> Optional[str]:
        """Validate credentials & return JWT token, or None on failure."""
        user = self._repo.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            return None
        return create_access_token({"sub": user.id, "email": user.email})

    def get_user(self, user_id: str) -> Optional[User]:
        return self._repo.get_by_id(user_id)
