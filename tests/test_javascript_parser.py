import pytest

from backend.repository_scanner import SourceFile, Language
from backend.parse_result import ParseResult
from backend.repository_parser import RepositoryParser


def test_javascript_parser_valid_file(tmp_path):
    file_path = tmp_path / "valid.js"
    file_path.write_text("const x = 1;\nconsole.log(x);", encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.JAVASCRIPT,
        extension=".js",
        relative_path="valid.js",
        size_bytes=file_path.stat().st_size
    )

    parser = RepositoryParser()
    result = parser.parse(source_file)

    assert isinstance(result, ParseResult)
    assert result.source_file == source_file
    assert result.tree is not None
    assert result.tree.root_node.type == "program"
    assert not result.has_errors
    assert result.error_message is None


def test_javascript_parser_syntax_error(tmp_path):
    file_path = tmp_path / "syntax_error.js"
    file_path.write_text("const x =\n", encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.JAVASCRIPT,
        extension=".js",
        relative_path="syntax_error.js",
        size_bytes=file_path.stat().st_size
    )

    parser = RepositoryParser()
    result = parser.parse(source_file)

    assert result.tree is not None
    assert result.has_errors
    assert result.tree.root_node.has_error
    assert result.error_message == "AST contains syntax errors"
