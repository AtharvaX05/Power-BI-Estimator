from backend.repositories.memory import InMemoryUserRepository, InMemoryProjectRepository
from backend.repositories.supabase import SupabaseUserRepository, SupabaseProjectRepository
from backend.services.auth_service import AuthService
from backend.services.project_service import ProjectService
from backend.config import settings
import logging

# Instantiate repositories (Supabase backed)
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    user_repo = SupabaseUserRepository()
    project_repo = SupabaseProjectRepository()
else:
    logging.warning("SUPABASE_URL or SUPABASE_KEY not set. Falling back to in-memory repositories.")
    user_repo = InMemoryUserRepository()
    project_repo = InMemoryProjectRepository()

# Instantiate services
auth_service = AuthService(user_repo)
project_service = ProjectService(project_repo)
