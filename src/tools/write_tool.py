"""Write build config files tool."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.logger import get_logger

logger = get_logger(__name__)

# Allowed file extensions for write operations
ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".cfg",
    ".ini",
    ".conf",
    ".env",
    ".sh",
    ".requirements",
    "dockerfile",  # lowercase - name check is now lowercased
}


class WriteFileInput(BaseModel):
    """Input for WriteFileTool."""

    file_path: str = Field(description="Path to write the file")
    content: str = Field(description="Content to write")
    create_dirs: bool = Field(
        default=True, description="Create parent directories if needed"
    )


class WriteFileTool(BaseTool):
    """Write content to a build config file."""

    name: str = "write_file"
    description: str = (
        "Write content to a build config file. Only allowed file types can be written."
    )
    args_schema: type[BaseModel] = WriteFileInput

    def _run(
        self, file_path: str, content: str, create_dirs: bool = True, **_: Any
    ) -> str:  # noqa: FBT001, FBT002
        try:
            path = Path(file_path).resolve()
            workspace = Path(".").resolve()
            try:
                path.relative_to(workspace)
            except ValueError:
                return f"ERROR: Access denied: {file_path} is outside the workspace"
            suffix = path.suffix.lower()
            name = path.name.lower()  # lowercase for consistent matching
            if suffix not in ALLOWED_EXTENSIONS and name not in ALLOWED_EXTENSIONS:
                return f"ERROR: Writing to {suffix or name} files is not allowed"
            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except PermissionError:
            return f"ERROR: Permission denied: {file_path}"
        except OSError as e:
            return f"ERROR: Failed to write file: {e}"
        else:
            return f"Successfully wrote {len(content)} characters to {file_path}"
