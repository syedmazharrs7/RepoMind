import logging
from abc import ABC
import tree_sitter

from backend.repository_scanner import SourceFile
from backend.parse_result import ParseResult
from backend.parser_exceptions import ParseFailureError

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base class for all language-specific parsers, completely language-agnostic."""

    def __init__(self, language: tree_sitter.Language) -> None:
        """
        Initialize the BaseParser with a specific Tree-sitter Language.

        Args:
            language: The Tree-sitter Language instance.
        """
        self._language = language
        self._parser = tree_sitter.Parser(self._language)
        logger.debug(f"Initialized Tree-sitter Parser for {self.__class__.__name__}")

    def parse_bytes(self, content_bytes: bytes, source_file: SourceFile, parse_time_ms: float) -> ParseResult:
        """
        Parse raw bytes into a Tree-sitter AST Tree.

        Args:
            content_bytes: The raw file content in bytes.
            source_file: The SourceFile object representing the file metadata.
            parse_time_ms: The elapsed time in milliseconds for the complete operation (I/O + parsing).

        Returns:
            ParseResult: Container representing the parsed AST tree and metadata.

        Raises:
            ParseFailureError: If parsing fails catastrophically.
        """
        try:
            tree = self._parser.parse(content_bytes)

            has_errors = tree.root_node.has_error
            error_message = "AST contains syntax errors" if has_errors else None

            return ParseResult(
                source_file=source_file,
                tree=tree,
                has_errors=has_errors,
                error_message=error_message,
                parse_time_ms=parse_time_ms
            )
        except Exception as e:
            logger.error(f"Tree-sitter parse failure for '{source_file.relative_path}': {e}")
            raise ParseFailureError(f"Tree-sitter failed to parse file at '{source_file.path}': {e}") from e
