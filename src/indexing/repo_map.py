"""Personalized PageRank Repository Map Generator.

Extracts definitions and references across codebase files to construct a
symbol relationship graph, ranks files and definitions via PageRank, and
outputs a compact, token-budgeted architectural outline for the LLM.
"""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from src.indexing.ast_parser import ASTParser, CodeSymbol, ParsedFileAST


@dataclass
class Tag:
    """Represents a definition or reference tag in a source file."""

    file_path: str
    symbol_name: str
    kind: str  # "def" (definition) or "ref" (reference)
    line: int
    signature: str = ""


class RepoMapGenerator:
    """Generates token-budgeted repository maps using Tree-sitter tags and PageRank."""

    def __init__(self, workspace_dir: Path | str, max_tokens: int = 1500) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.max_tokens = max_tokens
        self.parser = ASTParser()
        self.file_tags: Dict[str, List[Tag]] = {}
        self.file_parsed: Dict[str, ParsedFileAST] = {}

    def scan_repository(self, ignore_patterns: Optional[Set[str]] = None) -> None:
        """Scans workspace source files and extracts tags."""
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

        self.file_tags.clear()
        self.file_parsed.clear()

        for path in self.workspace_dir.rglob("*"):
            if not path.is_file():
                continue

            # Check if any parent part matches ignore patterns
            parts = set(path.relative_to(self.workspace_dir).parts)
            if parts.intersection(ignore_patterns):
                continue

            lang = self.parser.detect_language(path)
            if not lang:
                continue

            rel_path = str(path.relative_to(self.workspace_dir)).replace("\\", "/")
            parsed = self.parser.parse_file(path)
            if not parsed:
                continue

            parsed.file_path = rel_path
            self.file_parsed[rel_path] = parsed
            tags: List[Tag] = []

            # Add definition tags
            for sym in parsed.symbols:
                tags.append(
                    Tag(
                        file_path=rel_path,
                        symbol_name=sym.name,
                        kind="def",
                        line=sym.start_line,
                        signature=sym.signature,
                    )
                )

            # Add reference tags
            for ident in parsed.referenced_identifiers:
                tags.append(
                    Tag(
                        file_path=rel_path,
                        symbol_name=ident,
                        kind="ref",
                        line=0,
                    )
                )

            self.file_tags[rel_path] = tags

    def compute_pagerank(
        self,
        active_files: Optional[List[str]] = None,
        damping: float = 0.85,
        iterations: int = 25,
    ) -> Dict[str, float]:
        """Calculates PageRank scores for all scanned files."""
        files = list(self.file_tags.keys())
        n = len(files)
        if n == 0:
            return {}
        if n == 1:
            return {files[0]: 1.0}

        # Index definitions by symbol name
        defs_by_name: Dict[str, Set[str]] = defaultdict(set)
        for f, tags in self.file_tags.items():
            for t in tags:
                if t.kind == "def":
                    defs_by_name[t.symbol_name].add(f)

        # Build adjacency graph (outgoing edges from file to files defining referenced symbols)
        adj: Dict[str, Set[str]] = defaultdict(set)
        for f, tags in self.file_tags.items():
            for t in tags:
                if t.kind == "ref" and t.symbol_name in defs_by_name:
                    for target_file in defs_by_name[t.symbol_name]:
                        if target_file != f:
                            adj[f].add(target_file)

        # Personalization vector
        pers: Dict[str, float] = {}
        if active_files:
            active_set = {f.replace("\\", "/") for f in active_files if f in self.file_tags}
            if active_set:
                weight = 1.0 / len(active_set)
                for f in files:
                    pers[f] = weight if f in active_set else 0.0
            else:
                uniform = 1.0 / n
                pers = {f: uniform for f in files}
        else:
            uniform = 1.0 / n
            pers = {f: uniform for f in files}

        # Initialize ranks
        ranks: Dict[str, float] = {f: 1.0 / n for f in files}

        # Power iteration
        for _ in range(iterations):
            new_ranks: Dict[str, float] = defaultdict(float)
            dangling_sum = 0.0

            for f in files:
                out_degree = len(adj[f])
                if out_degree > 0:
                    share = ranks[f] / out_degree
                    for dest in adj[f]:
                        new_ranks[dest] += share
                else:
                    dangling_sum += ranks[f]

            for f in files:
                new_ranks[f] = (
                    damping * (new_ranks[f] + dangling_sum / n)
                    + (1.0 - damping) * pers[f]
                )
            ranks = new_ranks

        return ranks

    def generate_map(self, active_files: Optional[List[str]] = None) -> str:
        """Generates a hierarchical token-budgeted outline of the repository."""
        if not self.file_tags:
            self.scan_repository()

        if not self.file_tags:
            return "No indexable source code files found in repository."

        ranks = self.compute_pagerank(active_files)
        # Sort files by PageRank descending
        sorted_files = sorted(ranks.items(), key=lambda x: x[1], reverse=True)

        lines: List[str] = []
        token_estimate = 0
        tokens_per_word = 1.3  # rough estimate

        for f, score in sorted_files:
            file_header = f"{f}:"
            lines.append(file_header)
            token_estimate += int(len(file_header.split()) * tokens_per_word)

            parsed = self.file_parsed.get(f)
            if parsed and parsed.symbols:
                for sym in parsed.symbols:
                    indent = "    " if sym.parent_symbol else "  "
                    kind_badge = f"[{sym.kind}]"
                    sig = sym.signature if sym.signature else sym.name
                    entry = f"{indent}{kind_badge} {sig} (line {sym.start_line})"
                    lines.append(entry)
                    token_estimate += int(len(entry.split()) * tokens_per_word)

                    if token_estimate >= self.max_tokens:
                        lines.append("  ... (remaining files omitted for token budget)")
                        return "\n".join(lines)

        return "\n".join(lines)
