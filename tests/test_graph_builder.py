import pytest

from backend.builders.hierarchy_graph_builder import HierarchyGraphBuilder
from backend.extractors.python_symbol_extractor import PythonSymbolExtractor
from backend.graph_edge_kind import GraphEdgeKind
from backend.graph_exceptions import (
    CycleDetectedError,
    DuplicateSymbolError,
    InvalidHierarchyError,
    MissingParentError,
)
from backend.graph_node import GraphNode
from backend.graph_validator import GraphValidator
from backend.parse_result import ParseResult
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, SourceFile
from backend.symbol import Symbol, generate_symbol_id
from backend.symbol_kind import SymbolKind
from backend.symbol_result import SymbolExtractionResult


def _extract(tmp_path, code: str, filename: str = "main.py") -> SymbolExtractionResult:
    file_path = tmp_path / filename
    file_path.write_text(code, encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.PYTHON,
        extension=".py",
        relative_path=filename,
        size_bytes=file_path.stat().st_size,
    )

    parser = RepositoryParser()
    parse_result = parser.parse(source_file)

    extractor = PythonSymbolExtractor()
    symbols = extractor.extract(parse_result)
    return SymbolExtractionResult(
        parse_result=parse_result,
        symbols=tuple(symbols),
        extraction_time_ms=1.0,
        has_errors=False,
    )


def test_hierarchy_graph_builder_single_module(tmp_path):
    res = _extract(tmp_path, "class User:\n    def login(self):\n        pass\n")

    builder = HierarchyGraphBuilder()
    graph = builder.build([res], repository_name="TestRepo")

    assert graph.root_node is not None
    assert graph.root_node.name == "TestRepo"

    mod_nodes = graph.children(graph.root_node.id)
    assert len(mod_nodes) == 1
    assert mod_nodes[0].kind == SymbolKind.MODULE

    cls_nodes = graph.children(mod_nodes[0].id)
    assert len(cls_nodes) == 1
    assert cls_nodes[0].name == "User"

    method_nodes = graph.children(cls_nodes[0].id)
    assert len(method_nodes) == 1
    assert method_nodes[0].name == "login"


def test_validator_duplicate_symbol_id(tmp_path):
    res = _extract(tmp_path, "x = 10\n")
    dup_symbol = res.symbols[0]  # duplicate root module symbol
    bad_res = SymbolExtractionResult(
        parse_result=res.parse_result,
        symbols=res.symbols + (dup_symbol,),
    )

    builder = HierarchyGraphBuilder()
    with pytest.raises(DuplicateSymbolError):
        builder.build([bad_res])


def test_validator_missing_parent(tmp_path):
    orphan_symbol = Symbol(
        id="orphan_1",
        name="OrphanClass",
        qualified_name="missing_mod.OrphanClass",
        kind=SymbolKind.CLASS,
        language=Language.PYTHON,
        file_path="orphan.py",
        start_line=1,
        end_line=5,
        start_column=0,
        end_column=0,
        parent_symbol="non_existent_parent_id",
    )

    validator = GraphValidator()
    node = GraphNode(symbol=orphan_symbol)
    with pytest.raises(MissingParentError):
        validator.validate(nodes=[node], edges=[])


def test_validator_cycle_detection():
    s1 = Symbol(
        id="node_a",
        name="A",
        qualified_name="mod.A",
        kind=SymbolKind.CLASS,
        language=Language.PYTHON,
        file_path="mod.py",
        start_line=1,
        end_line=5,
        start_column=0,
        end_column=0,
        parent_symbol="node_b",
    )
    s2 = Symbol(
        id="node_b",
        name="B",
        qualified_name="mod.B",
        kind=SymbolKind.CLASS,
        language=Language.PYTHON,
        file_path="mod.py",
        start_line=6,
        end_line=10,
        start_column=0,
        end_column=0,
        parent_symbol="node_a",
    )

    from backend.graph_edge import GraphEdge
    e1 = GraphEdge(id="e1", source_symbol_id="node_a", target_symbol_id="node_b", kind=GraphEdgeKind.OWNS)
    e2 = GraphEdge(id="e2", source_symbol_id="node_b", target_symbol_id="node_a", kind=GraphEdgeKind.OWNS)

    validator = GraphValidator()
    n1 = GraphNode(symbol=s1, incoming_edges=(e2,), outgoing_edges=(e1,))
    n2 = GraphNode(symbol=s2, incoming_edges=(e1,), outgoing_edges=(e2,))

    with pytest.raises(CycleDetectedError):
        validator.validate(nodes=[n1, n2], edges=[e1, e2])
