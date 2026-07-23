"""
Health Score Calculator. Computes a deterministic quality score for a repository.
"""
from backend.analysis.metrics.metric_models import (
    ArchitectureMetrics,
    ComplexityMetrics,
    DependencyMetrics,
    SymbolMetrics,
)


class HealthScoreCalculator:
    """
    Computes a deterministic, quality-focused health score between 0.0 and 100.0.
    Considers structural factors like circular dependencies, layer violations, nesting, and coupling.
    """

    def calculate(
        self,
        symbol_metrics: SymbolMetrics,
        dependency_metrics: DependencyMetrics,
        complexity_metrics: ComplexityMetrics,
        architecture_metrics: ArchitectureMetrics,
    ) -> float:
        """
        Calculate health score.

        Args:
            symbol_metrics: Computed symbol metrics.
            dependency_metrics: Computed dependency metrics.
            complexity_metrics: Computed complexity metrics.
            architecture_metrics: Computed architectural metrics.

        Returns:
            float: Deterministic score in range [0.0, 100.0].
        """
        score = 100.0

        # 1. Circular dependency penalty: cycles are high risk (max 40 pts penalty)
        cycles = dependency_metrics.circular_dependency_count
        cycle_penalty = min(cycles * 10.0, 40.0)
        score -= cycle_penalty

        # 2. Layer violations penalty: architectural decay (max 20 pts penalty)
        violations = architecture_metrics.layer_violations
        violation_penalty = min(violations * 5.0, 20.0)
        score -= violation_penalty

        # 3. Deepest nesting level penalty: readability check (max 10 pts penalty)
        nesting = symbol_metrics.deepest_nesting
        nesting_penalty = max(0.0, float(nesting - 5)) * 2.0
        score -= min(nesting_penalty, 10.0)

        # 4. Maximum inheritance depth penalty: class hierarchy check (max 10 pts penalty)
        inheritance = symbol_metrics.max_inheritance_depth
        inheritance_penalty = max(0.0, float(inheritance - 4)) * 3.0
        score -= min(inheritance_penalty, 10.0)

        # 5. Instability / coupling penalty: high coupling indicates fragile system (max 10 pts penalty)
        coupling = architecture_metrics.package_coupling
        # Coupling index from 0.0 to 1.0; penalize if coupling > 0.6
        coupling_penalty = max(0.0, coupling - 0.6) * 25.0
        score -= min(coupling_penalty, 10.0)

        # 6. Class/method complexity penalty (max 10 pts penalty)
        avg_class_complexity = complexity_metrics.class_complexity.mean
        complexity_penalty = max(0.0, avg_class_complexity - 10.0) * 0.5
        score -= min(complexity_penalty, 10.0)

        # Ensure bounds
        return max(0.0, min(score, 100.0))
