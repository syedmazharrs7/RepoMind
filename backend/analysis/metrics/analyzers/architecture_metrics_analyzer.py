"""
Architecture Metrics Analyzer. Computes ArchitectureMetrics including layer violations, coupling, cohesion, and hotspots.
"""
from pathlib import Path
from typing import Dict, List, Set, Tuple

from backend.analysis.metrics.analyzers.base_metric_analyzer import BaseMetricAnalyzer
from backend.analysis.metrics.analyzers.hotspot_strategy import (
    ComplexityDependencyStrategy,
    ComplexityOnlyStrategy,
    DependencyOnlyStrategy,
    HotspotStrategy,
)
from backend.analysis.metrics.metric_models import ArchitectureMetrics, RepositoryAnalysisContext
from backend.symbol_kind import SymbolKind


def _get_layer_index(file_path: str, rules: Dict[str, int]) -> int:
    """Determine layer index for a file path based on matching segments."""
    default_rules = {
        "db": 0, "database": 0, "model": 0, "models": 0, "entity": 0,
        "repo": 1, "repository": 1, "service": 2, "services": 2, "logic": 2,
        "controller": 3, "controllers": 3, "api": 3, "router": 3, "views": 3,
        "ui": 4, "view": 4, "components": 4
    }
    active_rules = rules if rules else default_rules
    
    # Split path and check segments
    parts = Path(file_path).parts
    for part in parts:
        part_lower = part.lower()
        if part_lower in active_rules:
            return active_rules[part_lower]
            
    # Default layer if no match
    return -1


