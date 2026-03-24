"""Abstract repository interfaces (DAL contracts).

All data access goes through these interfaces.
Swap implementations to migrate from in-memory to SQLite / PostgreSQL.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from backend.models.user import User
from backend.models.project import Project, ProjectVersion


class UserRepository(ABC):
    """Contract for user persistence."""

    @abstractmethod
    def create(self, user: User) -> User: ...

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]: ...

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    def list_all(self) -> List[User]: ...


class ProjectRepository(ABC):
    """Contract for project persistence."""

    @abstractmethod
    def create(self, project: Project) -> Project: ...

    @abstractmethod
    def get_by_id(self, project_id: str) -> Optional[Project]: ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> List[Project]: ...

    @abstractmethod
    def add_version(self, project_id: str, version: ProjectVersion) -> Project: ...

    @abstractmethod
    def get_version(self, project_id: str, version_id: str) -> Optional[ProjectVersion]: ...

    @abstractmethod
    def delete(self, project_id: str) -> bool: ...
