import pytest
from pathlib import Path

from backend.repository_scanner import (
    RepositoryScanner,
    RepositoryNotFoundError,
    InvalidRepositoryError,
    Language,
)


def test_scan_empty_repository(tmp_path):
    scanner = RepositoryScanner()
    files = scanner.scan(tmp_path)
    assert files == []


def test_scan_invalid_path(tmp_path):
    scanner = RepositoryScanner()

    # Non-existent path
    non_existent = tmp_path / "does_not_exist"
    with pytest.raises(RepositoryNotFoundError):
        scanner.scan(non_existent)

    # Path is a file, not a directory
    file_path = tmp_path / "file.txt"
    file_path.touch()
    with pytest.raises(InvalidRepositoryError):
        scanner.scan(file_path)


@pytest.mark.parametrize(
    "filename,expected_language",
    [
        ("main.py", Language.PYTHON),
        ("index.js", Language.JAVASCRIPT),
        ("app.ts", Language.TYPESCRIPT),
        ("Service.java", Language.JAVA),
        ("main.c", Language.C),
        ("main.cpp", Language.CPP),
        ("lib.hpp", Language.CPP),
        ("helper.cc", Language.CPP),
        ("Program.cs", Language.CSHARP),
        ("main.go", Language.GO),
        ("main.rs", Language.RUST),
        ("index.php", Language.PHP),
        ("app.rb", Language.RUBY),
        ("main.kt", Language.KOTLIN),
        ("main.swift", Language.SWIFT),
    ],
)
def test_language_detection(tmp_path, filename, expected_language):
    file_path = tmp_path / filename
    file_path.touch()

    scanner = RepositoryScanner()
    files = scanner.scan(tmp_path)

    assert len(files) == 1
    assert files[0].relative_path == filename
    assert files[0].language == expected_language
    assert files[0].extension == file_path.suffix
    assert files[0].path.is_absolute()


@pytest.mark.parametrize(
    "unsupported_filename",
    [
        "image.png",
        "video.mp4",
        "document.pdf",
        "archive.zip",
        "run.exe",
        "library.dll",
        "lib.so",
        "lib.dylib",
        "App.class",
        "app.jar",
        "main.pyc",
        "output.log",
        "readme.md",
    ],
)
def test_unsupported_files_ignored(tmp_path, unsupported_filename):
    # Create a supported file to verify we only collect supported ones
    (tmp_path / "main.py").touch()
    (tmp_path / unsupported_filename).touch()

    scanner = RepositoryScanner()
    files = scanner.scan(tmp_path)

    # Assert the unsupported file is explicitly absent
    relative_paths = [f.relative_path for f in files]
    assert unsupported_filename not in relative_paths
    assert len(files) == 1


def test_scan_nested_directories_and_relative_paths(tmp_path):
    # Setup nested directories
    src = tmp_path / "src"
    src.mkdir()
    (src / "utils.py").touch()

    components = src / "components"
    components.mkdir()
    (components / "Button.ts").touch()

    (tmp_path / "main.py").touch()

    scanner = RepositoryScanner()
    files = scanner.scan(tmp_path)

    assert len(files) == 3

    # Verify relative paths sorted alphabetically/deterministically
    assert files[0].relative_path == "main.py"
    assert files[1].relative_path == "src/components/Button.ts"
    assert files[2].relative_path == "src/utils.py"

    # Path must be absolute
    assert files[0].path == (tmp_path / "main.py").resolve()
    assert files[1].path == (components / "Button.ts").resolve()
    assert files[2].path == (src / "utils.py").resolve()

    for f in files:
        assert f.path.is_absolute()


def test_scan_ignored_folders(tmp_path):
    (tmp_path / "main.py").touch()

    # Setup ignored folders and valid py files inside them to verify exclusion
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config.py").touch()

    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    (node_modules / "lib.js").touch()

    venv = tmp_path / "venv"
    venv.mkdir()
    (venv / "site-packages.py").touch()

    # Traversal should never descend into them
    scanner = RepositoryScanner()
    files = scanner.scan(tmp_path)

    # Should only find main.py
    assert len(files) == 1
    assert files[0].relative_path == "main.py"
    assert files[0].path.is_absolute()


def test_recursive_ignored_directories(tmp_path):
    # Create a valid source file at the root
    (tmp_path / "main.py").touch()

    # Create deeply nested directories inside an ignored directory
    ignored_deep_dir = tmp_path / "node_modules" / "sub_module" / "src" / "utils"
    ignored_deep_dir.mkdir(parents=True, exist_ok=True)
    # Add python/js files inside the ignored structure
    (ignored_deep_dir / "ignored.py").touch()
    (ignored_deep_dir / "helper.js").touch()

    # Create another ignored nested directory
    venv_deep_dir = tmp_path / "venv" / "lib" / "python3.10" / "site-packages" / "package"
    venv_deep_dir.mkdir(parents=True, exist_ok=True)
    (venv_deep_dir / "package_file.py").touch()

    scanner = RepositoryScanner()
    files = scanner.scan(tmp_path)

    # Only main.py at the root should be found
    assert len(files) == 1
    assert files[0].relative_path == "main.py"
    assert files[0].path.is_absolute()


def test_scan_file_size_captured(tmp_path):
    file_content = "def hello():\n    return 'world'"
    py_file = tmp_path / "helper.py"
    py_file.write_text(file_content, encoding="utf-8")

    scanner = RepositoryScanner()
    files = scanner.scan(tmp_path)

    assert len(files) == 1
    assert files[0].size_bytes == py_file.stat().st_size
    assert files[0].extension == ".py"
    assert files[0].path.is_absolute()


def test_deterministic_ordering(tmp_path):
    # Create files in random order
    (tmp_path / "z.py").touch()
    (tmp_path / "a.py").touch()
    (tmp_path / "m.py").touch()
    (tmp_path / "b.py").touch()

    scanner = RepositoryScanner()
    scan_1 = scanner.scan(tmp_path)
    scan_2 = scanner.scan(tmp_path)

    # Ensure both lists of SourceFile are completely identical
    assert scan_1 == scan_2
    # Ensure they are sorted alphabetically by relative_path
    assert [f.relative_path for f in scan_1] == ["a.py", "b.py", "m.py", "z.py"]
    for f in scan_1:
        assert f.path.is_absolute()
