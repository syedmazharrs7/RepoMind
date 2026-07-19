import pytest

from backend.repository_scanner import SourceFile, Language
from backend.parse_result import ParseResult
from backend.repository_parser import RepositoryParser


def test_typescript_parser_valid_file(tmp_path):
    file_path = tmp_path / "valid.ts"
    file_path.write_text("const x: number = 1;\nconsole.log(x);", encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.TYPESCRIPT,
        extension=".ts",
        relative_path="valid.ts",
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


def test_typescript_parser_syntax_error(tmp_path):
    file_path = tmp_path / "syntax_error.ts"
    file_path.write_text("const x: number =\n", encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.TYPESCRIPT,
        extension=".ts",
        relative_path="syntax_error.ts",
        size_bytes=file_path.stat().st_size
    )

    parser = RepositoryParser()
    result = parser.parse(source_file)

    assert result.tree is not None
    assert result.has_errors
    assert result.tree.root_node.has_error
    assert result.error_message == "AST contains syntax errors"
