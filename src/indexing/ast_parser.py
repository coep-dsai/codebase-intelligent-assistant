"""AST Parser for multi-language code intelligence using pre-compiled Tree-sitter grammars.

Extracts semantic symbols (classes, functions, methods, signatures, imports,
and calls) across multiple programming languages completely offline without
network calls or runtime downloads.
"""

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from tree_sitter import Language, Node, Parser, Tree

# Language module mapping for pre-compiled wheels
LANGUAGE_MODULES: Dict[str, str] = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "tsx": "tree_sitter_typescript",
    "go": "tree_sitter_go",
    "rust": "tree_sitter_rust",
    "java": "tree_sitter_java",
    "c": "tree_sitter_c",
    "cpp": "tree_sitter_cpp",
}

# Extension to Tree-sitter language name mapping
EXTENSION_TO_LANGUAGE: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
}


@dataclass
class CodeSymbol:
    """Represents an extracted code symbol (function, class, method, or interface)."""

    name: str
    kind: str  # "class", "function", "method", "interface", "struct"
    file_path: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    signature: str = ""
    docstring: Optional[str] = None
    parent_symbol: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)


@dataclass
class ParsedFileAST:
    """Container for all symbols, imports, and calls extracted from a file."""

    file_path: str
    language: str
    symbols: List[CodeSymbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    referenced_identifiers: Set[str] = field(default_factory=set)


class ASTParser:
    """Multi-language AST Parser backed by modular Tree-sitter grammars."""

    def __init__(self) -> None:
        self._parsers: Dict[str, Parser] = {}

    def get_parser_for_language(self, language_name: str) -> Parser:
        """Retrieves or initializes an offline Tree-sitter parser for a language."""
        if language_name in self._parsers:
            return self._parsers[language_name]

        # 1. Try modular package first (e.g. tree_sitter_python)
        module_name = LANGUAGE_MODULES.get(language_name)
        if module_name:
            try:
                mod = importlib.import_module(module_name)
                if language_name == "tsx":
                    lang_func = getattr(mod, "language_tsx", getattr(mod, "language"))
                else:
                    lang_func = getattr(mod, "language")

                language = Language(lang_func())
                parser = Parser(language)
                self._parsers[language_name] = parser
                return parser
            except (ImportError, AttributeError):
                pass

        # 2. Fallback to tree_sitter_language_pack
        try:
            from tree_sitter_language_pack import get_parser
            parser = get_parser(language_name)
            self._parsers[language_name] = parser
            return parser
        except Exception:
            pass

        raise ValueError(f"Could not load Tree-sitter parser for language '{language_name}'. Ensure 'tree-sitter-{language_name}' is installed.")

    def detect_language(self, file_path: str | Path) -> Optional[str]:
        """Detects the Tree-sitter language name based on file extension."""
        path = Path(file_path)
        ext = path.suffix.lower()
        return EXTENSION_TO_LANGUAGE.get(ext)

    def parse_source(self, code: str, language_name: str, file_path: str = "") -> ParsedFileAST:
        """Parses source code into an AST and extracts symbols and references."""
        parser = self.get_parser_for_language(language_name)
        code_bytes = code.encode("utf-8", errors="replace")
        tree = parser.parse(code_bytes)

        parsed = ParsedFileAST(file_path=file_path, language=language_name)
        self._extract_symbols_and_references(tree.root_node, code_bytes, parsed, parent_name=None)
        return parsed

    def parse_file(self, file_path: str | Path) -> Optional[ParsedFileAST]:
        """Reads and parses a file from disk if the language is supported."""
        path = Path(file_path)
        lang = self.detect_language(path)
        if not lang or not path.is_file():
            return None

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            return self.parse_source(content, lang, file_path=str(path))
        except Exception:
            return None

    def _extract_symbols_and_references(
        self,
        node: Node,
        code_bytes: bytes,
        result: ParsedFileAST,
        parent_name: Optional[str] = None,
    ) -> None:
        """Recursively walks the AST to collect symbols, imports, and identifier references."""
        node_type = node.type
        current_symbol_name = parent_name

        # Detect Python and generic function/class nodes
        if node_type in ("function_definition", "async_function_definition", "function_declaration", "method_declaration", "method_definition"):
            symbol = self._parse_function(node, code_bytes, result.file_path, parent_name)
            if symbol:
                result.symbols.append(symbol)
                current_symbol_name = symbol.name
        elif node_type in ("class_definition", "class_declaration", "struct_specifier", "type_declaration"):
            symbol = self._parse_class(node, code_bytes, result.file_path, parent_name)
            if symbol:
                result.symbols.append(symbol)
                current_symbol_name = symbol.name
        elif node_type in ("import_statement", "import_from_statement"):
            import_text = self._get_node_text(node, code_bytes).strip()
            result.imports.append(import_text)
        elif node_type == "call" or node_type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node:
                call_name = self._get_node_text(func_node, code_bytes)
                if call_name:
                    result.referenced_identifiers.add(call_name.split(".")[-1])
        elif node_type == "identifier":
            ident = self._get_node_text(node, code_bytes)
            if ident and len(ident) > 1:
                result.referenced_identifiers.add(ident)

        # Recursively inspect child nodes
        for child in node.children:
            self._extract_symbols_and_references(child, code_bytes, result, current_symbol_name)

    def _parse_function(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        parent_name: Optional[str],
    ) -> Optional[CodeSymbol]:
        """Extracts function or method metadata."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = self._get_node_text(name_node, code_bytes)
        kind = "method" if parent_name else "function"

        # Parameters
        params: List[str] = []
        param_node = node.child_by_field_name("parameters")
        if param_node:
            for child in param_node.children:
                if child.type in ("identifier", "typed_parameter", "default_parameter", "parameter_declaration"):
                    child_id = child.child_by_field_name("name") or child
                    pname = self._get_node_text(child_id, code_bytes)
                    if pname and pname not in (",", "(", ")"):
                        params.append(pname)

        # First line as signature preview
        full_text = self._get_node_text(node, code_bytes)
        signature = full_text.split("\n")[0].strip()

        # Docstring extraction
        docstring = self._extract_docstring(node, code_bytes)

        return CodeSymbol(
            name=name,
            kind=kind,
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            signature=signature,
            docstring=docstring,
            parent_symbol=parent_name,
            parameters=params,
        )

    def _parse_class(
        self,
        node: Node,
        code_bytes: bytes,
        file_path: str,
        parent_name: Optional[str],
    ) -> Optional[CodeSymbol]:
        """Extracts class definition metadata."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        name = self._get_node_text(name_node, code_bytes)
        full_text = self._get_node_text(node, code_bytes)
        signature = full_text.split("\n")[0].strip()
        docstring = self._extract_docstring(node, code_bytes)

        return CodeSymbol(
            name=name,
            kind="class",
            file_path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            signature=signature,
            docstring=docstring,
            parent_symbol=parent_name,
        )

    def _extract_docstring(self, node: Node, code_bytes: bytes) -> Optional[str]:
        """Extracts docstring from class or function body."""
        body_node = node.child_by_field_name("body")
        if not body_node or not body_node.children:
            return None

        first_child = body_node.children[0]
        if first_child.type == "expression_statement":
            expr = first_child.children[0] if first_child.children else None
            if expr and expr.type == "string":
                raw_text = self._get_node_text(expr, code_bytes).strip()
                for quote in ('"""', "'''"):
                    if raw_text.startswith(quote) and raw_text.endswith(quote):
                        return raw_text[3:-3].strip()
                return raw_text.strip('"\' ')
        return None

    def _get_node_text(self, node: Node, code_bytes: bytes) -> str:
        """Retrieves raw utf-8 string for an AST node."""
        return code_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")
