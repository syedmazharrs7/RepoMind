from dataclasses import dataclass
from typing import Optional
import tree_sitter

from backend.repository_scanner import SourceFile


@dataclass(frozen=True)
class ParseResult:
    """Immutable representation of a file parsing result."""
    source_file: SourceFile
    tree: Optional[tree_sitter.Tree]
    has_errors: bool
    error_message: Optional[str]
    parse_time_ms: float
