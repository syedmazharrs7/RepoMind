from dataclasses import dataclass, field
from typing import Tuple

from backend.graph_edge import GraphEdge
from backend.symbol import Symbol
from backend.symbol_kind import SymbolKind


@dataclass(frozen=True)
class GraphNode:
    """
    Immutable representation of a graph node wrapping a Symbol with incoming and outgoing edges.
    """
    symbol: Symbol
    incoming_edges: Tuple[GraphEdge, ...] = field(default_factory=tuple)
    outgoing_edges: Tuple[GraphEdge, ...] = field(default_factory=tuple)

    @property
    def id(self) -> str:
        """Convenience accessor for symbol ID."""
        return self.symbol.id

    @property
    def name(self) -> str:
        """Convenience accessor for symbol name."""
        return self.symbol.name

    @property
    def qualified_name(self) -> str:
        """Convenience accessor for symbol qualified name."""
        return self.symbol.qualified_name

    @property
    def kind(self) -> SymbolKind:
        """Convenience accessor for symbol kind."""
        return self.symbol.kind
