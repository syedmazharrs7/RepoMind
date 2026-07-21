import logging
import time
from typing import List, Optional

from backend.dependency_analyzer_factory import (
    DependencyAnalyzerFactory,
    get_default_dependency_analyzer_factory,
)
from backend.dependency_candidate import DependencyCandidate
from backend.dependency_edge import DependencyEdge
from backend.dependency_graph import DependencyGraph, UnresolvedDependency
from backend.dependency_graph_exceptions import DependencyGraphError
from backend.dependency_graph_result import DependencyGraphResult
from backend.dependency_graph_validator import DependencyGraphValidator
from backend.dependency_resolver import DependencyResolver
from backend.parse_result import ParseResult
from backend.repository_scanner import Language
from backend.symbol_graph import SymbolGraph

logger = logging.getLogger(__name__)


class RepositoryDependencyGraphBuilder:
    """
    Orchestrator class responsible for obtaining language analyzers to extract dependency candidates,
    resolving candidates via DependencyResolver, validating graph edges with DependencyGraphValidator,
    and returning DependencyGraphResult instances.
    """

    def __init__(
        self,
        factory: Optional[DependencyAnalyzerFactory] = None,
        resolver: Optional[DependencyResolver] = None,
        validator: Optional[DependencyGraphValidator] = None,
    ) -> None:
        """
        Initialize RepositoryDependencyGraphBuilder.

        Args:
            factory: Optional DependencyAnalyzerFactory instance.
            resolver: Optional DependencyResolver instance.
            validator: Optional DependencyGraphValidator instance.
        """
        self._factory = factory if factory is not None else get_default_dependency_analyzer_factory()
        self._resolver = resolver if resolver is not None else DependencyResolver()
        self._validator = validator if validator is not None else DependencyGraphValidator()
        logger.debug("Initialized RepositoryDependencyGraphBuilder orchestrator")

    def build_dependency_graph(
        self,
        symbol_graph: SymbolGraph,
        parse_results: List[ParseResult],
    ) -> DependencyGraphResult:
        """
        Build an immutable DependencyGraph from a SymbolGraph and ParseResult ASTs.

        Args:
            symbol_graph: Immutable SymbolGraph from Module 5.
            parse_results: List of ParseResult objects from Module 3.

        Returns:
            DependencyGraphResult: Container with built DependencyGraph, timing, and error details.
        """
        logger.info(
            f"Dependency analysis started for {len(parse_results)} files ({len(symbol_graph.nodes)} symbols)"
        )
        start_time = time.perf_counter()

        try:
            # 1. Group parse results by language
            results_by_lang: dict[Language, List[ParseResult]] = {}
            for pr in parse_results:
                results_by_lang.setdefault(pr.source_file.language, []).append(pr)

            # 2. Extract DependencyCandidate objects using language analyzers
            candidates: List[DependencyCandidate] = []
            for lang, prs in results_by_lang.items():
                try:
                    analyzer = self._factory.get_analyzer(lang)
                    logger.debug(f"Selected analyzer {analyzer.__class__.__name__} for {lang}")
                    lang_candidates = analyzer.analyze(symbol_graph, prs)
                    candidates.extend(lang_candidates)
                except Exception as e:
                    logger.warning(f"Skipping language '{lang}' during dependency analysis: {e}")

            # 3. Resolve candidates into DependencyEdge objects via DependencyResolver
            resolved_edges, unresolved_deps = self._resolver.resolve_candidates(
                symbol_graph=symbol_graph,
                candidates=candidates,
            )

            # 4. Validate resolved graph edges
            self._validator.validate(symbol_graph=symbol_graph, edges=resolved_edges)

            # 5. Construct immutable DependencyGraph
            dep_graph = DependencyGraph(
                symbol_graph=symbol_graph,
                edges=resolved_edges,
                unresolved=unresolved_deps,
            )

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            stats = dep_graph.stats

            logger.info(
                f"Dependency graph created: {stats.dependency_count} edges resolved ({stats.call_count} calls, "
                f"{stats.import_count} imports, {stats.inheritance_count} inherits), {stats.unresolved_count} unresolved "
                f"in {duration_ms:.2f} ms"
            )

            return DependencyGraphResult(
                dependency_graph=dep_graph,
                analysis_time_ms=duration_ms,
                has_errors=False,
                error_message=None,
            )
        except DependencyGraphError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Dependency analysis failed: {e}")
            return DependencyGraphResult(
                dependency_graph=None,
                analysis_time_ms=duration_ms,
                has_errors=True,
                error_message=str(e),
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Unexpected error during dependency analysis: {e}")
            raise DependencyGraphError(f"Unexpected error during dependency analysis: {e}") from e
