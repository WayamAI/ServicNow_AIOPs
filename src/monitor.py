"""Docker container monitor — auto-creates incidents for stopped containers."""

from __future__ import annotations

import asyncio
import sqlite3
import subprocess

from src.config import settings
from src.db import (
    create_incident,
    create_session,
    get_monitored_containers,
    list_sessions,
)
from src.logger import get_logger

logger = get_logger(__name__)

_pipeline_tasks: set[asyncio.Task] = set()


def _get_container_status(container_name: str) -> str:
    """Get container status via docker inspect. Returns 'running', 'stopped', or 'unknown'."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return "unknown"
        status = result.stdout.strip().lower()
        if status in ("running",):
            return "running"
        elif status in ("exited", "dead", "removing"):
            return "stopped"
        return status
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return "unknown"


def _has_active_incident(db_path: str, container_name: str) -> bool:
    """Check for active incident for this container using direct SQL."""
    with sqlite3.connect(db_path, check_same_thread=False) as conn:
        row = conn.execute(
            """SELECT COUNT(*) as cnt FROM incidents
               WHERE container_name = ?
               AND status NOT IN ('resolved', 'failed', 'cancelled')""",
            (container_name,),
        ).fetchone()
        return (row[0] if row else 0) > 0


def _get_or_create_monitor_session(db_path: str) -> str:
    """Get the existing monitor session or create one."""
    from src.db import create_project

    sessions = list_sessions(db_path)
    for session in sessions:
        if session.get("config", {}).get("monitor_session"):
            return session["id"]

    # Check for existing monitor project by querying projects table
    with sqlite3.connect(db_path, check_same_thread=False) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT id FROM projects WHERE name = 'monitor' LIMIT 1"
        ).fetchone()
        if row:
            project_id = row["id"]
        else:
            project_id = create_project(
                db_path, "monitor", "Auto-created by Docker monitor"
            )

    session_id = create_session(db_path, project_id, {"monitor_session": True})
    logger.info("monitor_session_created", session_id=session_id)
    return session_id


class DockerMonitor:
    """Monitors Docker containers and creates incidents for failures."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._running = False
        self._known_stopped: set[str] = set()

    async def start(self) -> None:
        """Start the monitoring loop."""
        self._running = True
        logger.info(
            "docker_monitor_started", poll_interval=settings.monitor_poll_interval
        )
        while self._running:
            try:
                await self._poll()
            except Exception:
                logger.exception("docker_monitor_poll_error")
            await asyncio.sleep(settings.monitor_poll_interval)

    def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False
        logger.info("docker_monitor_stopped")

    async def _poll(self) -> None:
        """Poll all monitored containers and create incidents for failures."""
        containers = get_monitored_containers(self.db_path)
        if not containers:
            return

        for container in containers:
            container_name = container["container_name"]
            expected_status = container.get("expected_status", "running")
            actual_status = _get_container_status(container_name)

            if actual_status == expected_status:
                # Container is healthy — clear from known_stopped if it was there
                if container_name in self._known_stopped:
                    self._known_stopped.discard(container_name)
                    logger.info("container_recovered", container=container_name)
                continue

            # Container is not in expected state
            if actual_status == "unknown":
                logger.warning("container_status_unknown", container=container_name)
                continue

            if container_name in self._known_stopped:
                # Already know about this, don't create duplicate incident
                continue

            # Check for existing active incident
            if _has_active_incident(self.db_path, container_name):
                self._known_stopped.add(container_name)
                continue

            # Create new incident
            self._known_stopped.add(container_name)
            await self._create_container_incident(
                container_name, actual_status, expected_status
            )

    async def _create_container_incident(
        self,
        container_name: str,
        actual_status: str,
        expected_status: str,
    ) -> None:
        """Create an incident and trigger the pipeline."""
        from src.db import IncidentData

        session_id = _get_or_create_monitor_session(self.db_path)
        title = f"Container '{container_name}' is {actual_status} (expected: {expected_status})"
        description = (
            f"Docker container '{container_name}' was detected as '{actual_status}' "
            f"during monitoring. Expected status: '{expected_status}'."
        )

        data = IncidentData(
            session_id=session_id,
            title=title,
            description=description,
            container_id=None,
            container_name=container_name,
            severity="high",
        )
        incident_id = create_incident(self.db_path, data)
        logger.info(
            "incident_created_by_monitor",
            incident_id=incident_id,
            container=container_name,
        )

        # Trigger pipeline
        from src.bus import event_bus
        from src.orchestrator import run_incident_pipeline
        from src.ws_callback import SSECallbackHandler

        cb = SSECallbackHandler(
            bus=event_bus,
            session_id=session_id,
            run_id="",
            db_path=self.db_path,
        )
        task = asyncio.create_task(
            run_incident_pipeline(
                incident_id=incident_id,
                session_id=session_id,
                container_name=container_name,
                title=title,
                description=description,
                db_path=self.db_path,
                callback_handler=cb,
            )
        )
        _pipeline_tasks.add(task)
        task.add_done_callback(_pipeline_tasks.discard)


# Global monitor instance
_monitor: DockerMonitor | None = None
_monitor_task: asyncio.Task | None = None


def get_monitor() -> DockerMonitor | None:
    return _monitor


async def start_monitor(db_path: str) -> DockerMonitor:
    """Create and start the Docker monitor as a background task."""
    global _monitor, _monitor_task
    _monitor = DockerMonitor(db_path)
    _monitor_task = asyncio.create_task(_monitor.start())
    return _monitor
