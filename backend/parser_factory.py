import logging
import threading
from typing import Dict, Optional

from backend.repository_scanner import Language
from backend.parsers.base_parser import BaseParser
from backend.parser_exceptions import UnsupportedLanguageError

logger = logging.getLogger(__name__)


class ParserFactory:
    """Registry-based factory for obtaining language parsers as a reusable application service."""

    def __init__(self) -> None:
        """Initialize the ParserFactory with an empty registry."""
        self._registry: Dict[Language, BaseParser] = {}
        logger.debug("Initialized ParserFactory registry")

    def register_parser(self, language: Language, parser_instance: BaseParser) -> None:
        """
        Register a parser instance for a specific Language.

        Args:
            language: The Language enum.
            parser_instance: The parser instance inheriting from BaseParser.
        """
        self._registry[language] = parser_instance
        logger.info(f"Registered parser for language: {language}")

    def get_parser(self, language: Language) -> BaseParser:
        """
        Get the parser instance registered for the specified Language.

        Args:
            language: The Language enum.

        Returns:
            BaseParser: The registered parser instance.

        Raises:
            UnsupportedLanguageError: If no parser is registered for the given language.
        """
        if language not in self._registry:
            logger.error(f"No parser registered for language: {language}")
            raise UnsupportedLanguageError(f"No parser registered for language: {language}")
        return self._registry[language]


# Reusable global factory instance for application service usage
_default_factory: Optional[ParserFactory] = None
_lock = threading.Lock()


def get_default_factory() -> ParserFactory:
    """
    Get or initialize the default global ParserFactory instance populated with standard parsers.
    Uses a thread-safe double-checked locking pattern for concurrent safety.

    Returns:
        ParserFactory: The global ParserFactory instance.
    """
    global _default_factory
    if _default_factory is None:
        with _lock:
            if _default_factory is None:
                logger.info("Initializing default ParserFactory application service...")
                factory = ParserFactory()

                # Import and register standard language parsers
                from backend.parsers.python_parser import PythonParser
                from backend.parsers.javascript_parser import JavaScriptParser
                from backend.parsers.typescript_parser import TypeScriptParser

                factory.register_parser(Language.PYTHON, PythonParser())
                factory.register_parser(Language.JAVASCRIPT, JavaScriptParser())
                factory.register_parser(Language.TYPESCRIPT, TypeScriptParser())

                _default_factory = factory
    return _default_factory
