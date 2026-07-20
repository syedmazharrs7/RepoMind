class GraphBuildError(Exception):
    """Base exception for Symbol Graph module."""
    pass


class DuplicateSymbolError(GraphBuildError):
    """Raised when duplicate symbol IDs are detected in the graph."""
    pass


class MissingParentError(GraphBuildError):
    """Raised when a non-root symbol references a parent symbol ID that does not exist in the graph."""
    pass


class CycleDetectedError(GraphBuildError):
    """Raised when a cycle is detected in the ownership graph."""
    pass


class InvalidHierarchyError(GraphBuildError):
    """Raised when graph validation detects orphan symbols or invalid hierarchy structure."""
    pass
