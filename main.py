import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, PlainTextResponse

from backend.routes.auth import router as auth_router
from backend.routes.projects import router as projects_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

app = FastAPI(title="Power BI Effort Estimation", version="1.0.0")

# Mount static files (using absolute path for Vercel compatibility)
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "frontend" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.on_event("startup")
async def startup_event():
    logging.info("Starting Power BI Estimator app")
    logging.info("Working dir: %s", BASE_DIR)
    logging.info("Static dir exists: %s (%s)", STATIC_DIR.exists(), STATIC_DIR)
    
    # Check templates dir
    TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"
    logging.info("Templates dir exists: %s (%s)", TEMPLATES_DIR.exists(), TEMPLATES_DIR)
    
    if not TEMPLATES_DIR.exists():
        logging.error("CRITICAL: Templates directory not found!")

# Register route modules
app.include_router(auth_router)
app.include_router(projects_router)


@app.get("/")
async def root():
    """Redirect root to login page."""
    return RedirectResponse(url="/login", status_code=303)


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc):
    return RedirectResponse(url="/login", status_code=303)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    error_msg = f"Unhandled exception for {request.method} {request.url}\n\n{traceback.format_exc()}"
    logging.error(error_msg)
    # Returning error message in plain text for easier debugging in Vercel logs or browser
    return PlainTextResponse(error_msg, status_code=500)
