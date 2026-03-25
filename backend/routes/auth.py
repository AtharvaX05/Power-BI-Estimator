"""Authentication routes — registration, login, logout."""
import logging
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.models.user import UserCreate
from backend.dependencies import auth_service
from backend.utils.templates import render_template

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return render_template("login.html", request, {"error": None})


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    token = auth_service.login(email, password)
    if token is None:
        return render_template("login.html", request, {"error": "Invalid email or password."})

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token", value=token,
        httponly=True, samesite="lax", max_age=3600,
    )
    logger.info("User logged in: %s", email)
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return render_template("register.html", request, {"error": None})


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
        return render_template("register.html", request, {"error": str(e)})
    except Exception:
        logger.exception("Registration failed")
        return render_template("register.html", request, {"error": "Registration failed."})

    return RedirectResponse(url="/login", status_code=303)


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response
