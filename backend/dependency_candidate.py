from dataclasses import dataclass
from typing import Optional

from backend.dependency_edge_kind import DependencyEdgeKind


@dataclass(frozen=True)
class DependencyCandidate:
    """
    Unresolved dependency candidate produced by language AST analyzers.
    Represents an extracted intent prior to symbol resolution.
    """
    source_symbol_id: str
    target_name: str
    kind: DependencyEdgeKind
    start_line: int = 1
    start_column: int = 0
    alias: Optional[str] = None
    context_qname: Optional[str] = None
