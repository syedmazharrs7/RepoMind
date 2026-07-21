import hashlib
from dataclasses import dataclass, field
from typing import Union

from backend.dependency_edge_kind import DependencyEdgeKind
from backend.dependency_metadata import DependencyMetadata


def generate_dependency_edge_id(
    source_symbol_id: str,
    target_symbol_id: str,
    kind: Union[DependencyEdgeKind, str],
    start_line: int = 1,
    start_column: int = 0,
) -> str:
    """
    Generate a deterministic, stable hash ID for a dependency edge.

    Args:
        source_symbol_id: ID of the source symbol.
        target_symbol_id: ID of the target symbol.
        kind: The dependency relationship kind.
        start_line: Line number where dependency occurs.
        start_column: Column number where dependency occurs.

    Returns:
        str: 16-character hexadecimal SHA-256 hash.
    """
    kind_str = kind.value if isinstance(kind, DependencyEdgeKind) else str(kind)
    raw_key = f"{source_symbol_id}:{target_symbol_id}:{kind_str}:{start_line}:{start_column}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class DependencyEdge:
    """Immutable representation of a directed dependency relationship between two symbols."""
    id: str
    source_symbol_id: str
    target_symbol_id: str
    kind: DependencyEdgeKind
    metadata: DependencyMetadata = field(default_factory=DependencyMetadata)
