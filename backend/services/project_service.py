"""Project service — orchestrates project CRUD and versioning."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from backend.models.project import (
    Project, ProjectCreate, ProjectVersion,
    EstimationInput, EstimationOutput,
)
from backend.repositories.base import ProjectRepository
from backend.services.estimation_engine import EstimationEngine


class ProjectService:
    def __init__(self, project_repo: ProjectRepository) -> None:
        self._repo = project_repo
        self._engine = EstimationEngine()

    def create_project(self, data: ProjectCreate, user_id: str) -> Project:
        now = datetime.now(timezone.utc)
        project = Project(
            id=uuid.uuid4().hex,
            name=data.name,
            client_name=data.client_name,
            description=data.description,
            created_by=user_id,
            created_at=now,
            updated_at=now,
            versions=[],
        )
        return self._repo.create(project)

    def list_projects(self, user_id: str) -> List[Project]:
        return self._repo.list_by_user(user_id)

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._repo.get_by_id(project_id)

    def create_version(self, project_id: str, inputs: EstimationInput) -> ProjectVersion:
        """Run estimation engine and append a new version (never overwrites)."""
        project = self._repo.get_by_id(project_id)
        if project is None:
            raise ValueError("Project not found")

        outputs: EstimationOutput = self._engine.calculate(inputs)
        version_number = len(project.versions) + 1

        version = ProjectVersion(
            version_id=uuid.uuid4().hex,
            version_number=version_number,
            timestamp=datetime.now(timezone.utc),
            inputs=inputs,
            outputs=outputs,
        )
        self._repo.add_version(project_id, version)
        return version

    def get_version(self, project_id: str, version_id: str) -> Optional[ProjectVersion]:
        return self._repo.get_version(project_id, version_id)

    def delete_project(self, project_id: str) -> bool:
        return self._repo.delete(project_id)
