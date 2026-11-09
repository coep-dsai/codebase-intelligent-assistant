"""Tests for BM25 code tokenization and lexical retrieval."""

from src.retrieval.bm25_search import BM25Retriever, SearchResult


def test_code_tokenization() -> None:
    """Verifies that snake_case, camelCase, and identifiers are properly tokenized."""
    tokens = BM25Retriever.tokenize_code("def get_user_profile(userId: str):")
    assert "user" in tokens
    assert "profile" in tokens
    assert "userid" in tokens


def test_bm25_search_ranking() -> None:
    """Verifies that relevant code chunks are ranked highest by BM25."""
    chunks = [
        SearchResult(
            file_path="src/auth.py",
            symbol_name="authenticate_user",
            start_line=1,
            end_line=10,
            content="def authenticate_user(username, password): return check_hash(password)",
            score=0.0,
        ),
        SearchResult(
            file_path="src/db.py",
            symbol_name="connect_database",
            start_line=1,
            end_line=10,
            content="def connect_database(host, port): return create_pool()",
            score=0.0,
        ),
    ]

    retriever = BM25Retriever()
    retriever.index_chunks(chunks)

    results = retriever.search("authenticate user with password")
    assert len(results) > 0
    assert results[0].symbol_name == "authenticate_user"
