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
    try:
        token = auth_service.login(email, password)
    except Exception as exc:
        logger.exception("Login failed due to backend error")
        return render_template("login.html", request, {
            "error": "Unable to authenticate right now. Please try again later.",
        })

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


@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return render_template("forgot_password.html", request, {"error": None, "success": None})


@router.post("/forgot-password", response_class=HTMLResponse)
async def forgot_password(request: Request, email: str = Form(...)):
    try:
        reset_token = auth_service.initiate_password_reset(email)
        if reset_token:
            # In production, send email with reset link
            # For demo purposes, show the token directly
            reset_url = f"/reset-password?token={reset_token}"
            return render_template("forgot_password.html", request, {
                "error": None,
                "success": f"Password reset initiated. Use this link to reset: {reset_url}"
            })
        else:
            # Don't reveal if email exists or not, or if operation failed
            return render_template("forgot_password.html", request, {
                "error": None,
                "success": "If an account with that email exists, a password reset link has been sent."
            })
    except Exception as e:
        logger.exception("Password reset initiation failed")
        return render_template("forgot_password.html", request, {
            "error": "Unable to process request. Please try again later.",
            "success": None
        })


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, token: str = None):
    if not token:
        return render_template("reset_password.html", request, {
            "error": "Invalid reset link.",
            "token": None
        })
    return render_template("reset_password.html", request, {
        "error": None,
        "token": token
    })


@router.post("/reset-password", response_class=HTMLResponse)
async def reset_password(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    if new_password != confirm_password:
        return render_template("reset_password.html", request, {
            "error": "Passwords do not match.",
            "token": token
        })
    
    if len(new_password) < 6:
        return render_template("reset_password.html", request, {
            "error": "Password must be at least 6 characters long.",
            "token": token
        })
    
    try:
        success = auth_service.reset_password(token, new_password)
        if success:
            return render_template("reset_password.html", request, {
                "error": None,
                "token": None,
                "success": "Password reset successfully. You can now log in with your new password."
            })
        else:
            return render_template("reset_password.html", request, {
                "error": "Invalid or expired reset token.",
                "token": token
            })
    except Exception as e:
        logger.exception("Password reset failed")
        return render_template("reset_password.html", request, {
            "error": "Unable to reset password. Please try again later.",
            "token": token
        })
