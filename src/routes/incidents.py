"""Incident endpoints."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from src.config import settings
from src.db import (
    create_incident,
    get_incident,
    get_session,
    list_incidents,
    list_runs,
)
from src.errors import IncidentNotFoundError, SessionNotFoundError
from src.models import (
    CreateIncidentRequest,
    IncidentResponse,
    IncidentWithRunsResponse,
    RunResponse,
)

router = APIRouter(tags=["incidents"])


def _row_to_incident(row: dict) -> IncidentResponse:
    return IncidentResponse(
        id=row["id"],
        session_id=row["session_id"],
        title=row["title"],
        description=row["description"],
        container_id=row.get("container_id"),
        container_name=row.get("container_name"),
        status=row["status"],
        severity=row["severity"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        resolved_at=row.get("resolved_at"),
    )


def _row_to_run(row: dict) -> RunResponse:
    return RunResponse(
        id=row["id"],
        incident_id=row["incident_id"],
        run_number=row["run_number"],
        status=row["status"],
        rca_result=row.get("rca_result"),
        plan_result=row.get("plan_result"),
        execution_result=row.get("execution_result"),
        validation_result=row.get("validation_result"),
        started_at=row["started_at"],
        completed_at=row.get("completed_at"),
    )


@router.post(
    "/sessions/{session_id}/incidents", response_model=IncidentResponse, status_code=201
)
async def create_incident_endpoint(
    session_id: str,
    request: CreateIncidentRequest,
    background_tasks: BackgroundTasks,
) -> IncidentResponse:
    from src.db import IncidentData

    session = get_session(settings.db_path, session_id)
    if not session:
        raise SessionNotFoundError(f"Session {session_id} not found")

    data = IncidentData(
        session_id=session_id,
        title=request.title,
        description=request.description,
        container_id=request.container_id,
        container_name=request.container_name,
        severity=request.severity.value,
    )
    incident_id = create_incident(settings.db_path, data)
    row = get_incident(settings.db_path, incident_id)

    # Trigger pipeline in background
    background_tasks.add_task(_run_pipeline, incident_id, session_id)

    return _row_to_incident(row)


async def _run_pipeline(incident_id: str, session_id: str) -> None:
    """Background task to run the incident pipeline."""
    from src.bus import event_bus
    from src.db import get_incident
    from src.orchestrator import run_incident_pipeline
    from src.run_registry import unregister_run
    from src.ws_callback import SSECallbackHandler

    incident = get_incident(settings.db_path, incident_id)
    if not incident:
        return

    cb = SSECallbackHandler(
        bus=event_bus,
        session_id=session_id,
        run_id="",  # will be set by pipeline
        db_path=settings.db_path,
    )

    try:
        await run_incident_pipeline(
            incident_id=incident_id,
            session_id=session_id,
            container_name=incident.get("container_name") or "",
            title=incident["title"],
            description=incident["description"],
            db_path=settings.db_path,
            callback_handler=cb,
            container_id=incident.get("container_id"),
        )
    finally:
        # Unregister after pipeline completes (run_id set by pipeline on cb)
        if cb.run_id:
            unregister_run(cb.run_id)


@router.get("/sessions/{session_id}/incidents", response_model=list[IncidentResponse])
async def list_incidents_endpoint(
    session_id: str,
    status: str | None = None,
) -> list[IncidentResponse]:
    session = get_session(settings.db_path, session_id)
    if not session:
        raise SessionNotFoundError(f"Session {session_id} not found")
    rows = list_incidents(settings.db_path, session_id, status)
    return [_row_to_incident(r) for r in rows]


@router.get("/incidents/{incident_id}", response_model=IncidentWithRunsResponse)
async def get_incident_endpoint(
    incident_id: str,
) -> IncidentWithRunsResponse:
    row = get_incident(settings.db_path, incident_id)
    if not row:
        raise IncidentNotFoundError(f"Incident {incident_id} not found")
    runs = list_runs(settings.db_path, incident_id)
    incident = _row_to_incident(row)
    return IncidentWithRunsResponse(
        **incident.model_dump(),
        runs=[_row_to_run(r) for r in runs],
    )
