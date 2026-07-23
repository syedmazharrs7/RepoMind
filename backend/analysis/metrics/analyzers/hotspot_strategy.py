"""
Strategy pattern interface and implementations for calculating code hotspots.
"""
from abc import ABC, abstractmethod


class HotspotStrategy(ABC):
    """Abstract Strategy interface for computing hotspot scores."""

    @abstractmethod
    def calculate_score(self, complexity: float, degree: int) -> float:
        """
        Calculate hotspot score based on structural complexity and dependency connections.

        Args:
            complexity: Structural complexity score of the file.
            degree: Count of incoming and outgoing dependency edges for the file.

        Returns:
            float: Computed hotspot score.
        """
        pass


class ComplexityDependencyStrategy(HotspotStrategy):
    """
    Default Strategy: Multiplies complexity by degree connections.
    Highlights files that are both structurally complex and highly connected.
    """

    def calculate_score(self, complexity: float, degree: int) -> float:
        return complexity * (degree + 1)


class DependencyOnlyStrategy(HotspotStrategy):
    """Strategy that scores hotspots purely by dependency degree (coupling)."""

    def calculate_score(self, complexity: float, degree: int) -> float:
        return float(degree)


class ComplexityOnlyStrategy(HotspotStrategy):
    """Strategy that scores hotspots purely by file size/structural complexity."""

    def calculate_score(self, complexity: float, degree: int) -> float:
        return complexity
