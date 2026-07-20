from dataclasses import dataclass, field
from typing import Optional, Tuple

from backend.parse_result import ParseResult
from backend.symbol import Symbol


@dataclass(frozen=True)
class SymbolExtractionResult:
    """Immutable result container holding extracted symbols for a single ParseResult."""
    parse_result: ParseResult
    symbols: Tuple[Symbol, ...] = field(default_factory=tuple)
    extraction_time_ms: float = 0.0
    has_errors: bool = False
    error_message: Optional[str] = None
