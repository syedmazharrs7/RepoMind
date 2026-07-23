import pytest
import time
from pathlib import Path

from backend.builders.hierarchy_graph_builder import HierarchyGraphBuilder
from backend.dependency_edge import DependencyEdge, generate_dependency_edge_id
from backend.dependency_edge_kind import DependencyEdgeKind
from backend.dependency_graph import DependencyGraph
from backend.dependency_metadata import DependencyMetadata
from backend.extractors.python_symbol_extractor import PythonSymbolExtractor
from backend.repository_parser import RepositoryParser
from backend.repository_scanner import Language, SourceFile
from backend.symbol_result import SymbolExtractionResult

# Metrics imports
from backend.analysis.metrics.repository_metrics_analyzer import RepositoryMetricsAnalyzer
from backend.analysis.metrics.analyzer_factory import MetricAnalyzerFactory
from backend.analysis.metrics.metric_statistics import MetricStatistics
from backend.analysis.metrics.metric_models import (
    AnalysisConfiguration,
    RepositoryMetadata,
    RepositoryAnalysisContext,
    SharedAnalysisCache,
)
from backend.analysis.metrics.metrics_result import RepositoryMetricsResult
from backend.analysis.metrics.exceptions.metrics_exceptions import (
    ValidationError,
    GraphConsistencyError,
    DuplicateAnalyzerError,
)
from backend.analysis.metrics.health_score_calculator import HealthScoreCalculator


def _build_project_graphs(tmp_path, files: dict):
    """
    Builds SymbolGraph and DependencyGraph for a multi-file python repository.
    files is a dict mapping filename -> code string.
    """
    extraction_results = []
    parser = RepositoryParser()
    extractor = PythonSymbolExtractor()

    for filename, code in files.items():
        file_path = tmp_path / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(code, encoding="utf-8")

        source_file = SourceFile(
            path=file_path,
            language=Language.PYTHON,
            extension=".py",
            relative_path=filename,
            size_bytes=file_path.stat().st_size,
        )

        parse_result = parser.parse(source_file)
        symbols = extractor.extract(parse_result)
        
        res = SymbolExtractionResult(
            parse_result=parse_result,
            symbols=tuple(symbols),
            extraction_time_ms=1.0,
            has_errors=False,
        )
        extraction_results.append(res)

    builder = HierarchyGraphBuilder()
    sg = builder.build(extraction_results, repository_name="TestApp")
    return sg


