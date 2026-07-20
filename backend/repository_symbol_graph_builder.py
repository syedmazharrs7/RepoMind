import logging
import time
from typing import List, Optional, Union

from backend.graph_builder_factory import (
    GraphBuilderFactory,
    get_default_graph_builder_factory,
)
from backend.graph_exceptions import GraphBuildError
from backend.graph_result import GraphResult
from backend.symbol_result import SymbolExtractionResult

logger = logging.getLogger(__name__)


class RepositorySymbolGraphBuilder:
    """
    Orchestrator class responsible for obtaining graph builders, processing symbol extraction
    results, measuring build performance, and returning GraphResult objects.
    """

    def __init__(self, factory: Optional[GraphBuilderFactory] = None) -> None:
        """
        Initialize RepositorySymbolGraphBuilder.

        Args:
            factory: Optional GraphBuilderFactory instance. If None, default factory is used.
        """
        self._factory = factory if factory is not None else get_default_graph_builder_factory()
        logger.debug("Initialized RepositorySymbolGraphBuilder orchestrator")

    def build_graph(
        self,
        extraction_results: Union[SymbolExtractionResult, List[SymbolExtractionResult]],
        repository_name: str = "Repository",
        builder_type: str = "HIERARCHY",
    ) -> GraphResult:
        """
        Build a SymbolGraph from one or more SymbolExtractionResult objects.

        Args:
            extraction_results: A single SymbolExtractionResult or list of SymbolExtractionResult objects.
            repository_name: Canonical name for the root repository node.
            builder_type: Graph builder strategy type string (default 'HIERARCHY').

        Returns:
            GraphResult: Container holding the built SymbolGraph, build time, and error details.
        """
        results_list = (
            [extraction_results]
            if isinstance(extraction_results, SymbolExtractionResult)
            else extraction_results
        )

        logger.info(
            f"Graph creation started for repository '{repository_name}' ({len(results_list)} file extraction results)"
        )
        start_time = time.perf_counter()

        try:
            builder = self._factory.get_builder(builder_type)
            symbol_graph = builder.build(results_list, repository_name=repository_name)

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            stats = symbol_graph.stats

            logger.info(
                f"Graph created for '{repository_name}': {stats.node_count} nodes, "
                f"{stats.edge_count} edges, max depth {stats.max_depth} in {duration_ms:.2f} ms"
            )

            return GraphResult(
                symbol_graph=symbol_graph,
                build_time_ms=duration_ms,
                has_errors=False,
                error_message=None,
            )
        except GraphBuildError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Graph construction failed for '{repository_name}': {e}")
            return GraphResult(
                symbol_graph=None,
                build_time_ms=duration_ms,
                has_errors=True,
                error_message=str(e),
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Unexpected error during graph construction for '{repository_name}': {e}")
            raise GraphBuildError(
                f"Unexpected error during graph construction for '{repository_name}': {e}"
            ) from e
