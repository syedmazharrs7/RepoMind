import logging
from typing import List

from backend.analyzers.base_dependency_analyzer import BaseDependencyAnalyzer
from backend.dependency_candidate import DependencyCandidate
from backend.dependency_edge_kind import DependencyEdgeKind
from backend.extractors.base_symbol_extractor import ASTNodeContext
from backend.graph_node import GraphNode
from backend.parse_result import ParseResult
from backend.symbol_kind import SymbolKind

logger = logging.getLogger(__name__)


class JavaScriptDependencyAnalyzer(BaseDependencyAnalyzer):
    """Dependency analyzer specialized for JavaScript source ASTs."""

    def _extract_candidates_for_file(
        self,
        parse_result: ParseResult,
        file_symbols: List[GraphNode],
    ) -> List[DependencyCandidate]:
        """Extract dependency candidates from JavaScript AST."""
        if not parse_result.tree or not parse_result.tree.root_node:
            return []

        try:
            code_bytes = parse_result.source_file.path.read_bytes()
        except Exception:
            code_bytes = b""

        root_ctx = ASTNodeContext(parse_result.tree.root_node, code_bytes)
        mod_node = next((n for n in file_symbols if n.kind == SymbolKind.MODULE), None)
        if not mod_node:
            return []

        candidates: List[DependencyCandidate] = []
        self._traverse_js_node(
            ctx=root_ctx,
            current_symbol=mod_node,
            file_symbols=file_symbols,
            candidates=candidates,
        )
        return candidates

    def _traverse_js_node(
        self,
        ctx: ASTNodeContext,
        current_symbol: GraphNode,
        file_symbols: List[GraphNode],
        candidates: List[DependencyCandidate],
    ) -> None:
        """Traverse JavaScript AST nodes to identify dependency candidates."""
        for child in ctx.node.children:
            c_ctx = ASTNodeContext(child, ctx.code_bytes)
            node_type = c_ctx.type

            enclosing = self._find_enclosing_symbol(c_ctx, file_symbols, fallback=current_symbol)

            if node_type == "import_statement":
                self._extract_js_import_candidate(c_ctx, enclosing, candidates)
            elif node_type == "class_declaration":
                self._extract_js_inheritance_candidate(c_ctx, enclosing, candidates)
                self._traverse_js_node(c_ctx, enclosing, file_symbols, candidates)
            elif node_type == "call_expression":
                self._extract_js_call_candidate(c_ctx, enclosing, candidates)
                self._traverse_js_node(c_ctx, enclosing, file_symbols, candidates)
            else:
                self._traverse_js_node(c_ctx, enclosing, file_symbols, candidates)

    def _extract_js_import_candidate(
        self,
        ctx: ASTNodeContext,
        enclosing: GraphNode,
        candidates: List[DependencyCandidate],
    ) -> None:
        """Extract IMPORTS candidate from JS import statement."""
        import_text = ctx.text.strip()
        if not import_text:
            return

        source_node = ctx.child_by_field_name("source")
        target_name = source_node.text.strip("'\"") if source_node else import_text
        candidates.append(
            DependencyCandidate(
                source_symbol_id=enclosing.id,
                target_name=target_name,
                kind=DependencyEdgeKind.IMPORTS,
                start_line=ctx.start_line,
                start_column=ctx.start_column,
                context_qname=enclosing.qualified_name,
            )
        )

    def _extract_js_inheritance_candidate(
        self,
        class_ctx: ASTNodeContext,
        enclosing: GraphNode,
        candidates: List[DependencyCandidate],
    ) -> None:
        """Extract INHERITS candidate from class extends clause."""
        heritage = class_ctx.find_first_child_of_type("class_heritage")
        if heritage:
            super_name = heritage.text.replace("extends", "").strip()
            if super_name:
                candidates.append(
                    DependencyCandidate(
                        source_symbol_id=enclosing.id,
                        target_name=super_name,
                        kind=DependencyEdgeKind.INHERITS,
                        start_line=class_ctx.start_line,
                        start_column=class_ctx.start_column,
                        context_qname=enclosing.qualified_name,
                    )
                )

    def _extract_js_call_candidate(
        self,
        call_ctx: ASTNodeContext,
        enclosing: GraphNode,
        candidates: List[DependencyCandidate],
    ) -> None:
        """Extract CALLS candidate from JS call expression."""
        func_node = call_ctx.child_by_field_name("function")
        if not func_node:
            return

        target_name = func_node.text.strip()
        if target_name == "require":
            # CommonJS import require('...')
            args = call_ctx.child_by_field_name("arguments")
            if args:
                module_name = args.text.strip("() '\"")
                candidates.append(
                    DependencyCandidate(
                        source_symbol_id=enclosing.id,
                        target_name=module_name,
                        kind=DependencyEdgeKind.IMPORTS,
                        start_line=call_ctx.start_line,
                        start_column=call_ctx.start_column,
                        context_qname=enclosing.qualified_name,
                    )
                )
        elif target_name:
            candidates.append(
                DependencyCandidate(
                    source_symbol_id=enclosing.id,
                    target_name=target_name,
                    kind=DependencyEdgeKind.CALLS,
                    start_line=call_ctx.start_line,
                    start_column=call_ctx.start_column,
                    context_qname=enclosing.qualified_name,
                )
            )

    def _find_enclosing_symbol(
        self,
        ctx: ASTNodeContext,
        file_symbols: List[GraphNode],
        fallback: GraphNode,
    ) -> GraphNode:
        """Find the tightest enclosing symbol for line range."""
        best: GraphNode = fallback
        best_span = float("inf")

        for s in file_symbols:
            if s.symbol.start_line <= ctx.start_line and s.symbol.end_line >= ctx.end_line:
                span = s.symbol.end_line - s.symbol.start_line
                if span < best_span:
                    best_span = span
                    best = s
        return best
