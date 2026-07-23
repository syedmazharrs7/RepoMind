"""
Validator class to ensure metrics results are correct, complete, and consistent.
"""
from typing import Any

from backend.analysis.metrics.exceptions.metrics_exceptions import GraphConsistencyError, ValidationError
from backend.analysis.metrics.metric_models import (
    ArchitectureMetrics,
    ComplexityMetrics,
    DependencyMetrics,
    RepositoryAnalysisContext,
    RepositoryMetrics,
    SymbolMetrics,
)


class MetricsValidator:
    """
    Validates correctness, boundary limits (percentages/ratios), non-negativity,
    graph consistency, and deterministic sorting in metric results.
    """

    def validate(
        self,
        context: RepositoryAnalysisContext,
        repository_metrics: RepositoryMetrics,
        symbol_metrics: SymbolMetrics,
        dependency_metrics: DependencyMetrics,
        complexity_metrics: ComplexityMetrics,
        architecture_metrics: ArchitectureMetrics,
    ) -> None:
        """
        Validate all computed metrics against physical and logical constraints.

        Args:
            context: The repository analysis context.
            repository_metrics: Computed repository metrics.
            symbol_metrics: Computed symbol metrics.
            dependency_metrics: Computed dependency metrics.
            complexity_metrics: Computed complexity metrics.
            architecture_metrics: Computed architectural metrics.

        Raises:
            ValidationError: If value boundaries or percentage checks are violated.
            GraphConsistencyError: If counts don't align with graph state.
        """
        # 1. Missing Values check
        self._check_not_none(repository_metrics, "RepositoryMetrics")
        self._check_not_none(symbol_metrics, "SymbolMetrics")
        self._check_not_none(dependency_metrics, "DependencyMetrics")
        self._check_not_none(complexity_metrics, "ComplexityMetrics")
        self._check_not_none(architecture_metrics, "ArchitectureMetrics")

        # 2. Non-negative Counts check
        self._assert_non_negative(repository_metrics.total_files, "total_files")
        self._assert_non_negative(repository_metrics.source_files, "source_files")
        self._assert_non_negative(repository_metrics.directories, "directories")
        self._assert_non_negative(repository_metrics.total_symbols, "total_symbols")
        self._assert_non_negative(repository_metrics.total_dependency_edges, "total_dependency_edges")
        self._assert_non_negative(repository_metrics.repository_size, "repository_size")

        self._assert_non_negative(symbol_metrics.classes, "classes")
        self._assert_non_negative(symbol_metrics.functions, "functions")
        self._assert_non_negative(symbol_metrics.methods, "methods")
        self._assert_non_negative(symbol_metrics.variables, "variables")
        self._assert_non_negative(symbol_metrics.constants, "constants")
        self._assert_non_negative(symbol_metrics.interfaces, "interfaces")
        self._assert_non_negative(symbol_metrics.enums, "enums")
        self._assert_non_negative(symbol_metrics.modules, "modules")

        self._assert_non_negative(dependency_metrics.calls, "calls")
        self._assert_non_negative(dependency_metrics.imports, "imports")
        self._assert_non_negative(dependency_metrics.uses, "uses")
        self._assert_non_negative(dependency_metrics.references, "references")
        self._assert_non_negative(dependency_metrics.inheritance, "inheritance")
        self._assert_non_negative(dependency_metrics.implementation, "implementation")

        # 3. Invalid Percentages/Ratios checks (must be in [0.0, 1.0])
        self._assert_in_range(complexity_metrics.graph_density, 0.0, 1.0, "graph_density")
        self._assert_in_range(architecture_metrics.dependency_direction, 0.0, 1.0, "dependency_direction")
        self._assert_in_range(architecture_metrics.package_coupling, 0.0, 1.0, "package_coupling")
        self._assert_in_range(architecture_metrics.module_cohesion, 0.0, 1.0, "module_cohesion")

        # 4. Graph Consistency checks
        expected_symbols = len(context.symbol_graph.nodes)
        expected_edges = len(context.dependency_graph.edges)

        if repository_metrics.total_symbols != expected_symbols:
            raise GraphConsistencyError(
                f"RepositoryMetrics total_symbols ({repository_metrics.total_symbols}) "
                f"does not match SymbolGraph node count ({expected_symbols})."
            )

        if repository_metrics.total_dependency_edges != expected_edges:
            raise GraphConsistencyError(
                f"RepositoryMetrics total_dependency_edges ({repository_metrics.total_dependency_edges}) "
                f"does not match DependencyGraph edge count ({expected_edges})."
            )

        # Sum of specific symbols should not exceed total symbols in the graph
        summed_symbols = (
            symbol_metrics.classes
            + symbol_metrics.functions
            + symbol_metrics.methods
            + symbol_metrics.variables
            + symbol_metrics.constants
            + symbol_metrics.interfaces
            + symbol_metrics.enums
            + symbol_metrics.modules
        )
        if summed_symbols > expected_symbols:
            raise GraphConsistencyError(
                f"Sum of categorized symbols ({summed_symbols}) exceeds "
                f"total symbols in SymbolGraph ({expected_symbols})."
            )

        # Sum of specific dependency kinds should match total resolved dependency edges
        summed_edges = (
            dependency_metrics.calls
            + dependency_metrics.imports
            + dependency_metrics.uses
            + dependency_metrics.references
            + dependency_metrics.inheritance
            + dependency_metrics.implementation
        )
        if summed_edges != expected_edges:
            raise GraphConsistencyError(
                f"Sum of categorized dependency edges ({summed_edges}) does not match "
                f"total edges in DependencyGraph ({expected_edges})."
            )

    def _check_not_none(self, obj: Any, name: str) -> None:
        if obj is None:
            raise ValidationError(f"Computed metrics model '{name}' cannot be None.")
        for field_name, val in obj.__dict__.items():
            if val is None and field_name not in ("repo_path", "largest_class", "largest_module", "largest_file"):
                raise ValidationError(f"Field '{field_name}' in '{name}' is unexpectedly None.")

    def _assert_non_negative(self, val: Any, name: str) -> None:
        if isinstance(val, (int, float)) and val < 0:
            raise ValidationError(f"Metric '{name}' cannot be negative. Value: {val}")

    def _assert_in_range(self, val: float, low: float, high: float, name: str) -> None:
        if val < low or val > high:
            raise ValidationError(
                f"Metric '{name}' must be in range [{low}, {high}]. Value: {val}"
            )
