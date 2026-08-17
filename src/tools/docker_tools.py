"""Docker LangChain tools wrapping subprocess docker CLI calls."""

from __future__ import annotations

import subprocess
import time
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.db import record_tool_timing
from src.errors import DockerToolError
from src.logger import get_logger

logger = get_logger(__name__)

DOCKER_TIMEOUT = 30


def _run_docker(cmd: list[str], db_path: str, event_id: str | None = None) -> str:
    """Run a docker command and return stdout. Records timing if event_id given."""
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=DOCKER_TIMEOUT,
            check=False,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        if event_id and db_path:
            record_tool_timing(
                db_path,
                event_id,
                cmd[1] if len(cmd) > 1 else cmd[0],
                elapsed_ms,
                success=result.returncode == 0,
            )
        if result.returncode != 0:
            msg = f"docker command failed: {result.stderr.strip()}"
            raise DockerToolError(msg)
        return result.stdout.strip()
    except subprocess.TimeoutExpired as e:
        msg = f"docker command timed out after {DOCKER_TIMEOUT}s"
        raise DockerToolError(msg) from e
    except FileNotFoundError as e:
        raise DockerToolError("docker CLI not found in PATH") from e


class DockerPsInput(BaseModel):
    """Input for DockerPsTool."""

    all_containers: bool = Field(
        default=True, description="Show all containers including stopped ones"
    )


class DockerPsTool(BaseTool):
    """List Docker containers."""

    name: str = "docker_ps"
    description: str = "List Docker containers. Returns JSON-formatted container info."
    args_schema: type[BaseModel] = DockerPsInput
    db_path: str = ""
    event_id: str | None = None

    def _run(
        self, all_containers: bool = True, **_: Any
    ) -> str:  # noqa: FBT001, FBT002
        cmd = ["docker", "ps", "--format", "{{json .}}"]
        if all_containers:
            cmd.insert(2, "-a")
        return _run_docker(cmd, self.db_path, self.event_id)


class DockerLogsInput(BaseModel):
    """Input for DockerLogsTool."""

    container: str = Field(description="Container name or ID")
    tail: int = Field(default=100, description="Number of log lines to fetch")


class DockerLogsTool(BaseTool):
    """Fetch logs from a Docker container."""

    name: str = "docker_logs"
    description: str = "Fetch logs from a Docker container."
    args_schema: type[BaseModel] = DockerLogsInput
    db_path: str = ""
    event_id: str | None = None

    def _run(self, container: str, tail: int = 100, **_: Any) -> str:
        cmd = ["docker", "logs", "--tail", str(tail), container]
        return _run_docker(cmd, self.db_path, self.event_id)


class DockerInspectInput(BaseModel):
    """Input for DockerInspectTool."""

    container: str = Field(description="Container name or ID")


class DockerInspectTool(BaseTool):
    """Inspect a Docker container."""

    name: str = "docker_inspect"
    description: str = (
        "Inspect a Docker container and return its full JSON configuration and state."
    )
    args_schema: type[BaseModel] = DockerInspectInput
    db_path: str = ""
    event_id: str | None = None

    def _run(self, container: str, **_: Any) -> str:
        cmd = ["docker", "inspect", container]
        return _run_docker(cmd, self.db_path, self.event_id)


class DockerStartInput(BaseModel):
    """Input for DockerStartTool."""

    container: str = Field(description="Container name or ID to start")


class DockerStartTool(BaseTool):
    """Start a stopped Docker container."""

    name: str = "docker_start"
    description: str = "Start a stopped Docker container."
    args_schema: type[BaseModel] = DockerStartInput
    db_path: str = ""
    event_id: str | None = None

    def _run(self, container: str, **_: Any) -> str:
        cmd = ["docker", "start", container]
        return _run_docker(cmd, self.db_path, self.event_id)


class DockerRestartInput(BaseModel):
    """Input for DockerRestartTool."""

    container: str = Field(description="Container name or ID to restart")


class DockerRestartTool(BaseTool):
    """Restart a Docker container."""

    name: str = "docker_restart"
    description: str = "Restart a Docker container."
    args_schema: type[BaseModel] = DockerRestartInput
    db_path: str = ""
    event_id: str | None = None

    def _run(self, container: str, **_: Any) -> str:
        cmd = ["docker", "restart", container]
        return _run_docker(cmd, self.db_path, self.event_id)


class DockerStopInput(BaseModel):
    """Input for DockerStopTool."""

    container: str = Field(description="Container name or ID to stop")


class DockerStopTool(BaseTool):
    """Stop a running Docker container."""

    name: str = "docker_stop"
    description: str = "Stop a running Docker container."
    args_schema: type[BaseModel] = DockerStopInput
    db_path: str = ""
    event_id: str | None = None

    def _run(self, container: str, **_: Any) -> str:
        cmd = ["docker", "stop", container]
        return _run_docker(cmd, self.db_path, self.event_id)


class DockerStatsInput(BaseModel):
    """Input for DockerStatsTool."""

    container: str = Field(description="Container name or ID")


class DockerStatsTool(BaseTool):
    """Get resource usage statistics for a Docker container."""

    name: str = "docker_stats"
    description: str = (
        "Get resource usage statistics for a Docker container (CPU, memory, network)."
    )
    args_schema: type[BaseModel] = DockerStatsInput
    db_path: str = ""
    event_id: str | None = None

    def _run(self, container: str, **_: Any) -> str:
        cmd = ["docker", "stats", "--no-stream", "--format", "{{json .}}", container]
        return _run_docker(cmd, self.db_path, self.event_id)


class FetchLogInput(BaseModel):
    """Input for FetchLogTool."""

    container: str = Field(description="Container name or ID")
    tail: int = Field(default=200, description="Number of log lines to fetch")
    filter_pattern: str = Field(
        default="", description="Optional string to filter log lines"
    )


class FetchLogTool(BaseTool):
    """Fetch and optionally filter logs from a Docker container."""

    name: str = "fetch_log"
    description: str = "Fetch and optionally filter logs from a Docker container."
    args_schema: type[BaseModel] = FetchLogInput
    db_path: str = ""
    event_id: str | None = None

    def _run(
        self, container: str, tail: int = 200, filter_pattern: str = "", **_: Any
    ) -> str:
        cmd = ["docker", "logs", "--tail", str(tail), container]
        output = _run_docker(cmd, self.db_path, self.event_id)
        if filter_pattern:
            lines = output.splitlines()
            output = "\n".join(
                line for line in lines if filter_pattern.lower() in line.lower()
            )
        return output
