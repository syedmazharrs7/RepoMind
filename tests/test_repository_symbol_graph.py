from pathlib import Path
import pytest

from backend.graph_edge_kind import GraphEdgeKind
from backend.graph_result import GraphResult
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, RepositoryScanner
from backend.repository_symbol_extractor import RepositorySymbolExtractor
from backend.repository_symbol_graph_builder import RepositorySymbolGraphBuilder
from backend.symbol_graph import SymbolGraph
from backend.symbol_kind import SymbolKind


def test_repository_symbol_graph_builder_orchestrator(tmp_path):
    f1 = tmp_path / "a.py"
    f1.write_text("class Alpha:\n    def run(self):\n        pass\n", encoding="utf-8")

    f2 = tmp_path / "b.py"
    f2.write_text("def beta():\n    pass\n", encoding="utf-8")

    scanner = RepositoryScanner()
    source_files = scanner.scan(tmp_path)

    parser = RepositoryParser()
    parse_results = [parser.parse(sf) for sf in source_files]

    extractor = RepositorySymbolExtractor()
    extraction_results = extractor.extract_repository(parse_results)

    graph_builder = RepositorySymbolGraphBuilder()
    graph_res = graph_builder.build_graph(extraction_results, repository_name="TestProject")

    assert isinstance(graph_res, GraphResult)
    assert not graph_res.has_errors
    assert graph_res.symbol_graph is not None

    graph = graph_res.symbol_graph
    assert graph.root_node is not None
    assert graph.root_node.name == "TestProject"

    alpha_node = graph.find_symbol("a.Alpha")
    assert alpha_node is not None

    beta_node = graph.find_symbol("b.beta")
    assert beta_node is not None


def test_flask_repository_graph_integration():
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
    graph_builder = RepositorySymbolGraphBuilder()
    graph_res = graph_builder.build_graph(extraction_results, repository_name="Flask")

    assert not graph_res.has_errors
    assert graph_res.symbol_graph is not None

    graph = graph_res.symbol_graph
    stats = graph.stats

    # 5. Verification
    assert stats.node_count > 100
    assert stats.edge_count > 100
    assert stats.root_count == 1
    assert graph.root_node is not None
    assert graph.root_node.name == "Flask"

    # Verify every extracted symbol exists in the graph
    extracted_symbols = [s for res in extraction_results for s in res.symbols]
    for s in extracted_symbols:
        node = graph.lookup_by_id(s.id)
        assert node is not None

    # Verify root module nodes are children of Flask canonical root node
    module_kids = graph.children(graph.root_node.id)
    assert len(module_kids) == len(py_files)
    assert all(k.kind == SymbolKind.MODULE for k in module_kids)

    # Verify ancestors and descendants traversal on Flask app class / methods if present
    flask_node = graph.find_symbol("src.flask.app.Flask")
    if flask_node:
        anc = graph.ancestors(flask_node.id)
        anc_names = [a.name for a in anc]
        assert "Flask" in anc_names  # root project name

        desc = graph.descendants(flask_node.id)
        assert len(desc) > 0
