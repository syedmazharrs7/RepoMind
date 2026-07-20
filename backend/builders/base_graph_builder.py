from abc import ABC, abstractmethod
from typing import List

from backend.symbol_graph import SymbolGraph
from backend.symbol_result import SymbolExtractionResult


class BaseGraphBuilder(ABC):
    """Abstract base class for graph builders."""

    @abstractmethod
    def build(
        self,
        extraction_results: List[SymbolExtractionResult],
        repository_name: str = "Repository",
    ) -> SymbolGraph:
        """
        Construct a SymbolGraph from symbol extraction results.

        Args:
            extraction_results: List of SymbolExtractionResult objects.
            repository_name: Optional name for the root repository node.

        Returns:
            SymbolGraph: The constructed immutable graph instance.
        """
        pass
