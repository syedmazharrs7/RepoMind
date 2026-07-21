import logging
import threading
from typing import Dict, Optional

from backend.analyzers.base_dependency_analyzer import BaseDependencyAnalyzer
from backend.dependency_graph_exceptions import UnsupportedLanguageError
from backend.repository_scanner import Language

logger = logging.getLogger(__name__)


class DependencyAnalyzerFactory:
    """Registry-based factory for obtaining language-specific dependency analyzers."""

    def __init__(self) -> None:
        """Initialize factory with an empty registry."""
        self._registry: Dict[Language, BaseDependencyAnalyzer] = {}
        logger.debug("Initialized DependencyAnalyzerFactory registry")

    def register_analyzer(
        self, language: Language, analyzer_instance: BaseDependencyAnalyzer
    ) -> None:
        """
        Register a dependency analyzer instance for a specified Language.

        Args:
            language: The Language enum.
            analyzer_instance: Instance of BaseDependencyAnalyzer.
        """
        self._registry[language] = analyzer_instance
        logger.info(f"Registered dependency analyzer for language: {language}")

    def get_analyzer(self, language: Language) -> BaseDependencyAnalyzer:
        """
        Get the dependency analyzer instance registered for Language.

        Args:
            language: The Language enum.

        Returns:
            BaseDependencyAnalyzer: Registered analyzer instance.

        Raises:
            UnsupportedLanguageError: If no analyzer is registered for the given language.
        """
        if language not in self._registry:
            logger.error(f"No dependency analyzer registered for language: {language}")
            raise UnsupportedLanguageError(
                f"No dependency analyzer registered for language: {language}"
            )
        return self._registry[language]


# Reusable global factory instance for application service usage
_default_factory: Optional[DependencyAnalyzerFactory] = None
_lock = threading.Lock()


def get_default_dependency_analyzer_factory() -> DependencyAnalyzerFactory:
    """
    Get or initialize the default global DependencyAnalyzerFactory instance.
    Thread-safe double-checked locking.

    Returns:
        DependencyAnalyzerFactory: Default global factory instance.
    """
    global _default_factory
    if _default_factory is None:
        with _lock:
            if _default_factory is None:
                logger.info("Initializing default DependencyAnalyzerFactory service...")
                factory = DependencyAnalyzerFactory()

                from backend.analyzers.javascript_dependency_analyzer import JavaScriptDependencyAnalyzer
                from backend.analyzers.python_dependency_analyzer import PythonDependencyAnalyzer
                from backend.analyzers.typescript_dependency_analyzer import TypeScriptDependencyAnalyzer

                factory.register_analyzer(Language.PYTHON, PythonDependencyAnalyzer())
                factory.register_analyzer(Language.JAVASCRIPT, JavaScriptDependencyAnalyzer())
                factory.register_analyzer(Language.TYPESCRIPT, TypeScriptDependencyAnalyzer())

                _default_factory = factory
    return _default_factory
