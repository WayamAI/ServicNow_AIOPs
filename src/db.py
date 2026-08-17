import contextlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with _connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                config TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                container_id TEXT,
                container_name TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                severity TEXT DEFAULT 'medium',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                incident_id TEXT NOT NULL,
                run_number INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'running',
                rca_result TEXT,
                plan_result TEXT,
                execution_result TEXT,
                validation_result TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (incident_id) REFERENCES incidents(id)
            );

            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            );

            CREATE TABLE IF NOT EXISTS tool_timings (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                success INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events(id)
            );

            CREATE TABLE IF NOT EXISTS monitored_containers (
                container_name TEXT PRIMARY KEY,
                image TEXT,
                expected_status TEXT DEFAULT 'running',
                added_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id);
            CREATE INDEX IF NOT EXISTS idx_incidents_session ON incidents(session_id);
            CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
            CREATE INDEX IF NOT EXISTS idx_runs_incident ON runs(incident_id);
            CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
            CREATE INDEX IF NOT EXISTS idx_tool_timings_event ON tool_timings(event_id);
        """)


# --- Projects ---


def create_project(db_path: str, name: str, description: str = "") -> str:
    project_id = str(uuid.uuid4())
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO projects (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, name, description, now, now),
        )
    return project_id


def get_project(db_path: str, project_id: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    return dict(row) if row else None


# --- Sessions ---


def create_session(db_path: str, project_id: str, config: dict | None = None) -> str:
    session_id = str(uuid.uuid4())
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO sessions (id, project_id, status, config, created_at, updated_at) VALUES (?, ?, 'active', ?, ?, ?)",
            (session_id, project_id, json.dumps(config or {}), now, now),
        )
    return session_id


def get_session(db_path: str, session_id: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["config"] = json.loads(d["config"] or "{}")
    return d


_SESSION_ALLOWED_FIELDS = frozenset({"status", "config", "updated_at"})
_INCIDENT_ALLOWED_FIELDS = frozenset(
    {
        "status",
        "severity",
        "resolved_at",
        "updated_at",
        "container_id",
        "container_name",
    },
)
_RUN_ALLOWED_FIELDS = frozenset(
    {
        "status",
        "rca_result",
        "plan_result",
        "execution_result",
        "validation_result",
        "completed_at",
    },
)


def _build_update(allowed: frozenset[str], fields: dict) -> tuple[str, list]:
    unknown = set(fields) - allowed
    if unknown:
        msg = f"Unknown update fields: {unknown}"
        raise ValueError(msg)
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    return set_clause, list(fields.values())


def update_session(db_path: str, session_id: str, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    if "config" in fields and isinstance(fields["config"], dict):
        fields["config"] = json.dumps(fields["config"])
    set_clause, values = _build_update(_SESSION_ALLOWED_FIELDS, fields)
    with _connect(db_path) as conn:
        conn.execute(
            f"UPDATE sessions SET {set_clause} WHERE id = ?",  # noqa: S608
            [*values, session_id],
        )


def list_sessions(db_path: str, project_id: str | None = None) -> list[dict]:
    with _connect(db_path) as conn:
        if project_id:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE project_id = ? ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC",
            ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["config"] = json.loads(d["config"] or "{}")
        result.append(d)
    return result


# --- Incidents ---


@dataclass
class IncidentData:
    session_id: str
    title: str
    description: str
    container_id: str | None = None
    container_name: str | None = None
    severity: str = "medium"


def create_incident(db_path: str, data: IncidentData) -> str:
    incident_id = str(uuid.uuid4())
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO incidents
               (id, session_id, title, description, container_id, container_name, status, severity, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'new', ?, ?, ?)""",
            (
                incident_id,
                data.session_id,
                data.title,
                data.description,
                data.container_id,
                data.container_name,
                data.severity,
                now,
                now,
            ),
        )
    return incident_id


def get_incident(db_path: str, incident_id: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM incidents WHERE id = ?",
            (incident_id,),
        ).fetchone()
    return dict(row) if row else None


