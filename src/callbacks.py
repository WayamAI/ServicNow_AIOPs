"""Base event callback utilities for agent execution tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.logger import get_logger

logger = get_logger(__name__)


def build_event_payload(
    agent_name: str,
    event_type: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Build a standardized event payload dict."""
    return {
        "agent_name": agent_name,
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


def format_tool_event(
    tool_name: str,
    tool_input: str | dict,
    tool_output: str | None = None,
    duration_ms: int | None = None,
    success: bool = True,
) -> dict[str, Any]:
    """Format a tool call/result event payload."""
    payload: dict[str, Any] = {
        "tool_name": tool_name,
        "input": tool_input if isinstance(tool_input, str) else str(tool_input),
    }
    if tool_output is not None:
        payload["output"] = (
            tool_output[:2000] if len(str(tool_output)) > 2000 else tool_output
        )
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    payload["success"] = success
    return payload