def test_metric_statistics_utility():
    # 1. Empty values
    empty_stats = MetricStatistics.from_values([])
    assert empty_stats.count == 0
    assert empty_stats.mean == 0.0
    assert empty_stats.median() == 0.0
    assert empty_stats.min == 0.0
    assert empty_stats.max == 0.0
    assert empty_stats.percentiles() == {"25": 0.0, "50": 0.0, "75": 0.0, "90": 0.0, "95": 0.0, "99": 0.0}
    assert empty_stats.summary() == {"count": 0, "sum": 0.0, "mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}

    # 2. Identical values
    single_stats = MetricStatistics.from_values([5.0, 5.0, 5.0])
    assert single_stats.count == 3
    assert single_stats.mean == 5.0
    assert single_stats.median() == 5.0
    assert single_stats.min == 5.0
    assert single_stats.max == 5.0
    assert single_stats.histograms()["counts"] == (3,)

    # 3. Dynamic distribution
    vals = [10.0, 20.0, 30.0, 40.0, 50.0]
    stats = MetricStatistics.from_values(vals, bin_count=4)
    assert stats.count == 5
    assert stats.mean == 30.0
    assert stats.median() == 30.0
    assert stats.min == 10.0
    assert stats.max == 50.0
    assert stats.percentiles(25.0) == 20.0
    assert stats.percentiles(75.0) == 40.0
    assert stats.distribution() == vals
    hist = stats.histograms()
    assert len(hist["bins"]) == 5
    assert sum(hist["counts"]) == 5


def test_analyzer_factory_registration():
    factory = MetricAnalyzerFactory()
    assert "file" in factory.registered_analyzers
    assert "repository" in factory.registered_analyzers
    assert "symbol" in factory.registered_analyzers
    assert "dependency" in factory.registered_analyzers
    assert "complexity" in factory.registered_analyzers
    assert "architecture" in factory.registered_analyzers

    # Dynamic registration
    class MockAnalyzer:
        @property
        def name(self):
            return "mock"
    
    factory.register("mock", MockAnalyzer)
    assert "mock" in factory.registered_analyzers

    # Duplicate registration raises exception
    with pytest.raises(DuplicateAnalyzerError):
        factory.register("file", MockAnalyzer)

    # Missing analyzer raises exception
    with pytest.raises(KeyError):
        factory.get("nonexistent")


def test_integration_and_orchestrator(tmp_path):
    # Setup test repository files representing a clean architecture
    files = {
        "models/user.py": "class User:\n    def __init__(self):\n        self.name = 'John'\n",
        "services/user_service.py": "from models.user import User\nclass UserService:\n    def get_user(self) -> User:\n        return User()\n",
        "controllers/user_controller.py": "from services.user_service import UserService\nclass UserController:\n    def index(self):\n        return UserService().get_user()\n",
    }
    
    sg = _build_project_graphs(tmp_path, files)
    
    # Manually resolve some mock dependency edges to test the full metrics logic
    # UserService.get_user imports / uses User
    user_node = sg.find_symbol("models.user.User")
    service_node = sg.find_symbol("services.user_service.UserService")
    controller_node = sg.find_symbol("controllers.user_controller.UserController")
    
    assert user_node and service_node and controller_node
    
    e1 = DependencyEdge(
        id=generate_dependency_edge_id(service_node.id, user_node.id, DependencyEdgeKind.USES),
        source_symbol_id=service_node.id,
        target_symbol_id=user_node.id,
        kind=DependencyEdgeKind.USES,
        metadata=DependencyMetadata(start_line=2, start_column=0),
    )
    
    # UserController calls UserService
    e2 = DependencyEdge(
        id=generate_dependency_edge_id(controller_node.id, service_node.id, DependencyEdgeKind.CALLS),
        source_symbol_id=controller_node.id,
        target_symbol_id=service_node.id,
        kind=DependencyEdgeKind.CALLS,
        metadata=DependencyMetadata(start_line=3, start_column=0),
    )
    
    dg = DependencyGraph(symbol_graph=sg, edges=[e1, e2])
    
    metadata = RepositoryMetadata(
        repo_name="TestApp",
        repo_path=str(tmp_path),
        detected_languages=("Python",),
        scanned_at="2026-07-23T00:00:00",
    )
    
    config = AnalysisConfiguration(
        hotspot_strategy="default",
        layer_rules={
            "models": 0,
            "services": 1,
            "controllers": 2,
        }
    )
    
    analyzer = RepositoryMetricsAnalyzer()
    result = analyzer.analyze(symbol_graph=sg, dependency_graph=dg, metadata=metadata, config=config)
    
    # Verify result structure
    assert result.health_score() == 100.0  # Perfect score since no cycles or violations
    assert result.repository_metadata().repo_name == "TestApp"
    
    repo_metrics = result.repository_metrics()
    assert repo_metrics.total_files == 3
    assert repo_metrics.source_files == 3
    assert repo_metrics.directories == 3  # models, services, controllers
    assert repo_metrics.total_symbols == len(sg.nodes)
    assert repo_metrics.total_dependency_edges == 2
    
    symbol_metrics = result.symbol_metrics()
    assert symbol_metrics.classes == 3
    assert symbol_metrics.functions == 0
    assert symbol_metrics.methods == 3
    assert symbol_metrics.visibility_public > 0
    
    dep_metrics = result.dependency_metrics()
    assert dep_metrics.calls == 1
    assert dep_metrics.uses == 1
    assert dep_metrics.circular_dependency_count == 0
    
    comp_metrics = result.complexity_metrics()
    assert comp_metrics.connected_components > 0
    assert comp_metrics.average_graph_degree > 0.0
    
    arch_metrics = result.architecture_metrics()
    assert arch_metrics.layer_violations == 0  # controllers (2) -> services (1) -> models (0) conforms
    assert arch_metrics.dependency_direction == 1.0
    assert len(arch_metrics.hotspots) > 0
    
    # Test JSON and Dictionary serialization
    res_dict = result.to_dict()
    assert "health_score" in res_dict
    assert res_dict["repository_metrics"]["total_files"] == 3
    
    res_json = result.to_json()
    assert '"total_files": 3' in res_json


def test_validation_layer(tmp_path):
    files = {
        "app.py": "class Calculator:\n    def add(self):\n        pass\n"
    }
    sg = _build_project_graphs(tmp_path, files)
    dg = DependencyGraph(symbol_graph=sg, edges=[])
    
    metadata = RepositoryMetadata(
        repo_name="TestApp",
        repo_path=str(tmp_path),
        detected_languages=("Python",),
        scanned_at="2026-07-23T00:00:00",
    )
    
    # Test validator with wrong counts (simulating consistency failure)
    # We will construct an analyzer with a mock factory that returns invalid metrics.
    factory = MetricAnalyzerFactory()
    
    class BrokenRepoAnalyzer:
        def analyze(self, context):
            # Returns total_symbols as 999 which is inconsistent with sg
            from backend.analysis.metrics.analyzers.repository_metrics_analyzer_impl import RepositoryMetricsAnalyzerImpl
            original = RepositoryMetricsAnalyzerImpl().analyze(context)
            # Rebuild with a broken field
            import dataclasses
            return dataclasses.replace(original, total_symbols=999)
            
        @property
        def name(self):
            return "BrokenRepoAnalyzer"
        @property
        def description(self):
            return "Broken"
        @property
        def supported_inputs(self):
            return (RepositoryAnalysisContext,)
            
    factory._registry["repository"] = BrokenRepoAnalyzer
    analyzer = RepositoryMetricsAnalyzer(factory=factory)
    
    with pytest.raises(GraphConsistencyError):
        analyzer.analyze(symbol_graph=sg, dependency_graph=dg, metadata=metadata)


def test_determinism(tmp_path):
    files = {
        "a.py": "class A:\n    pass\n",
        "b.py": "class B:\n    pass\n",
        "c.py": "class C:\n    pass\n",
    }
    sg = _build_project_graphs(tmp_path, files)
    dg = DependencyGraph(symbol_graph=sg, edges=[])
    metadata = RepositoryMetadata("TestApp", str(tmp_path), ("Python",), "2026-07-23T00:00:00")
    
    analyzer = RepositoryMetricsAnalyzer()
    
    # Run twice
    r1 = analyzer.analyze(symbol_graph=sg, dependency_graph=dg, metadata=metadata)
    r2 = analyzer.analyze(symbol_graph=sg, dependency_graph=dg, metadata=metadata)
    
    assert r1.to_dict() == r2.to_dict()
    assert r1.to_json() == r2.to_json()


def test_performance_and_complexity(tmp_path):
    # Simulate a larger graph
    # 20 files, each containing 5 symbols, connected with multiple dependency edges
    files = {}
    for i in range(20):
        code = f"class Class{i}:\n"
        for j in range(4):
            code += f"    def method{j}(self):\n        pass\n"
        files[f"file{i}.py"] = code
        
    sg = _build_project_graphs(tmp_path, files)
    
    # Connect them sequentially to create edges
    edges = []
    for i in range(19):
        # Class{i} calls Class{i+1}
        src = sg.find_symbol(f"file{i}.Class{i}")
        tgt = sg.find_symbol(f"file{i+1}.Class{i+1}")
        if src and tgt:
            edges.append(
                DependencyEdge(
                    id=generate_dependency_edge_id(src.id, tgt.id, DependencyEdgeKind.CALLS),
                    source_symbol_id=src.id,
                    target_symbol_id=tgt.id,
                    kind=DependencyEdgeKind.CALLS,
                    metadata=DependencyMetadata(start_line=1, start_column=0),
                )
            )
            
    dg = DependencyGraph(symbol_graph=sg, edges=edges)
    metadata = RepositoryMetadata("PerformanceTest", str(tmp_path), ("Python",), "2026-07-23T00:00:00")
    
    analyzer = RepositoryMetricsAnalyzer()
    
    t0 = time.perf_counter()
    result = analyzer.analyze(symbol_graph=sg, dependency_graph=dg, metadata=metadata)
    t1 = time.perf_counter()
    
    duration_ms = (t1 - t0) * 1000
    # O(N+E) operations on a graph of this size should run extremely fast (usually < 50ms)
    assert duration_ms < 200.0  # Safe upper limit for lightweight simulated graph
