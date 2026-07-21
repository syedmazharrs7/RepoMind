import pytest

from backend.analyzers.javascript_dependency_analyzer import JavaScriptDependencyAnalyzer
from backend.analyzers.python_dependency_analyzer import PythonDependencyAnalyzer
from backend.analyzers.typescript_dependency_analyzer import TypeScriptDependencyAnalyzer
from backend.dependency_analyzer_factory import (
    DependencyAnalyzerFactory,
    get_default_dependency_analyzer_factory,
)
from backend.dependency_graph_exceptions import UnsupportedLanguageError
from backend.repository_scanner import Language


def test_factory_get_default_analyzers():
    factory = get_default_dependency_analyzer_factory()

    py_analyzer = factory.get_analyzer(Language.PYTHON)
    assert isinstance(py_analyzer, PythonDependencyAnalyzer)

    js_analyzer = factory.get_analyzer(Language.JAVASCRIPT)
    assert isinstance(js_analyzer, JavaScriptDependencyAnalyzer)

    ts_analyzer = factory.get_analyzer(Language.TYPESCRIPT)
    assert isinstance(ts_analyzer, TypeScriptDependencyAnalyzer)


def test_factory_unsupported_language():
    factory = DependencyAnalyzerFactory()
    with pytest.raises(UnsupportedLanguageError):
        factory.get_analyzer(Language.JAVA)


def test_factory_custom_registration():
    factory = DependencyAnalyzerFactory()
    custom_analyzer = PythonDependencyAnalyzer()
    factory.register_analyzer(Language.PYTHON, custom_analyzer)

    retrieved = factory.get_analyzer(Language.PYTHON)
    assert retrieved is custom_analyzer
