import pytest

from backend.repository_scanner import Language
from backend.parser_factory import ParserFactory, get_default_factory
from backend.parsers.python_parser import PythonParser
from backend.parsers.javascript_parser import JavaScriptParser
from backend.parsers.typescript_parser import TypeScriptParser
from backend.parser_exceptions import UnsupportedLanguageError


def test_factory_registry():
    factory = ParserFactory()
    python_parser = PythonParser()

    factory.register_parser(Language.PYTHON, python_parser)
    assert factory.get_parser(Language.PYTHON) is python_parser

    with pytest.raises(UnsupportedLanguageError):
        factory.get_parser(Language.JAVASCRIPT)


def test_default_factory_service():
    factory = get_default_factory()
    assert isinstance(factory.get_parser(Language.PYTHON), PythonParser)
    assert isinstance(factory.get_parser(Language.JAVASCRIPT), JavaScriptParser)
    assert isinstance(factory.get_parser(Language.TYPESCRIPT), TypeScriptParser)

    # Validating registry correctness on unsupported language
    with pytest.raises(UnsupportedLanguageError):
        factory.get_parser(Language.RUST)
