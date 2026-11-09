"""Call graph and dependency hierarchy extraction engine for repository visualization."""

from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.indexing.ast_parser import ASTParser, CodeSymbol, ParsedFileAST


@dataclass
class GraphNode:
    """Represents a function or class node in the call graph."""

    id: str
    label: str
    kind: str
    file_path: str
    line: int


@dataclass
class GraphEdge:
    """Represents a call or inheritance edge between two symbols."""

    source: str
    target: str
    relation: str = "calls"


@dataclass
class CallGraphData:
    """Serializable call graph container ready for Cytoscape.js or D3.js."""

    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class CallGraphAnalyzer:
    """Analyzes AST symbols to construct symbol call graphs and file dependencies."""

    def __init__(self, workspace_dir: Path | str) -> None:
        self.workspace_dir = Path(workspace_dir).resolve()
        self.parser = ASTParser()

    def build_graph(self, target_files: Optional[List[str]] = None) -> CallGraphData:
        """Constructs an interactive call graph of functions, classes, and calls."""
        nodes_map: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []
        symbol_to_node_id: Dict[str, str] = {}

        # Scan files
        files_to_scan = []
        if target_files:
            files_to_scan = [self.workspace_dir / f for f in target_files]
        else:
            for p in self.workspace_dir.rglob("*.py"):
                if not any(ign in p.parts for ign in (".git", ".venv", "__pycache__")):
                    files_to_scan.append(p)

        parsed_files: List[ParsedFileAST] = []
        for f in files_to_scan:
            parsed = self.parser.parse_file(f)
            if parsed:
                rel = str(f.relative_to(self.workspace_dir)).replace("\\", "/")
                parsed.file_path = rel
                parsed_files.append(parsed)

                # Register nodes
                for sym in parsed.symbols:
                    node_id = f"{rel}::{sym.name}"
                    nodes_map[node_id] = GraphNode(
                        id=node_id,
                        label=sym.name,
                        kind=sym.kind,
                        file_path=rel,
                        line=sym.start_line,
                    )
                    # Index by short name for call resolution
                    symbol_to_node_id[sym.name] = node_id

        # Build edges based on referenced calls
        for parsed in parsed_files:
            for sym in parsed.symbols:
                caller_id = f"{parsed.file_path}::{sym.name}"
                for ref in parsed.referenced_identifiers:
                    if ref in symbol_to_node_id and symbol_to_node_id[ref] != caller_id:
                        edges.append(
                            GraphEdge(
                                source=caller_id,
                                target=symbol_to_node_id[ref],
                                relation="calls",
                            )
                        )

        return CallGraphData(
            nodes=[asdict(n) for n in nodes_map.values()],
            edges=[asdict(e) for e in edges],
        )
