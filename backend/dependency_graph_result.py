from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from backend.dependency_graph import DependencyGraph


@dataclass(frozen=True)
class DependencyGraphStats:
    """Immutable read-only container for dependency graph metrics."""
    dependency_count: int
    call_count: int
    import_count: int
    inheritance_count: int
    implementation_count: int
    reference_count: int
    use_count: int
    unresolved_count: int
    maximum_dependency_depth: int


@dataclass(frozen=True)
class DependencyGraphResult:
    """Immutable result container holding the built DependencyGraph, timing, and error details."""
    dependency_graph: Optional["DependencyGraph"]
    analysis_time_ms: float = 0.0
    has_errors: bool = False
    error_message: Optional[str] = None
