"""Tests for FastAPI endpoint handlers."""

import asyncio
from src.server.app import get_git_status, get_repo_map, health_check


def test_health_check() -> None:
    """Verifies that the health_check endpoint returns expected fields."""
    data = asyncio.run(health_check())
    assert data["status"] == "healthy"
    assert "model" in data
    assert "workspace" in data
    assert "git_branch" in data


def test_get_repo_map() -> None:
    """Verifies that get_repo_map returns a valid outline."""
    data = asyncio.run(get_repo_map())
    assert "repo_map" in data
    assert isinstance(data["repo_map"], str)


def test_get_git_status() -> None:
    """Verifies that get_git_status returns git status object."""
    data = asyncio.run(get_git_status())
    assert "branch" in data
    assert "is_clean" in data
    assert "modified" in data
