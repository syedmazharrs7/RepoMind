"""
Dependency Metrics Analyzer. Computes DependencyMetrics from the DependencyGraph.
"""
from typing import Tuple

from backend.analysis.metrics.analyzers.base_metric_analyzer import BaseMetricAnalyzer
from backend.analysis.metrics.metric_models import DependencyMetrics, RepositoryAnalysisContext
from backend.dependency_edge_kind import DependencyEdgeKind


class DependencyMetricsAnalyzer(BaseMetricAnalyzer):
    """
    Analyzes semantic dependency edges, degrees, and cycles.
    """

    def analyze(self, context: RepositoryAnalysisContext) -> DependencyMetrics:
        dependency_graph = context.dependency_graph
        symbol_graph = context.symbol_graph

        calls = 0
        imports = 0
        uses = 0
        references = 0
        inheritance = 0
        implementation = 0

        # Count edge types
        for edge in dependency_graph.edges:
            kind = edge.kind
            if kind == DependencyEdgeKind.CALLS:
                calls += 1
            elif kind == DependencyEdgeKind.IMPORTS:
                imports += 1
            elif kind == DependencyEdgeKind.USES:
                uses += 1
            elif kind == DependencyEdgeKind.REFERENCES:
                references += 1
            elif kind == DependencyEdgeKind.INHERITS:
                inheritance += 1
            elif kind == DependencyEdgeKind.IMPLEMENTS:
                implementation += 1

        total_symbols = len(symbol_graph.nodes)
        total_edges = len(dependency_graph.edges)

        fan_in_sum = 0
        fan_out_sum = 0
        max_fan_in = 0
        max_fan_out = 0

        isolated_symbols = 0
        leaf_symbols = 0
        root_symbols = 0

        for node in symbol_graph.nodes:
            in_edges = len(dependency_graph.incoming_edges(node.id))
            out_edges = len(dependency_graph.outgoing_edges(node.id))

            fan_in_sum += in_edges
            fan_out_sum += out_edges

            if in_edges > max_fan_in:
                max_fan_in = in_edges
            if out_edges > max_fan_out:
                max_fan_out = out_edges

            # Classification
            if in_edges == 0 and out_edges == 0:
                isolated_symbols += 1
            elif out_edges == 0 and in_edges > 0:
                leaf_symbols += 1
            elif in_edges == 0 and out_edges > 0:
                root_symbols += 1

        average_fan_in = fan_in_sum / total_symbols if total_symbols > 0 else 0.0
        average_fan_out = fan_out_sum / total_symbols if total_symbols > 0 else 0.0
        average_dependencies = total_edges / total_symbols if total_symbols > 0 else 0.0

        # Find dependency cycles (circular dependency count)
        cycles = dependency_graph.find_dependency_cycles()
        circular_dependency_count = len(cycles)

        return DependencyMetrics(
            calls=calls,
            imports=imports,
            uses=uses,
            references=references,
            inheritance=inheritance,
            implementation=implementation,
            average_fan_in=average_fan_in,
            average_fan_out=average_fan_out,
            max_fan_in=max_fan_in,
            max_fan_out=max_fan_out,
            average_dependencies=average_dependencies,
            max_dependencies=max_fan_out,
            isolated_symbols=isolated_symbols,
            leaf_symbols=leaf_symbols,
            root_symbols=root_symbols,
            circular_dependency_count=circular_dependency_count,
        )

    @property
    def name(self) -> str:
        return "DependencyMetricsAnalyzer"

    @property
    def description(self) -> str:
        return "Analyzes coupling distributions, connection densities, and recursive cycle loops."

    @property
    def supported_inputs(self) -> Tuple[type, ...]:
        return (RepositoryAnalysisContext,)
