import pytest
from dataclasses import FrozenInstanceError
from pathlib import Path

from backend.repository_scanner import RepositoryScanner, SourceFile, Language
from backend.repository_parser import RepositoryParser
from backend.parse_result import ParseResult
from backend.parser_exceptions import UnsupportedLanguageError


def test_repository_parser_delegation(tmp_path):
    file_path = tmp_path / "main.py"
    file_path.write_text("print('hello')", encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.PYTHON,
        extension=".py",
        relative_path="main.py",
        size_bytes=file_path.stat().st_size
    )

    parser = RepositoryParser()
    result = parser.parse(source_file)

    assert isinstance(result, ParseResult)
    assert result.source_file == source_file
    assert result.tree is not None
    assert result.tree.root_node.type == "module"


def test_parse_result_immutability(tmp_path):
    file_path = tmp_path / "main.py"
    file_path.touch()

    source_file = SourceFile(
        path=file_path,
        language=Language.PYTHON,
        extension=".py",
        relative_path="main.py",
        size_bytes=0
    )

    parser = RepositoryParser()
    result = parser.parse(source_file)

    with pytest.raises(FrozenInstanceError):
        result.has_errors = True  # type: ignore


def test_unsupported_language_error(tmp_path):
    file_path = tmp_path / "main.rs"
    file_path.touch()

    # Create SourceFile with Rust (which scanner scans but no parser is registered for)
    source_file = SourceFile(
        path=file_path,
        language=Language.RUST,
        extension=".rs",
        relative_path="main.rs",
        size_bytes=0
    )

    parser = RepositoryParser()
    with pytest.raises(UnsupportedLanguageError):
        parser.parse(source_file)


def test_integration_with_flask_repo():
    repo_path = Path("repos/pallets/flask")
    if not repo_path.exists():
        pytest.skip("Local pallets/flask repository not found for integration testing")

    scanner = RepositoryScanner()
    scanned_files = scanner.scan(repo_path)

    # Filter to only Python files
    python_files = [f for f in scanned_files if f.language == Language.PYTHON]
    assert len(python_files) > 0, "No Python files found in Flask repository"

    parser = RepositoryParser()

    # Parse every file
    results = []
    for sf in python_files:
        res = parser.parse(sf)
        results.append(res)

        # Verify AST root node type is 'module' for Python
        assert res.tree is not None
        assert res.tree.root_node.type == "module"
        assert res.parse_time_ms >= 0

    # Test deterministic behavior
    results_2 = []
    for sf in python_files:
        res = parser.parse(sf)
        results_2.append(res)

    assert len(results) == len(results_2)
    for r1, r2 in zip(results, results_2):
        assert r1.source_file == r2.source_file
        assert r1.has_errors == r2.has_errors
        assert r1.tree.root_node.type == r2.tree.root_node.type
