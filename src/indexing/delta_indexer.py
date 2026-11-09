"""Delta and incremental indexing engine with SQLite content-hash caching."""

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.indexing.ast_parser import ASTParser, CodeSymbol, ParsedFileAST
from src.retrieval.bm25_search import SearchResult


class DeltaIndexer:
    """Tracks workspace file content hashes in SQLite to enable sub-second incremental indexing."""

    def __init__(self, workspace_dir: Path | str, db_path: Path | str) -> None:
        self.workspace_dir = Path(workspace_dir).resolve()
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.parser = ASTParser()
        self._init_db()

    def _init_db(self) -> None:
        """Initializes SQLite schema for file hash and symbol tracking."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_cache (
                    file_path TEXT PRIMARY KEY,
                    sha256_hash TEXT NOT NULL,
                    mtime REAL NOT NULL,
                    language TEXT NOT NULL,
                    symbols_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def compute_sha256(content: str) -> str:
        """Calculates SHA-256 hash of a string."""
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

    def get_cached_files(self) -> Dict[str, Tuple[str, float]]:
        """Returns map of {file_path: (sha256_hash, mtime)} from cache."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path, sha256_hash, mtime FROM file_cache")
            return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}

    def scan_changes(
        self, ignore_patterns: Optional[Set[str]] = None
    ) -> Tuple[List[str], List[str], List[str]]:
        """Detects added, modified, and deleted files since the last indexing run.

        Returns:
            Tuple of (added_files, modified_files, deleted_files) as relative paths.
        """
        if ignore_patterns is None:
            ignore_patterns = {
                ".git",
                ".venv",
                "node_modules",
                "__pycache__",
                ".pytest_cache",
                "dist",
                "build",
                ".codebase_agent",
            }

        cached = self.get_cached_files()
        current_files: Dict[str, Path] = {}

        for p in self.workspace_dir.rglob("*"):
            if not p.is_file():
                continue
            parts = set(p.relative_to(self.workspace_dir).parts)
            if parts.intersection(ignore_patterns):
                continue
            lang = self.parser.detect_language(p)
            if not lang:
                continue
            rel_str = str(p.relative_to(self.workspace_dir)).replace("\\", "/")
            current_files[rel_str] = p

        added: List[str] = []
        modified: List[str] = []
        deleted: List[str] = [f for f in cached if f not in current_files]

        for rel_path, full_path in current_files.items():
            try:
                mtime = full_path.stat().st_mtime
                if rel_path not in cached:
                    added.append(rel_path)
                else:
                    cached_hash, cached_mtime = cached[rel_path]
                    # Quick check: mtime changed
                    if mtime != cached_mtime:
                        content = full_path.read_text(encoding="utf-8", errors="replace")
                        current_hash = self.compute_sha256(content)
                        if current_hash != cached_hash:
                            modified.append(rel_path)
            except Exception:
                continue

        return added, modified, deleted

    def index_file(self, rel_path: str) -> Optional[Tuple[ParsedFileAST, List[SearchResult]]]:
        """Parses a file, converts symbols to searchable chunks, and updates the SQLite cache."""
        full_path = self.workspace_dir / rel_path
        if not full_path.is_file():
            return None

        content = full_path.read_text(encoding="utf-8", errors="replace")
        sha256_hash = self.compute_sha256(content)
        mtime = full_path.stat().st_mtime
        lang = self.parser.detect_language(full_path)
        if not lang:
            return None

        parsed = self.parser.parse_source(content, lang, file_path=rel_path)

        # Convert symbols to search chunks
        chunks: List[SearchResult] = []
        content_lines = content.splitlines()

        for sym in parsed.symbols:
            # Extract snippet
            snippet_lines = content_lines[max(0, sym.start_line - 1) : sym.end_line]
            snippet = "\n".join(snippet_lines)
            chunks.append(
                SearchResult(
                    file_path=rel_path,
                    symbol_name=sym.name,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    content=snippet,
                    score=0.0,
                )
            )

        # Save to SQLite
        symbols_serialized = json.dumps([asdict(s) for s in parsed.symbols])
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO file_cache (file_path, sha256_hash, mtime, language, symbols_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (rel_path, sha256_hash, mtime, lang, symbols_serialized),
            )
            conn.commit()

        return parsed, chunks

    def remove_file(self, rel_path: str) -> None:
        """Removes a deleted file from the SQLite cache."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM file_cache WHERE file_path = ?", (rel_path,))
            conn.commit()
