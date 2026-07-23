"""
Orchestrator class coordinating the execution of all metric analyzers.
"""
import logging
from typing import Optional

from backend.symbol_graph import SymbolGraph
from backend.dependency_graph import DependencyGraph
from backend.analysis.metrics.analyzer_factory import MetricAnalyzerFactory
from backend.analysis.metrics.health_score_calculator import HealthScoreCalculator
from backend.analysis.metrics.metric_models import (
    AnalysisConfiguration,
    RepositoryAnalysisContext,
    RepositoryMetadata,
    SharedAnalysisCache,
)
from backend.analysis.metrics.metrics_result import RepositoryMetricsResult
from backend.analysis.metrics.validators.metrics_validator import MetricsValidator

logger = logging.getLogger(__name__)


class RepositoryMetricsAnalyzer:
    """
    Main entry point and orchestrator for the Repository Metrics & Analysis Engine.
    Coordinates initialization of analysis contexts, deterministic analyzer runs,
    results validation, health scoring, and cache cleanup.
    """

    def __init__(
        self,
        factory: Optional[MetricAnalyzerFactory] = None,
        validator: Optional[MetricsValidator] = None,
        health_calculator: Optional[HealthScoreCalculator] = None,
    ) -> None:
        """
        Initialize orchestrator with factory registry, validator, and health calculator.
        Uses dependency injection to allow overriding implementations.
        """
        self._factory = factory or MetricAnalyzerFactory()
        self._validator = validator or MetricsValidator()
        self._health_calculator = health_calculator or HealthScoreCalculator()

    def analyze(
        self,
        symbol_graph: SymbolGraph,
        dependency_graph: DependencyGraph,
        metadata: RepositoryMetadata,
        config: Optional[AnalysisConfiguration] = None,
    ) -> RepositoryMetricsResult:
        """
        Run the complete repository metrics calculation process in deterministic order.

        Args:
            symbol_graph: Immutable semantic ownership SymbolGraph.
            dependency_graph: Immutable Symbol relationship DependencyGraph.
            metadata: Descriptive repository metadata.
            config: Optional AnalysisConfiguration.

        Returns:
            RepositoryMetricsResult containing validation-cleared, scored metrics.
        """
        active_config = config or AnalysisConfiguration()
        cache = SharedAnalysisCache()

        # Build context
        context = RepositoryAnalysisContext(
            symbol_graph=symbol_graph,
            dependency_graph=dependency_graph,
            metadata=metadata,
            config=active_config,
            cache=cache,
        )

        logger.info(f"Starting metrics analysis for repository: '{metadata.repo_name}'")

        try:
            # Deterministic execution order:
            # 1. File Metrics Analyzer (populates layout, size & lang cache)
            logger.debug("Executing FileMetricsAnalyzer...")
            self._factory.get("file").analyze(context)

            # 2. Repository Metrics Analyzer (computes summary aggregates)
            logger.debug("Executing RepositoryMetricsAnalyzerImpl...")
            repo_metrics = self._factory.get("repository").analyze(context)

            # 3. Symbol Metrics Analyzer (evaluates classes, methods, nesting, inheritance)
            logger.debug("Executing SymbolMetricsAnalyzer...")
            symbol_metrics = self._factory.get("symbol").analyze(context)

            # 4. Dependency Metrics Analyzer (measures coupling and cycles)
            logger.debug("Executing DependencyMetricsAnalyzer...")
            dependency_metrics = self._factory.get("dependency").analyze(context)

            # 5. Complexity Metrics Analyzer (calculates structural densities and degrees)
            logger.debug("Executing ComplexityMetricsAnalyzer...")
            complexity_metrics = self._factory.get("complexity").analyze(context)

            # 6. Architecture Metrics Analyzer (detects violations and hotspots)
            logger.debug("Executing ArchitectureMetricsAnalyzer...")
            architecture_metrics = self._factory.get("architecture").analyze(context)

            # Run boundary validations
            logger.debug("Validating computed metrics consistency...")
            self._validator.validate(
                context=context,
                repository_metrics=repo_metrics,
                symbol_metrics=symbol_metrics,
                dependency_metrics=dependency_metrics,
                complexity_metrics=complexity_metrics,
                architecture_metrics=architecture_metrics,
            )

            # Calculate deterministic health score
            logger.debug("Calculating repository health score...")
            health_score = self._health_calculator.calculate(
                symbol_metrics=symbol_metrics,
                dependency_metrics=dependency_metrics,
                complexity_metrics=complexity_metrics,
                architecture_metrics=architecture_metrics,
            )

            result = RepositoryMetricsResult(
                _metadata=metadata,
                _repository_metrics=repo_metrics,
                _symbol_metrics=symbol_metrics,
                _dependency_metrics=dependency_metrics,
                _complexity_metrics=complexity_metrics,
                _architecture_metrics=architecture_metrics,
                _health_score=health_score,
            )

            logger.info("Metrics analysis successfully completed.")
            return result

        finally:
            # Enforce cache cleanup to release memory
            cache.clear()
            logger.debug("Shared analysis cache cleared.")
