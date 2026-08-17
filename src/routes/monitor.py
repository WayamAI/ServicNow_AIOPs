"""Monitor control endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from src.config import settings
from src.db import (
    add_monitored_container,
    get_monitored_containers,
    remove_monitored_container,
)
from src.models import AddContainerRequest
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.post("/containers", status_code=201)
async def add_container(
    request: AddContainerRequest,
) -> dict:
    add_monitored_container(
        settings.db_path,
        request.container_name,
        request.image,
        request.expected_status,
    )
    logger.info("container_added_to_monitor", container=request.container_name)
    return {
        "container_name": request.container_name,
        "image": request.image,
        "expected_status": request.expected_status,
        "message": "Container added to monitoring",
    }


@router.delete("/containers/{container_name}", status_code=200)
async def remove_container(container_name: str) -> dict:
    remove_monitored_container(settings.db_path, container_name)
    logger.info("container_removed_from_monitor", container=container_name)
    return {
        "container_name": container_name,
        "message": "Container removed from monitoring",
    }


@router.get("/containers")
async def list_containers() -> list[dict]:
    return get_monitored_containers(settings.db_path)


@router.get("/status")
async def monitor_status() -> dict:
    containers = get_monitored_containers(settings.db_path)
    return {
        "monitored_containers": len(containers),
        "containers": [c["container_name"] for c in containers],
        "status": "running",
    }
