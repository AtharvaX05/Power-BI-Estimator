"""Supabase repository implementations."""
from typing import List, Optional, Dict
from datetime import datetime, timezone
import json

from supabase import create_client, Client
from backend.models.user import User
from backend.models.project import Project, ProjectVersion, EstimationInput, EstimationOutput
from backend.repositories.base import UserRepository, ProjectRepository
from backend.config import settings


class SupabaseUserRepository(UserRepository):
    """UserRepository implementation using Supabase."""

    def __init__(self) -> None:
        self._supabase_url = settings.SUPABASE_URL
        self._supabase_key = settings.SUPABASE_KEY

    def _get_client(self) -> Client:
        if not self._supabase_url or not self._supabase_key:
            raise ValueError("Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_KEY in .env")
        return create_client(self._supabase_url, self._supabase_key)

    def create(self, user: User) -> User:
        data = user.model_dump()
        # Convert datetime to ISO string for Supabase
        data["created_at"] = data["created_at"].isoformat()
        self._get_client().table("users").insert(data).execute()
        return user

    def get_by_id(self, user_id: str) -> Optional[User]:
        res = self._get_client().table("users").select("*").eq("id", user_id).execute()
        if not res.data:
            return None
        return User(**res.data[0])

    def get_by_email(self, email: str) -> Optional[User]:
        res = self._get_client().table("users").select("*").eq("email", email).execute()
        if not res.data:
            return None
        return User(**res.data[0])

    def update_password(self, user_id: str, hashed_password: str) -> bool:
        result = self._get_client().table("users").update({"hashed_password": hashed_password}).eq("id", user_id).execute()
        return len(result.data) > 0

    def set_reset_token(self, user_id: str, token: str, expires_at: datetime) -> bool:
        result = self._get_client().table("users").update({
            "reset_token": token,
            "reset_token_expires": expires_at.isoformat()
        }).eq("id", user_id).execute()
        return len(result.data) > 0

    def get_by_reset_token(self, token: str) -> Optional[User]:
        res = self._get_client().table("users").select("*").eq("reset_token", token).execute()
        if not res.data:
            return None
        return User(**res.data[0])

    def clear_reset_token(self, user_id: str) -> bool:
        result = self._get_client().table("users").update({
            "reset_token": None,
            "reset_token_expires": None
        }).eq("id", user_id).execute()
        return len(result.data) > 0


class SupabaseProjectRepository(ProjectRepository):
    """ProjectRepository implementation using Supabase."""

    def __init__(self) -> None:
        self._supabase_url = settings.SUPABASE_URL
        self._supabase_key = settings.SUPABASE_KEY

    def _get_client(self) -> Client:
        if not self._supabase_url or not self._supabase_key:
            raise ValueError("Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_KEY in .env")
        return create_client(self._supabase_url, self._supabase_key)

    def create(self, project: Project) -> Project:
        data = project.model_dump(exclude={"versions"})
        data["created_at"] = data["created_at"].isoformat()
        data["updated_at"] = data["updated_at"].isoformat()
        self._get_client().table("projects").insert(data).execute()
        return project

    def get_by_id(self, project_id: str) -> Optional[Project]:
        # Get project info
        res = self._get_client().table("projects").select("*").eq("id", project_id).execute()
        if not res.data:
            return None
        
        project_data = res.data[0]
        
        # Get versions
        v_res = self._get_client().table("project_versions").select("*").eq("project_id", project_id).order("version_number").execute()
        versions = [ProjectVersion(**v) for v in v_res.data]
        
        project_data["versions"] = versions
        return Project(**project_data)

    def list_by_user(self, user_id: str) -> List[Project]:
        res = self._get_client().table("projects").select("*").eq("created_by", user_id).execute()
        projects = []
        for p_data in res.data:
            # We don't load all versions for the list view to save BW
            p_data["versions"] = [] 
            projects.append(Project(**p_data))
        return projects

    def add_version(self, project_id: str, version: ProjectVersion) -> Project:
        # 1. Insert version
        data = version.model_dump()
        data["project_id"] = project_id
        data["timestamp"] = data["timestamp"].isoformat()
        # inputs and outputs are dicts here, Supabase handles them as JSONB
        self._get_client().table("project_versions").insert(data).execute()
        
        # 2. Update project updated_at
        now = datetime.now(timezone.utc).isoformat()
        self._get_client().table("projects").update({"updated_at": now}).eq("id", project_id).execute()
        
        return self.get_by_id(project_id)

    def get_version(self, project_id: str, version_id: str) -> Optional[ProjectVersion]:
        res = self._get_client().table("project_versions").select("*").eq("version_id", version_id).eq("project_id", project_id).execute()
        if not res.data:
            return None
        return ProjectVersion(**res.data[0])

    def delete(self, project_id: str) -> bool:
        # Cascading delete will handle project_versions if foreign key is set up with ON DELETE CASCADE
        res = self._get_client().table("projects").delete().eq("id", project_id).execute()
        return len(res.data) > 0
