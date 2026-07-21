import logging
from typing import Dict, List, Optional, Set, Tuple

from backend.dependency_candidate import DependencyCandidate
from backend.dependency_edge import DependencyEdge, generate_dependency_edge_id
from backend.dependency_edge_kind import DependencyEdgeKind
from backend.dependency_metadata import DependencyMetadata
from backend.graph_node import GraphNode
from backend.symbol_graph import SymbolGraph
from backend.symbol_kind import SymbolKind

logger = logging.getLogger(__name__)


class DependencyResolver:
    """
    Dedicated resolver responsible for resolving DependencyCandidate objects into
    deterministic Symbol IDs using SymbolGraph index tables, or tracking UnresolvedDependency instances.
    """

    def resolve_candidates(
        self,
        symbol_graph: SymbolGraph,
        candidates: List[DependencyCandidate],
    ) -> Tuple[List[DependencyEdge], List["UnresolvedDependency"]]:
        """
        Resolve a list of DependencyCandidate objects against the SymbolGraph.

        Args:
            symbol_graph: Immutable SymbolGraph containing all repository symbols.
            candidates: List of DependencyCandidate objects produced by AST analyzers.

        Returns:
            Tuple[List[DependencyEdge], List[UnresolvedDependency]]: Resolved edges and unresolved dependencies.
        """
        from backend.dependency_graph import UnresolvedDependency

        logger.debug(f"Starting resolution for {len(candidates)} dependency candidates")

        # Pre-index SymbolGraph lookup structures
        qname_map: Dict[str, GraphNode] = {n.qualified_name: n for n in symbol_graph.nodes}
        file_name_map: Dict[Tuple[str, str], GraphNode] = {
            (n.symbol.file_path, n.name): n for n in symbol_graph.nodes
        }
        mod_qname_map: Dict[str, GraphNode] = {
            n.name: n for n in symbol_graph.nodes if n.kind == SymbolKind.MODULE
        }
        for n in symbol_graph.nodes:
            if n.kind == SymbolKind.MODULE:
                mod_qname_map[n.qualified_name] = n

        # Build import alias table per file (file_path, name/alias) -> target_qname
        import_table: Dict[Tuple[str, str], str] = {}
        for n in symbol_graph.nodes:
            if n.kind == SymbolKind.IMPORT:
                # e.g., signature: "from flask import Flask" or "import os as operating_system"
                text = n.symbol.signature or n.name
                file_p = n.symbol.file_path
                self._populate_import_aliases(file_p, text, import_table)

        edges: List[DependencyEdge] = []
        unresolved: List[UnresolvedDependency] = []
        resolved_edge_keys: Set[str] = set()

        for c in candidates:
            src_node = symbol_graph.find_node(c.source_symbol_id)
            if not src_node:
                unresolved.append(
                    UnresolvedDependency(
                        kind=c.kind,
                        name=c.target_name,
                        source_symbol_id=c.source_symbol_id,
                        reason="Source symbol ID not found in SymbolGraph",
                    )
                )
                continue

            file_path = src_node.symbol.file_path
            target_node = self._resolve_target(
                c=c,
                src_node=src_node,
                file_path=file_path,
                qname_map=qname_map,
                file_name_map=file_name_map,
                mod_qname_map=mod_qname_map,
                import_table=import_table,
            )

            if target_node:
                edge_id = generate_dependency_edge_id(
                    source_symbol_id=c.source_symbol_id,
                    target_symbol_id=target_node.id,
                    kind=c.kind,
                    start_line=c.start_line,
                    start_column=c.start_column,
                )

                # Avoid duplicate identical edges
                if edge_id not in resolved_edge_keys:
                    resolved_edge_keys.add(edge_id)
                    meta = DependencyMetadata(
                        start_line=c.start_line,
                        start_column=c.start_column,
                        alias=c.alias,
                        resolution_status="RESOLVED",
                        confidence=1.0,
                    )
                    edge = DependencyEdge(
                        id=edge_id,
                        source_symbol_id=c.source_symbol_id,
                        target_symbol_id=target_node.id,
                        kind=c.kind,
                        metadata=meta,
                    )
                    edges.append(edge)
            else:
                unresolved.append(
                    UnresolvedDependency(
                        kind=c.kind,
                        name=c.target_name,
                        source_symbol_id=c.source_symbol_id,
                        reason="External package or unbound identifier",
                    )
                )

        logger.debug(
            f"Dependency resolution complete: {len(edges)} edges resolved, {len(unresolved)} unresolved candidates"
        )
        return edges, unresolved

    def _resolve_target(
        self,
        c: DependencyCandidate,
        src_node: GraphNode,
        file_path: str,
        qname_map: Dict[str, GraphNode],
        file_name_map: Dict[Tuple[str, str], GraphNode],
        mod_qname_map: Dict[str, GraphNode],
        import_table: Dict[Tuple[str, str], str],
    ) -> Optional[GraphNode]:
        """Attempt multi-stage symbol resolution."""
        target_name = c.target_name.strip()
        if not target_name:
            return None

        # Strategy 1: Exact Qualified Name match
        if target_name in qname_map:
            return qname_map[target_name]

        # Strategy 2: Scoped Qualified Name match (e.g. scope 'app' + 'UserService' -> 'app.UserService')
        scope_qname = c.context_qname or src_node.qualified_name
        # Walk parent scopes up to module
        scope_parts = scope_qname.split(".")
        while scope_parts:
            candidate_qname = f"{'.'.join(scope_parts)}.{target_name}"
            if candidate_qname in qname_map:
                return qname_map[candidate_qname]
            scope_parts.pop()

        # Strategy 3: File Scope match (same file, matching symbol name)
        if (file_path, target_name) in file_name_map:
            return file_name_map[(file_path, target_name)]

        # Strategy 4: Import Alias / Imported Symbol match
        if (file_path, target_name) in import_table:
            imported_qname = import_table[(file_path, target_name)]
            if imported_qname in qname_map:
                return qname_map[imported_qname]
            if imported_qname in mod_qname_map:
                return mod_qname_map[imported_qname]

        # Strategy 5: Module Name match
        if target_name in mod_qname_map:
            return mod_qname_map[target_name]

        return None

    def _populate_import_aliases(
        self, file_path: str, import_text: str, import_table: Dict[Tuple[str, str], str]
    ) -> None:
        """Parse import statement text to build (file_path, name_or_alias) -> target_qname mapping."""
        # Handles "import a.b.c as x", "from a.b import c as d", "import x"
        if "from " in import_text:
            try:
                parts = import_text.split("from ")[1].split(" import ")
                mod = parts[0].strip()
                symbols_part = parts[1].strip()
                for sym in symbols_part.split(","):
                    sym = sym.strip()
                    if " as " in sym:
                        orig, alias = sym.split(" as ")
                        import_table[(file_path, alias.strip())] = f"{mod}.{orig.strip()}"
                    else:
                        import_table[(file_path, sym)] = f"{mod}.{sym}"
            except Exception:
                pass
        elif "import " in import_text:
            try:
                imp_part = import_text.replace("import ", "").strip()
                for item in imp_part.split(","):
                    item = item.strip()
                    if " as " in item:
                        orig, alias = item.split(" as ")
                        import_table[(file_path, alias.strip())] = orig.strip()
                    else:
                        import_table[(file_path, item)] = item
            except Exception:
                pass
