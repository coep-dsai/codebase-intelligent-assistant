"""Safe file management with path traversal checks, atomic writes, and backups."""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional


class FileManager:
    """Provides safe, sandboxed file operations for the assistant within the workspace."""

    def __init__(self, workspace_dir: Path | str, backup_dir: Optional[Path | str] = None) -> None:
        self.workspace_dir = Path(workspace_dir).resolve()
        if backup_dir:
            self.backup_dir = Path(backup_dir).resolve()
        else:
            self.backup_dir = self.workspace_dir / ".codebase_agent" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, relative_path: str | Path) -> Path:
        """Resolves a relative path safely against the workspace directory."""
        target = (self.workspace_dir / relative_path).resolve()
        # Security check: ensure path does not escape workspace
        try:
            target.relative_to(self.workspace_dir)
        except ValueError:
            raise PermissionError(f"Access denied: path '{relative_path}' is outside workspace.")
        return target

    def read_file(self, relative_path: str | Path) -> str:
        """Reads a file's content as text."""
        target = self.resolve_path(relative_path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return target.read_text(encoding="utf-8", errors="replace")

    def create_backup(self, relative_path: str | Path) -> Optional[Path]:
        """Creates a timestamped backup of the target file in the backup directory."""
        target = self.resolve_path(relative_path)
        if not target.is_file():
            return None

        timestamp = int(time.time() * 1000)
        rel_str = str(target.relative_to(self.workspace_dir)).replace("/", "_").replace("\\", "_")
        backup_file = self.backup_dir / f"{rel_str}.{timestamp}.bak"
        shutil.copy2(target, backup_file)
        return backup_file

    def write_file(self, relative_path: str | Path, content: str, backup: bool = True) -> Path:
        """Atomically writes content to a file, creating parent directories and backups."""
        target = self.resolve_path(relative_path)

        if backup and target.is_file():
            self.create_backup(relative_path)

        target.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write via temporary file
        temp_dir = target.parent
        with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
            tf.write(content)
            temp_path = Path(tf.name)

        try:
            temp_path.replace(target)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

        return target

    def delete_file(self, relative_path: str | Path, backup: bool = True) -> bool:
        """Deletes a file after creating an optional backup."""
        target = self.resolve_path(relative_path)
        if not target.is_file():
            return False

        if backup:
            self.create_backup(relative_path)

        target.unlink()
        return True
