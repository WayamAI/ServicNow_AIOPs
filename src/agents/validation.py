"""Validation agent using GPT-4o-mini."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.agents.base import BaseAgent
from src.config import settings
from src.prompts.agent_prompts import VALIDATION_HUMAN_PROMPT, VALIDATION_SYSTEM_PROMPT
from src.tools.docker_tools import (
    DockerInspectTool,
    DockerLogsTool,
    DockerPsTool,
    DockerStatsTool,
)

if TYPE_CHECKING:
    from langchain_core.callbacks import BaseCallbackHandler


class ValidationAgent(BaseAgent):
    """Validation agent — verifies incident resolution."""

    name = "validation"
    system_prompt = VALIDATION_SYSTEM_PROMPT

    @property
    def model_name(self) -> str:
        return settings.gpt4o_mini_deployment

    def __init__(
        self, db_path: str, callback_handler: BaseCallbackHandler | None = None
    ) -> None:
        super().__init__(db_path, callback_handler)
        self._tools = [
            DockerPsTool(db_path=db_path),
            DockerLogsTool(db_path=db_path),
            DockerInspectTool(db_path=db_path),
            DockerStatsTool(db_path=db_path),
        ]

    @property
    def tools(self):
        return self._tools

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        execution_result = state.get("execution_result") or {}
        incident_details = (
            f"Title: {state.get('title', 'Unknown')}\n"
            f"Description: {state.get('description', '')}\n"
            f"Container: {state.get('container_name', 'unknown')}"
        )
        input_vars = {
            "execution_result": json.dumps(execution_result, indent=2),
            "incident_details": incident_details,
        }
        raw = self._invoke_with_tools(VALIDATION_HUMAN_PROMPT, input_vars)
        return self._parse_json_response(raw)
