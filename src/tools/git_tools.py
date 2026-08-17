"""Git LangChain tools wrapping subprocess git CLI calls."""

from __future__ import annotations

import subprocess
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.logger import get_logger

logger = get_logger(__name__)

GIT_TIMEOUT = 60


def _run_cmd(cmd: list[str], cwd: str | None = None) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            cwd=cwd,
            check=False,
        )
        if result.returncode != 0:
            return f"ERROR: {result.stderr.strip()}"
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return f"ERROR: git command timed out after {GIT_TIMEOUT}s"
    except FileNotFoundError:
        return "ERROR: git CLI not found in PATH"


class GitPullInput(BaseModel):
    """Input for GitPullTool."""

    cwd: str = Field(default=".", description="Working directory for git operations")


class GitPullTool(BaseTool):
    """Pull latest changes from remote git repository."""

    name: str = "git_pull"
    description: str = "Pull latest changes from remote git repository."
    args_schema: type[BaseModel] = GitPullInput

    def _run(self, cwd: str = ".", **_: Any) -> str:
        return _run_cmd(["git", "pull"], cwd=cwd)


class GitAddInput(BaseModel):
    """Input for GitAddTool."""

    files: str = Field(description="Files to stage, space-separated or '.' for all")
    cwd: str = Field(default=".", description="Working directory for git operations")


class GitAddTool(BaseTool):
    """Stage files for git commit."""

    name: str = "git_add"
    description: str = "Stage files for git commit."
    args_schema: type[BaseModel] = GitAddInput

    def _run(self, files: str, cwd: str = ".", **_: Any) -> str:
        file_list = files.split() if files != "." else ["."]
        return _run_cmd(["git", "add", *file_list], cwd=cwd)


class GitCommitInput(BaseModel):
    """Input for GitCommitTool."""

    message: str = Field(description="Commit message")
    cwd: str = Field(default=".", description="Working directory for git operations")


class GitCommitTool(BaseTool):
    """Create a git commit with a message."""

    name: str = "git_commit"
    description: str = "Create a git commit with a message."
    args_schema: type[BaseModel] = GitCommitInput

    def _run(self, message: str, cwd: str = ".", **_: Any) -> str:
        return _run_cmd(["git", "commit", "-m", message], cwd=cwd)


class GitCheckoutInput(BaseModel):
    """Input for GitCheckoutTool."""

    branch: str = Field(description="Branch name to checkout")
    create: bool = Field(default=False, description="Create new branch if True")
    cwd: str = Field(default=".", description="Working directory for git operations")


class GitCheckoutTool(BaseTool):
    """Checkout a git branch, optionally creating it."""

    name: str = "git_checkout"
    description: str = "Checkout a git branch, optionally creating it."
    args_schema: type[BaseModel] = GitCheckoutInput

    def _run(
        self, branch: str, create: bool = False, cwd: str = ".", **_: Any
    ) -> str:  # noqa: FBT001, FBT002
        cmd = ["git", "checkout"]
        if create:
            cmd.append("-b")
        cmd.append(branch)
        return _run_cmd(cmd, cwd=cwd)


class GitPushInput(BaseModel):
    """Input for GitPushTool."""

    remote: str = Field(default="origin", description="Remote name")
    branch: str = Field(default="", description="Branch name (empty = current branch)")
    cwd: str = Field(default=".", description="Working directory for git operations")


class GitPushTool(BaseTool):
    """Push commits to remote git repository."""

    name: str = "git_push"
    description: str = "Push commits to remote git repository."
    args_schema: type[BaseModel] = GitPushInput

    def _run(
        self, remote: str = "origin", branch: str = "", cwd: str = ".", **_: Any
    ) -> str:
        cmd = ["git", "push", remote]
        if branch:
            cmd.append(branch)
        return _run_cmd(cmd, cwd=cwd)


class GitDeleteRemoteBranchInput(BaseModel):
    """Input for GitDeleteRemoteBranchTool."""

    branch: str = Field(description="Branch name to delete from remote")
    remote: str = Field(default="origin", description="Remote name")
    cwd: str = Field(default=".", description="Working directory for git operations")


class GitDeleteRemoteBranchTool(BaseTool):
    """Delete a branch from a remote git repository."""

    name: str = "git_delete_remote_branch"
    description: str = "Delete a branch from a remote git repository."
    args_schema: type[BaseModel] = GitDeleteRemoteBranchInput

    def _run(
        self, branch: str, remote: str = "origin", cwd: str = ".", **_: Any
    ) -> str:
        return _run_cmd(["git", "push", remote, "--delete", branch], cwd=cwd)


class CreateGitHubPRInput(BaseModel):
    """Input for CreateGitHubPRTool."""

    title: str = Field(description="PR title")
    body: str = Field(default="", description="PR description body")
    base: str = Field(default="main", description="Base branch for the PR")
    cwd: str = Field(default=".", description="Working directory for git operations")


class CreateGitHubPRTool(BaseTool):
    """Create a GitHub pull request using the gh CLI."""

    name: str = "create_github_pr"
    description: str = "Create a GitHub pull request using the gh CLI."
    args_schema: type[BaseModel] = CreateGitHubPRInput

    def _run(
        self, title: str, body: str = "", base: str = "main", cwd: str = ".", **_: Any
    ) -> str:
        cmd = ["gh", "pr", "create", "--title", title, "--base", base]
        if body:
            cmd.extend(["--body", body])
        return _run_cmd(cmd, cwd=cwd)
