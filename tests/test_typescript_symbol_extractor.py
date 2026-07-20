import pytest

from backend.extractors.typescript_symbol_extractor import TypeScriptSymbolExtractor
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, SourceFile
from backend.symbol_kind import SymbolKind


def _parse_and_extract(tmp_path, code: str, filename: str = "service.ts"):
    file_path = tmp_path / filename
    file_path.write_text(code, encoding="utf-8")

    source_file = SourceFile(
        path=file_path,
        language=Language.TYPESCRIPT,
        extension=".ts",
        relative_path=filename,
        size_bytes=file_path.stat().st_size,
    )

    parser = RepositoryParser()
    parse_result = parser.parse(source_file)

    extractor = TypeScriptSymbolExtractor()
    symbols = extractor.extract(parse_result)
    return parse_result, symbols


def test_typescript_accessibility_interfaces_enums(tmp_path):
    code = '''export interface UserConfig {
    id: string;
    name: string;
}

export enum UserRole {
    ADMIN = "ADMIN",
    USER = "USER"
}

export class AuthService {
    private apiKey: string;
    protected tenantId: string;

    constructor(key: string) {
        this.apiKey = key;
    }

    public async login(username: string): Promise<boolean> {
        return true;
    }

    protected validate(): void {
    }
}
'''
    _, symbols = _parse_and_extract(tmp_path, code)

    by_name = {s.name: s for s in symbols}

    assert "UserConfig" in by_name
    assert by_name["UserConfig"].kind == SymbolKind.CLASS
    assert by_name["UserConfig"].is_exported is True

    assert "UserRole" in by_name
    assert by_name["UserRole"].kind == SymbolKind.CLASS

    assert "AuthService" in by_name
    auth_cls = by_name["AuthService"]
    assert auth_cls.kind == SymbolKind.CLASS

    assert "constructor" in by_name
    ctor = by_name["constructor"]
    assert ctor.kind == SymbolKind.CONSTRUCTOR
    assert ctor.parent_symbol == auth_cls.id

    assert "login" in by_name
    login_m = by_name["login"]
    assert login_m.kind == SymbolKind.METHOD
    assert login_m.visibility == "public"
    assert login_m.is_async is True
    assert "Promise<boolean>" in login_m.signature

    assert "validate" in by_name
    val_m = by_name["validate"]
    assert val_m.kind == SymbolKind.METHOD
    assert val_m.visibility == "protected"
