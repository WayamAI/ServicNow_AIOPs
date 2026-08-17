"""Root Cause Analysis agent using Codestral."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.agents.base import BaseAgent
from src.config import settings
from src.prompts.agent_prompts import RCA_HUMAN_PROMPT, RCA_SYSTEM_PROMPT
from src.tools.docker_tools import (
    DockerInspectTool,
    DockerLogsTool,
    DockerPsTool,
    DockerStatsTool,
    FetchLogTool,
)
from src.tools.read_tool import ReadFileTool

if TYPE_CHECKING:
    from langchain_core.callbacks import BaseCallbackHandler


class RCAAgent(BaseAgent):
    """Root Cause Analysis agent — investigates container failures."""

    name = "rca"
    system_prompt = RCA_SYSTEM_PROMPT

    @property
    def model_name(self) -> str:
        return settings.codestral_deployment

    def __init__(
        self, db_path: str, callback_handler: BaseCallbackHandler | None = None
    ) -> None:
        super().__init__(db_path, callback_handler)
        self._tools = [
            DockerPsTool(db_path=db_path),
            DockerLogsTool(db_path=db_path),
            DockerInspectTool(db_path=db_path),
            DockerStatsTool(db_path=db_path),
            FetchLogTool(db_path=db_path),
            ReadFileTool(),
        ]

    @property
    def tools(self):
        return self._tools

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        input_vars = {
            "title": state.get("title", "Unknown incident"),
            "description": state.get("description", ""),
            "container_name": state.get("container_name", "unknown"),
            "container_id": state.get("container_id") or "unknown",
        }
        raw = self._invoke_with_tools(RCA_HUMAN_PROMPT, input_vars)
        return self._parse_json_response(raw)
