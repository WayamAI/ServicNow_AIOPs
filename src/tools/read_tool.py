"""Read workspace files tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.logger import get_logger

logger = get_logger(__name__)


class ReadFileInput(BaseModel):
    """Input for ReadFileTool."""

    file_path: str = Field(description="Path to the file to read")
    max_lines: int = Field(default=500, description="Maximum number of lines to return")


class ReadFileTool(BaseTool):
    """Read the contents of a workspace file."""

    name: str = "read_file"
    description: str = "Read the contents of a workspace file."
    args_schema: type[BaseModel] = ReadFileInput

    def _run(self, file_path: str, max_lines: int = 500, **_: Any) -> str:
        try:
            path = Path(file_path).resolve()
            workspace = Path(".").resolve()
            # Block path traversal outside workspace
            try:
                path.relative_to(workspace)
            except ValueError:
                return f"ERROR: Access denied: {file_path} is outside the workspace"
            if not path.exists():
                return f"ERROR: File not found: {file_path}"
            if not path.is_file():
                return f"ERROR: Not a file: {file_path}"
            content = path.read_text(encoding="utf-8")
            lines = content.splitlines()
        except PermissionError:
            return f"ERROR: Permission denied: {file_path}"
        except UnicodeDecodeError:
            return f"ERROR: Cannot read binary file: {file_path}"
        else:
            if len(lines) > max_lines:
                truncated = lines[:max_lines]
                truncated.append(
                    f"... (truncated, {len(lines) - max_lines} more lines)"
                )
                return "\n".join(truncated)
            return content
