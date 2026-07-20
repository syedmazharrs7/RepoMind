import pytest

from backend.extractors.python_symbol_extractor import PythonSymbolExtractor
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, SourceFile
from backend.symbol_kind import SymbolKind


def _parse_and_extract(tmp_path, code: str, filename: str = "app.py"):
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
    return parse_result, symbols


def test_python_empty_file(tmp_path):
    _, symbols = _parse_and_extract(tmp_path, "")
    assert len(symbols) == 1
    mod = symbols[0]
    assert mod.kind == SymbolKind.MODULE
    assert mod.name == "app"
    assert mod.qualified_name == "app"
    assert mod.parent_symbol is None


def test_python_classes_methods_constructors_nested(tmp_path):
    code = '''"""Module docstring."""

class OuterClass:
    """Outer class docstring."""

    def __init__(self, value: int):
        self.value = value

    @property
    def value_prop(self) -> int:
        return self.value

    @staticmethod
    def static_func():
        pass

    class InnerClass:
        def inner_method(self):
            pass
'''
    _, symbols = _parse_and_extract(tmp_path, code)

    by_name = {s.name: s for s in symbols}

    assert "app" in by_name
    assert by_name["app"].docstring == "Module docstring."

    assert "OuterClass" in by_name
    outer = by_name["OuterClass"]
    assert outer.kind == SymbolKind.CLASS
    assert outer.qualified_name == "app.OuterClass"
    assert outer.docstring == "Outer class docstring."
    assert outer.parent_symbol == by_name["app"].id
    assert outer.line_count > 0

    assert "__init__" in by_name
    init_sym = by_name["__init__"]
    assert init_sym.kind == SymbolKind.CONSTRUCTOR
    assert init_sym.qualified_name == "app.OuterClass.__init__"
    assert init_sym.parent_symbol == outer.id

    assert "value_prop" in by_name
    prop_sym = by_name["value_prop"]
    assert prop_sym.kind == SymbolKind.PROPERTY
    assert "@property" in prop_sym.decorators

    assert "static_func" in by_name
    static_sym = by_name["static_func"]
    assert static_sym.kind == SymbolKind.METHOD
    assert "@staticmethod" in static_sym.decorators

    assert "InnerClass" in by_name
    inner = by_name["InnerClass"]
    assert inner.kind == SymbolKind.CLASS
    assert inner.qualified_name == "app.OuterClass.InnerClass"
    assert inner.parent_symbol == outer.id

    assert "inner_method" in by_name
    inner_m = by_name["inner_method"]
    assert inner_m.kind == SymbolKind.METHOD
    assert inner_m.qualified_name == "app.OuterClass.InnerClass.inner_method"
    assert inner_m.parent_symbol == inner.id


def test_python_functions_async_nested_visibility(tmp_path):
    code = '''async def public_async_func(a: int) -> str:
    """Async docstring."""
    def _nested_protected_func():
        def __nested_private_func():
            pass
        __nested_private_func()
    return "done"
'''
    _, symbols = _parse_and_extract(tmp_path, code)

    by_name = {s.name: s for s in symbols}

    assert "public_async_func" in by_name
    async_f = by_name["public_async_func"]
    assert async_f.kind == SymbolKind.FUNCTION
    assert async_f.is_async is True
    assert async_f.visibility == "public"
    assert async_f.docstring == "Async docstring."

    assert "_nested_protected_func" in by_name
    prot_f = by_name["_nested_protected_func"]
    assert prot_f.visibility == "_protected"
    assert prot_f.parent_symbol == async_f.id

    assert "__nested_private_func" in by_name
    priv_f = by_name["__nested_private_func"]
    assert priv_f.visibility == "__private"
    assert priv_f.parent_symbol == prot_f.id


def test_python_imports_constants_variables(tmp_path):
    code = '''import os
from typing import Final

MAX_RETRY_COUNT = 5
timeout_seconds = 30
API_KEY: Final[str] = "secret"
'''
    _, symbols = _parse_and_extract(tmp_path, code)

    kinds = [s.kind for s in symbols]
    assert SymbolKind.IMPORT in kinds
    assert SymbolKind.CONSTANT in kinds
    assert SymbolKind.VARIABLE in kinds

    by_name = {s.name: s for s in symbols if s.name in ("MAX_RETRY_COUNT", "timeout_seconds", "API_KEY")}
    assert by_name["MAX_RETRY_COUNT"].kind == SymbolKind.CONSTANT
    assert by_name["timeout_seconds"].kind == SymbolKind.VARIABLE
    assert by_name["API_KEY"].kind == SymbolKind.CONSTANT
