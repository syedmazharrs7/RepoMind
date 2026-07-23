"""
Complexity Metrics Analyzer. Computes ComplexityMetrics using graph structural analytics.
"""
from collections import deque
from typing import Dict, List, Set, Tuple

from backend.analysis.metrics.analyzers.base_metric_analyzer import BaseMetricAnalyzer
from backend.analysis.metrics.metric_models import ComplexityMetrics, RepositoryAnalysisContext
from backend.analysis.metrics.metric_statistics import MetricStatistics
from backend.symbol_kind import SymbolKind


class ComplexityMetricsAnalyzer(BaseMetricAnalyzer):
    """
    Computes structural complexities for files, classes, and modules,
    along with graph metrics like density, degrees, depths, and connected components.
    """

    def analyze(self, context: RepositoryAnalysisContext) -> ComplexityMetrics:
        symbol_graph = context.symbol_graph
        dependency_graph = context.dependency_graph

        files_data = context.cache.get("files_data", {})
        total_symbols = len(symbol_graph.nodes)
        total_edges = len(dependency_graph.edges)

        # 1. File Complexity
        file_complexities: Dict[str, float] = {}
        for file_path, data in files_data.items():
            file_symbols = data["symbols"]
            # Count incoming/outgoing edges involving symbols in this file
            edge_count = 0
            for node in file_symbols:
                edge_count += len(dependency_graph.incoming_edges(node.id))
                edge_count += len(dependency_graph.outgoing_edges(node.id))

            # Complexity = symbols_count + edges involving those symbols
            file_complexities[file_path] = float(len(file_symbols) + edge_count)

        # Cache file complexities for hotspot analysis in ArchitectureMetricsAnalyzer
        context.cache.set("file_complexities_dict", file_complexities)
        file_stats = MetricStatistics.from_values(
            list(file_complexities.values()),
            bin_count=context.config.histogram_bins,
        )

        # 2. Class Complexity
        class_complexities: List[float] = []
        for node in symbol_graph.nodes:
            if node.kind == SymbolKind.CLASS:
                descendants_count = len(symbol_graph.descendants(node.id))
                in_edges = len(dependency_graph.incoming_edges(node.id))
                out_edges = len(dependency_graph.outgoing_edges(node.id))
                class_complexities.append(float(1 + descendants_count + in_edges + out_edges))

        class_stats = MetricStatistics.from_values(
            class_complexities,
            bin_count=context.config.histogram_bins,
        )

        # 3. Module Complexity
        module_complexities: List[float] = []
        for node in symbol_graph.nodes:
            if node.kind == SymbolKind.MODULE:
                descendants_count = len(symbol_graph.descendants(node.id))
                in_edges = len(dependency_graph.incoming_edges(node.id))
                out_edges = len(dependency_graph.outgoing_edges(node.id))
                module_complexities.append(float(1 + descendants_count + in_edges + out_edges))

        module_stats = MetricStatistics.from_values(
            module_complexities,
            bin_count=context.config.histogram_bins,
        )

        # 4. Densities and degrees
        dependency_density = total_edges / total_symbols if total_symbols > 0 else 0.0
        graph_density = total_edges / (total_symbols * (total_symbols - 1)) if total_symbols > 1 else 0.0

        degrees = []
        max_deg = 0
        depths = []
        max_dep = 0

        for node in symbol_graph.nodes:
            deg = len(dependency_graph.incoming_edges(node.id)) + len(dependency_graph.outgoing_edges(node.id))
            degrees.append(deg)
            if deg > max_deg:
                max_deg = deg

            dep = len(symbol_graph.ancestors(node.id))
            depths.append(dep)
            if dep > max_dep:
                max_dep = dep

        average_graph_degree = sum(degrees) / total_symbols if total_symbols > 0 else 0.0
        average_depth = sum(depths) / total_symbols if total_symbols > 0 else 0.0

        # 5. Connected components (undirected)
        undirected_adj: Dict[str, Set[str]] = {node.id: set() for node in symbol_graph.nodes}
        for edge in dependency_graph.edges:
            src = edge.source_symbol_id
            tgt = edge.target_symbol_id
            if src in undirected_adj and tgt in undirected_adj:
                undirected_adj[src].add(tgt)
                undirected_adj[tgt].add(src)

        visited: Set[str] = set()
        connected_components = 0

        for node in symbol_graph.nodes:
            if node.id not in visited:
                connected_components += 1
                # BFS to mark all nodes in component
                queue = deque([node.id])
                visited.add(node.id)
                while queue:
                    curr = queue.popleft()
                    for neighbor in undirected_adj.get(curr, []):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

        return ComplexityMetrics(
            file_complexity=file_stats,
            class_complexity=class_stats,
            module_complexity=module_stats,
            dependency_density=dependency_density,
            graph_density=graph_density,
            average_graph_degree=average_graph_degree,
            maximum_graph_degree=max_deg,
            average_depth=average_depth,
            maximum_depth=max_dep,
            connected_components=connected_components,
        )

    @property
    def name(self) -> str:
        return "ComplexityMetricsAnalyzer"

    @property
    def description(self) -> str:
        return "Analyzes structural complexity distributions, densities, and connected component metrics."

    @property
    def supported_inputs(self) -> Tuple[type, ...]:
        return (RepositoryAnalysisContext,)
