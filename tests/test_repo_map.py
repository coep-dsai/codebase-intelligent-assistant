"""Tests for PageRank repository map generation."""

from pathlib import Path
from src.indexing.repo_map import RepoMapGenerator


def test_repo_map_scanning_and_ranking(temp_workspace: Path) -> None:
    """Verifies that repo map extracts tags, computes PageRank, and formats outlines."""
    gen = RepoMapGenerator(temp_workspace, max_tokens=1000)
    gen.scan_repository()

    assert len(gen.file_tags) >= 2
    ranks = gen.compute_pagerank()
    assert len(ranks) >= 2

    # Since utils.py imports and references AuthService from auth.py, auth.py should have higher PageRank!
    auth_key = next((k for k in ranks if "auth.py" in k), None)
    utils_key = next((k for k in ranks if "utils.py" in k), None)

    assert auth_key is not None
    assert utils_key is not None
    assert ranks[auth_key] >= ranks[utils_key]

    # Verify map outline text
    map_text = gen.generate_map()
    assert "AuthService" in map_text
    assert "[class]" in map_text
