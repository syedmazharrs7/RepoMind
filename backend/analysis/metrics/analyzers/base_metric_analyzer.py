"""
Base interface and class for all metric analyzers in the engine.
"""
from abc import ABC, abstractmethod
from typing import Any, Tuple

from backend.analysis.metrics.metric_models import RepositoryAnalysisContext


class BaseMetricAnalyzer(ABC):
    """
    Abstract Base Class that every metric analyzer must inherit from.
    Enforces a consistent execution interface.
    """

    @abstractmethod
    def analyze(self, context: RepositoryAnalysisContext) -> Any:
        """
        Perform analysis on the provided repository context and return computed metric model.

        Args:
            context: The immutable RepositoryAnalysisContext containing graphs and configs.

        Returns:
            The specific metrics dataclass (e.g. SymbolMetrics, ComplexityMetrics, etc.).
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier/name of the analyzer."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable explanation of what this analyzer calculates."""
        pass

    @property
    @abstractmethod
    def supported_inputs(self) -> Tuple[type, ...]:
        """Tuple of input types supported by this analyzer (e.g. RepositoryAnalysisContext)."""
        pass
