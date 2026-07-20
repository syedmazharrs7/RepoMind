import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple

import tree_sitter

from backend.parse_result import ParseResult
from backend.repository_scanner import Language
from backend.symbol import Symbol, generate_symbol_id
from backend.symbol_exceptions import InvalidASTError
from backend.symbol_kind import SymbolKind

logger = logging.getLogger(__name__)


class ASTNodeContext:
    """Helper context wrapper around a Tree-sitter Node and source code bytes."""

    def __init__(self, node: tree_sitter.Node, code_bytes: bytes) -> None:
        self.node = node
        self.code_bytes = code_bytes

    @property
    def type(self) -> str:
        """Node type string."""
        return self.node.type

    @property
    def text(self) -> str:
        """Decoded text representation of the node from source bytes."""
        if not self.code_bytes:
            return ""
        raw = self.code_bytes[self.node.start_byte : self.node.end_byte]
        return raw.decode("utf-8", errors="replace")

    @property
    def start_line(self) -> int:
        """1-indexed start line number."""
        return self.node.start_point[0] + 1

    @property
    def end_line(self) -> int:
        """1-indexed end line number."""
        return self.node.end_point[0] + 1

    @property
    def start_column(self) -> int:
        """0-indexed start column position."""
        return self.node.start_point[1]

    @property
    def end_column(self) -> int:
        """0-indexed end column position."""
        return self.node.end_point[1]

    def child_by_field_name(self, name: str) -> Optional["ASTNodeContext"]:
        """
        Retrieve child node by Tree-sitter field name.

        Args:
            name: Field name in the Tree-sitter grammar.

        Returns:
            Optional[ASTNodeContext]: Wrapped child context if found, None otherwise.
        """
        child = self.node.child_by_field_name(name)
        return ASTNodeContext(child, self.code_bytes) if child is not None else None

    def children_by_type(self, type_name: str) -> List["ASTNodeContext"]:
        """
        Retrieve all immediate children matching the specified AST node type.

        Args:
            type_name: Tree-sitter AST node type string.

        Returns:
            List[ASTNodeContext]: List of matching child node contexts.
        """
        return [
            ASTNodeContext(c, self.code_bytes)
            for c in self.node.children
            if c.type == type_name
        ]

    def find_first_child_of_type(self, type_name: str) -> Optional["ASTNodeContext"]:
        """
        Find the first immediate child matching the specified AST node type.

        Args:
            type_name: Tree-sitter AST node type string.

        Returns:
            Optional[ASTNodeContext]: First matching child node context, or None.
        """
        for c in self.node.children:
            if c.type == type_name:
                return ASTNodeContext(c, self.code_bytes)
        return None


class BaseSymbolExtractor(ABC):
    """Abstract base class for all language-specific symbol extractors."""

    def _get_code_bytes(self, parse_result: ParseResult) -> bytes:
        """
        Read source file raw bytes from ParseResult.

        Args:
            parse_result: The ParseResult container.

        Returns:
            bytes: Source code byte sequence, or b"" if unreadable.
        """
        try:
            return parse_result.source_file.path.read_bytes()
        except (OSError, IOError, ValueError) as e:
            logger.warning(f"Failed to read source bytes for '{parse_result.source_file.relative_path}': {e}")
            return b""

    def _derive_module_name(self, relative_path: str) -> str:
        """
        Derive a clean module name from a file's relative path.
        Example: 'backend/utils/parser.py' -> 'backend.utils.parser'

        Args:
            relative_path: Relative file path string.

        Returns:
            str: Clean dot-separated module qualified name.
        """
        p = Path(relative_path)
        parts = list(p.parts)
        if parts and parts[-1].endswith(p.suffix):
            parts[-1] = p.stem
        name = ".".join(parts)
        return name if name else "module"

    def _create_module_symbol(
        self, parse_result: ParseResult, root_ctx: ASTNodeContext
    ) -> Symbol:
        """
        Create the root MODULE symbol for a source file.

        Args:
            parse_result: The ParseResult container.
            root_ctx: ASTNodeContext wrapping the root AST node.

        Returns:
            Symbol: The root MODULE symbol representing the source file.
        """
        rel_path = parse_result.source_file.relative_path
        mod_name = self._derive_module_name(rel_path)
        lang = parse_result.source_file.language

        symbol_id = generate_symbol_id(
            language=lang,
            file_path=rel_path,
            qualified_name=mod_name,
            kind=SymbolKind.MODULE,
        )

        return Symbol(
            id=symbol_id,
            name=mod_name,
            qualified_name=mod_name,
            kind=SymbolKind.MODULE,
            language=lang,
            file_path=rel_path,
            start_line=root_ctx.start_line,
            end_line=root_ctx.end_line,
            start_column=root_ctx.start_column,
            end_column=root_ctx.end_column,
            parent_symbol=None,
            signature=f"module {mod_name}",
            docstring=None,
            decorators=(),
            visibility="public",
            is_async=False,
            is_exported=True,
        )

    def extract(self, parse_result: ParseResult) -> List[Symbol]:
        """
        Extract semantic symbols from a ParseResult AST.

        Args:
            parse_result: The ParseResult object from Module 3.

        Returns:
            List[Symbol]: List of extracted Symbol objects starting with the root MODULE symbol.

        Raises:
            InvalidASTError: If tree or root_node is missing.
        """
        if parse_result.tree is None or parse_result.tree.root_node is None:
            logger.error(f"Invalid AST: tree is missing for '{parse_result.source_file.relative_path}'")
            raise InvalidASTError(f"AST missing for file '{parse_result.source_file.relative_path}'")

        code_bytes = self._get_code_bytes(parse_result)
        root_ctx = ASTNodeContext(parse_result.tree.root_node, code_bytes)

        module_symbol = self._create_module_symbol(parse_result, root_ctx)
        symbols: List[Symbol] = [module_symbol]

        self._extract_language_symbols(parse_result, root_ctx, module_symbol, symbols)

        return symbols

    @abstractmethod
    def _extract_language_symbols(
        self,
        parse_result: ParseResult,
        root_ctx: ASTNodeContext,
        module_symbol: Symbol,
        symbols_list: List[Symbol],
    ) -> None:
        """Language-specific single-pass AST traversal to extract symbols."""
        pass
