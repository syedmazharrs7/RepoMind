import logging
from typing import Dict, List, Set

from backend.dependency_edge import DependencyEdge
from backend.dependency_graph_exceptions import DependencyValidationError
from backend.symbol_graph import SymbolGraph

logger = logging.getLogger(__name__)


class DependencyGraphValidator:
    """
    Validator responsible for verifying dependency graph edge integrity and checking
    for duplicate edges or dangling symbol IDs.
    """

    def validate(
        self,
        symbol_graph: SymbolGraph,
        edges: List[DependencyEdge],
    ) -> None:
        """
        Validate dependency edges against the SymbolGraph.

        Args:
            symbol_graph: The target SymbolGraph.
            edges: List of DependencyEdge objects to validate.

        Raises:
            DependencyValidationError: If duplicate edge IDs or dangling symbol IDs are detected.
        """
        logger.debug(f"Starting dependency graph validation for {len(edges)} edges")

        valid_symbol_ids: Set[str] = {n.id for n in symbol_graph.nodes}
        seen_edge_ids: Set[str] = set()

        for edge in edges:
            if edge.id in seen_edge_ids:
                logger.error(f"Duplicate dependency edge ID detected: '{edge.id}'")
                raise DependencyValidationError(f"Duplicate dependency edge ID found: '{edge.id}'")
            seen_edge_ids.add(edge.id)

            if edge.source_symbol_id not in valid_symbol_ids:
                logger.error(f"Dangling source symbol ID in edge '{edge.id}': '{edge.source_symbol_id}'")
                raise DependencyValidationError(
                    f"Dependency edge '{edge.id}' references non-existent source symbol ID: '{edge.source_symbol_id}'"
                )

            if edge.target_symbol_id not in valid_symbol_ids:
                logger.error(f"Dangling target symbol ID in edge '{edge.id}': '{edge.target_symbol_id}'")
                raise DependencyValidationError(
                    f"Dependency edge '{edge.id}' references non-existent target symbol ID: '{edge.target_symbol_id}'"
                )

        logger.debug("Dependency graph validation completed successfully with 0 errors")
