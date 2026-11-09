"""Repository Comparison Mode: AST-aware semantic diffing between branches or commits."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

from src.git_manager.git_ops import GitManager
from src.indexing.ast_parser import ASTParser, CodeSymbol


@dataclass
class SymbolDiff:
    """Represents an AST-level change to a code symbol."""

    file_path: str
    symbol_name: str
    change_type: str  # "added", "removed", "modified"
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    details: str = ""


@dataclass
class RepoComparisonResult:
    """High-level semantic comparison between two repository states."""

    base_ref: str
    target_ref: str
    added_symbols: List[SymbolDiff] = field(default_factory=list)
    removed_symbols: List[SymbolDiff] = field(default_factory=list)
    modified_symbols: List[SymbolDiff] = field(default_factory=list)
    changed_files: List[str] = field(default_factory=list)


class RepoDiffAnalyzer:
    """Performs semantic AST diffs between Git branches or working directories."""

    def __init__(self, workspace_dir: Path | str) -> None:
        self.workspace_dir = Path(workspace_dir).resolve()
        self.git = GitManager(self.workspace_dir)
        self.parser = ASTParser()

    def compare_working_tree_against_commit(
        self, base_ref: str = "HEAD"
    ) -> RepoComparisonResult:
        """Compares current working tree against a base Git commit or branch."""
        # Get changed files from git
        raw_diff_files = self.git._run_git(
            ["diff", "--name-only", base_ref], check=False
        )
        changed_files = [f.strip() for f in raw_diff_files.splitlines() if f.strip()]

        result = RepoComparisonResult(
            base_ref=base_ref,
            target_ref="working_tree",
            changed_files=changed_files,
        )

        for rel_file in changed_files:
            file_path = self.workspace_dir / rel_file
            lang = self.parser.detect_language(file_path)
            if not lang:
                continue

            # Parse new working tree content if it exists
            new_symbols: Dict[str, CodeSymbol] = {}
            if file_path.is_file():
                parsed_new = self.parser.parse_file(file_path)
                if parsed_new:
                    new_symbols = {s.name: s for s in parsed_new.symbols}

            # Parse old content from base_ref via git show
            old_symbols: Dict[str, CodeSymbol] = {}
            try:
                old_content = self.git._run_git(["show", f"{base_ref}:{rel_file}"], check=False)
                if old_content:
                    parsed_old = self.parser.parse_source(old_content, lang, file_path=rel_file)
                    old_symbols = {s.name: s for s in parsed_old.symbols}
            except Exception:
                old_symbols = {}

            # Detect added symbols
            for name, sym in new_symbols.items():
                if name not in old_symbols:
                    result.added_symbols.append(
                        SymbolDiff(
                            file_path=rel_file,
                            symbol_name=name,
                            change_type="added",
                            new_signature=sym.signature,
                            details=f"New {sym.kind} defined at line {sym.start_line}",
                        )
                    )
                else:
                    old_sym = old_symbols[name]
                    if sym.signature != old_sym.signature:
                        result.modified_symbols.append(
                            SymbolDiff(
                                file_path=rel_file,
                                symbol_name=name,
                                change_type="modified",
                                old_signature=old_sym.signature,
                                new_signature=sym.signature,
                                details="Signature or parameters modified",
                            )
                        )

            # Detect removed symbols
            for name, old_sym in old_symbols.items():
                if name not in new_symbols:
                    result.removed_symbols.append(
                        SymbolDiff(
                            file_path=rel_file,
                            symbol_name=name,
                            change_type="removed",
                            old_signature=old_sym.signature,
                            details=f"Removed {old_sym.kind}",
                        )
                    )

        return result
