from enum import Enum


class DependencyEdgeKind(str, Enum):
    """Enum representing relationship types between symbols in the dependency graph."""
    CALLS = "CALLS"
    IMPORTS = "IMPORTS"
    INHERITS = "INHERITS"
    IMPLEMENTS = "IMPLEMENTS"
    REFERENCES = "REFERENCES"
    USES = "USES"

    @property
    def is_structural(self) -> bool:
        """
        Check if the relationship is structural (IMPORTS, INHERITS, IMPLEMENTS).

        Returns:
            bool: True if structural relationship.
        """
        return self in (
            DependencyEdgeKind.IMPORTS,
            DependencyEdgeKind.INHERITS,
            DependencyEdgeKind.IMPLEMENTS,
        )

    @property
    def is_behavioral(self) -> bool:
        """
        Check if the relationship is behavioral (CALLS, REFERENCES, USES).

        Returns:
            bool: True if behavioral relationship.
        """
        return self in (
            DependencyEdgeKind.CALLS,
            DependencyEdgeKind.REFERENCES,
            DependencyEdgeKind.USES,
        )
