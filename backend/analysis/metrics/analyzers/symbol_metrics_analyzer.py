"""
Symbol Metrics Analyzer. Computes SymbolMetrics for the repository.
"""
from typing import Tuple

from backend.analysis.metrics.analyzers.base_metric_analyzer import BaseMetricAnalyzer
from backend.analysis.metrics.metric_models import RepositoryAnalysisContext, SymbolMetrics
from backend.symbol_kind import SymbolKind


class SymbolMetricsAnalyzer(BaseMetricAnalyzer):
    """
    Analyzes types of symbols, visibility, nesting level, and inheritance relationships.
    """

    def analyze(self, context: RepositoryAnalysisContext) -> SymbolMetrics:
        symbol_graph = context.symbol_graph
        dependency_graph = context.dependency_graph

        classes = 0
        functions = 0
        methods = 0
        variables = 0
        constants = 0
        interfaces = 0
        enums = 0
        modules = 0

        visibility_public = 0
        visibility_private = 0
        visibility_protected = 0

        largest_class = ""
        largest_class_lines = -1
        largest_module = ""
        largest_module_lines = -1
        deepest_nesting = 0

        for node in symbol_graph.nodes:
            symbol = node.symbol
            kind = symbol.kind
            kind_val = kind.value if isinstance(kind, SymbolKind) else str(kind)

            # Map kinds
            if kind == SymbolKind.CLASS:
                classes += 1
                lines = symbol.line_count
                if lines > largest_class_lines:
                    largest_class_lines = lines
                    largest_class = symbol.qualified_name
            elif kind == SymbolKind.FUNCTION:
                functions += 1
            elif kind in (SymbolKind.METHOD, SymbolKind.CONSTRUCTOR):
                methods += 1
            elif kind == SymbolKind.VARIABLE:
                variables += 1
            elif kind == SymbolKind.CONSTANT:
                constants += 1
            elif kind_val == "INTERFACE":
                interfaces += 1
            elif kind_val == "ENUM":
                enums += 1
            elif kind == SymbolKind.MODULE:
                modules += 1
                lines = symbol.line_count
                if lines > largest_module_lines:
                    largest_module_lines = lines
                    largest_module = symbol.qualified_name

            # Map visibility (case insensitive check)
            vis = (symbol.visibility or "public").lower()
            if vis == "public":
                visibility_public += 1
            elif vis == "private":
                visibility_private += 1
            elif vis == "protected":
                visibility_protected += 1
            else:
                visibility_public += 1  # Default fallback

            # Nesting depth: count ancestors
            ancestors_count = len(symbol_graph.ancestors(node.id))
            if ancestors_count > deepest_nesting:
                deepest_nesting = ancestors_count

        # Average methods per class
        average_methods_per_class = methods / classes if classes > 0 else 0.0

        # Maximum inheritance depth
        inheritance_depths = {}

        def get_inheritance_depth(node_id: str, visited: set) -> int:
            if node_id in visited:
                return 0  # Break circular reference
            if node_id in inheritance_depths:
                return inheritance_depths[node_id]

            # dependency_graph.inherits returns the base classes
            bases = dependency_graph.inherits(node_id)
            if not bases:
                inheritance_depths[node_id] = 0
                return 0

            max_depth = 0
            visited.add(node_id)
            for base in bases:
                max_depth = max(max_depth, get_inheritance_depth(base.id, visited))
            visited.remove(node_id)

            inheritance_depths[node_id] = 1 + max_depth
            return 1 + max_depth

        max_inheritance_depth = 0
        for node in symbol_graph.nodes:
            if node.kind == SymbolKind.CLASS:
                d = get_inheritance_depth(node.id, set())
                if d > max_inheritance_depth:
                    max_inheritance_depth = d

        return SymbolMetrics(
            classes=classes,
            functions=functions,
            methods=methods,
            variables=variables,
            constants=constants,
            interfaces=interfaces,
            enums=enums,
            modules=modules,
            visibility_public=visibility_public,
            visibility_private=visibility_private,
            visibility_protected=visibility_protected,
            average_methods_per_class=average_methods_per_class,
            largest_class=largest_class,
            largest_module=largest_module,
            deepest_nesting=deepest_nesting,
            max_inheritance_depth=max_inheritance_depth,
        )

    @property
    def name(self) -> str:
        return "SymbolMetricsAnalyzer"

    @property
    def description(self) -> str:
        return "Calculates symbol counts, visibility distributions, nesting, and inheritance depth."

    @property
    def supported_inputs(self) -> Tuple[type, ...]:
        return (RepositoryAnalysisContext,)
