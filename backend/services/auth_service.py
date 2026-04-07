"""Authentication service — sits between routes and repository."""
import uuid
from datetime import datetime, timedelta, timezone
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

    def initiate_password_reset(self, email: str) -> Optional[str]:
        """Generate a reset token for the user and return it. In production, this would send an email."""
        user = self._repo.get_by_email(email)
        if user is None:
            return None  # Don't reveal if email exists
        
        reset_token = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # Token valid for 1 hour
        
        # Try to set the reset token, but don't fail if database schema isn't updated
        try:
            success = self._repo.set_reset_token(user.id, reset_token, expires_at)
            if not success:
                # If setting reset token fails, return None to indicate failure
                return None
        except Exception:
            # If database operation fails, return None
            return None
        
        return reset_token

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using a valid reset token."""
        try:
            user = self._repo.get_by_reset_token(token)
            if user is None or user.reset_token_expires is None:
                return False
            
            # Check if token is expired
            if datetime.now(timezone.utc) > user.reset_token_expires:
                return False
            
            # Update password and clear reset token
            hashed_password = hash_password(new_password)
            success = self._repo.update_password(user.id, hashed_password)
            if success:
                # Try to clear reset token, but don't fail the whole operation if it fails
                try:
                    self._repo.clear_reset_token(user.id)
                except Exception:
                    pass  # Reset token clearing is not critical
            return success
        except Exception:
            # If any database operation fails, return False
            return False
