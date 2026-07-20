import hashlib
from dataclasses import dataclass, field
from typing import Optional, Tuple, Union

from backend.repository_scanner import Language
from backend.symbol_kind import SymbolKind


def generate_symbol_id(
    language: Union[Language, str],
    file_path: str,
    qualified_name: str,
    kind: Union[SymbolKind, str],
) -> str:
    """
    Generate a deterministic, stable hash ID for a symbol.

    Args:
        language: The programming language of the source file.
        file_path: Relative file path of the source file.
        qualified_name: Fully qualified name of the symbol.
        kind: The kind of the symbol.

    Returns:
        str: 16-character hexadecimal SHA-256 hash.
    """
    lang_str = language.value if isinstance(language, Language) else str(language)
    kind_str = kind.value if isinstance(kind, SymbolKind) else str(kind)
    raw_key = f"{lang_str}:{file_path}:{qualified_name}:{kind_str}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Symbol:
    """
    Immutable representation of a semantic code entity in RepoMind.
    """
    id: str
    name: str
    qualified_name: str
    kind: SymbolKind
    language: Language
    file_path: str
    start_line: int
    end_line: int
    start_column: int
    end_column: int
    parent_symbol: Optional[str] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None
    decorators: Tuple[str, ...] = field(default_factory=tuple)
    visibility: str = "public"
    is_async: bool = False
    is_exported: bool = False

    @property
    def line_count(self) -> int:
        """
        Calculate total line count occupied by the symbol.

        Returns:
            int: Number of lines span.
        """
        if self.end_line >= self.start_line:
            return self.end_line - self.start_line + 1
        return 0
