"""Authentication routes — registration, login, logout."""
import logging
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from pathlib import Path
from backend.models.user import UserCreate
from backend.dependencies import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

# Resolve template directory absolutely
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    token = auth_service.login(email, password)
    if token is None:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password."})

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token", value=token,
        httponly=True, samesite="lax", max_age=3600,
    )
    logger.info("User logged in: %s", email)
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register", response_class=HTMLResponse)
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        auth_service.register(UserCreate(name=name, email=email, password=password))
    except ValueError as e:
        return templates.TemplateResponse("register.html", {"request": request, "error": str(e)})
    except Exception:
        logger.exception("Registration failed")
        return templates.TemplateResponse("register.html", {"request": request, "error": "Registration failed."})

    return RedirectResponse(url="/login", status_code=303)


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response
