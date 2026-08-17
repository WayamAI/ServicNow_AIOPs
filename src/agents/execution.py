"""Execution agent using Codestral."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.agents.base import BaseAgent
from src.config import settings
from src.prompts.agent_prompts import EXECUTION_HUMAN_PROMPT, EXECUTION_SYSTEM_PROMPT
from src.tools.command_tool import CommandTool
from src.tools.docker_tools import DockerRestartTool, DockerStartTool, DockerStopTool
from src.tools.git_tools import (
    GitAddTool,
    GitCheckoutTool,
    GitCommitTool,
    GitPullTool,
    GitPushTool,
)
from src.tools.read_tool import ReadFileTool
from src.tools.update_tool import UpdateDepsTool
from src.tools.write_tool import WriteFileTool

if TYPE_CHECKING:
    from langchain_core.callbacks import BaseCallbackHandler


class ExecutionAgent(BaseAgent):
    """Execution agent — executes remediation plan steps."""

    name = "execution"
    system_prompt = EXECUTION_SYSTEM_PROMPT

    @property
    def model_name(self) -> str:
        return settings.codestral_deployment

    def __init__(
        self, db_path: str, callback_handler: BaseCallbackHandler | None = None
    ) -> None:
        super().__init__(db_path, callback_handler)
        self._tools = [
            DockerStartTool(db_path=db_path),
            DockerRestartTool(db_path=db_path),
            DockerStopTool(db_path=db_path),
            CommandTool(),
            GitPullTool(),
            GitAddTool(),
            GitCommitTool(),
            GitCheckoutTool(),
            GitPushTool(),
            WriteFileTool(),
            UpdateDepsTool(),
            ReadFileTool(),
        ]

    @property
    def tools(self):
        return self._tools

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        plan_result = state.get("plan_result") or {}
        incident_details = (
            f"Title: {state.get('title', 'Unknown')}\n"
            f"Description: {state.get('description', '')}\n"
            f"Container: {state.get('container_name', 'unknown')}"
        )
        input_vars = {
            "plan_result": json.dumps(plan_result, indent=2),
            "incident_details": incident_details,
        }
        raw = self._invoke_with_tools(EXECUTION_HUMAN_PROMPT, input_vars)
        return self._parse_json_response(raw)
