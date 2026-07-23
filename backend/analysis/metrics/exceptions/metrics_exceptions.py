"""
Custom exception classes for the RepoMind Repository Metrics & Analysis Engine.
"""

class MetricsError(Exception):
    """Base exception for all metrics and analysis errors."""
    pass


class ValidationError(MetricsError):
    """Exception raised when metric validation fails."""
    pass


class AnalyzerError(MetricsError):
    """Exception raised when an individual metric analyzer fails during execution."""
    pass


class DuplicateAnalyzerError(MetricsError):
    """Exception raised when registering an analyzer that already exists in the factory registry."""
    pass


class GraphConsistencyError(ValidationError):
    """Exception raised when the symbol graph and dependency graph are inconsistent with computed metrics."""
    pass
