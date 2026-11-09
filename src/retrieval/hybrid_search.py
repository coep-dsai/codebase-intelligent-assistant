"""Hybrid code search combining BM25 lexical retrieval and dense vector search via RRF."""

from collections import defaultdict
from typing import Dict, List, Tuple

from src.retrieval.bm25_search import BM25Retriever, SearchResult
from src.retrieval.vector_search import VectorRetriever


class HybridRetriever:
    """Combines BM25 and Dense Vector search using Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        vector_retriever: VectorRetriever,
        rrf_k: int = 60,
    ) -> None:
        self.bm25 = bm25_retriever
        self.vector = vector_retriever
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k: int = 10,
        bm25_weight: float = 1.0,
        vector_weight: float = 1.0,
    ) -> List[SearchResult]:
        """Executes both retrievers and fuses their rankings using RRF."""
        # Retrieve candidates from both
        bm25_results = self.bm25.search(query, top_k=top_k * 2)
        vector_results = self.vector.search(query, top_k=top_k * 2)

        # Map by unique chunk key: "file_path:start_line-end_line"
        chunk_map: Dict[str, SearchResult] = {}
        rrf_scores: Dict[str, float] = defaultdict(float)

        # Process BM25 ranks
        for rank, res in enumerate(bm25_results, start=1):
            key = f"{res.file_path}:{res.start_line}-{res.end_line}"
            chunk_map[key] = res
            rrf_scores[key] += bm25_weight * (1.0 / (self.rrf_k + rank))

        # Process Vector ranks
        for rank, res in enumerate(vector_results, start=1):
            key = f"{res.file_path}:{res.start_line}-{res.end_line}"
            chunk_map[key] = res
            rrf_scores[key] += vector_weight * (1.0 / (self.rrf_k + rank))

        # Sort by fused RRF score descending
        sorted_keys = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        final_results: List[SearchResult] = []
        for key, score in sorted_keys[:top_k]:
            original = chunk_map[key]
            final_results.append(
                SearchResult(
                    file_path=original.file_path,
                    symbol_name=original.symbol_name,
                    start_line=original.start_line,
                    end_line=original.end_line,
                    content=original.content,
                    score=score,
                    retrieval_type="hybrid_rrf",
                )
            )

        return final_results
