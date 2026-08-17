"""Execute shell commands with allowlist/denylist safety."""

from __future__ import annotations

import shlex
import subprocess
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.logger import get_logger

logger = get_logger(__name__)

COMMAND_TIMEOUT = 60

# Commands that are always denied for safety
DENIED_COMMANDS = frozenset(
    {
        "rm",
        "rmdir",
        "dd",
        "mkfs",
        "fdisk",
        "format",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "iptables",
        "ip6tables",
        "ufw",
        "passwd",
        "useradd",
        "userdel",
        "usermod",
        "sudo",
        "su",
        "chmod",
        "chown",
        "curl",
        "wget",  # use dedicated HTTP tools
        "ssh",
        "scp",
        "sftp",
    }
)

# Commands that are allowed
ALLOWED_COMMANDS = frozenset(
    {
        "ls",
        "cat",
        "head",
        "tail",
        "grep",
        "find",
        "wc",
        "sort",
        "uniq",
        "echo",
        "pwd",
        "env",
        "printenv",
        "which",
        "type",
        "ps",
        "top",
        "df",
        "du",
        "free",
        "uptime",
        "pip",
        "pip3",
        "uv",
        "npm",
        "yarn",
        "node",
        "python",
        "python3",
        "make",
        "cmake",
        "gcc",
        "g++",
        "systemctl",
        "service",
        "docker",  # docker commands via CommandTool (more flexible than dedicated tools)
        "git",
        "test",
        "true",
        "false",
        "date",
        "id",
        "whoami",
        "hostname",
        "tar",
        "gzip",
        "gunzip",
        "zip",
        "unzip",
        "sed",
        "awk",
        "tr",
        "cut",
        "paste",
        "diff",
        "patch",
        "jq",
        "openssl",
    }
)


def _validate_command(tokens: list[str]) -> str | None:
    """Validate command tokens. Returns error string or None if valid."""
    if not tokens:
        return "ERROR: Empty command"
    base_cmd = tokens[0]
    if base_cmd in DENIED_COMMANDS:
        return f"ERROR: Command '{base_cmd}' is not allowed for safety reasons"
    if base_cmd not in ALLOWED_COMMANDS:
        return f"ERROR: Command '{base_cmd}' is not in the allowed commands list"
    return None


def _execute_command(tokens: list[str], cwd: str, actual_timeout: int) -> str:
    """Execute validated command tokens and return output."""
    base_cmd = tokens[0]
    try:
        result = subprocess.run(
            tokens,
            capture_output=True,
            text=True,
            timeout=actual_timeout,
            cwd=cwd,
            check=False,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr:
            output += f"\nSTDERR: {result.stderr.strip()}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after {actual_timeout}s"
    except FileNotFoundError:
        return f"ERROR: Command not found: {base_cmd}"
    except PermissionError:
        return f"ERROR: Permission denied executing: {base_cmd}"


class CommandInput(BaseModel):
    """Input for CommandTool."""

    command: str = Field(description="Shell command to execute")
    cwd: str = Field(default=".", description="Working directory")
    timeout: int = Field(default=30, description="Timeout in seconds")


class CommandTool(BaseTool):
    """Execute an allowed shell command. Dangerous commands are blocked."""

    name: str = "command"
    description: str = (
        "Execute an allowed shell command. Dangerous commands are blocked."
    )
    args_schema: type[BaseModel] = CommandInput

    def _run(self, command: str, cwd: str = ".", timeout: int = 30, **_: Any) -> str:
        try:
            tokens = shlex.split(command)
        except ValueError as e:
            return f"ERROR: Invalid command syntax: {e}"

        error = _validate_command(tokens)
        if error:
            return error

        actual_timeout = min(timeout, COMMAND_TIMEOUT)
        return _execute_command(tokens, cwd, actual_timeout)
