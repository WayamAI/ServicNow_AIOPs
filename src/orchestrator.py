"""LangGraph orchestrator — incident remediation pipeline."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from src.agents.execution import ExecutionAgent
from src.agents.plan import PlanAgent
from src.agents.rca import RCAAgent
from src.agents.validation import ValidationAgent
from src.config import settings
from src.db import (
    create_run,
    update_incident,
    update_run,
)
from src.errors import RunCancelledError
from src.logger import get_logger

logger = get_logger(__name__)


class IncidentState(TypedDict):
    """LangGraph state for the incident remediation pipeline."""

    incident_id: str
    session_id: str
    run_id: str
    container_name: str
    container_id: str | None
    title: str
    description: str
    rca_result: dict[str, Any] | None
    plan_result: dict[str, Any] | None
    execution_result: dict[str, Any] | None
    validation_result: dict[str, Any] | None
    retry_count: int
    max_retries: int
    status: str
    db_path: str
    callback_handler: Any  # SSECallbackHandler


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_cancelled(state: IncidentState) -> None:
    cb = state.get("callback_handler")
    if cb and cb.is_cancelled:
        raise RunCancelledError(f"Run {state['run_id']} was cancelled")


# --- Graph Nodes ---


def rca_node(state: IncidentState) -> dict[str, Any]:
    """Run Root Cause Analysis."""
    _check_cancelled(state)
    logger.info("rca_node_start", incident_id=state["incident_id"])
    update_incident(state["db_path"], state["incident_id"], status="rca")

    cb = state.get("callback_handler")
    if cb:
        cb.agent_name = "rca"
    agent = RCAAgent(db_path=state["db_path"], callback_handler=cb)

    try:
        result = agent.run(state)
    except RunCancelledError:
        raise
    except Exception as e:
        logger.exception("rca_node_error", incident_id=state["incident_id"])
        result = {"error": str(e), "root_cause": "unknown", "confidence": 0.0}

    update_run(state["db_path"], state["run_id"], rca_result=result)
    logger.info("rca_node_complete", incident_id=state["incident_id"])
    return {"rca_result": result, "status": "rca_complete"}


def plan_node(state: IncidentState) -> dict[str, Any]:
    """Create remediation plan."""
    _check_cancelled(state)
    logger.info("plan_node_start", incident_id=state["incident_id"])
    update_incident(state["db_path"], state["incident_id"], status="planned")

    cb = state.get("callback_handler")
    if cb:
        cb.agent_name = "plan"
    agent = PlanAgent(db_path=state["db_path"], callback_handler=cb)

    try:
        result = agent.run(state)
    except RunCancelledError:
        raise
    except Exception as e:
        logger.exception("plan_node_error", incident_id=state["incident_id"])
        result = {"error": str(e), "steps": []}

    update_run(state["db_path"], state["run_id"], plan_result=result)
    logger.info("plan_node_complete", incident_id=state["incident_id"])
    return {"plan_result": result, "status": "plan_complete"}


def execution_node(state: IncidentState) -> dict[str, Any]:
    """Execute remediation plan."""
    _check_cancelled(state)
    logger.info("execution_node_start", incident_id=state["incident_id"])
    update_incident(state["db_path"], state["incident_id"], status="executing")

    cb = state.get("callback_handler")
    if cb:
        cb.agent_name = "execution"
    agent = ExecutionAgent(db_path=state["db_path"], callback_handler=cb)

    try:
        result = agent.run(state)
    except RunCancelledError:
        raise
    except Exception as e:
        logger.exception("execution_node_error", incident_id=state["incident_id"])
        result = {"error": str(e), "overall_success": False, "executed_steps": []}

    update_run(state["db_path"], state["run_id"], execution_result=result)
    logger.info("execution_node_complete", incident_id=state["incident_id"])
    return {"execution_result": result, "status": "execution_complete"}


def validation_node(state: IncidentState) -> dict[str, Any]:
    """Validate incident resolution."""
    _check_cancelled(state)
    logger.info("validation_node_start", incident_id=state["incident_id"])
    update_incident(state["db_path"], state["incident_id"], status="validating")

    cb = state.get("callback_handler")
    if cb:
        cb.agent_name = "validation"
    agent = ValidationAgent(db_path=state["db_path"], callback_handler=cb)

    try:
        result = agent.run(state)
    except RunCancelledError:
        raise
    except Exception as e:
        logger.exception("validation_node_error", incident_id=state["incident_id"])
        result = {"error": str(e), "validated": False}

    update_run(state["db_path"], state["run_id"], validation_result=result)
    logger.info("validation_node_complete", incident_id=state["incident_id"])

    # Increment retry_count so decide_next sees a moving counter
    return {
        "validation_result": result,
        "status": "validation_complete",
        "retry_count": state.get("retry_count", 0) + 1,
    }


def resolved_node(state: IncidentState) -> dict[str, Any]:
    """Mark incident as resolved."""
    logger.info("incident_resolved", incident_id=state["incident_id"])
    update_incident(
        state["db_path"],
        state["incident_id"],
        status="resolved",
        resolved_at=_now(),
    )
    update_run(
        state["db_path"],
        state["run_id"],
        status="completed",
        completed_at=_now(),
    )
    cb = state.get("callback_handler")
    if cb:
        cb._publish("agent_response", {"message": "Incident resolved successfully"})
    return {"status": "resolved"}


def failed_node(state: IncidentState) -> dict[str, Any]:
    """Mark incident as failed (max retries exhausted)."""
    logger.info("incident_failed", incident_id=state["incident_id"])
    update_incident(state["db_path"], state["incident_id"], status="failed")
    update_run(
        state["db_path"],
        state["run_id"],
        status="failed",
        completed_at=_now(),
    )
    cb = state.get("callback_handler")
    if cb:
        cb._publish("error", {"message": "Incident failed after max retries"})
    return {"status": "failed"}


def cancelled_node(state: IncidentState) -> dict[str, Any]:
    """Mark run and incident as cancelled."""
    logger.info("incident_cancelled", incident_id=state["incident_id"])
    update_incident(state["db_path"], state["incident_id"], status="cancelled")
    update_run(
        state["db_path"],
        state["run_id"],
        status="cancelled",
        completed_at=_now(),
    )
    return {"status": "cancelled"}


# --- Conditional Edge ---


def decide_next(state: IncidentState) -> str:
    """Route after validation: resolved, retry, or failed."""
    cb = state.get("callback_handler")
    if cb and cb.is_cancelled:
        return "cancelled"

    val = state.get("validation_result") or {}
    if val.get("validated"):
        return "resolved"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", settings.max_incident_retries)
    if retry_count >= max_retries:
        return "failed"

    return "retry"


# --- Build Graph ---


def build_graph() -> StateGraph:
    """Build and compile the incident remediation LangGraph."""
    graph = StateGraph(IncidentState)

    # Add nodes
    graph.add_node("rca", rca_node)
    graph.add_node("plan", plan_node)
    graph.add_node("execution", execution_node)
    graph.add_node("validation", validation_node)
    graph.add_node("resolved", resolved_node)
    graph.add_node("failed", failed_node)
    graph.add_node("cancelled", cancelled_node)

    # Linear pipeline
    graph.add_edge(START, "rca")
    graph.add_edge("rca", "plan")
    graph.add_edge("plan", "execution")
    graph.add_edge("execution", "validation")

    # Conditional routing after validation
    graph.add_conditional_edges(
        "validation",
        decide_next,
        {
            "resolved": "resolved",
            "failed": "failed",
            "cancelled": "cancelled",
            "retry": "rca",  # Retry from RCA
        },
    )

    # Terminal nodes
    graph.add_edge("resolved", END)
    graph.add_edge("failed", END)
    graph.add_edge("cancelled", END)

    return graph.compile()


# Compiled graph singleton
incident_graph = build_graph()


# --- Public API ---


async def run_incident_pipeline(
    incident_id: str,
    session_id: str,
    container_name: str,
    title: str,
    description: str,
    db_path: str,
    callback_handler: Any,
    container_id: str | None = None,
    max_retries: int | None = None,
) -> dict[str, Any]:
    """Run the full incident remediation pipeline asynchronously.

    Creates a run record, invokes the LangGraph pipeline, and returns the final state.
    """
    from src.state import RetryState

    from src.run_registry import register_run

    retry_state = RetryState(db_path)
    run_number = retry_state.increment_retry(incident_id)
    run_id = create_run(db_path, incident_id, run_number)

    if callback_handler:
        callback_handler.run_id = run_id
        register_run(run_id, callback_handler)

    initial_state: IncidentState = {
        "incident_id": incident_id,
        "session_id": session_id,
        "run_id": run_id,
        "container_name": container_name,
        "container_id": container_id,
        "title": title,
        "description": description,
        "rca_result": None,
        "plan_result": None,
        "execution_result": None,
        "validation_result": None,
        "retry_count": retry_state.get_retry_count(incident_id),
        "max_retries": (
            max_retries if max_retries is not None else settings.max_incident_retries
        ),
        "status": "running",
        "db_path": db_path,
        "callback_handler": callback_handler,
    }

    logger.info(
        "pipeline_start", incident_id=incident_id, run_id=run_id, run_number=run_number
    )

    try:
        # LangGraph invoke is synchronous — run in thread pool to not block event loop
        loop = asyncio.get_running_loop()
        final_state = await loop.run_in_executor(
            None,
            lambda: incident_graph.invoke(initial_state),
        )
    except RunCancelledError:
        update_run(db_path, run_id, status="cancelled", completed_at=_now())
        return {"status": "cancelled", "run_id": run_id}
    except Exception as e:
        logger.exception("pipeline_error", incident_id=incident_id, run_id=run_id)
        update_run(db_path, run_id, status="failed", completed_at=_now())
        update_incident(db_path, incident_id, status="failed")
        return {"status": "failed", "run_id": run_id, "error": str(e)}

    logger.info(
        "pipeline_complete",
        incident_id=incident_id,
        run_id=run_id,
        status=final_state.get("status"),
    )
    return dict(final_state)
