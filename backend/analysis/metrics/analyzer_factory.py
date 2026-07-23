"""
Registry-based factory for obtaining metric analyzers.
"""
from typing import Dict, List, Tuple, Type

from backend.analysis.metrics.analyzers.base_metric_analyzer import BaseMetricAnalyzer
from backend.analysis.metrics.analyzers.file_metrics_analyzer import FileMetricsAnalyzer
from backend.analysis.metrics.analyzers.repository_metrics_analyzer_impl import RepositoryMetricsAnalyzerImpl
from backend.analysis.metrics.analyzers.symbol_metrics_analyzer import SymbolMetricsAnalyzer
from backend.analysis.metrics.analyzers.dependency_metrics_analyzer import DependencyMetricsAnalyzer
from backend.analysis.metrics.analyzers.complexity_metrics_analyzer import ComplexityMetricsAnalyzer
from backend.analysis.metrics.analyzers.architecture_metrics_analyzer import ArchitectureMetricsAnalyzer
from backend.analysis.metrics.exceptions.metrics_exceptions import DuplicateAnalyzerError
from backend.repository_scanner import Language


class MetricAnalyzerFactory:
    """
    Factory registry for managing and instantiating metric analyzers.
    Avoids switch-case conditionals and supports dynamic registration.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Type[BaseMetricAnalyzer]] = {}
        # Pre-register default analyzers
        self.register("file", FileMetricsAnalyzer)
        self.register("repository", RepositoryMetricsAnalyzerImpl)
        self.register("symbol", SymbolMetricsAnalyzer)
        self.register("dependency", DependencyMetricsAnalyzer)
        self.register("complexity", ComplexityMetricsAnalyzer)
        self.register("architecture", ArchitectureMetricsAnalyzer)

    def register(self, name: str, analyzer_cls: Type[BaseMetricAnalyzer]) -> None:
        """
        Register a new metric analyzer.

        Args:
            name: The registry key identifier.
            analyzer_cls: The analyzer class definition.

        Raises:
            DuplicateAnalyzerError: If the analyzer name is already registered.
        """
        if name in self._registry:
            raise DuplicateAnalyzerError(f"Analyzer '{name}' is already registered in the factory.")
        self._registry[name] = analyzer_cls

    def get(self, name: str) -> BaseMetricAnalyzer:
        """
        Get an instance of a registered analyzer.

        Args:
            name: The registry key identifier.

        Returns:
            BaseMetricAnalyzer instance.

        Raises:
            KeyError: If the analyzer name is not registered.
        """
        if name not in self._registry:
            raise KeyError(f"Analyzer '{name}' is not registered.")
        return self._registry[name]()

    def supported_languages(self) -> List[str]:
        """Get a list of languages supported by the repository scanner module."""
        return [lang.value for lang in Language]

    @property
    def registered_analyzers(self) -> Tuple[str, ...]:
        """Get tuple of all registered analyzer keys."""
        return tuple(self._registry.keys())
