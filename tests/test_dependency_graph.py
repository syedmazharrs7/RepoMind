import pytest

from backend.builders.hierarchy_graph_builder import HierarchyGraphBuilder
from backend.dependency_edge import DependencyEdge, generate_dependency_edge_id
from backend.dependency_edge_kind import DependencyEdgeKind
from backend.dependency_graph import DependencyGraph, UnresolvedDependency
from backend.dependency_metadata import DependencyMetadata
from backend.extractors.python_symbol_extractor import PythonSymbolExtractor
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, SourceFile
from backend.symbol_result import SymbolExtractionResult


def _build_test_symbol_graph(tmp_path, code: str, filename: str = "app.py"):
    file_path = tmp_path / filename
    file_path.write_text(code, encoding="utf-8")

    sf = SourceFile(path=file_path, language=Language.PYTHON, extension=".py", relative_path=filename, size_bytes=file_path.stat().st_size)
    pr = RepositoryParser().parse(sf)
    symbols = PythonSymbolExtractor().extract(pr)
    res = SymbolExtractionResult(parse_result=pr, symbols=tuple(symbols), extraction_time_ms=1.0, has_errors=False)

    sg = HierarchyGraphBuilder().build([res], repository_name="TestApp")
    return sg


def test_dependency_graph_queries_and_stats(tmp_path):
    code = '''class Base:
    def execute(self):
        pass

class Child(Base):
    def run(self):
        self.execute()
'''
    sg = _build_test_symbol_graph(tmp_path, code)

    base_node = sg.find_symbol("app.Base")
    child_node = sg.find_symbol("app.Child")
    execute_node = sg.find_symbol("app.Base.execute")
    run_node = sg.find_symbol("app.Child.run")

    assert base_node and child_node and execute_node and run_node

    # Build manual edges to test query APIs
    meta1 = DependencyMetadata(start_line=5, start_column=0)
    e1 = DependencyEdge(
        id=generate_dependency_edge_id(child_node.id, base_node.id, DependencyEdgeKind.INHERITS, 5, 0),
        source_symbol_id=child_node.id,
        target_symbol_id=base_node.id,
        kind=DependencyEdgeKind.INHERITS,
        metadata=meta1,
    )

    meta2 = DependencyMetadata(start_line=7, start_column=8)
    e2 = DependencyEdge(
        id=generate_dependency_edge_id(run_node.id, execute_node.id, DependencyEdgeKind.CALLS, 7, 8),
        source_symbol_id=run_node.id,
        target_symbol_id=execute_node.id,
        kind=DependencyEdgeKind.CALLS,
        metadata=meta2,
    )

    unres = UnresolvedDependency(
        kind=DependencyEdgeKind.IMPORTS,
        name="os",
        source_symbol_id=run_node.id,
        reason="Standard Library",
    )

    dep_graph = DependencyGraph(symbol_graph=sg, edges=[e1, e2], unresolved=[unres])

    # 1. Structural vs Behavioral edges
    assert len(dep_graph.structural_edges) == 1
    assert dep_graph.structural_edges[0].kind == DependencyEdgeKind.INHERITS

    assert len(dep_graph.behavioral_edges) == 1
    assert dep_graph.behavioral_edges[0].kind == DependencyEdgeKind.CALLS

    # 2. Specific query APIs
    assert dep_graph.inherits(child_node.id)[0].id == base_node.id
    assert dep_graph.calls(run_node.id)[0].id == execute_node.id
    assert len(dep_graph.dependents(execute_node.id, kind=DependencyEdgeKind.CALLS)) == 1

    # 3. Transitive Reachability
    reachable_from_child = dep_graph.reachable(child_node.id)
    assert base_node in reachable_from_child

    reverse_from_exec = dep_graph.reverse_reachable(execute_node.id)
    assert run_node in reverse_from_exec

    # 4. Cycle Detection APIs
    assert not dep_graph.has_cycles()
    assert len(dep_graph.find_dependency_cycles()) == 0

    # 5. Stats API
    stats = dep_graph.stats
    assert stats.dependency_count == 2
    assert stats.inheritance_count == 1
    assert stats.call_count == 1
    assert stats.unresolved_count == 1

    # 6. Serialization
    as_dict = dep_graph.to_dict()
    assert "stats" in as_dict
    assert "edges" in as_dict
    assert "unresolved" in as_dict
