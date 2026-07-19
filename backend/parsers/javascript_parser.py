import logging
import tree_sitter
import tree_sitter_javascript as tsjavascript

from backend.parsers.base_parser import BaseParser
from backend.parser_exceptions import ParserInitializationError

logger = logging.getLogger(__name__)


class JavaScriptParser(BaseParser):
    """Tree-sitter parser for JavaScript source files."""

    def __init__(self) -> None:
        """
        Initialize the JavaScriptParser and load the JavaScript grammar.

        Raises:
            ParserInitializationError: If the JavaScript grammar cannot be loaded.
        """
        try:
            language = tree_sitter.Language(tsjavascript.language())
            super().__init__(language)
        except Exception as e:
            logger.error(f"Failed to load JavaScript grammar: {e}")
            raise ParserInitializationError(f"Failed to load JavaScript grammar: {e}") from e
