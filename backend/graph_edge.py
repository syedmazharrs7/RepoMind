import hashlib
from dataclasses import dataclass
from typing import Union

from backend.graph_edge_kind import GraphEdgeKind


def generate_edge_id(
    source_symbol_id: str,
    target_symbol_id: str,
    kind: Union[GraphEdgeKind, str],
) -> str:
    """
    Generate a deterministic, stable hash ID for a graph edge.

    Args:
        source_symbol_id: ID of the source symbol.
        target_symbol_id: ID of the target symbol.
        kind: The edge relationship kind.

    Returns:
        str: 16-character hexadecimal SHA-256 hash.
    """
    kind_str = kind.value if isinstance(kind, GraphEdgeKind) else str(kind)
    raw_key = f"{source_symbol_id}:{target_symbol_id}:{kind_str}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class GraphEdge:
    """Immutable representation of a directed relationship edge between two symbols."""
    id: str
    source_symbol_id: str
    target_symbol_id: str
    kind: GraphEdgeKind
