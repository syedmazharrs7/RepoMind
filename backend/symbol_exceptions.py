class SymbolExtractionError(Exception):
    """Base exception for Symbol Extraction module."""
    pass


class UnsupportedLanguageError(SymbolExtractionError):
    """Raised when no extractor is registered for the specified language."""
    pass


class InvalidASTError(SymbolExtractionError):
    """Raised when the ParseResult AST is missing or malformed."""
    pass


class ExtractionFailureError(SymbolExtractionError):
    """Raised when symbol extraction fails during processing."""
    pass
