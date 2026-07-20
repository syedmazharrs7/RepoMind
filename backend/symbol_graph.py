from collections import deque
import logging
from typing import Dict, Iterator, List, Optional, Tuple

from backend.graph_edge import GraphEdge
from backend.graph_node import GraphNode
from backend.graph_result import GraphStats
from backend.symbol_kind import SymbolKind

logger = logging.getLogger(__name__)


def _sort_nodes_key(node: GraphNode) -> Tuple[int, int, str]:
    """Deterministic sorting key: start_line, start_column, qualified_name."""
    return (
        node.symbol.start_line,
        node.symbol.start_column,
        node.symbol.qualified_name,
    )


class SymbolGraph:
    """
    Immutable, high-performance Symbol Graph representing the repository semantic ownership hierarchy.
    Provides O(1) symbol lookups, deterministic graph traversals, and serialization-friendly APIs.
    """

    def __init__(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        root_nodes: Optional[List[GraphNode]] = None,
    ) -> None:
        """
        Initialize SymbolGraph with nodes and edges.

        Args:
            nodes: List of GraphNode instances.
            edges: List of GraphEdge instances.
            root_nodes: Optional explicit list of root nodes.
        """
        self._nodes_by_id: Dict[str, GraphNode] = {n.id: n for n in nodes}
        self._edges_by_id: Dict[str, GraphEdge] = {e.id: e for e in edges}

        # Index by qualified name (supporting multiple nodes with same qname if any across files)
        self._nodes_by_qname: Dict[str, List[GraphNode]] = {}
        for n in nodes:
            self._nodes_by_qname.setdefault(n.qualified_name, []).append(n)

        # Parent and child maps
        self._parent_map: Dict[str, Optional[GraphNode]] = {n.id: None for n in nodes}
        self._children_map: Dict[str, List[GraphNode]] = {n.id: [] for n in nodes}

        for edge in edges:
            src_id = edge.source_symbol_id
            tgt_id = edge.target_symbol_id
            if src_id in self._nodes_by_id and tgt_id in self._nodes_by_id:
                target_node = self._nodes_by_id[tgt_id]
                source_node = self._nodes_by_id[src_id]
                self._children_map[src_id].append(target_node)
                self._parent_map[tgt_id] = source_node

        # Guarantee deterministic child traversal order: primary start location, secondary qname
        for src_id in self._children_map:
            self._children_map[src_id].sort(key=_sort_nodes_key)

        # Identify roots
        if root_nodes is not None:
            self._root_nodes_list = sorted(root_nodes, key=_sort_nodes_key)
        else:
            self._root_nodes_list = sorted(
                [n for n in nodes if self._parent_map[n.id] is None],
                key=_sort_nodes_key,
            )

        # Sort all nodes and edges deterministically
        self._ordered_nodes: Tuple[GraphNode, ...] = tuple(
            sorted(nodes, key=lambda n: (n.symbol.file_path, n.symbol.start_line, n.qualified_name))
        )
        self._ordered_edges: Tuple[GraphEdge, ...] = tuple(
            sorted(edges, key=lambda e: (e.source_symbol_id, e.target_symbol_id, e.kind))
        )

        logger.debug(
            f"Initialized SymbolGraph: {len(self._ordered_nodes)} nodes, {len(self._ordered_edges)} edges, {len(self._root_nodes_list)} root(s)"
        )

    @property
    def nodes(self) -> Tuple[GraphNode, ...]:
        """Immutable tuple of all nodes in the graph."""
        return self._ordered_nodes

    @property
    def edges(self) -> Tuple[GraphEdge, ...]:
        """Immutable tuple of all edges in the graph."""
        return self._ordered_edges

    @property
    def root_nodes(self) -> Tuple[GraphNode, ...]:
        """Immutable tuple of root nodes in the graph."""
        return tuple(self._root_nodes_list)

    @property
    def root_node(self) -> Optional[GraphNode]:
        """Convenience property for single repository root node if present."""
        return self._root_nodes_list[0] if self._root_nodes_list else None

    @property
    def stats(self) -> GraphStats:
        """Calculate and return read-only repository graph health statistics."""
        node_count = len(self._ordered_nodes)
        edge_count = len(self._ordered_edges)
        root_count = len(self._root_nodes_list)

        leaf_count = sum(1 for nid, kids in self._children_map.items() if len(kids) == 0)

        # Calculate maximum depth across all roots
        max_depth = 0

        def calc_depth(curr_id: str, depth: int) -> int:
            kids = self._children_map.get(curr_id, [])
            if not kids:
                return depth
            return max(calc_depth(k.id, depth + 1) for k in kids)

        if self._root_nodes_list:
            max_depth = max(calc_depth(r.id, 1) for r in self._root_nodes_list)

        return GraphStats(
            node_count=node_count,
            edge_count=edge_count,
            root_count=root_count,
            leaf_count=leaf_count,
            max_depth=max_depth,
        )

    def find_node(self, node_id: str) -> Optional[GraphNode]:
        """O(1) lookup of a graph node by symbol ID."""
        return self._nodes_by_id.get(node_id)

    def lookup_by_id(self, symbol_id: str) -> Optional[GraphNode]:
        """Alias for find_node."""
        return self.find_node(symbol_id)

    def find_symbol(self, qualified_name: str) -> Optional[GraphNode]:
        """O(1) lookup of first graph node matching qualified name."""
        matches = self._nodes_by_qname.get(qualified_name)
        return matches[0] if matches else None

    def lookup_by_qualified_name(self, qualified_name: str) -> List[GraphNode]:
        """O(1) lookup of all graph nodes matching qualified name."""
        return list(self._nodes_by_qname.get(qualified_name, []))

    def children(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """Retrieve immediate children of a symbol in deterministic order."""
        return tuple(self._children_map.get(symbol_id, []))

    def parent(self, symbol_id: str) -> Optional[GraphNode]:
        """Retrieve direct parent node of a symbol."""
        return self._parent_map.get(symbol_id)

    def ancestors(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """
        Retrieve all ancestors of a symbol in order from direct parent up to root.

        Args:
            symbol_id: The target symbol ID.

        Returns:
            Tuple[GraphNode, ...]: Sequence of parent, grandparent, ..., root.
        """
        result: List[GraphNode] = []
        curr_parent = self._parent_map.get(symbol_id)
        while curr_parent is not None:
            result.append(curr_parent)
            curr_parent = self._parent_map.get(curr_parent.id)
        return tuple(result)

    def descendants(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """
        Retrieve all descendant nodes of a symbol in deterministic DFS order.

        Args:
            symbol_id: The target symbol ID.

        Returns:
            Tuple[GraphNode, ...]: Sequence of all descendants.
        """
        result: List[GraphNode] = []

        def _dfs(curr_id: str) -> None:
            for child in self._children_map.get(curr_id, []):
                result.append(child)
                _dfs(child.id)

        _dfs(symbol_id)
        return tuple(result)

    def walk_depth_first(self, root_id: Optional[str] = None) -> Iterator[GraphNode]:
        """
        Yield nodes in deterministic Depth-First Search (DFS) order.

        Args:
            root_id: Optional starting root node ID. If None, walks all roots.
        """
        start_nodes = (
            [self._nodes_by_id[root_id]]
            if root_id and root_id in self._nodes_by_id
            else self._root_nodes_list
        )

        visited = set()

        def _dfs(node: GraphNode) -> Iterator[GraphNode]:
            if node.id in visited:
                return
            visited.add(node.id)
            yield node
            for child in self._children_map.get(node.id, []):
                yield from _dfs(child)

        for r in start_nodes:
            yield from _dfs(r)

    def walk_breadth_first(self, root_id: Optional[str] = None) -> Iterator[GraphNode]:
        """
        Yield nodes in deterministic Breadth-First Search (BFS) order.

        Args:
            root_id: Optional starting root node ID. If None, walks all roots.
        """
        start_nodes = (
            [self._nodes_by_id[root_id]]
            if root_id and root_id in self._nodes_by_id
            else self._root_nodes_list
        )

        visited = set()
        queue = deque(start_nodes)

        while queue:
            node = queue.popleft()
            if node.id in visited:
                continue
            visited.add(node.id)
            yield node
            for child in self._children_map.get(node.id, []):
                if child.id not in visited:
                    queue.append(child)

    def iter_nodes(self) -> Iterator[GraphNode]:
        """Yield all nodes in the graph."""
        yield from self._ordered_nodes

    def iter_edges(self) -> Iterator[GraphEdge]:
        """Yield all edges in the graph."""
        yield from self._ordered_edges

    def to_dict(self) -> dict:
        """
        Export graph representation to a clean, JSON-serializable dictionary structure.
        Enables future export modules (JSON, GraphML, DOT) without architectural changes.
        """
        return {
            "stats": {
                "node_count": self.stats.node_count,
                "edge_count": self.stats.edge_count,
                "root_count": self.stats.root_count,
                "leaf_count": self.stats.leaf_count,
                "max_depth": self.stats.max_depth,
            },
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "qualified_name": n.qualified_name,
                    "kind": n.kind.value,
                    "language": n.symbol.language.value,
                    "file_path": n.symbol.file_path,
                    "start_line": n.symbol.start_line,
                    "end_line": n.symbol.end_line,
                    "parent_symbol": n.symbol.parent_symbol,
                    "signature": n.symbol.signature,
                    "docstring": n.symbol.docstring,
                    "visibility": n.symbol.visibility,
                    "is_async": n.symbol.is_async,
                    "is_exported": n.symbol.is_exported,
                }
                for n in self._ordered_nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source_symbol_id": e.source_symbol_id,
                    "target_symbol_id": e.target_symbol_id,
                    "kind": e.kind.value,
                }
                for e in self._ordered_edges
            ],
        }
