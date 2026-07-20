from pathlib import Path
import pytest

from backend.parse_result import ParseResult
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, RepositoryScanner, SourceFile
from backend.repository_symbol_extractor import RepositorySymbolExtractor
from backend.symbol_kind import SymbolKind


def test_repository_symbol_extractor_single_file(tmp_path):
    file_path = tmp_path / "utils.py"
    file_path.write_text("def compute(x: int) -> int:\n    return x * 2\n", encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.PYTHON,
        extension=".py",
        relative_path="utils.py",
        size_bytes=file_path.stat().st_size,
    )

    parser = RepositoryParser()
    parse_result = parser.parse(source_file)

    extractor = RepositorySymbolExtractor()
    result = extractor.extract_symbols(parse_result)

    assert not result.has_errors
    assert result.error_message is None
    assert result.extraction_time_ms >= 0
    assert len(result.symbols) >= 2  # MODULE + compute function + parameters

    mod_symbol = result.symbols[0]
    assert mod_symbol.kind == SymbolKind.MODULE
    assert mod_symbol.name == "utils"


def test_repository_symbol_extractor_multiple_files(tmp_path):
    f1 = tmp_path / "a.py"
    f1.write_text("class A:\n    pass\n", encoding="utf-8")

    f2 = tmp_path / "b.js"
    f2.write_text("function b() {}\n", encoding="utf-8")

    sf1 = SourceFile(path=f1, language=Language.PYTHON, extension=".py", relative_path="a.py", size_bytes=f1.stat().st_size)
    sf2 = SourceFile(path=f2, language=Language.JAVASCRIPT, extension=".js", relative_path="b.js", size_bytes=f2.stat().st_size)

    parser = RepositoryParser()
    prs = [parser.parse(sf1), parser.parse(sf2)]

    extractor = RepositorySymbolExtractor()
    results = extractor.extract_repository(prs)

    assert len(results) == 2
    assert all(not r.has_errors for r in results)
    assert any(s.name == "A" for r in results for s in r.symbols)
    assert any(s.name == "b" for r in results for s in r.symbols)


def test_flask_repository_integration():
    flask_dir = Path("repos/pallets/flask").resolve()
    if not flask_dir.exists():
        pytest.skip("Flask repository not found at repos/pallets/flask")

    scanner = RepositoryScanner()
    source_files = scanner.scan(flask_dir)
    assert len(source_files) > 0

    # Filter Python source files
    py_files = [sf for sf in source_files if sf.language == Language.PYTHON]
    assert len(py_files) > 0

    parser = RepositoryParser()
    parse_results = [parser.parse(sf) for sf in py_files]
    assert len(parse_results) == len(py_files)

    extractor = RepositorySymbolExtractor()
    symbol_results = extractor.extract_repository(parse_results)

    assert len(symbol_results) == len(parse_results)

    total_symbols = 0
    for res in symbol_results:
        assert isinstance(res.parse_result, ParseResult)
        assert not res.has_errors
        assert len(res.symbols) >= 1  # Every file has at least a root MODULE symbol

        # Root symbol must be MODULE
        root_symbol = res.symbols[0]
        assert root_symbol.kind == SymbolKind.MODULE
        assert root_symbol.parent_symbol is None

        # Verify child symbols reference parent IDs properly
        symbol_ids = {s.id for s in res.symbols}
        for s in res.symbols[1:]:
            assert s.parent_symbol in symbol_ids

        total_symbols += len(res.symbols)

    assert total_symbols > 50  # Flask repository contains hundreds of symbols
