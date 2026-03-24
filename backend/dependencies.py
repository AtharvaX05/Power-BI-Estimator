from backend.repositories.memory import InMemoryUserRepository, InMemoryProjectRepository
from backend.repositories.supabase import SupabaseUserRepository, SupabaseProjectRepository
from backend.services.auth_service import AuthService
from backend.services.project_service import ProjectService

# Instantiate repositories (Supabase backed)
user_repo = SupabaseUserRepository()
project_repo = SupabaseProjectRepository()

# To use in-memory repositories instead, uncomment these:
# user_repo = InMemoryUserRepository()
# project_repo = InMemoryProjectRepository()

# Instantiate services
auth_service = AuthService(user_repo)
project_service = ProjectService(project_repo)
