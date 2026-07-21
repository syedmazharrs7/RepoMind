import logging
from abc import ABC, abstractmethod
from typing import Dict, List

from backend.dependency_candidate import DependencyCandidate
from backend.graph_node import GraphNode
from backend.parse_result import ParseResult
from backend.symbol_graph import SymbolGraph

logger = logging.getLogger(__name__)


class BaseDependencyAnalyzer(ABC):
    """Abstract base class for all language-specific dependency analyzers."""

    def analyze(
        self,
        symbol_graph: SymbolGraph,
        parse_results: List[ParseResult],
    ) -> List[DependencyCandidate]:
        """
        Analyze AST parse results and produce raw DependencyCandidate objects.

        Args:
            symbol_graph: Immutable SymbolGraph.
            parse_results: List of ParseResult objects for source files.

        Returns:
            List[DependencyCandidate]: Extracted dependency candidate objects.
        """
        # Map nodes by file_path
        nodes_by_file: Dict[str, List[GraphNode]] = {}
        for n in symbol_graph.nodes:
            nodes_by_file.setdefault(n.symbol.file_path, []).append(n)

        candidates: List[DependencyCandidate] = []
        for pr in parse_results:
            file_path = pr.source_file.relative_path
            file_symbols = nodes_by_file.get(file_path, [])
            if pr.tree and pr.tree.root_node:
                file_candidates = self._extract_candidates_for_file(pr, file_symbols)
                candidates.extend(file_candidates)

        return candidates

    @abstractmethod
    def _extract_candidates_for_file(
        self,
        parse_result: ParseResult,
        file_symbols: List[GraphNode],
    ) -> List[DependencyCandidate]:
        """Extract dependency candidates from a single file's AST."""
        pass
