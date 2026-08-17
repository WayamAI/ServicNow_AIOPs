"""Cancel and config endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from src.config import settings
from src.db import get_run, update_run
from src.errors import RunNotFoundError
from src.models import ConfigUpdateRequest
from src.logger import get_logger
from src.run_registry import get_run_handler

logger = get_logger(__name__)

router = APIRouter(tags=["control"])


@router.post("/runs/{run_id}/cancel", status_code=200)
async def cancel_run(run_id: str) -> dict:
    run = get_run(settings.db_path, run_id)
    if not run:
        raise RunNotFoundError(f"Run {run_id} not found")
    if run["status"] not in ("running",):
        return {"message": f"Run {run_id} is not running (status: {run['status']})"}

    cb = get_run_handler(run_id)
    if cb and hasattr(cb, "cancel"):
        cb.cancel()
        logger.info("run_cancel_requested", run_id=run_id)
        return {"message": f"Cancellation requested for run {run_id}"}
    else:
        # Mark as cancelled in DB even if no active handler
        update_run(settings.db_path, run_id, status="cancelled")
        return {"message": f"Run {run_id} marked as cancelled"}


@router.get("/config")
async def get_config() -> dict:
    return {
        "monitor_poll_interval": settings.monitor_poll_interval,
        "orchestrator_poll_interval": settings.orchestrator_poll_interval,
        "max_incident_retries": settings.max_incident_retries,
        "max_tool_iterations": settings.max_tool_iterations,
        "codestral_deployment": settings.codestral_deployment,
        "gpt4o_mini_deployment": settings.gpt4o_mini_deployment,
        "host": settings.host,
        "port": settings.port,
    }


@router.patch("/config")
async def update_config(request: ConfigUpdateRequest) -> dict:
    updated = {}
    if request.monitor_poll_interval is not None:
        settings.monitor_poll_interval = request.monitor_poll_interval
        updated["monitor_poll_interval"] = request.monitor_poll_interval
    if request.orchestrator_poll_interval is not None:
        settings.orchestrator_poll_interval = request.orchestrator_poll_interval
        updated["orchestrator_poll_interval"] = request.orchestrator_poll_interval
    if request.max_incident_retries is not None:
        settings.max_incident_retries = request.max_incident_retries
        updated["max_incident_retries"] = request.max_incident_retries
    if request.max_tool_iterations is not None:
        settings.max_tool_iterations = request.max_tool_iterations
        updated["max_tool_iterations"] = request.max_tool_iterations
    return {"updated": updated, "message": "Config updated"}
