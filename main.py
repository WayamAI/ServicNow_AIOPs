"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.bus import event_bus
from src.config import settings
from src.db import create_project, init_db
from src.errors import AIOpsError
from src.logger import get_logger, setup_logging
from src.monitor import start_monitor
from src.routes import control, incidents, monitor, sessions, stream

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    logger.info("aiops_server_starting", host=settings.host, port=settings.port)
    init_db(settings.db_path)

    # Create default project
    project_id = create_project(settings.db_path, "default", "Default AIOPs project")
    sessions.set_default_project_id(project_id)

    # Set event loop on the event bus for thread-safe publishing
    event_bus.set_loop(asyncio.get_running_loop())

    await start_monitor(settings.db_path)
    logger.info("docker_monitor_started_background")

    logger.info("aiops_server_ready", db_path=settings.db_path, project_id=project_id)

    yield

    # Shutdown
    logger.info("aiops_server_stopping")
    from src.monitor import get_monitor

    monitor = get_monitor()
    if monitor:
        monitor.stop()


app = FastAPI(
    title="AIOPs Agent Server",
    description="Automated Docker container incident detection, diagnosis, and remediation",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(AIOpsError)
async def aiops_error_handler(request: Request, exc: AIOpsError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


# Mount routers
app.include_router(sessions.router)
app.include_router(incidents.router)
app.include_router(stream.router)
app.include_router(control.router)
app.include_router(monitor.router)


@app.get("/incidents/{incident_id}/report")
async def get_incident_report(incident_id: str) -> dict:
    from src.reporter import generate_report

    return generate_report(settings.db_path, incident_id)


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
