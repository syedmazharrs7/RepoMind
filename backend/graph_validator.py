import logging
from typing import Dict, List, Optional, Set

from backend.graph_edge import GraphEdge
from backend.graph_exceptions import (
    CycleDetectedError,
    DuplicateSymbolError,
    InvalidHierarchyError,
    MissingParentError,
)
from backend.graph_node import GraphNode
from backend.symbol_kind import SymbolKind

logger = logging.getLogger(__name__)


class GraphValidator:
    """
    Dedicated validator responsible for graph integrity checks:
    - Duplicate symbol ID detection
    - Missing parent detection
    - Cycle detection in ownership hierarchy
    - Orphan symbol detection & reachability validation
    """

    def validate(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        root_nodes: Optional[List[GraphNode]] = None,
    ) -> None:
        """
        Validate the structural integrity and hierarchy rules of the graph nodes and edges.

        Args:
            nodes: List of GraphNode instances.
            edges: List of GraphEdge instances.
            root_nodes: Optional list of root GraphNode instances.

        Raises:
            DuplicateSymbolError: If duplicate symbol IDs exist.
            MissingParentError: If a non-root symbol references a non-existent parent ID.
            CycleDetectedError: If an ownership cycle is detected.
            InvalidHierarchyError: If unreachable orphan nodes exist in the graph.
        """
        logger.debug(f"Starting graph validation for {len(nodes)} nodes and {len(edges)} edges")

        # 1. Duplicate Symbol ID Detection
        node_map: Dict[str, GraphNode] = {}
        for node in nodes:
            if node.id in node_map:
                logger.error(f"Duplicate symbol ID detected: '{node.id}' (qualified_name: '{node.qualified_name}')")
                raise DuplicateSymbolError(f"Duplicate symbol ID found in graph: '{node.id}'")
            node_map[node.id] = node

        # Determine roots
        if root_nodes is None:
            roots = [n for n in nodes if n.symbol.parent_symbol is None]
        else:
            roots = root_nodes

        # 2. Missing Parent Validation
        for node in nodes:
            parent_id = node.symbol.parent_symbol
            if parent_id is not None and parent_id not in node_map:
                logger.error(
                    f"Missing parent ID '{parent_id}' for symbol '{node.qualified_name}' (ID: '{node.id}')"
                )
                raise MissingParentError(
                    f"Symbol '{node.qualified_name}' (ID: '{node.id}') references missing parent ID: '{parent_id}'"
                )

        # 3. Cycle Detection (DFS 3-color marking: 0=UNVISITED, 1=VISITING, 2=VISITED)
        # Adjacency list for outgoing OWNS edges
        adj_map: Dict[str, List[str]] = {n.id: [] for n in nodes}
        for edge in edges:
            if edge.source_symbol_id in adj_map:
                adj_map[edge.source_symbol_id].append(edge.target_symbol_id)

        color: Dict[str, int] = {n.id: 0 for n in nodes}

        def dfs_cycle(node_id: str, path: List[str]) -> None:
            color[node_id] = 1  # VISITING
            path.append(node_id)
            for neighbor_id in adj_map.get(node_id, []):
                if color[neighbor_id] == 1:
                    cycle_str = " -> ".join(path + [neighbor_id])
                    logger.error(f"Cycle detected in symbol ownership graph: {cycle_str}")
                    raise CycleDetectedError(f"Ownership cycle detected: {cycle_str}")
                elif color[neighbor_id] == 0:
                    dfs_cycle(neighbor_id, path)
            path.pop()
            color[node_id] = 2  # VISITED

        for node in nodes:
            if color[node.id] == 0:
                dfs_cycle(node.id, [])

        # 4. Orphan Symbol & Reachability Validation
        # Every non-root node must be reachable from at least one root node
        reachable: Set[str] = set()

        def dfs_reachability(curr_id: str) -> None:
            if curr_id in reachable:
                return
            reachable.add(curr_id)
            for child_id in adj_map.get(curr_id, []):
                dfs_reachability(child_id)

        for r in roots:
            dfs_reachability(r.id)

        unreachable = set(node_map.keys()) - reachable
        if unreachable:
            orphan_qnames = [node_map[nid].qualified_name for nid in sorted(unreachable)]
            logger.error(f"Orphan symbols detected ({len(unreachable)} unreachable): {orphan_qnames[:5]}")
            raise InvalidHierarchyError(
                f"Found {len(unreachable)} unreachable/orphan symbols in graph, e.g.: {orphan_qnames[0]}"
            )

        logger.debug("Graph validation completed successfully with 0 errors")
