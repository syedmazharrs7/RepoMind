import pytest

from backend.builders.hierarchy_graph_builder import HierarchyGraphBuilder
from backend.graph_builder_factory import (
    GraphBuilderFactory,
    get_default_graph_builder_factory,
)
from backend.graph_exceptions import GraphBuildError


def test_graph_factory_default_builder():
    factory = get_default_graph_builder_factory()

    builder = factory.get_builder("HIERARCHY")
    assert isinstance(builder, HierarchyGraphBuilder)


def test_graph_factory_custom_registration():
    factory = GraphBuilderFactory()
    custom_builder = HierarchyGraphBuilder()
    factory.register_builder("CUSTOM_HIERARCHY", custom_builder)

    retrieved = factory.get_builder("custom_hierarchy")
    assert retrieved is custom_builder


def test_graph_factory_unregistered_builder():
    factory = GraphBuilderFactory()
    with pytest.raises(GraphBuildError):
        factory.get_builder("UNKNOWN_BUILDER")
