"""
Repository Metrics Analyzer. Computes RepositoryMetrics using cached file metrics.
"""
from typing import Tuple

from backend.analysis.metrics.analyzers.base_metric_analyzer import BaseMetricAnalyzer
from backend.analysis.metrics.metric_models import RepositoryAnalysisContext, RepositoryMetrics


class RepositoryMetricsAnalyzerImpl(BaseMetricAnalyzer):
    """
    Computes high-level analytical repository metrics by combining
    cached file characteristics and graph statistics.
    """

    def analyze(self, context: RepositoryAnalysisContext) -> RepositoryMetrics:
        # Retrieve cached metrics from FileMetricsAnalyzer
        files_data = context.cache.get("files_data", {})
        unique_files = context.cache.get("unique_files", ())
        unique_directories = context.cache.get("unique_directories", ())
        languages_count = context.cache.get("languages_count", {})
        largest_file = context.cache.get("largest_file", "")
        total_file_size = context.cache.get("total_file_size", 0)

        total_files = len(unique_files)
        directories = len(unique_directories)
        total_symbols = len(context.symbol_graph.nodes)
        total_dependency_edges = len(context.dependency_graph.edges)

        average_file_size = total_file_size / total_files if total_files > 0 else 0.0
        average_symbols_per_file = total_symbols / total_files if total_files > 0 else 0.0
        average_dependencies_per_file = total_dependency_edges / total_files if total_files > 0 else 0.0

        return RepositoryMetrics(
            total_files=total_files,
            source_files=total_files,  # Source files containing symbols
            directories=directories,
            languages=dict(languages_count),
            total_symbols=total_symbols,
            total_dependency_edges=total_dependency_edges,
            repository_size=total_file_size,
            largest_file=largest_file,
            average_file_size=average_file_size,
            average_symbols_per_file=average_symbols_per_file,
            average_dependencies_per_file=average_dependencies_per_file,
            metadata=context.metadata,
        )

    @property
    def name(self) -> str:
        return "RepositoryMetricsAnalyzer"

    @property
    def description(self) -> str:
        return "Computes summary metrics for files, sizes, languages, symbols, and dependencies."

    @property
    def supported_inputs(self) -> Tuple[type, ...]:
        return (RepositoryAnalysisContext,)
