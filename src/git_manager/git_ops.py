"""Git automation manager for repository status, diffs, branching, and commits."""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class GitStatus:
    """Parsed git status summary."""

    current_branch: str
    is_clean: bool
    modified: List[str] = field(default_factory=list)
    staged: List[str] = field(default_factory=list)
    untracked: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)


class GitManager:
    """Manages Git version control operations within the workspace."""

    def __init__(self, workspace_dir: Path | str) -> None:
        self.workspace_dir = Path(workspace_dir).resolve()

    def _run_git(self, args: List[str], check: bool = True, timeout: float = 5.0) -> str:
        """Executes a git command with --no-pager and a strict timeout."""
        cmd = ["git", "--no-pager"] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.workspace_dir),
                capture_output=True,
                text=True,
                check=check,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return ""
        except subprocess.CalledProcessError as e:
            err = e.stderr.strip() if e.stderr else str(e)
            raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{err}")

    def is_git_repo(self) -> bool:
        """Checks if the workspace contains a .git folder or is inside a work tree."""
        git_dir = self.workspace_dir / ".git"
        if git_dir.exists():
            return True
        try:
            out = self._run_git(["rev-parse", "--is-inside-work-tree"], check=False)
            return out == "true"
        except Exception:
            return False

    def get_current_branch(self) -> str:
        """Retrieves current git branch name via .git/HEAD file or git command."""
        # Fast path: read .git/HEAD directly
        head_file = self.workspace_dir / ".git" / "HEAD"
        if head_file.is_file():
            try:
                content = head_file.read_text(encoding="utf-8").strip()
                if content.startswith("ref: refs/heads/"):
                    return content.replace("ref: refs/heads/", "").strip()
                return content[:8]  # Detached commit hash
            except Exception:
                pass

        try:
            return self._run_git(["branch", "--show-current"]) or "main"
        except Exception:
            return "main"

    def get_status(self) -> GitStatus:
        """Parses git status porcelain output."""
        branch = self.get_current_branch()
        raw_output = self._run_git(["status", "--porcelain=v1"], check=False)

        modified: List[str] = []
        staged: List[str] = []
        untracked: List[str] = []
        deleted: List[str] = []

        if not raw_output:
            return GitStatus(
                current_branch=branch,
                is_clean=True,
            )

        for line in raw_output.splitlines():
            if len(line) < 3:
                continue
            index_status = line[0]
            worktree_status = line[1]
            file_path = line[3:].strip()

            if index_status in ("M", "A", "R"):
                staged.append(file_path)
            if worktree_status == "M":
                modified.append(file_path)
            elif worktree_status == "D" or index_status == "D":
                deleted.append(file_path)
            elif index_status == "?" and worktree_status == "?":
                untracked.append(file_path)

        is_clean = not (modified or staged or untracked or deleted)
        return GitStatus(
            current_branch=branch,
            is_clean=is_clean,
            modified=modified,
            staged=staged,
            untracked=untracked,
            deleted=deleted,
        )

    def get_diff(self, staged: bool = False, file_path: Optional[str] = None) -> str:
        """Retrieves git diff for the repository or a specific file."""
        args = ["diff"]
        if staged:
            args.append("--staged")
        if file_path:
            args.extend(["--", file_path])
        return self._run_git(args, check=False)

    def create_branch(self, branch_name: str, checkout: bool = True) -> str:
        """Creates a new branch and optionally checks it out."""
        if checkout:
            return self._run_git(["checkout", "-b", branch_name])
        return self._run_git(["branch", branch_name])

    def checkout_branch(self, branch_name: str) -> str:
        """Switches to an existing branch."""
        return self._run_git(["checkout", branch_name])

    def stage_files(self, files: List[str] | str) -> str:
        """Stages file(s) for commit."""
        if isinstance(files, str):
            files = [files]
        return self._run_git(["add"] + files)

    def commit(self, message: str) -> str:
        """Creates a git commit with the given message."""
        return self._run_git(["commit", "-m", message])

    def restore_file(self, file_path: str, staged: bool = False) -> str:
        """Discards modifications to a file in working tree or un-stages it."""
        if staged:
            return self._run_git(["restore", "--staged", file_path])
        return self._run_git(["restore", file_path])
