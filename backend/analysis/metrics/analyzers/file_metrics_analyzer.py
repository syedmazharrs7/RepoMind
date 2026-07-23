"""
File Metrics Analyzer. Runs first to extract and cache file-level structural metadata.
"""
from pathlib import Path
from typing import Dict, List, Tuple

from backend.analysis.metrics.analyzers.base_metric_analyzer import BaseMetricAnalyzer
from backend.analysis.metrics.metric_models import RepositoryAnalysisContext


class FileMetricsAnalyzer(BaseMetricAnalyzer):
    """
    Analyzes physical and logical properties of files in the repository.
    Caches intermediate calculations in context.cache to support downstream analyzers.
    """

    def analyze(self, context: RepositoryAnalysisContext) -> Dict[str, Dict]:
        symbol_graph = context.symbol_graph
        repo_path_str = context.metadata.repo_path

        # Group symbols by file path
        symbols_by_file: Dict[str, List] = {}
        for node in symbol_graph.nodes:
            file_path = node.symbol.file_path
            symbols_by_file.setdefault(file_path, []).append(node)

        files_data = {}
        unique_dirs = set()
        languages_count: Dict[str, int] = {}
        total_size = 0
        largest_file = ""
        largest_file_size = -1

        for file_path, nodes in symbols_by_file.items():
            # Skip root/directory placeholders
            if not file_path or file_path == "." or file_path == "root":
                continue
            p = Path(file_path)
            if repo_path_str:
                abs_path = Path(repo_path_str) / file_path
                try:
                    if abs_path.is_dir():
                        continue
                except (OSError, PermissionError):
                    pass
            if not p.suffix:
                continue

            # Calculate physical file size if possible
            size_bytes = 0
            if repo_path_str:
                abs_path = Path(repo_path_str) / file_path
                try:
                    if abs_path.is_file():
                        size_bytes = abs_path.stat().st_size
                except (OSError, PermissionError):
                    pass

            # Fallback size estimation using symbol lines if physical check is zero
            if size_bytes == 0 and nodes:
                # Max line span across symbols
                lines = [n.symbol.end_line for n in nodes if n.symbol.end_line]
                max_line = max(lines) if lines else 0
                # Estimate 40 bytes per line of code
                size_bytes = max_line * 40

            files_data[file_path] = {
                "size_bytes": size_bytes,
                "symbols_count": len(nodes),
                "symbols": nodes,
            }

            # Extract directory
            p = Path(file_path)
            parent_dir = str(p.parent).replace("\\", "/")
            if parent_dir and parent_dir != ".":
                unique_dirs.add(parent_dir)

            # Language tracking
            if nodes:
                lang = nodes[0].symbol.language.value
                languages_count[lang] = languages_count.get(lang, 0) + 1

            total_size += size_bytes
            if size_bytes > largest_file_size:
                largest_file_size = size_bytes
                largest_file = file_path

        # Save to cache
        context.cache.set("files_data", files_data)
        context.cache.set("unique_files", tuple(files_data.keys()))
        context.cache.set("unique_directories", tuple(unique_dirs))
        context.cache.set("languages_count", languages_count)
        context.cache.set("largest_file", largest_file)
        context.cache.set("total_file_size", total_size)

        return files_data

    @property
    def name(self) -> str:
        return "FileMetricsAnalyzer"

    @property
    def description(self) -> str:
        return "Analyzes repository source file layouts, sizes, and languages."

    @property
    def supported_inputs(self) -> Tuple[type, ...]:
        return (RepositoryAnalysisContext,)
