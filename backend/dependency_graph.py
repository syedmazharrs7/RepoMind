from collections import deque
from dataclasses import dataclass
import logging
from typing import Dict, Iterator, List, Optional, Set, Tuple

from backend.dependency_edge import DependencyEdge
from backend.dependency_edge_kind import DependencyEdgeKind
from backend.dependency_graph_result import DependencyGraphStats
from backend.graph_node import GraphNode
from backend.symbol_graph import SymbolGraph

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UnresolvedDependency:
    """Immutable representation of a dependency relationship that could not be resolved to a symbol in the graph."""
    kind: DependencyEdgeKind
    name: str
    source_symbol_id: str
    reason: str


class DependencyGraph:
    """
    Immutable, high-performance Dependency Graph representing semantic relationships between code symbols.
    Supports structural and behavioral query APIs, O(1) adjacency lookups, cycle detection, and reachability.
    """

    def __init__(
        self,
        symbol_graph: SymbolGraph,
        edges: List[DependencyEdge],
        unresolved: Optional[List[UnresolvedDependency]] = None,
    ) -> None:
        """
        Initialize DependencyGraph.

        Args:
            symbol_graph: The underlying immutable SymbolGraph containing GraphNodes.
            edges: List of resolved DependencyEdge objects.
            unresolved: Optional list of UnresolvedDependency instances.
        """
        self._symbol_graph = symbol_graph
        self._nodes_by_id: Dict[str, GraphNode] = {n.id: n for n in symbol_graph.nodes}
        self._edges_by_id: Dict[str, DependencyEdge] = {e.id: e for e in edges}
        self._unresolved_tuple: Tuple[UnresolvedDependency, ...] = (
            tuple(unresolved) if unresolved is not None else ()
        )

        self._outgoing_map: Dict[str, List[DependencyEdge]] = {n.id: [] for n in symbol_graph.nodes}
        self._incoming_map: Dict[str, List[DependencyEdge]] = {n.id: [] for n in symbol_graph.nodes}

        for edge in edges:
            src_id = edge.source_symbol_id
            tgt_id = edge.target_symbol_id
            if src_id in self._outgoing_map:
                self._outgoing_map[src_id].append(edge)
            if tgt_id in self._incoming_map:
                self._incoming_map[tgt_id].append(edge)

        self._ordered_edges: Tuple[DependencyEdge, ...] = tuple(
            sorted(
                edges,
                key=lambda e: (
                    e.source_symbol_id,
                    e.target_symbol_id,
                    e.kind.value,
                    e.metadata.start_line,
                    e.metadata.start_column,
                ),
            )
        )

        logger.debug(
            f"Initialized DependencyGraph: {len(self._ordered_edges)} edges, {len(self._unresolved_tuple)} unresolved"
        )

    @property
    def nodes(self) -> Tuple[GraphNode, ...]:
        """Immutable tuple of all nodes in the graph."""
        return self._symbol_graph.nodes

    @property
    def edges(self) -> Tuple[DependencyEdge, ...]:
        """Immutable tuple of all dependency edges in the graph."""
        return self._ordered_edges

    @property
    def structural_edges(self) -> Tuple[DependencyEdge, ...]:
        """Immutable tuple of structural dependency edges (IMPORTS, INHERITS, IMPLEMENTS)."""
        return tuple(e for e in self._ordered_edges if e.kind.is_structural)

    @property
    def behavioral_edges(self) -> Tuple[DependencyEdge, ...]:
        """Immutable tuple of behavioral dependency edges (CALLS, REFERENCES, USES)."""
        return tuple(e for e in self._ordered_edges if e.kind.is_behavioral)

    @property
    def unresolved_dependencies(self) -> Tuple[UnresolvedDependency, ...]:
        """Immutable tuple of unresolved dependencies."""
        return self._unresolved_tuple

    @property
    def stats(self) -> DependencyGraphStats:
        """Calculate and return read-only dependency graph statistics."""
        call_count = sum(1 for e in self._ordered_edges if e.kind == DependencyEdgeKind.CALLS)
        import_count = sum(1 for e in self._ordered_edges if e.kind == DependencyEdgeKind.IMPORTS)
        inheritance_count = sum(1 for e in self._ordered_edges if e.kind == DependencyEdgeKind.INHERITS)
        implementation_count = sum(1 for e in self._ordered_edges if e.kind == DependencyEdgeKind.IMPLEMENTS)
        reference_count = sum(1 for e in self._ordered_edges if e.kind == DependencyEdgeKind.REFERENCES)
        use_count = sum(1 for e in self._ordered_edges if e.kind == DependencyEdgeKind.USES)

        max_depth = 0
        visited_global = set()

        def get_max_depth(curr_id: str, current_depth: int, visited_path: Set[str]) -> int:
            if current_depth > 50 or curr_id in visited_path:
                return current_depth

            valid_outs = [
                e for e in self._outgoing_map.get(curr_id, [])
                if e.target_symbol_id not in visited_path and e.target_symbol_id != curr_id
            ]
            if not valid_outs:
                return current_depth

            new_path = visited_path | {curr_id}
            return max(
                get_max_depth(e.target_symbol_id, current_depth + 1, new_path)
                for e in valid_outs
            )

        for n in self._symbol_graph.nodes:
            if n.id not in visited_global and self._outgoing_map.get(n.id):
                d = get_max_depth(n.id, 1, set())
                if d > max_depth:
                    max_depth = d

        return DependencyGraphStats(
            dependency_count=len(self._ordered_edges),
            call_count=call_count,
            import_count=import_count,
            inheritance_count=inheritance_count,
            implementation_count=implementation_count,
            reference_count=reference_count,
            use_count=use_count,
            unresolved_count=len(self._unresolved_tuple),
            maximum_dependency_depth=max_depth,
        )

    def lookup_edge(self, edge_id: str) -> Optional[DependencyEdge]:
        """O(1) lookup of a dependency edge by ID."""
        return self._edges_by_id.get(edge_id)

    def outgoing_edges(self, symbol_id: str) -> Tuple[DependencyEdge, ...]:
        """Retrieve outgoing dependency edges for a symbol ID."""
        return tuple(self._outgoing_map.get(symbol_id, []))

    def incoming_edges(self, symbol_id: str) -> Tuple[DependencyEdge, ...]:
        """Retrieve incoming dependency edges for a symbol ID."""
        return tuple(self._incoming_map.get(symbol_id, []))

    def dependencies(
        self, symbol_id: str, kind: Optional[DependencyEdgeKind] = None
    ) -> Tuple[GraphNode, ...]:
        """
        Retrieve direct target symbols that symbol_id depends upon.

        Args:
            symbol_id: Source symbol ID.
            kind: Optional DependencyEdgeKind filter.

        Returns:
            Tuple[GraphNode, ...]: Sequence of dependent target nodes.
        """
        edges = self._outgoing_map.get(symbol_id, [])
        if kind is not None:
            edges = [e for e in edges if e.kind == kind]
        res = [self._nodes_by_id[e.target_symbol_id] for e in edges if e.target_symbol_id in self._nodes_by_id]
        return tuple(res)

    def dependents(
        self, symbol_id: str, kind: Optional[DependencyEdgeKind] = None
    ) -> Tuple[GraphNode, ...]:
        """
        Retrieve symbols that depend upon symbol_id.

        Args:
            symbol_id: Target symbol ID.
            kind: Optional DependencyEdgeKind filter.

        Returns:
            Tuple[GraphNode, ...]: Sequence of dependent source nodes.
        """
        edges = self._incoming_map.get(symbol_id, [])
        if kind is not None:
            edges = [e for e in edges if e.kind == kind]
        res = [self._nodes_by_id[e.source_symbol_id] for e in edges if e.source_symbol_id in self._nodes_by_id]
        return tuple(res)

    def calls(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """Retrieve symbols called by symbol_id."""
        return self.dependencies(symbol_id, kind=DependencyEdgeKind.CALLS)

    def imports(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """Retrieve symbols imported by symbol_id."""
        return self.dependencies(symbol_id, kind=DependencyEdgeKind.IMPORTS)

    def inherits(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """Retrieve base class symbols inherited by symbol_id."""
        return self.dependencies(symbol_id, kind=DependencyEdgeKind.INHERITS)

    def implements(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """Retrieve interface symbols implemented by symbol_id."""
        return self.dependencies(symbol_id, kind=DependencyEdgeKind.IMPLEMENTS)

    def references(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """Retrieve symbols referenced by symbol_id."""
        return self.dependencies(symbol_id, kind=DependencyEdgeKind.REFERENCES)

    def uses(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """Retrieve symbols used by symbol_id."""
        return self.dependencies(symbol_id, kind=DependencyEdgeKind.USES)

    def reachable(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """
        Calculate forward transitive closure (all reachable target symbols).

        Args:
            symbol_id: Starting source symbol ID.

        Returns:
            Tuple[GraphNode, ...]: Transitive sequence of target nodes.
        """
        visited: Set[str] = set()
        queue = deque([symbol_id])
        result: List[GraphNode] = []

        while queue:
            curr_id = queue.popleft()
            for edge in self._outgoing_map.get(curr_id, []):
                tgt_id = edge.target_symbol_id
                if tgt_id not in visited and tgt_id != symbol_id:
                    visited.add(tgt_id)
                    if tgt_id in self._nodes_by_id:
                        result.append(self._nodes_by_id[tgt_id])
                    queue.append(tgt_id)

        return tuple(result)

    def reverse_reachable(self, symbol_id: str) -> Tuple[GraphNode, ...]:
        """
        Calculate reverse transitive closure (all symbols that can reach symbol_id).

        Args:
            symbol_id: Target symbol ID.

        Returns:
            Tuple[GraphNode, ...]: Transitive sequence of source nodes.
        """
        visited: Set[str] = set()
        queue = deque([symbol_id])
        result: List[GraphNode] = []

        while queue:
            curr_id = queue.popleft()
            for edge in self._incoming_map.get(curr_id, []):
                src_id = edge.source_symbol_id
                if src_id not in visited and src_id != symbol_id:
                    visited.add(src_id)
                    if src_id in self._nodes_by_id:
                        result.append(self._nodes_by_id[src_id])
                    queue.append(src_id)

        return tuple(result)

    def has_cycles(self) -> bool:
        """Check if any cycles exist in the dependency graph."""
        return len(self.find_dependency_cycles()) > 0

    def find_dependency_cycles(self) -> Tuple[Tuple[GraphNode, ...], ...]:
        """
        Detect dependency cycles in the graph using DFS 3-color marking.

        Returns:
            Tuple[Tuple[GraphNode, ...], ...]: Tuple of detected cycles.
        """
        color: Dict[str, int] = {n.id: 0 for n in self._symbol_graph.nodes}
        cycles: List[Tuple[GraphNode, ...]] = []

        def _dfs(curr_id: str, path: List[str]) -> None:
            color[curr_id] = 1
            path.append(curr_id)
            for edge in self._outgoing_map.get(curr_id, []):
                tgt_id = edge.target_symbol_id
                if color.get(tgt_id, 0) == 1:
                    idx = path.index(tgt_id)
                    cycle_nodes = tuple(self._nodes_by_id[nid] for nid in path[idx:] if nid in self._nodes_by_id)
                    cycles.append(cycle_nodes)
                elif color.get(tgt_id, 0) == 0:
                    _dfs(tgt_id, path)
            path.pop()
            color[curr_id] = 2

        for n in self._symbol_graph.nodes:
            if color[n.id] == 0:
                _dfs(n.id, [])

        return tuple(cycles)

    def walk_dependencies(self, symbol_id: str) -> Iterator[GraphNode]:
        """Yield forward dependencies in DFS order."""
        for n in self.reachable(symbol_id):
            yield n

    def walk_reverse_dependencies(self, symbol_id: str) -> Iterator[GraphNode]:
        """Yield reverse dependencies in DFS order."""
        for n in self.reverse_reachable(symbol_id):
            yield n

    def iter_nodes(self) -> Iterator[GraphNode]:
        """Yield all nodes in the graph."""
        yield from self._symbol_graph.nodes

    def iter_edges(self) -> Iterator[DependencyEdge]:
        """Yield all dependency edges in the graph."""
        yield from self._ordered_edges

    def to_dict(self) -> dict:
        """
        Export dependency graph to a clean, JSON-serializable dictionary structure.
        """
        return {
            "stats": {
                "dependency_count": self.stats.dependency_count,
                "call_count": self.stats.call_count,
                "import_count": self.stats.import_count,
                "inheritance_count": self.stats.inheritance_count,
                "implementation_count": self.stats.implementation_count,
                "reference_count": self.stats.reference_count,
                "use_count": self.stats.use_count,
                "unresolved_count": self.stats.unresolved_count,
                "maximum_dependency_depth": self.stats.maximum_dependency_depth,
            },
            "edges": [
                {
                    "id": e.id,
                    "source_symbol_id": e.source_symbol_id,
                    "target_symbol_id": e.target_symbol_id,
                    "kind": e.kind.value,
                    "metadata": {
                        "start_line": e.metadata.start_line,
                        "start_column": e.metadata.start_column,
                        "alias": e.metadata.alias,
                        "resolution_status": e.metadata.resolution_status,
                        "confidence": e.metadata.confidence,
                    },
                }
                for e in self._ordered_edges
            ],
            "unresolved": [
                {
                    "kind": u.kind.value,
                    "name": u.name,
                    "source_symbol_id": u.source_symbol_id,
                    "reason": u.reason,
                }
                for u in self._unresolved_tuple
            ],
        }