def update_incident(db_path: str, incident_id: str, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = _now()
    set_clause, values = _build_update(_INCIDENT_ALLOWED_FIELDS, fields)
    with _connect(db_path) as conn:
        conn.execute(
            f"UPDATE incidents SET {set_clause} WHERE id = ?",  # noqa: S608
            [*values, incident_id],
        )


def list_incidents(
    db_path: str,
    session_id: str,
    status_filter: str | None = None,
) -> list[dict]:
    with _connect(db_path) as conn:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM incidents WHERE session_id = ? AND status = ? ORDER BY created_at DESC",
                (session_id, status_filter),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM incidents WHERE session_id = ? ORDER BY created_at DESC",
                (session_id,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_new_incidents(db_path: str) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM incidents WHERE status = 'new' ORDER BY created_at ASC",
        ).fetchall()
    return [dict(r) for r in rows]


# --- Runs ---


def create_run(db_path: str, incident_id: str, run_number: int = 1) -> str:
    run_id = str(uuid.uuid4())
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO runs (id, incident_id, run_number, status, started_at) VALUES (?, ?, ?, 'running', ?)",
            (run_id, incident_id, run_number, now),
        )
    return run_id


def update_run(db_path: str, run_id: str, **fields) -> None:
    if not fields:
        return
    for key in ("rca_result", "plan_result", "execution_result", "validation_result"):
        if key in fields and isinstance(fields[key], dict):
            fields[key] = json.dumps(fields[key])
    set_clause, values = _build_update(_RUN_ALLOWED_FIELDS, fields)
    with _connect(db_path) as conn:
        conn.execute(
            f"UPDATE runs SET {set_clause} WHERE id = ?",  # noqa: S608
            [*values, run_id],
        )


def _decode_run_json(d: dict) -> dict:
    for key in ("rca_result", "plan_result", "execution_result", "validation_result"):
        if d.get(key):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                d[key] = json.loads(d[key])
    return d


def get_run(db_path: str, run_id: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        return None
    return _decode_run_json(dict(row))


def list_runs(db_path: str, incident_id: str) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM runs WHERE incident_id = ? ORDER BY run_number ASC",
            (incident_id,),
        ).fetchall()
    return [_decode_run_json(dict(row)) for row in rows]


# --- Events ---


def create_event(
    db_path: str,
    run_id: str,
    agent_name: str,
    event_type: str,
    payload: dict,
) -> str:
    event_id = str(uuid.uuid4())
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO events (id, run_id, agent_name, event_type, payload, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (event_id, run_id, agent_name, event_type, json.dumps(payload), now),
        )
    return event_id


def list_events(db_path: str, run_id: str, after_id: str | None = None) -> list[dict]:
    with _connect(db_path) as conn:
        if after_id:
            rows = conn.execute(
                """SELECT * FROM events WHERE run_id = ?
                   AND rowid > (SELECT rowid FROM events WHERE id = ?)
                   ORDER BY rowid ASC""",
                (run_id, after_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY rowid ASC",
                (run_id,),
            ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            d["payload"] = json.loads(d["payload"])
        result.append(d)
    return result


# --- Tool Timings ---


def record_tool_timing(
    db_path: str,
    event_id: str,
    tool_name: str,
    duration_ms: int,
    *,
    success: bool = True,
) -> None:
    timing_id = str(uuid.uuid4())
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO tool_timings (id, event_id, tool_name, duration_ms, success, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (timing_id, event_id, tool_name, duration_ms, 1 if success else 0, now),
        )


def get_tool_timings(db_path: str, run_id: str) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            """SELECT tt.* FROM tool_timings tt
               JOIN events e ON tt.event_id = e.id
               WHERE e.run_id = ?
               ORDER BY tt.created_at ASC""",
            (run_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# --- Monitored Containers ---


def add_monitored_container(
    db_path: str,
    container_name: str,
    image: str = "",
    expected_status: str = "running",
) -> None:
    now = _now()
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO monitored_containers (container_name, image, expected_status, added_at)
               VALUES (?, ?, ?, ?)""",
            (container_name, image, expected_status, now),
        )


def remove_monitored_container(db_path: str, container_name: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "DELETE FROM monitored_containers WHERE container_name = ?",
            (container_name,),
        )


def get_monitored_containers(db_path: str) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM monitored_containers").fetchall()
    return [dict(r) for r in rows]
