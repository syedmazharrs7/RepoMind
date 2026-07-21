class DependencyGraphError(Exception):
    """Base exception for Dependency Graph module."""
    pass


class DependencyResolutionError(DependencyGraphError):
    """Raised when dependency resolution fails unexpectedly."""
    pass


class UnsupportedLanguageError(DependencyGraphError):
    """Raised when no dependency analyzer is registered for a language."""
    pass


class InvalidDependencyError(DependencyGraphError):
    """Raised when a dependency candidate or edge is malformed."""
    pass


class DependencyValidationError(DependencyGraphError):
    """Raised when dependency graph validation fails."""
    pass
