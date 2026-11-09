"""Tests for Tree-sitter AST parser and symbol extraction."""

from src.indexing.ast_parser import ASTParser


def test_ast_parser_python_symbols(sample_python_code: str) -> None:
    """Verifies that classes, methods, docstrings, and functions are properly extracted."""
    parser = ASTParser()
    parsed = parser.parse_source(sample_python_code, "python", file_path="auth.py")

    assert parsed.language == "python"
    assert len(parsed.symbols) >= 4  # AuthService, __init__, hash_password, verify_token, create_default_service

    names = [s.name for s in parsed.symbols]
    assert "AuthService" in names
    assert "hash_password" in names
    assert "create_default_service" in names

    # Check docstring extraction
    auth_class = next(s for s in parsed.symbols if s.name == "AuthService")
    assert auth_class.kind == "class"
    assert auth_class.docstring == "Handles credential validation and token generation."

    hash_method = next(s for s in parsed.symbols if s.name == "hash_password")
    assert hash_method.kind == "method"
    assert hash_method.docstring == "Computes SHA-256 hash of a password."


def test_ast_parser_language_detection() -> None:
    """Verifies mapping of file extensions to Tree-sitter grammar names."""
    parser = ASTParser()
    assert parser.detect_language("main.py") == "python"
    assert parser.detect_language("index.ts") == "typescript"
    assert parser.detect_language("App.tsx") == "tsx"
    assert parser.detect_language("server.go") == "go"
    assert parser.detect_language("main.rs") == "rust"
    assert parser.detect_language("readme.txt") is None
