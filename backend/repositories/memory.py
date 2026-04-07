"""In-memory repository implementations.

Replace this file (or add a new one) when migrating to a real database.
"""
import threading
from typing import Dict, List, Optional
from backend.models.user import User
from backend.models.project import Project, ProjectVersion
from backend.repositories.base import UserRepository, ProjectRepository


class InMemoryUserRepository(UserRepository):
    """Thread-safe in-memory user store."""

    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._lock = threading.Lock()

    def create(self, user: User) -> User:
        with self._lock:
            self._users[user.id] = user
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        for u in self._users.values():
            if u.email == email:
                return u
        return None

    def update_password(self, user_id: str, hashed_password: str) -> bool:
        with self._lock:
            if user_id in self._users:
                self._users[user_id].hashed_password = hashed_password
                return True
        return False

    def set_reset_token(self, user_id: str, token: str, expires_at) -> bool:
        with self._lock:
            if user_id in self._users:
                self._users[user_id].reset_token = token
                self._users[user_id].reset_token_expires = expires_at
                return True
        return False

    def get_by_reset_token(self, token: str) -> Optional[User]:
        for u in self._users.values():
            if u.reset_token == token:
                return u
        return None

    def clear_reset_token(self, user_id: str) -> bool:
        with self._lock:
            if user_id in self._users:
                self._users[user_id].reset_token = None
                self._users[user_id].reset_token_expires = None
                return True
        return False

    def list_all(self) -> List[User]:
        return list(self._users.values())


class InMemoryProjectRepository(ProjectRepository):
    """Thread-safe in-memory project store."""

    def __init__(self) -> None:
        self._projects: Dict[str, Project] = {}
        self._lock = threading.Lock()

    def create(self, project: Project) -> Project:
        with self._lock:
            self._projects[project.id] = project
        return project

    def get_by_id(self, project_id: str) -> Optional[Project]:
        return self._projects.get(project_id)

    def list_by_user(self, user_id: str) -> List[Project]:
        return [p for p in self._projects.values() if p.created_by == user_id]

    def add_version(self, project_id: str, version: ProjectVersion) -> Project:
        with self._lock:
            project = self._projects.get(project_id)
            if project is None:
                raise ValueError(f"Project {project_id} not found")
            project.versions.append(version)
            from datetime import datetime, timezone
            project.updated_at = datetime.now(timezone.utc)
            return project

    def get_version(self, project_id: str, version_id: str) -> Optional[ProjectVersion]:
        project = self._projects.get(project_id)
        if project is None:
            return None
        for v in project.versions:
            if v.version_id == version_id:
                return v
        return None

    def delete(self, project_id: str) -> bool:
        with self._lock:
            if project_id in self._projects:
                del self._projects[project_id]
                return True
            return False
