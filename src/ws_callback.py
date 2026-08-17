"""SSE callback handler — publishes LangChain events via EventBus."""

from __future__ import annotations

import threading
import time
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from src.callbacks import build_event_payload, format_tool_event
from src.db import create_event
from src.errors import RunCancelledError
from src.logger import get_logger

logger = get_logger(__name__)


class SSECallbackHandler(BaseCallbackHandler):
    """LangChain callback that persists events to DB and publishes via EventBus."""

    def __init__(
        self,
        bus: Any,  # EventBus — Any to avoid circular import
        session_id: str,
        run_id: str,
        db_path: str,
        agent_name: str = "unknown",
    ) -> None:
        super().__init__()
        self.bus = bus
        self.session_id = session_id
        self.run_id = run_id
        self.db_path = db_path
        self.agent_name = agent_name
        self._cancelled = False
        self._tool_start_times: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """Mark this run as cancelled. Agents check this flag between steps."""
        self._cancelled = True
        logger.info("run_cancelled", run_id=self.run_id, session_id=self.session_id)

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def _check_cancelled(self) -> None:
        if self._cancelled:
            raise RunCancelledError(f"Run {self.run_id} was cancelled")

    def _publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Persist event to DB and publish to EventBus."""
        payload = build_event_payload(self.agent_name, event_type, data)
        payload["event_type"] = event_type
        if self.run_id:  # Only persist to DB when run_id is set
            try:
                event_id = create_event(
                    self.db_path,
                    self.run_id,
                    self.agent_name,
                    event_type,
                    payload,
                )
                payload["event_id"] = event_id
            except Exception:
                logger.exception("failed_to_persist_event", event_type=event_type)
        self.bus.publish(self.session_id, payload)

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._check_cancelled()
        self._publish(
            "agent_start",
            {
                "model": serialized.get("name", "unknown"),
                "prompt_count": len(prompts),
            },
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._check_cancelled()
        generations = response.generations
        text = ""
        if generations and generations[0]:
            gen = generations[0][0]
            text = getattr(gen, "text", str(gen))
        self._publish(
            "agent_response",
            {
                "response_preview": text[:500] if text else "",
                "generation_count": len(generations),
            },
        )

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._check_cancelled()
        tool_name = serialized.get("name", "unknown")
        with self._lock:
            self._tool_start_times[str(run_id)] = (time.monotonic(), tool_name)
        self._publish("tool_call", format_tool_event(tool_name, input_str))

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        with self._lock:
            start_data = self._tool_start_times.pop(str(run_id), None)
        start_time, tool_name = start_data if start_data else (None, "unknown")
        duration_ms = (
            int((time.monotonic() - start_time) * 1000) if start_time else None
        )
        output_str = str(output)

        self._publish(
            "tool_result",
            format_tool_event(
                tool_name,
                "",
                tool_output=output_str,
                duration_ms=duration_ms,
                success=not output_str.startswith("ERROR"),
            ),
        )

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._publish(
            "error",
            {
                "error_type": type(error).__name__,
                "message": str(error)[:500],
            },
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        tool_name = kwargs.get("name", "unknown")
        with self._lock:
            self._tool_start_times.pop(str(run_id), None)
        self._publish(
            "error",
            {
                "error_type": type(error).__name__,
                "tool_name": tool_name,
                "message": str(error)[:500],
            },
        )
