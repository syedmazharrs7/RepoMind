import pytest

from backend.builders.hierarchy_graph_builder import HierarchyGraphBuilder
from backend.extractors.python_symbol_extractor import PythonSymbolExtractor
from backend.parse_result import ParseResult
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, SourceFile
from backend.symbol_kind import SymbolKind
from backend.symbol_result import SymbolExtractionResult


def _extract_and_build(tmp_path, code: str, filename: str = "app.py"):
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
    res = SymbolExtractionResult(
        parse_result=parse_result,
        symbols=tuple(symbols),
        extraction_time_ms=1.0,
        has_errors=False,
    )

    builder = HierarchyGraphBuilder()
    graph = builder.build([res], repository_name="RepoApp")
    return graph, res.symbols


def test_symbol_graph_lookups_and_stats(tmp_path):
    code = '''class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
'''
    graph, symbols = _extract_and_build(tmp_path, code)

    # 1. Lookup by ID
    calc_sym = next(s for s in symbols if s.name == "Calculator")
    node = graph.lookup_by_id(calc_sym.id)
    assert node is not None
    assert node.name == "Calculator"

    # 2. Lookup by Qualified Name
    node_qname = graph.find_symbol("app.Calculator")
    assert node_qname is not None
    assert node_qname.id == calc_sym.id

    # 3. Parent & Children
    add_node = graph.find_symbol("app.Calculator.add")
    assert add_node is not None
    parent_node = graph.parent(add_node.id)
    assert parent_node is not None
    assert parent_node.name == "Calculator"

    children = graph.children(calc_sym.id)
    assert len(children) == 1
    assert children[0].name == "add"

    # 4. Ancestors (add -> Calculator -> app module -> RepoApp root)
    anc = graph.ancestors(add_node.id)
    anc_names = [a.name for a in anc]
    assert anc_names == ["Calculator", "app", "RepoApp"]

    # 5. Descendants (Calculator -> add -> parameters)
    desc = graph.descendants(calc_sym.id)
    desc_names = [d.name for d in desc]
    assert "add" in desc_names
    assert "a" in desc_names
    assert "b" in desc_names

    # 6. Read-only Stats API
    stats = graph.stats
    assert stats.node_count >= 5  # RepoApp + app + Calculator + add + a + b
    assert stats.edge_count >= 4
    assert stats.root_count == 1
    assert stats.leaf_count >= 2
    assert stats.max_depth >= 5

    # 7. Serialization dictionary helper
    as_dict = graph.to_dict()
    assert "stats" in as_dict
    assert "nodes" in as_dict
    assert "edges" in as_dict
    assert len(as_dict["nodes"]) == stats.node_count


def test_symbol_graph_traversals(tmp_path):
    code = '''class Service:
    def process(self):
        pass
'''
    graph, _ = _extract_and_build(tmp_path, code)

    dfs_nodes = list(graph.walk_depth_first())
    bfs_nodes = list(graph.walk_breadth_first())

    assert len(dfs_nodes) == len(graph.nodes)
    assert len(bfs_nodes) == len(graph.nodes)

    # First node in walk is root
    assert dfs_nodes[0].name == "RepoApp"
    assert bfs_nodes[0].name == "RepoApp"