class ArchitectureMetricsAnalyzer(BaseMetricAnalyzer):
    """
    Analyzes architectural constraints, hotspots, and component coupling/cohesion.
    """

    def analyze(self, context: RepositoryAnalysisContext) -> ArchitectureMetrics:
        symbol_graph = context.symbol_graph
        dependency_graph = context.dependency_graph

        files_data = context.cache.get("files_data", {})
        file_complexities = context.cache.get("file_complexities_dict", {})

        # 1. Layer Violations & Dependency Direction
        layer_violations = 0
        conforming_edges = 0
        total_valid_layer_edges = 0

        for edge in dependency_graph.edges:
            src_node = symbol_graph.find_node(edge.source_symbol_id)
            tgt_node = symbol_graph.find_node(edge.target_symbol_id)
            if src_node and tgt_node:
                src_layer = _get_layer_index(src_node.symbol.file_path, context.config.layer_rules)
                tgt_layer = _get_layer_index(tgt_node.symbol.file_path, context.config.layer_rules)

                if src_layer != -1 and tgt_layer != -1:
                    total_valid_layer_edges += 1
                    # A violation occurs if a lower layer depends on a higher layer
                    # E.g. db (0) depends on controller (3)
                    if src_layer < tgt_layer:
                        layer_violations += 1
                    else:
                        conforming_edges += 1

        dependency_direction = conforming_edges / total_valid_layer_edges if total_valid_layer_edges > 0 else 1.0

        # 2. Package Coupling & Cohesion
        # Define package as the directory of the file
        package_symbols: Dict[str, Set[str]] = {}
        symbol_to_package: Dict[str, str] = {}

        for node in symbol_graph.nodes:
            p = str(Path(node.symbol.file_path).parent).replace("\\", "/")
            if p == ".":
                p = "root"
            package_symbols.setdefault(p, set()).add(node.id)
            symbol_to_package[node.id] = p

        packages = list(package_symbols.keys())
        afferent_coupling: Dict[str, Set[str]] = {p: set() for p in packages}
        efferent_coupling: Dict[str, Set[str]] = {p: set() for p in packages}
        internal_edges_count: Dict[str, int] = {p: 0 for p in packages}
        external_edges_count: Dict[str, int] = {p: 0 for p in packages}

        for edge in dependency_graph.edges:
            src_id = edge.source_symbol_id
            tgt_id = edge.target_symbol_id
            src_pkg = symbol_to_package.get(src_id)
            tgt_pkg = symbol_to_package.get(tgt_id)

            if src_pkg and tgt_pkg:
                if src_pkg == tgt_pkg:
                    internal_edges_count[src_pkg] += 1
                else:
                    external_edges_count[src_pkg] += 1
                    external_edges_count[tgt_pkg] += 1
                    # Efferent: src_pkg depends on tgt_pkg
                    efferent_coupling[src_pkg].add(tgt_pkg)
                    # Afferent: tgt_pkg is depended on by src_pkg
                    afferent_coupling[tgt_pkg].add(src_pkg)

        instabilities = []
        cohesions = []

        for p in packages:
            ca = len(afferent_coupling[p])
            ce = len(efferent_coupling[p])
            instability = ce / (ca + ce) if (ca + ce) > 0 else 0.0
            instabilities.append(instability)

            int_edges = internal_edges_count[p]
            ext_edges = external_edges_count[p]
            cohesion = int_edges / (int_edges + ext_edges) if (int_edges + ext_edges) > 0 else 1.0
            cohesions.append(cohesion)

        package_coupling = sum(instabilities) / len(packages) if packages else 0.0
        module_cohesion = sum(cohesions) / len(packages) if packages else 1.0

        # 3. Hotspot Strategy Pattern
        strategy_name = context.config.hotspot_strategy.lower()
        strategy: HotspotStrategy
        if strategy_name in ("dependency_only", "dependency"):
            strategy = DependencyOnlyStrategy()
        elif strategy_name in ("complexity_only", "complexity"):
            strategy = ComplexityOnlyStrategy()
        else:
            strategy = ComplexityDependencyStrategy()

        # Compute hotspot score for each file
        file_hotspots: List[Tuple[str, float]] = []
        for file_path, data in files_data.items():
            complexity = file_complexities.get(file_path, 0.0)
            # Count connections
            degree = 0
            for node in data["symbols"]:
                degree += len(dependency_graph.incoming_edges(node.id))
                degree += len(dependency_graph.outgoing_edges(node.id))

            score = strategy.calculate_score(complexity, degree)
            file_hotspots.append((file_path, score))

        # Sort: score descending, path ascending
        file_hotspots.sort(key=lambda item: (-item[1], item[0]))
        hotspots = tuple(item[0] for item in file_hotspots[:5])

        # 4. Most Depended-on Symbols (fan-in)
        symbol_fan_in: List[Tuple[str, int]] = []
        for node in symbol_graph.nodes:
            in_count = len(dependency_graph.incoming_edges(node.id))
            symbol_fan_in.append((node.qualified_name, in_count))

        symbol_fan_in.sort(key=lambda item: (-item[1], item[0]))
        most_depended_on = tuple(item[0] for item in symbol_fan_in[:5])

        # 5. Most Connected Files (sum of internal/external connections)
        file_connections: List[Tuple[str, int]] = []
        for file_path, data in files_data.items():
            conn_count = 0
            for node in data["symbols"]:
                conn_count += len(dependency_graph.incoming_edges(node.id))
                conn_count += len(dependency_graph.outgoing_edges(node.id))
            file_connections.append((file_path, conn_count))

        file_connections.sort(key=lambda item: (-item[1], item[0]))
        most_connected_files = tuple(item[0] for item in file_connections[:5])

        # 6. Most Central Modules
        # Find MODULE symbols in symbol graph, else use packages
        module_nodes = [node for node in symbol_graph.nodes if node.kind == SymbolKind.MODULE]
        module_centrality: List[Tuple[str, int]] = []
        if module_nodes:
            for node in module_nodes:
                conn_count = len(dependency_graph.incoming_edges(node.id)) + len(dependency_graph.outgoing_edges(node.id))
                module_centrality.append((node.qualified_name, conn_count))
        else:
            # Fallback to packages
            for p in packages:
                conn_count = len(afferent_coupling[p]) + len(efferent_coupling[p])
                module_centrality.append((p, conn_count))

        module_centrality.sort(key=lambda item: (-item[1], item[0]))
        most_central_modules = tuple(item[0] for item in module_centrality[:5])

        # 7. Cycles count
        cycles_count = len(dependency_graph.find_dependency_cycles())

        return ArchitectureMetrics(
            layer_violations=layer_violations,
            dependency_direction=dependency_direction,
            cycles=cycles_count,
            package_coupling=package_coupling,
            module_cohesion=module_cohesion,
            hotspots=hotspots,
            most_depended_on_symbols=most_depended_on,
            most_connected_files=most_connected_files,
            most_central_modules=most_central_modules,
        )

    @property
    def name(self) -> str:
        return "ArchitectureMetricsAnalyzer"

    @property
    def description(self) -> str:
        return "Detects architectural layer violations, package instability, cohesions, and hotspots."

    @property
    def supported_inputs(self) -> Tuple[type, ...]:
        return (RepositoryAnalysisContext,)
