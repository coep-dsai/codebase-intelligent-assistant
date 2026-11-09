"""Tests for FileManager sandboxing and path safety."""

from pathlib import Path
import pytest
from src.editor.file_manager import FileManager


def test_file_manager_write_and_read(tmp_path: Path) -> None:
    """Verifies atomic writing, backups, and reading."""
    fm = FileManager(tmp_path)
    file_path = fm.write_file("sub/test.txt", "initial content")

    assert file_path.is_file()
    assert fm.read_file("sub/test.txt") == "initial content"

    # Write update and check backup
    fm.write_file("sub/test.txt", "updated content")
    assert fm.read_file("sub/test.txt") == "updated content"
    assert len(list(fm.backup_dir.glob("*.bak"))) == 1


def test_file_manager_blocks_path_traversal(tmp_path: Path) -> None:
    """Verifies that attempts to access files outside workspace raise PermissionError."""
    fm = FileManager(tmp_path)
    with pytest.raises(PermissionError):
        fm.resolve_path("../../etc/passwd")
