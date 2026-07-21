from pathlib import Path
import pytest

from backend.dependency_edge_kind import DependencyEdgeKind
from backend.dependency_graph_result import DependencyGraphResult
from backend.repository_dependency_graph_builder import RepositoryDependencyGraphBuilder
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, RepositoryScanner
from backend.repository_symbol_extractor import RepositorySymbolExtractor
from backend.repository_symbol_graph_builder import RepositorySymbolGraphBuilder


def test_repository_dependency_graph_cross_file(tmp_path):
    f1 = tmp_path / "models.py"
    f1.write_text("class BaseModel:\n    pass\n", encoding="utf-8")

    f2 = tmp_path / "services.py"
    f2.write_text("from models import BaseModel\n\nclass UserService(BaseModel):\n    def login(self):\n        pass\n", encoding="utf-8")

    scanner = RepositoryScanner()
    source_files = scanner.scan(tmp_path)

    parser = RepositoryParser()
    parse_results = [parser.parse(sf) for sf in source_files]

    extractor = RepositorySymbolExtractor()
    extraction_results = extractor.extract_repository(parse_results)

    sg_builder = RepositorySymbolGraphBuilder()
    sg_res = sg_builder.build_graph(extraction_results, repository_name="CrossFileApp")
    assert not sg_res.has_errors and sg_res.symbol_graph is not None

    dep_builder = RepositoryDependencyGraphBuilder()
    dep_res = dep_builder.build_dependency_graph(sg_res.symbol_graph, parse_results)

    assert isinstance(dep_res, DependencyGraphResult)
    assert not dep_res.has_errors
    assert dep_res.dependency_graph is not None

    dep_graph = dep_res.dependency_graph
    stats = dep_graph.stats
    assert stats.dependency_count >= 1
    assert stats.structural_edges if hasattr(stats, 'structural_edges') else True

    # UserService should inherit BaseModel
    user_service_node = sg_res.symbol_graph.find_symbol("services.UserService")
    base_model_node = sg_res.symbol_graph.find_symbol("models.BaseModel")
    assert user_service_node and base_model_node

    inherits = dep_graph.inherits(user_service_node.id)
    assert base_model_node in inherits


def test_flask_repository_dependency_graph_integration():
    flask_dir = Path("repos/pallets/flask").resolve()
    if not flask_dir.exists():
        pytest.skip("Flask repository not found at repos/pallets/flask")

    # 1. Scan
    scanner = RepositoryScanner()
    source_files = scanner.scan(flask_dir)
    py_files = [sf for sf in source_files if sf.language == Language.PYTHON]
    assert len(py_files) > 0

    # 2. Parse
    parser = RepositoryParser()
    parse_results = [parser.parse(sf) for sf in py_files]

    # 3. Extract Symbols
    extractor = RepositorySymbolExtractor()
    extraction_results = extractor.extract_repository(parse_results)

    # 4. Build Symbol Graph
    sg_builder = RepositorySymbolGraphBuilder()
    sg_res = sg_builder.build_graph(extraction_results, repository_name="Flask")
    assert not sg_res.has_errors and sg_res.symbol_graph is not None

    # 5. Build Dependency Graph
    dep_builder = RepositoryDependencyGraphBuilder()
    dep_res = dep_builder.build_dependency_graph(sg_res.symbol_graph, parse_results)

    assert not dep_res.has_errors
    assert dep_res.dependency_graph is not None

    dep_graph = dep_res.dependency_graph
    stats = dep_graph.stats

    # Verify dependency metrics
    assert stats.dependency_count > 50
    assert stats.call_count > 0 or stats.import_count > 0
    assert stats.unresolved_count > 0  # stdlib imports (os, sys, typing) and external (werkzeug, jinja2, click)

    # Verify structural vs behavioral edges properties
    assert len(dep_graph.structural_edges) > 0
    assert len(dep_graph.behavioral_edges) > 0

    # Verify to_dict() export
    dict_export = dep_graph.to_dict()
    assert "stats" in dict_export
    assert "edges" in dict_export
    assert "unresolved" in dict_export
