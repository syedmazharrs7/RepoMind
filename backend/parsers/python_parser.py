import logging
import tree_sitter
import tree_sitter_python as tspython

from backend.parsers.base_parser import BaseParser
from backend.parser_exceptions import ParserInitializationError

logger = logging.getLogger(__name__)


class PythonParser(BaseParser):
    """Tree-sitter parser for Python source files."""

    def __init__(self) -> None:
        """
        Initialize the PythonParser and load the Python grammar.

        Raises:
            ParserInitializationError: If the Python grammar cannot be loaded.
        """
        try:
            language = tree_sitter.Language(tspython.language())
            super().__init__(language)
        except Exception as e:
            logger.error(f"Failed to load Python grammar: {e}")
            raise ParserInitializationError(f"Failed to load Python grammar: {e}") from e
