class RepositoryParserError(Exception):
    """Base exception for Repository Parser module."""
    pass


class ParserInitializationError(RepositoryParserError):
    """Exception raised when a specific tree-sitter parser cannot be initialized."""
    pass


class UnsupportedLanguageError(RepositoryParserError):
    """Exception raised when a file's language is not supported by the parser registry."""
    pass


class FileReadError(RepositoryParserError):
    """Exception raised when a source file cannot be read from the filesystem."""
    pass


class ParseFailureError(RepositoryParserError):
    """Exception raised when tree-sitter parsing fails catastrophically."""
    pass
