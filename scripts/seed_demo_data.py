"""Seed realistic demo data for the Wayam AIOps dashboard.

Inserts a handful of already-completed incidents (with plausible RCA,
plan, execution, and validation results) directly into the database,
bypassing the live LangGraph pipeline. This lets the dashboard show a
believable mix of resolved/active/failed incidents for a demo even
when no Azure OpenAI credentials are configured — the interactive
"Create Incident" flow still runs the real pipeline end to end.

Usage: uv run python scripts/seed_demo_data.py
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import db
from src.config import settings
from src.db import IncidentData


def iso(dt: datetime) -> str:
    return dt.isoformat()


def seed() -> None:
    db.init_db(settings.db_path)

    sessions = db.list_sessions(settings.db_path)
    active = next((s for s in sessions if s["status"] == "active"), None)
    if not active:
        project_id = db.create_project(settings.db_path, "default", "Default AIOps project")
        session_id = db.create_session(settings.db_path, project_id)
    else:
        session_id = active["id"]

    now = datetime.now(UTC)

    incidents = [
        {
            "title": "Payment gateway container restarting in a loop",
            "description": "payment-gateway has restarted 6 times in the last 10 minutes.",
            "container_name": "payment-gateway",
            "severity": "critical",
            "status": "resolved",
            "created_offset": timedelta(hours=6),
            "rca": {
                "root_cause": "Container exceeded its 512MB memory limit under peak checkout load, triggering OOM kills.",
                "evidence": [
                    "docker logs showed repeated 'Killed' entries with exit code 137",
                    "docker stats showed memory climbing to limit before each restart",
                ],
                "confidence": 0.91,
            },
            "plan": {
                "strategy": "Raise the container memory limit and restart with a clean state.",
                "steps": [
                    "Update memory limit from 512m to 1024m in the compose config",
                    "Restart the payment-gateway container",
                    "Monitor memory usage for 5 minutes post restart",
                ],
            },
            "execution": {
                "actions_taken": [
                    "Updated docker-compose.yml memory limit to 1024m",
                    "Ran docker compose up -d payment-gateway",
                ],
                "exit_code": 0,
            },
            "validation": {
                "passed": True,
                "checks": [
                    {"name": "container_running", "result": "pass"},
                    {"name": "memory_within_limit", "result": "pass"},
                    {"name": "health_endpoint_200", "result": "pass"},
                ],
            },
        },
        {
            "title": "Inventory sync worker unreachable after deploy",
            "description": "inventory-sync-worker health check failing since the 14:02 deploy.",
            "container_name": "inventory-sync-worker",
            "severity": "high",
            "status": "resolved",
            "created_offset": timedelta(hours=3),
            "rca": {
                "root_cause": "New image referenced a database connection string that hadn't been rotated in the secrets store.",
                "evidence": ["Connection refused errors in application logs pointing to the old DB host"],
                "confidence": 0.85,
            },
            "plan": {
                "strategy": "Roll the container's environment configuration back to the last known good secret.",
                "steps": [
                    "Fetch the previous DATABASE_URL from the secrets store",
                    "Recreate the container with the corrected environment variable",
                ],
            },
            "execution": {
                "actions_taken": [
                    "Recreated inventory-sync-worker with corrected DATABASE_URL",
                ],
                "exit_code": 0,
            },
            "validation": {
                "passed": True,
                "checks": [
                    {"name": "container_running", "result": "pass"},
                    {"name": "db_connection", "result": "pass"},
                ],
            },
        },
        {
            "title": "Notification service high memory usage",
            "description": "notification-service memory usage climbing steadily, approaching limit.",
            "container_name": "notification-service",
            "severity": "medium",
            "status": "executing",
            "created_offset": timedelta(minutes=18),
            "rca": {
                "root_cause": "Suspected slow memory leak in the email template cache; usage grows roughly 40MB per hour.",
                "evidence": ["docker stats shows steady upward memory trend over 4 hours with no traffic correlation"],
                "confidence": 0.62,
            },
            "plan": {
                "strategy": "Apply a scheduled restart while the underlying leak is investigated separately.",
                "steps": [
                    "Restart notification-service to reclaim memory",
                    "Flag for a code-level investigation of the template cache",
                ],
            },
            "execution": None,
            "validation": None,
        },
        {
            "title": "Auth service returning intermittent 502s",
            "description": "auth-service health checks flapping between healthy and unhealthy every few minutes.",
            "container_name": "auth-service",
            "severity": "high",
            "status": "failed",
            "created_offset": timedelta(hours=1, minutes=20),
            "rca": {
                "root_cause": "Upstream Redis session store connection pool exhausted under load.",
                "evidence": ["Connection pool timeout errors correlated with 502 spikes"],
                "confidence": 0.71,
            },
            "plan": {
                "strategy": "Increase the Redis connection pool size and restart.",
                "steps": ["Update REDIS_POOL_SIZE from 10 to 25", "Restart auth-service"],
            },
            "execution": {
                "actions_taken": ["Attempted to update REDIS_POOL_SIZE"],
                "error": "Config file was read only in the running container; write failed.",
                "exit_code": 1,
            },
            "validation": {
                "passed": False,
                "checks": [{"name": "container_running", "result": "pass"}, {"name": "health_endpoint_200", "result": "fail"}],
            },
        },
        {
            "title": "Search indexer container stopped unexpectedly",
            "description": "search-indexer container exited with code 1 and did not restart.",
            "container_name": "search-indexer",
            "severity": "low",
            "status": "new",
            "created_offset": timedelta(minutes=4),
            "rca": None,
            "plan": None,
            "execution": None,
            "validation": None,
        },
    ]

    for inc in incidents:
        data = IncidentData(
            session_id=session_id,
            title=inc["title"],
            description=inc["description"],
            container_name=inc["container_name"],
            severity=inc["severity"],
        )
        incident_id = db.create_incident(settings.db_path, data)

        created_at = iso(now - inc["created_offset"])
        db.update_incident(
            settings.db_path,
            incident_id,
            status=inc["status"],
            resolved_at=created_at if inc["status"] == "resolved" else None,
        )
        # created_at/updated_at aren't in the allowed-update set, so backdate directly.
        with db._connect(settings.db_path) as conn:  # noqa: SLF001
            conn.execute(
                "UPDATE incidents SET created_at = ?, updated_at = ? WHERE id = ?",
                (created_at, created_at, incident_id),
            )

        if inc["rca"] is not None or inc["status"] != "new":
            run_id = db.create_run(settings.db_path, incident_id, run_number=1)
            run_status = (
                "completed"
                if inc["status"] == "resolved"
                else "failed"
                if inc["status"] == "failed"
                else "running"
            )
            db.update_run(
                settings.db_path,
                run_id,
                status=run_status,
                rca_result=inc["rca"],
                plan_result=inc["plan"],
                execution_result=inc["execution"],
                validation_result=inc["validation"],
                completed_at=created_at if run_status in ("completed", "failed") else None,
            )

        print(f"Seeded incident: {inc['title']!r} ({inc['status']})")

    containers = [
        ("payment-gateway", "wayam/payment-gateway:2.4.1", "running"),
        ("inventory-sync-worker", "wayam/inventory-sync:1.9.0", "running"),
        ("notification-service", "wayam/notification-service:3.1.0", "running"),
        ("auth-service", "wayam/auth-service:4.0.2", "running"),
        ("search-indexer", "wayam/search-indexer:1.2.3", "running"),
    ]
    for name, image, expected_status in containers:
        db.add_monitored_container(settings.db_path, name, image, expected_status)
        print(f"Seeded monitored container: {name}")

    print("\nDemo data seeded.")


if __name__ == "__main__":
    seed()
