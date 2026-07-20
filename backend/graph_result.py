from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from backend.symbol_graph import SymbolGraph


@dataclass(frozen=True)
class GraphStats:
    """Immutable read-only container for repository graph health statistics."""
    node_count: int
    edge_count: int
    root_count: int
    leaf_count: int
    max_depth: int


@dataclass(frozen=True)
class GraphResult:
    """Immutable result container holding the constructed SymbolGraph, build time, and error status."""
    symbol_graph: Optional["SymbolGraph"]
    build_time_ms: float = 0.0
    has_errors: bool = False
    error_message: Optional[str] = None
