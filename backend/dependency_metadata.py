from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class DependencyMetadata:
    """
    Immutable metadata model holding contextual details for a dependency relationship.
    """
    start_line: int = 1
    start_column: int = 0
    alias: Optional[str] = None
    resolution_status: str = "RESOLVED"
    confidence: float = 1.0
    extra_info: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)
