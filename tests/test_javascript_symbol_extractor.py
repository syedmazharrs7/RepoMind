import pytest

from backend.extractors.javascript_symbol_extractor import JavaScriptSymbolExtractor
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, SourceFile
from backend.symbol_kind import SymbolKind


def _parse_and_extract(tmp_path, code: str, filename: str = "index.js"):
    file_path = tmp_path / filename
    file_path.write_text(code, encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.JAVASCRIPT,
        extension=".js",
        relative_path=filename,
        size_bytes=file_path.stat().st_size,
    )

    parser = RepositoryParser()
    parse_result = parser.parse(source_file)

    extractor = JavaScriptSymbolExtractor()
    symbols = extractor.extract(parse_result)
    return parse_result, symbols


def test_javascript_empty_file(tmp_path):
    _, symbols = _parse_and_extract(tmp_path, "")
    assert len(symbols) == 1
    assert symbols[0].kind == SymbolKind.MODULE
    assert symbols[0].name == "index"


def test_javascript_classes_constructors_jsdoc_methods(tmp_path):
    code = '''/**
 * User Service Class
 */
class UserService {
    /**
     * Create user service instance
     */
    constructor(db) {
        this.db = db;
    }

    async getUser(id) {
        return await this.db.find(id);
    }

    #privateHelper() {
        return true;
    }
}
'''
    _, symbols = _parse_and_extract(tmp_path, code)

    by_name = {s.name: s for s in symbols}

    assert "UserService" in by_name
    cls = by_name["UserService"]
    assert cls.kind == SymbolKind.CLASS
    assert cls.docstring == "User Service Class"

    assert "constructor" in by_name
    ctor = by_name["constructor"]
    assert ctor.kind == SymbolKind.CONSTRUCTOR
    assert ctor.parent_symbol == cls.id
    assert ctor.docstring == "Create user service instance"

    assert "getUser" in by_name
    get_u = by_name["getUser"]
    assert get_u.kind == SymbolKind.METHOD
    assert get_u.is_async is True
    assert get_u.parent_symbol == cls.id

    assert "#privateHelper" in by_name
    priv_m = by_name["#privateHelper"]
    assert priv_m.kind == SymbolKind.METHOD
    assert priv_m.visibility == "private"


def test_javascript_arrow_functions_constants_exports(tmp_path):
    code = '''import path from 'path';

export const DEFAULT_TIMEOUT = 5000;
let retryCount = 0;

export const fetchData = async (url) => {
    return fetch(url);
};
'''
    _, symbols = _parse_and_extract(tmp_path, code)

    by_name = {s.name: s for s in symbols}

    assert "DEFAULT_TIMEOUT" in by_name
    timeout = by_name["DEFAULT_TIMEOUT"]
    assert timeout.kind == SymbolKind.CONSTANT
    assert timeout.is_exported is True

    assert "retryCount" in by_name
    retry = by_name["retryCount"]
    assert retry.kind == SymbolKind.VARIABLE
    assert retry.is_exported is False

    assert "fetchData" in by_name
    fetch_sym = by_name["fetchData"]
    assert fetch_sym.kind == SymbolKind.FUNCTION
    assert fetch_sym.is_async is True
    assert fetch_sym.is_exported is True
