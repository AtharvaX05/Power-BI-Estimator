"""Project and estimation routes."""
import logging
from typing import Optional

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from pathlib import Path
from backend.dependencies import project_service, auth_service
from backend.models.project import (
    ProjectCreate, EstimationInput,
    Complexity, DataVolume, DeploymentType, PerformanceLevel,
)
from backend.utils.security import decode_access_token
from backend.utils.export import export_to_excel, export_to_pdf, export_to_excel_with_cost, export_to_pdf_with_cost

import json

logger = logging.getLogger(__name__)
router = APIRouter(tags=["projects"])

# Resolve template directory absolutely
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "frontend" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _get_current_user_id(request: Request) -> Optional[str]:
    """Extract user id from JWT cookie."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    return payload.get("sub")


def _require_user(request: Request) -> str:
    uid = _get_current_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return uid


# ── Dashboard ─────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    uid = _get_current_user_id(request)
    if uid is None:
        return RedirectResponse(url="/login", status_code=303)

    user = auth_service.get_user(uid)
    projects = project_service.list_projects(uid)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "projects": projects,
    })


# ── Create project ────────────────────────────────────────────────

@router.get("/projects/new", response_class=HTMLResponse)
async def new_project_page(request: Request):
    uid = _get_current_user_id(request)
    if uid is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("project_form.html", {"request": request, "error": None})


@router.post("/projects/new", response_class=HTMLResponse)
async def create_project(
    request: Request,
    name: str = Form(...),
    client_name: str = Form(...),
    description: str = Form(""),
):
    uid = _require_user(request)
    project = project_service.create_project(
        ProjectCreate(name=name, client_name=client_name, description=description), uid,
    )
    return RedirectResponse(url=f"/projects/{project.id}", status_code=303)


# ── Project detail ────────────────────────────────────────────────

@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: str):
    uid = _get_current_user_id(request)
    if uid is None:
        return RedirectResponse(url="/login", status_code=303)

    project = project_service.get_project(project_id)
    if project is None or project.created_by != uid:
        raise HTTPException(status_code=404, detail="Project not found")

    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "project": project,
    })


# ── Create new version (estimation) ──────────────────────────────

@router.get("/projects/{project_id}/estimate", response_class=HTMLResponse)
async def estimation_form(request: Request, project_id: str):
    uid = _get_current_user_id(request)
    if uid is None:
        return RedirectResponse(url="/login", status_code=303)

    project = project_service.get_project(project_id)
    if project is None or project.created_by != uid:
        raise HTTPException(status_code=404, detail="Project not found")

    return templates.TemplateResponse("estimation_form.html", {
        "request": request,
        "project": project,
    })


@router.post("/projects/{project_id}/estimate", response_class=HTMLResponse)
async def create_estimation(request: Request, project_id: str):
    uid = _require_user(request)
    project = project_service.get_project(project_id)
    if project is None or project.created_by != uid:
        raise HTTPException(status_code=404, detail="Project not found")

    form = await request.form()

    try:
        perf_level_raw = form.get("performance_level", "none")
        perf_level = PerformanceLevel(perf_level_raw)

        inputs = EstimationInput(
            scoping_hours=float(form.get("scoping_hours", 4)),
            num_data_sources=int(form.get("num_data_sources", 1)),
            data_source_types=[t.strip() for t in form.get("data_source_types", "database").split(",") if t.strip()],
            data_source_complexity=Complexity(form.get("data_source_complexity", "medium")),
            data_volume=DataVolume(form.get("data_volume", "medium")),
            num_tables=int(form.get("num_tables", 5)),
            transformation_complexity=Complexity(form.get("transformation_complexity", "medium")),
            num_data_models=int(form.get("num_data_models", 1)),
            modeling_complexity=Complexity(form.get("modeling_complexity", "medium")),
            incremental_refresh=form.get("incremental_refresh") == "on",
            dax_complexity=Complexity(form.get("dax_complexity", "medium")),
            num_measures=int(form.get("num_measures", 10)),
            num_reports=int(form.get("num_reports", 1)),
            pages_per_report=int(form.get("pages_per_report", 5)),
            report_complexity=Complexity(form.get("report_complexity", "medium")),
            feature_tooltips=form.get("feature_tooltips") == "on",
            feature_subscriptions=form.get("feature_subscriptions") == "on",
            feature_alerts=form.get("feature_alerts") == "on",
            ui_ux_designer=form.get("ui_ux_designer") == "on",
            rls_required=form.get("rls_required") == "yes",
            rls_complexity=Complexity(form.get("rls_complexity", "low")),
            performance_optimization=perf_level != PerformanceLevel.NONE,
            performance_level=perf_level,
            deployment_type=DeploymentType(form.get("deployment_type", "power_bi_service")),
            deployment_hours=float(form.get("deployment_hours", 8)),
            uat_cycles=int(form.get("uat_cycles", 2)),
            documentation_required=form.get("documentation_required") == "yes",
            tl_percentage=float(form.get("tl_percentage", 10)),
            ba_percentage=float(form.get("ba_percentage", 10)),
            buffer_percentage=float(form.get("buffer_percentage", 0)),
        )
    except (ValueError, TypeError) as e:
        logger.warning("Invalid estimation input: %s", e)
        return templates.TemplateResponse("estimation_form.html", {
            "request": request,
            "project": project,
            "error": f"Invalid input: {e}",
        })

    version = project_service.create_version(project_id, inputs)
    return RedirectResponse(
        url=f"/projects/{project_id}/versions/{version.version_id}",
        status_code=303,
    )


# ── View version ──────────────────────────────────────────────────

@router.get("/projects/{project_id}/versions/{version_id}", response_class=HTMLResponse)
async def view_version(request: Request, project_id: str, version_id: str):
    uid = _get_current_user_id(request)
    if uid is None:
        return RedirectResponse(url="/login", status_code=303)

    project = project_service.get_project(project_id)
    if project is None or project.created_by != uid:
        raise HTTPException(status_code=404, detail="Project not found")

    version = project_service.get_version(project_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    return templates.TemplateResponse("version_detail.html", {
        "request": request,
        "project": project,
        "version": version,
    })


# ── Export ────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/versions/{version_id}/export/excel")
async def export_excel(request: Request, project_id: str, version_id: str):
    uid = _require_user(request)
    project = project_service.get_project(project_id)
    if project is None or project.created_by != uid:
        raise HTTPException(status_code=404, detail="Project not found")
    version = project_service.get_version(project_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    roles = _parse_cost_roles(request.query_params.get("roles", ""))
    currency = request.query_params.get("currency", "")
    buf = export_to_excel(project, version, roles=roles or None, currency=currency)
    filename = f"{project.name}_v{version.version_number}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.get("/projects/{project_id}/versions/{version_id}/export/pdf")
async def export_pdf(request: Request, project_id: str, version_id: str):
    uid = _require_user(request)
    project = project_service.get_project(project_id)
    if project is None or project.created_by != uid:
        raise HTTPException(status_code=404, detail="Project not found")
    version = project_service.get_version(project_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    roles = _parse_cost_roles(request.query_params.get("roles", ""))
    currency = request.query_params.get("currency", "")
    buf = export_to_pdf(project, version, roles=roles or None, currency=currency)
    filename = f"{project.name}_v{version.version_number}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


# ── Cost export endpoints ─────────────────────────────────────────

def _parse_cost_roles(query_param: str) -> list:
    """Parse cost roles from JSON query param. Returns list of dicts with role, percentage, rate."""
    if not query_param:
        return []
    try:
        roles = json.loads(query_param)
        if not isinstance(roles, list):
            return []
        parsed = []
        for r in roles:
            parsed.append({
                "role": str(r.get("role", "")).strip(),
                "percentage": float(r.get("percentage", 0)),
                "rate": float(r.get("rate", 0)),
            })
        return parsed
    except (json.JSONDecodeError, ValueError, TypeError):
        return []


@router.get("/projects/{project_id}/versions/{version_id}/export/excel-cost")
async def export_excel_cost(request: Request, project_id: str, version_id: str):
    uid = _require_user(request)
    project = project_service.get_project(project_id)
    if project is None or project.created_by != uid:
        raise HTTPException(status_code=404, detail="Project not found")
    version = project_service.get_version(project_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    roles = _parse_cost_roles(request.query_params.get("roles", ""))
    if not roles:
        raise HTTPException(status_code=400, detail="No cost roles provided")

    currency = request.query_params.get("currency", "")
    buf = export_to_excel_with_cost(project, version, roles, currency=currency)
    filename = f"{project.name}_v{version.version_number}_cost.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )


@router.get("/projects/{project_id}/versions/{version_id}/export/pdf-cost")
async def export_pdf_cost(request: Request, project_id: str, version_id: str):
    uid = _require_user(request)
    project = project_service.get_project(project_id)
    if project is None or project.created_by != uid:
        raise HTTPException(status_code=404, detail="Project not found")
    version = project_service.get_version(project_id, version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    roles = _parse_cost_roles(request.query_params.get("roles", ""))
    if not roles:
        raise HTTPException(status_code=400, detail="No cost roles provided")

    currency = request.query_params.get("currency", "")
    buf = export_to_pdf_with_cost(project, version, roles, currency=currency)
    filename = f"{project.name}_v{version.version_number}_cost.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )
