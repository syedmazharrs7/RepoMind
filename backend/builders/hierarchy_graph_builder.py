import logging
from typing import Dict, List, Optional, Set, Tuple

from backend.builders.base_graph_builder import BaseGraphBuilder
from backend.graph_edge import GraphEdge, generate_edge_id
from backend.graph_edge_kind import GraphEdgeKind
from backend.graph_node import GraphNode
from backend.graph_validator import GraphValidator
from backend.repository_scanner import Language
from backend.symbol import Symbol, generate_symbol_id
from backend.symbol_graph import SymbolGraph
from backend.symbol_kind import SymbolKind
from backend.symbol_result import SymbolExtractionResult

logger = logging.getLogger(__name__)


class HierarchyGraphBuilder(BaseGraphBuilder):
    """
    Graph builder responsible for constructing the semantic ownership hierarchy.
    Wraps module roots under a canonical Repository root node and delegates validation
    to GraphValidator.
    """

    def __init__(self, validator: Optional[GraphValidator] = None) -> None:
        """
        Initialize HierarchyGraphBuilder.

        Args:
            validator: Optional GraphValidator instance. If None, default validator is used.
        """
        self._validator = validator if validator is not None else GraphValidator()

    def build(
        self,
        extraction_results: List[SymbolExtractionResult],
        repository_name: str = "Repository",
    ) -> SymbolGraph:
        """
        Build an immutable SymbolGraph representing the semantic ownership hierarchy.

        Args:
            extraction_results: List of SymbolExtractionResult objects.
            repository_name: Canonical name for the root repository node.

        Returns:
            SymbolGraph: Immutable symbol graph.
        """
        logger.info(
            f"Starting hierarchy graph construction for {len(extraction_results)} file extraction results"
        )

        # 1. Create canonical Repository root symbol
        repo_symbol_id = generate_symbol_id(
            language="REPOSITORY",
            file_path=".",
            qualified_name=repository_name,
            kind=SymbolKind.MODULE,
        )

        repo_symbol = Symbol(
            id=repo_symbol_id,
            name=repository_name,
            qualified_name=repository_name,
            kind=SymbolKind.MODULE,
            language=Language.PYTHON,
            file_path=".",
            start_line=1,
            end_line=1,
            start_column=0,
            end_column=0,
            parent_symbol=None,
            signature=f"repository {repository_name}",
            docstring=f"Canonical Repository root node for {repository_name}",
            decorators=(),
            visibility="public",
            is_async=False,
            is_exported=True,
        )

        all_symbols: List[Symbol] = [repo_symbol]

        # 2. Collect symbols and link top-level MODULE roots to canonical repository root
        for res in extraction_results:
            for s in res.symbols:
                if s.parent_symbol is None and s.kind == SymbolKind.MODULE:
                    linked_symbol = Symbol(
                        id=s.id,
                        name=s.name,
                        qualified_name=s.qualified_name,
                        kind=s.kind,
                        language=s.language,
                        file_path=s.file_path,
                        start_line=s.start_line,
                        end_line=s.end_line,
                        start_column=s.start_column,
                        end_column=s.end_column,
                        parent_symbol=repo_symbol.id,
                        signature=s.signature,
                        docstring=s.docstring,
                        decorators=s.decorators,
                        visibility=s.visibility,
                        is_async=s.is_async,
                        is_exported=s.is_exported,
                    )
                    all_symbols.append(linked_symbol)
                else:
                    all_symbols.append(s)

        # 3. Create GraphEdge objects for OWNS relationships
        edges: List[GraphEdge] = []
        edges_by_node_in: Dict[str, List[GraphEdge]] = {s.id: [] for s in all_symbols}
        edges_by_node_out: Dict[str, List[GraphEdge]] = {s.id: [] for s in all_symbols}

        for s in all_symbols:
            if s.parent_symbol is not None:
                parent_id = s.parent_symbol
                edge_id = generate_edge_id(parent_id, s.id, GraphEdgeKind.OWNS)
                edge = GraphEdge(
                    id=edge_id,
                    source_symbol_id=parent_id,
                    target_symbol_id=s.id,
                    kind=GraphEdgeKind.OWNS,
                )
                edges.append(edge)

                if parent_id in edges_by_node_out:
                    edges_by_node_out[parent_id].append(edge)
                if s.id in edges_by_node_in:
                    edges_by_node_in[s.id].append(edge)

        # 4. Construct GraphNode objects
        nodes: List[GraphNode] = []
        for s in all_symbols:
            inc_tuple = tuple(edges_by_node_in.get(s.id, []))
            out_tuple = tuple(edges_by_node_out.get(s.id, []))
            node = GraphNode(
                symbol=s,
                incoming_edges=inc_tuple,
                outgoing_edges=out_tuple,
            )
            nodes.append(node)

        repo_root_node = next(n for n in nodes if n.id == repo_symbol.id)

        # 5. Delegate Graph Validation (Refinement #1)
        self._validator.validate(nodes=nodes, edges=edges, root_nodes=[repo_root_node])

        logger.info(
            f"Hierarchy graph construction completed successfully: {len(nodes)} nodes, {len(edges)} edges"
        )

        return SymbolGraph(nodes=nodes, edges=edges, root_nodes=[repo_root_node])
