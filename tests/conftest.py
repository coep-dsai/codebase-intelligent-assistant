"""Pytest fixtures for Codebase Assistant test suites."""

from pathlib import Path
from typing import Generator
import pytest


@pytest.fixture
def sample_python_code() -> str:
    """Sample Python source code with classes, methods, docstrings, and functions."""
    return '''"""User authentication service module."""

import hashlib
from typing import Optional


class AuthService:
    """Handles credential validation and token generation."""

    def __init__(self, secret_key: str) -> None:
        self.secret_key = secret_key

    def hash_password(self, password: str) -> str:
        """Computes SHA-256 hash of a password."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def verify_token(self, token: str) -> bool:
        """Verifies authentication token."""
        return len(token) > 10


def create_default_service() -> AuthService:
    """Factory creating default auth service."""
    return AuthService(secret_key="default-secret")
'''


@pytest.fixture
def temp_workspace(tmp_path: Path, sample_python_code: str) -> Path:
    """Creates a temporary workspace with sample files."""
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    auth_file = src_dir / "auth.py"
    auth_file.write_text(sample_python_code, encoding="utf-8")

    utils_file = src_dir / "utils.py"
    utils_file.write_text(
        'from src.auth import AuthService\n\ndef helper():\n    return AuthService("key")\n',
        encoding="utf-8",
    )

    return tmp_path
