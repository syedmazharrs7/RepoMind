"""
Immutable models for Repository Metrics & Analysis Engine.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from backend.symbol_graph import SymbolGraph
from backend.dependency_graph import DependencyGraph
from backend.analysis.metrics.metric_statistics import MetricStatistics


@dataclass(frozen=True)
class AnalysisConfiguration:
    """
    Configuration parameters for metrics calculation.
    Decoupled from code logic to allow extensibility.
    """
    hotspot_strategy: str = "default"
    ignored_folders: Tuple[str, ...] = (".git", "venv", ".venv", "node_modules", "dist", "build")
    layer_rules: Dict[str, int] = field(default_factory=dict)
    histogram_bins: int = 10
    metric_thresholds: Dict[str, float] = field(default_factory=dict)
    scoring_weights: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class RepositoryMetadata:
    """
    Descriptive, non-analytical metadata for the repository.
    """
    repo_name: str
    repo_path: Optional[str]
    detected_languages: Tuple[str, ...]
    scanned_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SharedAnalysisCache:
    """
    Internally mutable cache container to share intermediate computation
    results during a single repository analysis pass.
    """
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def clear(self) -> None:
        self._cache.clear()


@dataclass(frozen=True)
class RepositoryAnalysisContext:
    """
    Immutable orchestrator context container.
    Wraps all inputs required for metric analyzers.
    """
    symbol_graph: SymbolGraph
    dependency_graph: DependencyGraph
    metadata: RepositoryMetadata
    config: AnalysisConfiguration
    cache: SharedAnalysisCache


@dataclass(frozen=True)
class RepositoryMetrics:
    """
    High-level, analytical repository metrics.
    """
    total_files: int
    source_files: int
    directories: int
    languages: Dict[str, int]
    total_symbols: int
    total_dependency_edges: int
    repository_size: int
    largest_file: str
    average_file_size: float
    average_symbols_per_file: float
    average_dependencies_per_file: float
    metadata: RepositoryMetadata


@dataclass(frozen=True)
class SymbolMetrics:
    """
    Metrics related to semantic symbols in the repository.
    """
    classes: int
    functions: int
    methods: int
    variables: int
    constants: int
    interfaces: int
    enums: int
    modules: int
    visibility_public: int
    visibility_private: int
    visibility_protected: int
    average_methods_per_class: float
    largest_class: str  # qualified_name of class
    largest_module: str  # qualified_name of module
    deepest_nesting: int
    max_inheritance_depth: int


@dataclass(frozen=True)
class DependencyMetrics:
    """
    Metrics calculated over the semantic dependency graph relationships.
    """
    calls: int
    imports: int
    uses: int
    references: int
    inheritance: int
    implementation: int
    average_fan_in: float
    average_fan_out: float
    max_fan_in: int
    max_fan_out: int
    average_dependencies: float
    max_dependencies: int
    isolated_symbols: int
    leaf_symbols: int
    root_symbols: int
    circular_dependency_count: int


@dataclass(frozen=True)
class ComplexityMetrics:
    """
    Metrics describing structural, hierarchical, and graph complexity.
    """
    file_complexity: MetricStatistics
    class_complexity: MetricStatistics
    module_complexity: MetricStatistics
    dependency_density: float
    graph_density: float
    average_graph_degree: float
    maximum_graph_degree: int
    average_depth: float
    maximum_depth: int
    connected_components: int


@dataclass(frozen=True)
class ArchitectureMetrics:
    """
    Metrics measuring structural coupling, cohesion, layer violations, and hotspots.
    """
    layer_violations: int
    dependency_direction: float
    cycles: int
    package_coupling: float
    module_cohesion: float
    hotspots: Tuple[str, ...]
    most_depended_on_symbols: Tuple[str, ...]
    most_connected_files: Tuple[str, ...]
    most_central_modules: Tuple[str, ...]
