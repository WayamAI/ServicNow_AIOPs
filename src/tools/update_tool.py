"""Update dependencies in requirements files tool."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.logger import get_logger

logger = get_logger(__name__)

ALLOWED_REQUIREMENTS_EXTENSIONS = {".txt", ".toml", ".cfg", ".ini"}


class UpdateDepsInput(BaseModel):
    """Input for UpdateDepsTool."""

    file_path: str = Field(
        description="Path to requirements file (requirements.txt, pyproject.toml)"
    )
    package: str = Field(description="Package name to update")
    version: str = Field(
        description="New version constraint (e.g. '>=1.2.0' or '==1.2.3')"
    )


class UpdateDepsTool(BaseTool):
    """Update a package version constraint in a requirements file."""

    name: str = "update_deps"
    description: str = "Update a package version constraint in a requirements file."
    args_schema: type[BaseModel] = UpdateDepsInput

    def _run(self, file_path: str, package: str, version: str, **_: Any) -> str:
        try:
            path = Path(file_path).resolve()
            workspace = Path(".").resolve()
            try:
                path.relative_to(workspace)
            except ValueError:
                return f"ERROR: Access denied: {file_path} is outside the workspace"
            if path.suffix.lower() not in ALLOWED_REQUIREMENTS_EXTENSIONS:
                return (
                    f"ERROR: Only requirements/config files "
                    f"({', '.join(sorted(ALLOWED_REQUIREMENTS_EXTENSIONS))}) are supported"
                )
            if not path.exists():
                return f"ERROR: File not found: {file_path}"
            content = path.read_text(encoding="utf-8")
            # Match package with optional version specifier
            pattern = re.compile(
                rf"^({re.escape(package)})\s*([><=!~^][^\s,\n]*)?",
                re.IGNORECASE | re.MULTILINE,
            )
            if not pattern.search(content):
                return f"Package '{package}' not found in {file_path}"
            new_content = pattern.sub(rf"\1{version}", content)
            path.write_text(new_content, encoding="utf-8")
        except PermissionError:
            return f"ERROR: Permission denied: {file_path}"
        except OSError as e:
            return f"ERROR: Failed to update file: {e}"
        else:
            return f"Updated {package}{version} in {file_path}"
