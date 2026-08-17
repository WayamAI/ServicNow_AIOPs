from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IncidentStatus(StrEnum):
    NEW = "new"
    RCA = "rca"
    PLANNED = "planned"
    EXECUTING = "executing"
    VALIDATING = "validating"
    RESOLVED = "resolved"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(StrEnum):
    AGENT_START = "agent_start"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    AGENT_RESPONSE = "agent_response"
    ERROR = "error"


# Request models
class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""


class CreateSessionRequest(BaseModel):
    project_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class UpdateSessionRequest(BaseModel):
    config: dict[str, Any] | None = None
    status: SessionStatus | None = None


class CreateIncidentRequest(BaseModel):
    title: str
    description: str
    container_id: str | None = None
    container_name: str | None = None
    severity: Severity = Severity.MEDIUM


# Response models
class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str


class SessionResponse(BaseModel):
    id: str
    project_id: str
    status: SessionStatus
    config: dict[str, Any]
    created_at: str
    updated_at: str


class IncidentResponse(BaseModel):
    id: str
    session_id: str
    title: str
    description: str
    container_id: str | None
    container_name: str | None
    status: IncidentStatus
    severity: Severity
    created_at: str
    updated_at: str
    resolved_at: str | None


class RunResponse(BaseModel):
    id: str
    incident_id: str
    run_number: int
    status: RunStatus
    rca_result: dict[str, Any] | None
    plan_result: dict[str, Any] | None
    execution_result: dict[str, Any] | None
    validation_result: dict[str, Any] | None
    started_at: str
    completed_at: str | None


class EventResponse(BaseModel):
    id: str
    run_id: str
    agent_name: str
    event_type: str
    payload: dict[str, Any]
    created_at: str


class IncidentWithRunsResponse(IncidentResponse):
    runs: list[RunResponse] = Field(default_factory=list)


class AddContainerRequest(BaseModel):
    container_name: str
    image: str = ""
    expected_status: str = "running"


class ConfigUpdateRequest(BaseModel):
    monitor_poll_interval: int | None = Field(default=None, gt=0)
    orchestrator_poll_interval: int | None = Field(default=None, gt=0)
    max_incident_retries: int | None = Field(default=None, gt=0)
    max_tool_iterations: int | None = Field(default=None, gt=0)
