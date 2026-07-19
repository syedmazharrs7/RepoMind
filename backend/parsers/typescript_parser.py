import logging
import tree_sitter
import tree_sitter_typescript as tstypescript

from backend.parsers.base_parser import BaseParser
from backend.parser_exceptions import ParserInitializationError

logger = logging.getLogger(__name__)


class TypeScriptParser(BaseParser):
    """Tree-sitter parser for TypeScript source files."""

    def __init__(self) -> None:
        """
        Initialize the TypeScriptParser and load the TypeScript grammar.

        Raises:
            ParserInitializationError: If the TypeScript grammar cannot be loaded.
        """
        try:
            language = tree_sitter.Language(tstypescript.language_typescript())
            super().__init__(language)
        except Exception as e:
            logger.error(f"Failed to load TypeScript grammar: {e}")
            raise ParserInitializationError(f"Failed to load TypeScript grammar: {e}") from e
