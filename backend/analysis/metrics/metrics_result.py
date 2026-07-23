"""
Repository Metrics Result model representing the final analysis output.
"""
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import json
from typing import Any, Dict

from backend.analysis.metrics.metric_models import (
    ArchitectureMetrics,
    ComplexityMetrics,
    DependencyMetrics,
    RepositoryMetadata,
    RepositoryMetrics,
    SymbolMetrics,
)
from backend.analysis.metrics.metric_statistics import MetricStatistics


def _serialize(obj: Any) -> Any:
    """Helper to recursively serialize objects including Enums and MetricStatistics."""
    if is_dataclass(obj) and not isinstance(obj, MetricStatistics):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, MetricStatistics):
        return {
            "count": obj.count,
            "sum": obj.sum,
            "mean": obj.mean,
            "median": obj.median,
            "min": obj.min,
            "max": obj.max,
            "p25": obj.p25,
            "p75": obj.p75,
            "p90": obj.p90,
            "p95": obj.p95,
            "p99": obj.p99,
            "histogram_bins": list(obj.histogram_bins),
            "histogram_counts": list(obj.histogram_counts),
        }
    elif isinstance(obj, tuple):
        return [_serialize(x) for x in obj]
    elif isinstance(obj, list):
        return [_serialize(x) for x in obj]
    elif isinstance(obj, dict):
        return {str(k): _serialize(v) for k, v in obj.items()}
    elif isinstance(obj, Enum):
        return obj.value
    return obj


@dataclass(frozen=True)
class RepositoryMetricsResult:
    """
    Immutable results container representing the final deterministic metrics report.
    Exposes dictionary, JSON, and specific model access APIs.
    """
    _metadata: RepositoryMetadata
    _repository_metrics: RepositoryMetrics
    _symbol_metrics: SymbolMetrics
    _dependency_metrics: DependencyMetrics
    _complexity_metrics: ComplexityMetrics
    _architecture_metrics: ArchitectureMetrics
    _health_score: float

    def repository_metadata(self) -> RepositoryMetadata:
        """Get the descriptive metadata for the repository."""
        return self._metadata

    def repository_metrics(self) -> RepositoryMetrics:
        """Get computed high-level repository-wide metrics."""
        return self._repository_metrics

    def symbol_metrics(self) -> SymbolMetrics:
        """Get computed semantic symbol statistics."""
        return self._symbol_metrics

    def dependency_metrics(self) -> DependencyMetrics:
        """Get computed dependency-level coupling metrics."""
        return self._dependency_metrics

    def complexity_metrics(self) -> ComplexityMetrics:
        """Get computed structural and graph complexity statistics."""
        return self._complexity_metrics

    def architecture_metrics(self) -> ArchitectureMetrics:
        """Get computed design and package architectural metrics."""
        return self._architecture_metrics

    def health_score(self) -> float:
        """Get the deterministic health score of the codebase [0-100]."""
        return self._health_score

    def statistics(self) -> Dict[str, MetricStatistics]:
        """Get a map of structural metric distributions."""
        return {
            "file_complexity": self._complexity_metrics.file_complexity,
            "class_complexity": self._complexity_metrics.class_complexity,
            "module_complexity": self._complexity_metrics.module_complexity,
        }

    def summary(self) -> Dict[str, Any]:
        """Get a high-level summary dictionary representing repository health."""
        return {
            "repository_name": self._metadata.repo_name,
            "health_score": self._health_score,
            "total_files": self._repository_metrics.total_files,
            "total_symbols": self._repository_metrics.total_symbols,
            "total_dependencies": self._repository_metrics.total_dependency_edges,
            "dependency_cycles": self._architecture_metrics.cycles,
            "layer_violations": self._architecture_metrics.layer_violations,
            "top_hotspots": list(self._architecture_metrics.hotspots),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert all computed results to a clean serializable dictionary."""
        return {
            "metadata": _serialize(self._metadata),
            "repository_metrics": _serialize(self._repository_metrics),
            "symbol_metrics": _serialize(self._symbol_metrics),
            "dependency_metrics": _serialize(self._dependency_metrics),
            "complexity_metrics": _serialize(self._complexity_metrics),
            "architecture_metrics": _serialize(self._architecture_metrics),
            "health_score": self._health_score,
        }

    def to_json(self) -> str:
        """Convert all computed results to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=2)
