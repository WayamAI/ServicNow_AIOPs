"""Base agent with shared LangGraph node logic."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent

from src.config import settings
from src.logger import get_logger

if TYPE_CHECKING:
    from langchain_core.callbacks import BaseCallbackHandler

logger = get_logger(__name__)


class BaseAgent(ABC):
    """Base agent wrapping AzureChatOpenAI with tool calling."""

    name: str
    model_name: str
    system_prompt: str

    def __init__(
        self,
        db_path: str,
        callback_handler: BaseCallbackHandler | None = None,
    ) -> None:
        self.db_path = db_path
        self.callback_handler = callback_handler
        callbacks = [callback_handler] if callback_handler else []
        self.llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            azure_deployment=self.model_name,
            api_version=settings.azure_openai_api_version,
            temperature=0,
            callbacks=callbacks,
        )

    @property
    def tools(self) -> list[BaseTool]:
        """Return tools for this agent. Override in subclasses."""
        return []

    def _build_prompt(self, human_template: str) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                ("human", human_template),
            ]
        )

    def _invoke_with_tools(
        self, human_template: str, input_vars: dict[str, Any]
    ) -> str:
        """Invoke LLM with tools bound, return string response."""
        agent_tools = self.tools
        if agent_tools:
            # Build the human message text by formatting the template
            human_text = human_template.format(**input_vars)
            graph = create_react_agent(
                self.llm,
                agent_tools,
                prompt=self.system_prompt,
            )
            result = graph.invoke(
                {"messages": [HumanMessage(content=human_text)]},
                config={"recursion_limit": settings.max_tool_iterations * 2 + 1},
            )
            # Last message is the final AI response
            messages = result.get("messages", [])
            for msg in reversed(messages):
                if hasattr(msg, "content") and not getattr(msg, "tool_calls", None):
                    content = msg.content
                    if isinstance(content, list):
                        # Extract text from content blocks (multimodal)
                        parts = []
                        for block in content:
                            if isinstance(block, dict):
                                parts.append(block.get("text", ""))
                            elif isinstance(block, str):
                                parts.append(block)
                        return " ".join(parts)
                    return str(content)
            return ""
        # No tools — direct LLM call
        prompt = self._build_prompt(human_template)
        chain = prompt | self.llm
        response = chain.invoke(input_vars)
        return str(response.content)

    def _parse_json_response(self, text: str) -> dict[str, Any]:
        """Extract and parse JSON from LLM response text."""
        # Try direct parse first
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {"result": parsed}
        except json.JSONDecodeError:
            pass

        # Try to extract JSON block from markdown fences
        patterns = [
            r"```json\s*(.*?)\s*```",
            r"```\s*(.*?)\s*```",
            r"\{.*\}",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(
                        match.group(1) if "```" in pattern else match.group(0)
                    )
                except json.JSONDecodeError:
                    continue

        # Return raw text in a wrapper if all parsing fails
        logger.warning("failed_to_parse_json", agent=self.name, text_preview=text[:200])
        return {"raw_response": text, "parse_error": True}

    @abstractmethod
    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the agent on the current incident state. Return result dict."""
