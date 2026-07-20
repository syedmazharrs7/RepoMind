import pytest

from backend.extractors.javascript_symbol_extractor import JavaScriptSymbolExtractor
from backend.extractors.python_symbol_extractor import PythonSymbolExtractor
from backend.extractors.typescript_symbol_extractor import TypeScriptSymbolExtractor
from backend.repository_scanner import Language
from backend.symbol_exceptions import UnsupportedLanguageError
from backend.symbol_extractor_factory import (
    LanguageExtractorFactory,
    get_default_extractor_factory,
)


def test_factory_get_default_extractors():
    factory = get_default_extractor_factory()

    py_extractor = factory.get_extractor(Language.PYTHON)
    assert isinstance(py_extractor, PythonSymbolExtractor)

    js_extractor = factory.get_extractor(Language.JAVASCRIPT)
    assert isinstance(js_extractor, JavaScriptSymbolExtractor)

    ts_extractor = factory.get_extractor(Language.TYPESCRIPT)
    assert isinstance(ts_extractor, TypeScriptSymbolExtractor)


def test_factory_unsupported_language():
    factory = LanguageExtractorFactory()
    with pytest.raises(UnsupportedLanguageError):
        factory.get_extractor(Language.JAVA)


def test_factory_custom_registration():
    factory = LanguageExtractorFactory()
    custom_extractor = PythonSymbolExtractor()
    factory.register_extractor(Language.PYTHON, custom_extractor)

    assert factory.get_extractor(Language.PYTHON) is custom_extractor
