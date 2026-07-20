import logging
import threading
from typing import Dict, Optional

from backend.builders.base_graph_builder import BaseGraphBuilder
from backend.graph_exceptions import GraphBuildError

logger = logging.getLogger(__name__)


class GraphBuilderFactory:
    """Registry-based factory for obtaining graph builders."""

    def __init__(self) -> None:
        """Initialize factory with an empty registry."""
        self._registry: Dict[str, BaseGraphBuilder] = {}
        logger.debug("Initialized GraphBuilderFactory registry")

    def register_builder(self, name: str, builder_instance: BaseGraphBuilder) -> None:
        """
        Register a graph builder instance for a specified key name.

        Args:
            name: Key name string (case-insensitive).
            builder_instance: Instance of BaseGraphBuilder.
        """
        key = name.upper()
        self._registry[key] = builder_instance
        logger.info(f"Registered graph builder for key: '{key}'")

    def get_builder(self, name: str = "HIERARCHY") -> BaseGraphBuilder:
        """
        Get the graph builder instance registered for key name.

        Args:
            name: Key name string (defaults to 'HIERARCHY').

        Returns:
            BaseGraphBuilder: Registered builder instance.

        Raises:
            GraphBuildError: If no builder is registered for the given key.
        """
        key = name.upper()
        if key not in self._registry:
            logger.error(f"No graph builder registered for key: '{key}'")
            raise GraphBuildError(f"No graph builder registered for key: '{name}'")
        return self._registry[key]


# Reusable global factory instance for application service usage
_default_factory: Optional[GraphBuilderFactory] = None
_lock = threading.Lock()


def get_default_graph_builder_factory() -> GraphBuilderFactory:
    """
    Get or initialize the default global GraphBuilderFactory instance.
    Thread-safe double-checked locking.

    Returns:
        GraphBuilderFactory: Default global factory instance.
    """
    global _default_factory
    if _default_factory is None:
        with _lock:
            if _default_factory is None:
                logger.info("Initializing default GraphBuilderFactory service...")
                factory = GraphBuilderFactory()

                from backend.builders.hierarchy_graph_builder import HierarchyGraphBuilder

                factory.register_builder("HIERARCHY", HierarchyGraphBuilder())

                _default_factory = factory
    return _default_factory
