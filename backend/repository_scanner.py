import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class RepositoryScannerError(Exception):
    """Base exception for Repository Scanner module."""
    pass


class RepositoryNotFoundError(RepositoryScannerError):
    """Exception raised when the target repository path does not exist."""
    pass


class InvalidRepositoryError(RepositoryScannerError):
    """Exception raised when the repository path is not a directory."""
    pass


class Language(str, Enum):
    """Enum representing supported programming languages."""
    PYTHON = "Python"
    JAVASCRIPT = "JavaScript"
    TYPESCRIPT = "TypeScript"
    JAVA = "Java"
    C = "C"
    CPP = "C++"
    CSHARP = "C#"
    GO = "Go"
    RUST = "Rust"
    PHP = "PHP"
    RUBY = "Ruby"
    KOTLIN = "Kotlin"
    SWIFT = "Swift"


# Module-level mapping of file extensions to Language Enum
LANGUAGE_MAP = {
    ".py": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".java": Language.JAVA,
    ".c": Language.C,
    ".cpp": Language.CPP,
    ".hpp": Language.CPP,
    ".cc": Language.CPP,
    ".cs": Language.CSHARP,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".php": Language.PHP,
    ".rb": Language.RUBY,
    ".kt": Language.KOTLIN,
    ".swift": Language.SWIFT,
}

# Directories that should be skipped during traversal
IGNORED_DIRECTORIES = {
    ".git",
    ".github",
    "venv",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "coverage",
    ".mypy_cache",
}


@dataclass(frozen=True)
class SourceFile:
    """Immutable representation of a scanned source file."""
    path: Path
    language: Language
    extension: str
    relative_path: str
    size_bytes: int


class RepositoryScanner:
    """Class responsible for scanning repositories and identifying source files."""

    def _should_ignore_directory(self, path: Path) -> bool:
        """
        Determine if the directory should be ignored during traversal.

        Args:
            path: Path to the directory.

        Returns:
            True if the directory name matches any of the ignored directory names.
        """
        return path.name in IGNORED_DIRECTORIES

    def _is_supported_source_file(self, path: Path) -> bool:
        """
        Check if the file is a supported source file based on extension.

        Args:
            path: Path to the file.

        Returns:
            True if the file extension is mapped in LANGUAGE_MAP, False otherwise.
        """
        return path.suffix.lower() in LANGUAGE_MAP

    def _detect_language(self, path: Path) -> Language:
        """
        Detect the programming language based on file extension.

        Args:
            path: Path to the file.

        Returns:
            Language: The corresponding language enum.

        Raises:
            ValueError: If the file extension is not supported.
        """
        ext = path.suffix.lower()
        if ext in LANGUAGE_MAP:
            return LANGUAGE_MAP[ext]
        raise ValueError(f"Unsupported file extension: {ext}")

    def _build_source_file(self, path: Path, repository_path: Path, language: Language) -> SourceFile:
        """
        Build a SourceFile dataclass instance.

        Args:
            path: Absolute path to the file.
            repository_path: Root path of the repository being scanned.
            language: The detected Language enum.

        Returns:
            SourceFile: A built SourceFile instance with normalized relative path.
        """
        # Ensure relative paths use forward slashes for cross-platform consistency
        relative_path = str(path.relative_to(repository_path)).replace("\\", "/")
        return SourceFile(
            path=path,
            language=language,
            extension=path.suffix,
            relative_path=relative_path,
            size_bytes=path.stat().st_size,
        )

    def _walk_directory(
        self, current_dir: Path, repository_path: Path, source_files: list[SourceFile], stats: dict
    ) -> None:
        """
        Recursively walk the directories using Path.iterdir(), skipping ignored ones.

        Args:
            current_dir: The directory currently being walked.
            repository_path: The root repository directory.
            source_files: List where identified SourceFile objects will be collected.
            stats: Dictionary tracking scan statistics.
        """
        stats["directories_visited"] += 1
        try:
            for entry in current_dir.iterdir():
                if entry.is_dir():
                    if self._should_ignore_directory(entry):
                        stats["ignored_directories_count"] += 1
                        logger.debug(f"Ignoring directory during traversal: {entry}")
                        continue
                    self._walk_directory(entry, repository_path, source_files, stats)
                elif entry.is_file():
                    if self._is_supported_source_file(entry):
                        lang = self._detect_language(entry)
                        source_file = self._build_source_file(entry, repository_path, lang)
                        source_files.append(source_file)
        except (OSError, PermissionError) as e:
            logger.warning(f"Error accessing directory '{current_dir}': {e}")

    def scan(self, repository_path: Path) -> list[SourceFile]:
        """
        Scan the repository path recursively for supported source code files.

        Args:
            repository_path: Path to the repository root directory.

        Returns:
            list[SourceFile]: Sorted list of SourceFile objects by relative_path.

        Raises:
            RepositoryNotFoundError: If the repository path does not exist.
            InvalidRepositoryError: If the repository path is not a directory.
        """
        repo_path = Path(repository_path).resolve()

        logger.info(f"Starting repository scan for path: {repo_path}")

        if not repo_path.exists():
            logger.error(f"Repository path does not exist: {repo_path}")
            raise RepositoryNotFoundError(f"Repository path does not exist: '{repo_path}'")

        if not repo_path.is_dir():
            logger.error(f"Repository path is not a directory: {repo_path}")
            raise InvalidRepositoryError(f"Repository path is not a directory: '{repo_path}'")

        source_files: list[SourceFile] = []
        stats = {
            "directories_visited": 0,
            "ignored_directories_count": 0,
        }

        self._walk_directory(repo_path, repo_path, source_files, stats)

        # Sort the files by relative_path to guarantee deterministic output
        source_files.sort(key=lambda sf: sf.relative_path)

        logger.info(
            f"Scan completed. Repository: '{repo_path}' | "
            f"Directories visited: {stats['directories_visited']} | "
            f"Ignored directories: {stats['ignored_directories_count']} | "
            f"Source files found: {len(source_files)}"
        )

        return source_files
