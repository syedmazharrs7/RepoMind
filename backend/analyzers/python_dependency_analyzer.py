import logging
from typing import List, Optional

import tree_sitter

from backend.analyzers.base_dependency_analyzer import BaseDependencyAnalyzer
from backend.dependency_candidate import DependencyCandidate
from backend.dependency_edge_kind import DependencyEdgeKind
from backend.extractors.base_symbol_extractor import ASTNodeContext
from backend.graph_node import GraphNode
from backend.parse_result import ParseResult
from backend.symbol_kind import SymbolKind

logger = logging.getLogger(__name__)


class PythonDependencyAnalyzer(BaseDependencyAnalyzer):
    """Dependency analyzer specialized for Python source ASTs."""

    def _extract_candidates_for_file(
        self,
        parse_result: ParseResult,
        file_symbols: List[GraphNode],
    ) -> List[DependencyCandidate]:
        """Extract dependency candidates from Python AST."""
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
        self._traverse_node(
            ctx=root_ctx,
            current_symbol=mod_node,
            file_symbols=file_symbols,
            candidates=candidates,
        )
        return candidates

    def _traverse_node(
        self,
        ctx: ASTNodeContext,
        current_symbol: GraphNode,
        file_symbols: List[GraphNode],
        candidates: List[DependencyCandidate],
    ) -> None:
        """Traverse Python AST nodes to identify dependency candidates."""
        for child in ctx.node.children:
            c_ctx = ASTNodeContext(child, ctx.code_bytes)
            node_type = c_ctx.type

            # Determine enclosing symbol context
            enclosing = self._find_enclosing_symbol(c_ctx, file_symbols, fallback=current_symbol)

            if node_type in ("import_statement", "import_from_statement"):
                self._extract_import_candidates(c_ctx, enclosing, candidates)
            elif node_type == "class_definition":
                self._extract_class_inheritance_candidates(c_ctx, enclosing, candidates)
                # Traverse class body
                self._traverse_node(c_ctx, enclosing, file_symbols, candidates)
            elif node_type == "function_definition":
                self._extract_function_signature_references(c_ctx, enclosing, candidates)
                # Traverse function body
                self._traverse_node(c_ctx, enclosing, file_symbols, candidates)
            elif node_type == "call":
                self._extract_call_candidate(c_ctx, enclosing, candidates)
                self._traverse_node(c_ctx, enclosing, file_symbols, candidates)
            else:
                self._traverse_node(c_ctx, enclosing, file_symbols, candidates)

    def _extract_import_candidates(
        self,
        ctx: ASTNodeContext,
        enclosing: GraphNode,
        candidates: List[DependencyCandidate],
    ) -> None:
        """Extract IMPORTS candidate from import statements."""
        import_text = ctx.text.strip()
        if not import_text:
            return

        if ctx.type == "import_statement":
            # e.g., "import os, sys"
            for child in ctx.node.children:
                if child.type == "dotted_name":
                    c_text = ASTNodeContext(child, ctx.code_bytes).text.strip()
                    candidates.append(
                        DependencyCandidate(
                            source_symbol_id=enclosing.id,
                            target_name=c_text,
                            kind=DependencyEdgeKind.IMPORTS,
                            start_line=ctx.start_line,
                            start_column=ctx.start_column,
                            context_qname=enclosing.qualified_name,
                        )
                    )
        elif ctx.type == "import_from_statement":
            # e.g., "from flask import Flask, jsonify"
            module_name = ""
            for child in ctx.node.children:
                if child.type == "dotted_name" or child.type == "relative_import":
                    module_name = ASTNodeContext(child, ctx.code_bytes).text.strip()
                    break

            for child in ctx.node.children:
                if child.type in ("dotted_name", "aliased_import", "identifier") and child.type != "from":
                    sym_text = ASTNodeContext(child, ctx.code_bytes).text.strip()
                    if sym_text and sym_text != module_name and sym_text != "import":
                        target_full = f"{module_name}.{sym_text}" if module_name else sym_text
                        candidates.append(
                            DependencyCandidate(
                                source_symbol_id=enclosing.id,
                                target_name=target_full,
                                kind=DependencyEdgeKind.IMPORTS,
                                start_line=ctx.start_line,
                                start_column=ctx.start_column,
                                context_qname=enclosing.qualified_name,
                            )
                        )

    def _extract_class_inheritance_candidates(
        self,
        class_ctx: ASTNodeContext,
        enclosing: GraphNode,
        candidates: List[DependencyCandidate],
    ) -> None:
        """Extract INHERITS candidate from superclasses."""
        superclasses_node = class_ctx.child_by_field_name("superclasses")
        if not superclasses_node:
            return

        for child in superclasses_node.node.children:
            if child.type in ("identifier", "attribute"):
                base_name = ASTNodeContext(child, class_ctx.code_bytes).text.strip()
                if base_name and base_name not in ("(", ")", ","):
                    candidates.append(
                        DependencyCandidate(
                            source_symbol_id=enclosing.id,
                            target_name=base_name,
                            kind=DependencyEdgeKind.INHERITS,
                            start_line=class_ctx.start_line,
                            start_column=class_ctx.start_column,
                            context_qname=enclosing.qualified_name,
                        )
                    )

    def _extract_call_candidate(
        self,
        call_ctx: ASTNodeContext,
        enclosing: GraphNode,
        candidates: List[DependencyCandidate],
    ) -> None:
        """Extract CALLS candidate from function/method invocation."""
        function_node = call_ctx.child_by_field_name("function")
        if not function_node:
            return

        target_name = function_node.text.strip()
        if target_name:
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

    def _extract_function_signature_references(
        self,
        func_ctx: ASTNodeContext,
        enclosing: GraphNode,
        candidates: List[DependencyCandidate],
    ) -> None:
        """Extract REFERENCES candidates from parameter and return type annotations."""
        ret_type = func_ctx.child_by_field_name("return_type")
        if ret_type:
            type_text = ret_type.text.strip()
            if type_text:
                candidates.append(
                    DependencyCandidate(
                        source_symbol_id=enclosing.id,
                        target_name=type_text,
                        kind=DependencyEdgeKind.REFERENCES,
                        start_line=func_ctx.start_line,
                        start_column=func_ctx.start_column,
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
