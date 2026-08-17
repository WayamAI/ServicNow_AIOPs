from typing import ClassVar


class AIOpsError(Exception):
    """Base domain error."""

    status_code: ClassVar[int] = 500
    error_code: ClassVar[str] = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class IncidentNotFoundError(AIOpsError):
    status_code: ClassVar[int] = 404
    error_code: ClassVar[str] = "INCIDENT_NOT_FOUND"


class SessionNotFoundError(AIOpsError):
    status_code: ClassVar[int] = 404
    error_code: ClassVar[str] = "SESSION_NOT_FOUND"


class ProjectNotFoundError(AIOpsError):
    status_code: ClassVar[int] = 404
    error_code: ClassVar[str] = "PROJECT_NOT_FOUND"


class RunNotFoundError(AIOpsError):
    status_code: ClassVar[int] = 404
    error_code: ClassVar[str] = "RUN_NOT_FOUND"


class RunCancelledError(AIOpsError):
    status_code: ClassVar[int] = 409
    error_code: ClassVar[str] = "RUN_CANCELLED"


class RunAlreadyCompleteError(AIOpsError):
    status_code: ClassVar[int] = 409
    error_code: ClassVar[str] = "RUN_ALREADY_COMPLETE"


class DockerToolError(AIOpsError):
    status_code: ClassVar[int] = 502
    error_code: ClassVar[str] = "DOCKER_TOOL_ERROR"


class LLMError(AIOpsError):
    status_code: ClassVar[int] = 502
    error_code: ClassVar[str] = "LLM_ERROR"
