"""Patch Engine for robust, syntax-safe code editing with rollback support.

Parses Search/Replace blocks, handles whitespace-tolerant fuzzy matching,
generates unified diff previews, runs pre-flight syntax checks, and guarantees
safe file rollbacks upon failure.
"""

import ast
import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class PatchBlock:
    """Represents a single Search/Replace block."""

    search_block: str
    replace_block: str


@dataclass
class PatchResult:
    """Outcome of a patch attempt."""

    file_path: str
    success: bool
    diff: str
    error_message: Optional[str] = None
    backup_content: Optional[str] = None


class PatchEngine:
    """Applies code edits reliably using Search/Replace blocks or unified diffs."""

    SEARCH_REPLACE_PATTERN = re.compile(
        r"<<<<<<< SEARCH\r?\n(.*?)\r?\n=======\r?\n(.*?)\r?\n>>>>>>> REPLACE",
        re.DOTALL,
    )

    @classmethod
    def parse_search_replace_blocks(cls, response_text: str) -> List[PatchBlock]:
        """Extracts all <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE blocks from text."""
        blocks: List[PatchBlock] = []
        matches = cls.SEARCH_REPLACE_PATTERN.findall(response_text)
        for search_text, replace_text in matches:
            blocks.append(PatchBlock(search_block=search_text, replace_block=replace_text))
        return blocks

    @staticmethod
    def generate_unified_diff(
        original: str, modified: str, file_name: str = "target_file"
    ) -> str:
        """Generates standard unified diff lines between original and modified strings."""
        orig_lines = original.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{file_name}",
            tofile=f"b/{file_name}",
            lineterm="",
        )
        return "".join(diff)

    @staticmethod
    def validate_syntax(code: str, file_path: str) -> Optional[str]:
        """Pre-flight syntax validation. Returns error message if syntax is invalid."""
        if file_path.endswith(".py"):
            try:
                ast.parse(code)
            except SyntaxError as e:
                return f"Python SyntaxError at line {e.lineno}: {e.msg}"
        return None

    @classmethod
    def apply_search_replace_blocks(
        cls,
        original_content: str,
        blocks: List[PatchBlock],
        file_path: str = "file",
    ) -> PatchResult:
        """Applies a sequence of Search/Replace blocks to content with fuzzy tolerance."""
        current_content = original_content

        for idx, block in enumerate(blocks, start=1):
            search = block.search_block
            replace = block.replace_block

            # 1. Exact match attempt
            if search in current_content:
                # Replace the first occurrence
                current_content = current_content.replace(search, replace, 1)
                continue

            # 2. Whitespace-normalized fuzzy matching
            matched, new_content = cls._fuzzy_replace(current_content, search, replace)
            if matched:
                current_content = new_content
                continue

            # If search block could not be matched
            return PatchResult(
                file_path=file_path,
                success=False,
                diff="",
                error_message=(
                    f"Block {idx} failed to apply: SEARCH block not found in {file_path}. "
                    "Ensure exact lines and indentation match the source code."
                ),
                backup_content=original_content,
            )

        # Pre-flight syntax validation
        syntax_err = cls.validate_syntax(current_content, file_path)
        if syntax_err:
            return PatchResult(
                file_path=file_path,
                success=False,
                diff="",
                error_message=f"Patch generated invalid syntax: {syntax_err}",
                backup_content=original_content,
            )

        diff = cls.generate_unified_diff(original_content, current_content, file_path)
        return PatchResult(
            file_path=file_path,
            success=True,
            diff=diff,
            backup_content=original_content,
        )

    @staticmethod
    def _fuzzy_replace(content: str, search: str, replace: str) -> Tuple[bool, str]:
        """Attempts line-by-line whitespace-tolerant matching for code blocks."""
        content_lines = content.splitlines(keepends=True)
        search_lines = [s.strip() for s in search.splitlines() if s.strip()]

        if not search_lines:
            return False, content

        for i in range(len(content_lines) - len(search_lines) + 1):
            slice_lines = [content_lines[i + j].strip() for j in range(len(search_lines))]
            if slice_lines == search_lines:
                # Found the target region
                prefix = "".join(content_lines[:i])
                suffix = "".join(content_lines[i + len(search_lines) :])
                # Ensure newline termination matches
                replace_formatted = replace
                if not replace_formatted.endswith("\n") and suffix:
                    replace_formatted += "\n"
                return True, prefix + replace_formatted + suffix

        return False, content
