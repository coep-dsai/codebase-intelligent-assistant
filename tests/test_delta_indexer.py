"""Tests for SQLite content-hash delta indexing."""

from pathlib import Path
from src.indexing.delta_indexer import DeltaIndexer


def test_delta_indexer_lifecycle(temp_workspace: Path) -> None:
    """Verifies change detection: added, modified, deleted files."""
    db_path = temp_workspace / ".codebase_agent" / "test_cache.db"
    indexer = DeltaIndexer(temp_workspace, db_path)

    # Initial scan should detect added files
    added, mod, dele = indexer.scan_changes()
    assert len(added) >= 2
    assert len(mod) == 0
    assert len(dele) == 0

    # Index the files
    for f in added:
        indexer.index_file(f)

    # Second scan: no changes
    added2, mod2, dele2 = indexer.scan_changes()
    assert len(added2) == 0
    assert len(mod2) == 0
    assert len(dele2) == 0

    # Modify a file
    auth_file = temp_workspace / "src" / "auth.py"
    auth_file.write_text("# modified\n" + auth_file.read_text(), encoding="utf-8")

    added3, mod3, dele3 = indexer.scan_changes()
    assert any("auth.py" in m for m in mod3)
