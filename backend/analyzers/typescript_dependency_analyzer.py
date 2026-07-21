import logging
from typing import List

from backend.analyzers.javascript_dependency_analyzer import JavaScriptDependencyAnalyzer
from backend.dependency_candidate import DependencyCandidate
from backend.dependency_edge_kind import DependencyEdgeKind
from backend.extractors.base_symbol_extractor import ASTNodeContext
from backend.graph_node import GraphNode

logger = logging.getLogger(__name__)


class TypeScriptDependencyAnalyzer(JavaScriptDependencyAnalyzer):
    """Dependency analyzer specialized for TypeScript ASTs, extending JS analyzer with TS features."""

    def _traverse_js_node(
        self,
        ctx: ASTNodeContext,
        current_symbol: GraphNode,
        file_symbols: List[GraphNode],
        candidates: List[DependencyCandidate],
    ) -> None:
        """Override JS node traversal to handle TS implements clauses and type references."""
        for child in ctx.node.children:
            c_ctx = ASTNodeContext(child, ctx.code_bytes)
            node_type = c_ctx.type

            enclosing = self._find_enclosing_symbol(c_ctx, file_symbols, fallback=current_symbol)

            if node_type == "class_declaration":
                self._extract_ts_implements_candidate(c_ctx, enclosing, candidates)
                super()._traverse_js_node(ctx=c_ctx, current_symbol=enclosing, file_symbols=file_symbols, candidates=candidates)
            elif node_type in ("type_annotation", "type_alias_declaration"):
                self._extract_ts_type_reference(c_ctx, enclosing, candidates)
                super()._traverse_js_node(ctx=c_ctx, current_symbol=enclosing, file_symbols=file_symbols, candidates=candidates)
            else:
                super()._traverse_js_node(ctx=c_ctx, current_symbol=current_symbol, file_symbols=file_symbols, candidates=candidates)

    def _extract_ts_implements_candidate(
        self,
        class_ctx: ASTNodeContext,
        enclosing: GraphNode,
        candidates: List[DependencyCandidate],
    ) -> None:
        """Extract IMPLEMENTS candidate from TS class implements clause."""
        implements_clause = class_ctx.find_first_child_of_type("implements_clause")
        if implements_clause:
            interface_names = implements_clause.text.replace("implements", "").strip()
            for iface in interface_names.split(","):
                iface = iface.strip()
                if iface:
                    candidates.append(
                        DependencyCandidate(
                            source_symbol_id=enclosing.id,
                            target_name=iface,
                            kind=DependencyEdgeKind.IMPLEMENTS,
                            start_line=class_ctx.start_line,
                            start_column=class_ctx.start_column,
                            context_qname=enclosing.qualified_name,
                        )
                    )

    def _extract_ts_type_reference(
        self,
        type_ctx: ASTNodeContext,
        enclosing: GraphNode,
        candidates: List[DependencyCandidate],
    ) -> None:
        """Extract REFERENCES candidate from TS type annotation."""
        type_name = type_ctx.text.strip().lstrip(":")
        if type_name:
            candidates.append(
                DependencyCandidate(
                    source_symbol_id=enclosing.id,
                    target_name=type_name,
                    kind=DependencyEdgeKind.REFERENCES,
                    start_line=type_ctx.start_line,
                    start_column=type_ctx.start_column,
                    context_qname=enclosing.qualified_name,
                )
            )
