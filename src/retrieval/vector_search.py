"""Dense vector retrieval using FastEmbed and ChromaDB."""

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from fastembed import TextEmbedding
except ImportError:
    chromadb = Any  # type: ignore
    ChromaSettings = Any  # type: ignore
    TextEmbedding = Any  # type: ignore

from src.retrieval.bm25_search import SearchResult


class VectorRetriever:
    """Manages dense code embeddings and ChromaDB vector search."""

    def __init__(
        self,
        persist_directory: Path | str,
        collection_name: str = "code_symbols",
        model_name: str = "BAAI/bge-small-en-v1.5",
    ) -> None:
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.model_name = model_name

        self._embedder: Optional[TextEmbedding] = None
        self._client: Optional[Any] = None
        self._collection: Optional[Any] = None

    @property
    def embedder(self) -> TextEmbedding:
        """Lazy-loaded FastEmbed model."""
        if self._embedder is None:
            self._embedder = TextEmbedding(model_name=self.model_name)
        return self._embedder

    @property
    def collection(self) -> Any:
        """Lazy-loaded Chroma collection."""
        if self._collection is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for texts."""
        embeddings_generator = self.embedder.embed(texts)
        return [emb.tolist() for emb in embeddings_generator]

    def index_chunks(self, chunks: List[SearchResult]) -> None:
        """Embeds and persists code chunks to ChromaDB."""
        if not chunks:
            return

        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            ids.append(chunk_id)
            documents.append(chunk.content)
            metadatas.append(
                {
                    "file_path": chunk.file_path,
                    "symbol_name": chunk.symbol_name,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                }
            )

        embeddings = self.embed_texts(documents)

        # Upsert into ChromaDB
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Searches ChromaDB for the closest code chunks."""
        query_embeddings = self.embed_texts([query])
        if not query_embeddings:
            return []

        results = self.collection.query(
            query_embeddings=query_embeddings,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        search_results: List[SearchResult] = []
        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        for doc, meta, dist in zip(docs, metas, distances):
            # Cosine distance to similarity score
            score = 1.0 - float(dist)
            search_results.append(
                SearchResult(
                    file_path=meta.get("file_path", ""),
                    symbol_name=meta.get("symbol_name", ""),
                    start_line=meta.get("start_line", 0),
                    end_line=meta.get("end_line", 0),
                    content=doc,
                    score=score,
                    retrieval_type="vector",
                )
            )

        return search_results
