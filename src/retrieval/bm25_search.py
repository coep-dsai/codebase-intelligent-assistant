"""Lexical code retrieval using BM25Okapi with code-aware tokenization."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = Any  # type: ignore


@dataclass
class SearchResult:
    """Represents a matched code chunk with score and location."""

    file_path: str
    symbol_name: str
    start_line: int
    end_line: int
    content: str
    score: float
    retrieval_type: str = "bm25"


class BM25Retriever:
    """Indexes code chunks and performs BM25Okapi keyword search."""

    def __init__(self) -> None:
        self.chunks: List[SearchResult] = []
        self.bm25: Optional[BM25Okapi] = None
        self.tokenized_corpus: List[List[str]] = []

    @staticmethod
    def tokenize_code(text: str) -> List[str]:
        """Tokenizes code by splitting snake_case, camelCase, and alphanumeric symbols."""
        # Split on non-alphanumeric characters
        raw_tokens = re.findall(r"[A-Za-z0-9_]+", text)
        result_tokens: List[str] = []

        for token in raw_tokens:
            # Add the full token in lowercase
            result_tokens.append(token.lower())

            # Split snake_case
            parts = token.split("_")
            if len(parts) > 1:
                for part in parts:
                    if part:
                        result_tokens.append(part.lower())

            # Split camelCase / PascalCase
            camel_parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\b)", token)
            if len(camel_parts) > 1:
                for cp in camel_parts:
                    result_tokens.append(cp.lower())

        return [t for t in result_tokens if len(t) > 1]

    def index_chunks(self, chunks: List[SearchResult]) -> None:
        """Builds the BM25 index over the provided code chunks."""
        self.chunks = chunks
        self.tokenized_corpus = [
            self.tokenize_code(c.content + " " + c.file_path + " " + c.symbol_name)
            for c in chunks
        ]
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Searches indexed code chunks using BM25 scoring."""
        if not self.bm25 or not self.chunks:
            return []

        query_tokens = self.tokenize_code(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # Pair chunks with scores
        scored_results: List[Tuple[SearchResult, float]] = []
        for idx, score in enumerate(scores):
            chunk = self.chunks[idx]
            scored_results.append((chunk, float(score)))

        # Sort descending by score
        scored_results.sort(key=lambda x: x[1], reverse=True)

        results: List[SearchResult] = []
        for chunk, score in scored_results[:top_k]:
            results.append(
                SearchResult(
                    file_path=chunk.file_path,
                    symbol_name=chunk.symbol_name,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    content=chunk.content,
                    score=score,
                    retrieval_type="bm25",
                )
            )

        return results
