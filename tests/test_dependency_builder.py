import pytest

from backend.analyzers.python_dependency_analyzer import PythonDependencyAnalyzer
from backend.builders.hierarchy_graph_builder import HierarchyGraphBuilder
from backend.dependency_candidate import DependencyCandidate
from backend.dependency_edge import DependencyEdge, generate_dependency_edge_id
from backend.dependency_edge_kind import DependencyEdgeKind
from backend.dependency_graph_exceptions import DependencyValidationError
from backend.dependency_graph_validator import DependencyGraphValidator
from backend.dependency_resolver import DependencyResolver
from backend.extractors.python_symbol_extractor import PythonSymbolExtractor
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, SourceFile
from backend.symbol_result import SymbolExtractionResult


def _parse_python(tmp_path, code: str, filename: str = "app.py"):
    file_path = tmp_path / filename
    file_path.write_text(code, encoding="utf-8")

    sf = SourceFile(path=file_path, language=Language.PYTHON, extension=".py", relative_path=filename, size_bytes=file_path.stat().st_size)
    pr = RepositoryParser().parse(sf)
    symbols = PythonSymbolExtractor().extract(pr)
    res = SymbolExtractionResult(parse_result=pr, symbols=tuple(symbols), extraction_time_ms=1.0, has_errors=False)

    sg = HierarchyGraphBuilder().build([res], repository_name="App")
    return sg, pr


def test_python_analyzer_and_resolver(tmp_path):
    code = '''import os
from math import sqrt

class Shape:
    pass

class Circle(Shape):
    def radius(self) -> float:
        return sqrt(16)
'''
    sg, pr = _parse_python(tmp_path, code)

    analyzer = PythonDependencyAnalyzer()
    candidates = analyzer.analyze(sg, [pr])

    assert len(candidates) > 0
    kinds = [c.kind for c in candidates]
    assert DependencyEdgeKind.IMPORTS in kinds
    assert DependencyEdgeKind.INHERITS in kinds
    assert DependencyEdgeKind.CALLS in kinds

    resolver = DependencyResolver()
    edges, unresolved = resolver.resolve_candidates(sg, candidates)

    # Inheritance Circle -> Shape should be resolved to a symbol ID
    inherits_edges = [e for e in edges if e.kind == DependencyEdgeKind.INHERITS]
    assert len(inherits_edges) == 1

    # Standard library imports (os, math) should produce UnresolvedDependency
    assert len(unresolved) >= 1
    unres_names = [u.name for u in unresolved]
    assert any("os" in name or "sqrt" in name for name in unres_names)


def test_validator_dangling_symbol_id(tmp_path):
    code = "x = 10\n"
    sg, _ = _parse_python(tmp_path, code)

    bad_edge = DependencyEdge(
        id="bad_1",
        source_symbol_id=sg.nodes[0].id,
        target_symbol_id="non_existent_target_id",
        kind=DependencyEdgeKind.CALLS,
    )

    validator = DependencyGraphValidator()
    with pytest.raises(DependencyValidationError):
        validator.validate(sg, [bad_edge])
