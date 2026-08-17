"""Plan agent using GPT-4o-mini."""

from __future__ import annotations

import json
from typing import Any

from src.agents.base import BaseAgent
from src.config import settings
from src.prompts.agent_prompts import PLAN_HUMAN_PROMPT, PLAN_SYSTEM_PROMPT


class PlanAgent(BaseAgent):
    """Plan agent — creates remediation plan from RCA findings."""

    name = "plan"
    system_prompt = PLAN_SYSTEM_PROMPT

    @property
    def model_name(self) -> str:
        return settings.gpt4o_mini_deployment

    @property
    def tools(self):
        return []

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        rca_result = state.get("rca_result") or {}
        incident_details = (
            f"Title: {state.get('title', 'Unknown')}\n"
            f"Description: {state.get('description', '')}\n"
            f"Container: {state.get('container_name', 'unknown')}"
        )
        input_vars = {
            "rca_result": json.dumps(rca_result, indent=2),
            "incident_details": incident_details,
        }
        raw = self._invoke_with_tools(PLAN_HUMAN_PROMPT, input_vars)
        return self._parse_json_response(raw)
