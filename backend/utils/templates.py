from pathlib import Path
from fastapi.templating import Jinja2Templates

# Resolve template directory absolutely relative to the project root
# This file is in backend/utils/, so .parent.parent.parent is the root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

def render_template(name: str, request, context: dict = None):
    """
    Helper to render templates with a signature compatible across multiple Starlette/FastAPI versions.
    """
    if context is None:
        context = {}
    
    # Ensure request is in context (required by newer Starlette)
    if "request" not in context:
        context["request"] = request
        
    # We use keyword arguments to be as flexible as possible with different Starlette versions
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=context
    )
