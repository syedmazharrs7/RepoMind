import dataclasses
import logging
import time
from typing import Optional

from backend.repository_scanner import SourceFile
from backend.parse_result import ParseResult
from backend.parser_factory import ParserFactory, get_default_factory
from backend.parser_exceptions import FileReadError

logger = logging.getLogger(__name__)


class RepositoryParser:
    """Orchestrator class responsible for obtaining parsers, reading files, and invoking parsing."""

    def __init__(self, factory: Optional[ParserFactory] = None) -> None:
        """
        Initialize RepositoryParser with a ParserFactory.

        Args:
            factory: Optional ParserFactory instance. If None, the global default factory service is used.
        """
        self._factory = factory if factory is not None else get_default_factory()
        logger.debug("Initialized RepositoryParser orchestrator")

    def parse(self, source_file: SourceFile) -> ParseResult:
        """
        Read a file's content and parse it into an AST Tree using the appropriate parser.

        Args:
            source_file: The SourceFile object to parse.

        Returns:
            ParseResult: Container representing the parsed AST tree, error info, and parse time.

        Raises:
            FileReadError: If the source file cannot be read.
            UnsupportedLanguageError: If the source file's language is not supported.
            ParseFailureError: If parsing fails catastrophically.
        """
        logger.info(f"Starting parsing orchestration for file: '{source_file.relative_path}' ({source_file.language})")
        start_time = time.perf_counter()

        # Retrieve the language parser from factory.
        # This will raise UnsupportedLanguageError if the language has no registered parser.
        parser = self._factory.get_parser(source_file.language)

        # Separate File I/O from parsing
        try:
            content_bytes = source_file.path.read_bytes()
        except Exception as e:
            logger.error(f"Failed to read file at '{source_file.path}': {e}")
            raise FileReadError(f"Failed to read file at '{source_file.path}': {e}") from e

        # Invoke parsing and record total parse execution time
        try:
            initial_duration_ms = (time.perf_counter() - start_time) * 1000.0
            result = parser.parse_bytes(content_bytes, source_file, initial_duration_ms)

            # Update the parse time to capture total orchestration time
            total_duration_ms = (time.perf_counter() - start_time) * 1000.0
            result = dataclasses.replace(result, parse_time_ms=total_duration_ms)

            logger.info(f"Completed parsing orchestration for '{source_file.relative_path}' in {result.parse_time_ms:.2f} ms")
            return result
        except Exception as e:
            logger.error(f"Parsing failed for '{source_file.relative_path}': {e}")
            raise
