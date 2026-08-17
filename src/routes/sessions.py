"""Session CRUD endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from src.config import settings
from src.db import (
    create_session,
    get_session,
    list_sessions,
    update_session,
)
from src.errors import SessionNotFoundError
from src.models import (
    CreateSessionRequest,
    SessionResponse,
    UpdateSessionRequest,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Internal default project ID (created on startup)
_DEFAULT_PROJECT_ID: str | None = None


def set_default_project_id(project_id: str) -> None:
    global _DEFAULT_PROJECT_ID
    _DEFAULT_PROJECT_ID = project_id


def get_default_project_id() -> str:
    if _DEFAULT_PROJECT_ID is None:
        raise HTTPException(status_code=500, detail="Server not initialized")
    return _DEFAULT_PROJECT_ID


def _row_to_session(row: dict) -> SessionResponse:
    config = row.get("config", {})
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except (json.JSONDecodeError, TypeError):
            config = {}
    return SessionResponse(
        id=row["id"],
        project_id=row["project_id"],
        status=row["status"],
        config=config,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session_endpoint(
    request: CreateSessionRequest,
) -> SessionResponse:
    project_id = request.project_id or get_default_project_id()
    session_id = create_session(settings.db_path, project_id, request.config)
    row = get_session(settings.db_path, session_id)
    return _row_to_session(row)


@router.get("", response_model=list[SessionResponse])
async def list_sessions_endpoint(
    project_id: str | None = None,
) -> list[SessionResponse]:
    rows = list_sessions(settings.db_path, project_id)
    return [_row_to_session(r) for r in rows]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_endpoint(
    session_id: str,
) -> SessionResponse:
    row = get_session(settings.db_path, session_id)
    if not row:
        raise SessionNotFoundError(f"Session {session_id} not found")
    return _row_to_session(row)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session_endpoint(
    session_id: str,
    request: UpdateSessionRequest,
) -> SessionResponse:
    row = get_session(settings.db_path, session_id)
    if not row:
        raise SessionNotFoundError(f"Session {session_id} not found")
    updates = {}
    if request.config is not None:
        updates["config"] = request.config
    if request.status is not None:
        updates["status"] = request.status.value
    if updates:
        update_session(settings.db_path, session_id, **updates)
    row = get_session(settings.db_path, session_id)
    return _row_to_session(row)


@router.delete("/{session_id}", status_code=204)
async def delete_session_endpoint(session_id: str) -> None:
    row = get_session(settings.db_path, session_id)
    if not row:
        raise SessionNotFoundError(f"Session {session_id} not found")
    update_session(settings.db_path, session_id, status="cancelled")
