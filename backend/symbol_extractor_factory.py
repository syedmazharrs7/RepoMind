import logging
import threading
from typing import Dict, Optional

from backend.extractors.base_symbol_extractor import BaseSymbolExtractor
from backend.repository_scanner import Language
from backend.symbol_exceptions import UnsupportedLanguageError

logger = logging.getLogger(__name__)


class LanguageExtractorFactory:
    """Registry-based factory for obtaining language-specific symbol extractors."""

    def __init__(self) -> None:
        """Initialize the factory with an empty registry."""
        self._registry: Dict[Language, BaseSymbolExtractor] = {}
        logger.debug("Initialized LanguageExtractorFactory registry")

    def register_extractor(
        self, language: Language, extractor_instance: BaseSymbolExtractor
    ) -> None:
        """
        Register a symbol extractor instance for a specific Language.

        Args:
            language: The Language enum.
            extractor_instance: The extractor instance inheriting from BaseSymbolExtractor.
        """
        self._registry[language] = extractor_instance
        logger.info(f"Registered symbol extractor for language: {language}")

    def get_extractor(self, language: Language) -> BaseSymbolExtractor:
        """
        Get the extractor instance registered for the specified Language.

        Args:
            language: The Language enum.

        Returns:
            BaseSymbolExtractor: Registered extractor instance.

        Raises:
            UnsupportedLanguageError: If no extractor is registered for the language.
        """
        if language not in self._registry:
            logger.error(f"No symbol extractor registered for language: {language}")
            raise UnsupportedLanguageError(
                f"No symbol extractor registered for language: {language}"
            )
        return self._registry[language]


# Alias for backward compatibility / explicit naming
SymbolExtractorFactory = LanguageExtractorFactory

# Reusable global factory instance for application service usage
_default_factory: Optional[LanguageExtractorFactory] = None
_lock = threading.Lock()


def get_default_extractor_factory() -> LanguageExtractorFactory:
    """
    Get or initialize the default global LanguageExtractorFactory instance.
    Thread-safe double-checked locking.

    Returns:
        LanguageExtractorFactory: Default global factory instance.
    """
    global _default_factory
    if _default_factory is None:
        with _lock:
            if _default_factory is None:
                logger.info("Initializing default LanguageExtractorFactory service...")
                factory = LanguageExtractorFactory()

                from backend.extractors.javascript_symbol_extractor import JavaScriptSymbolExtractor
                from backend.extractors.python_symbol_extractor import PythonSymbolExtractor
                from backend.extractors.typescript_symbol_extractor import TypeScriptSymbolExtractor

                factory.register_extractor(Language.PYTHON, PythonSymbolExtractor())
                factory.register_extractor(Language.JAVASCRIPT, JavaScriptSymbolExtractor())
                factory.register_extractor(Language.TYPESCRIPT, TypeScriptSymbolExtractor())

                _default_factory = factory
    return _default_factory
