import pytest

from backend.repository_scanner import SourceFile, Language
from backend.parser_exceptions import FileReadError
from backend.parse_result import ParseResult
from backend.repository_parser import RepositoryParser


def test_python_parser_valid_file(tmp_path):
    file_path = tmp_path / "valid.py"
    file_path.write_text("def hello():\n    print('world')", encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.PYTHON,
        extension=".py",
        relative_path="valid.py",
        size_bytes=file_path.stat().st_size
    )

    parser = RepositoryParser()
    result = parser.parse(source_file)

    assert isinstance(result, ParseResult)
    assert result.source_file == source_file
    assert result.tree is not None
    assert result.tree.root_node.type == "module"
    assert not result.has_errors
    assert result.error_message is None
    assert result.parse_time_ms >= 0


def test_python_parser_empty_file(tmp_path):
    file_path = tmp_path / "empty.py"
    file_path.touch()

    source_file = SourceFile(
        path=file_path,
        language=Language.PYTHON,
        extension=".py",
        relative_path="empty.py",
        size_bytes=0
    )

    parser = RepositoryParser()
    result = parser.parse(source_file)

    assert result.tree is not None
    assert result.tree.root_node.type == "module"
    assert not result.has_errors
    assert len(result.tree.root_node.children) == 0


def test_python_parser_syntax_error(tmp_path):
    file_path = tmp_path / "syntax_error.py"
    file_path.write_text("def hello(\n", encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.PYTHON,
        extension=".py",
        relative_path="syntax_error.py",
        size_bytes=file_path.stat().st_size
    )

    parser = RepositoryParser()
    result = parser.parse(source_file)

    # Verify root_node.has_error is True on syntax error recovery
    assert result.tree is not None
    assert result.has_errors
    assert result.tree.root_node.has_error
    assert result.error_message == "AST contains syntax errors"


def test_python_parser_unreadable_file(tmp_path):
    file_path = tmp_path / "unreadable.py"

    # Testing file read error by querying a non-existent path
    source_file = SourceFile(
        path=file_path,
        language=Language.PYTHON,
        extension=".py",
        relative_path="unreadable.py",
        size_bytes=0
    )

    parser = RepositoryParser()
    with pytest.raises(FileReadError):
        parser.parse(source_file)
