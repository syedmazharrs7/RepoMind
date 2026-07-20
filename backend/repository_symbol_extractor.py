import logging
import time
from typing import List, Optional

from backend.parse_result import ParseResult
from backend.symbol_exceptions import (
    ExtractionFailureError,
    InvalidASTError,
    UnsupportedLanguageError,
)
from backend.symbol_extractor_factory import (
    LanguageExtractorFactory,
    get_default_extractor_factory,
)
from backend.symbol_result import SymbolExtractionResult

logger = logging.getLogger(__name__)


class RepositorySymbolExtractor:
    """
    Orchestrator class responsible for obtaining language extractors, processing ParseResult objects,
    and returning SymbolExtractionResult instances.
    """

    def __init__(self, factory: Optional[LanguageExtractorFactory] = None) -> None:
        """
        Initialize RepositorySymbolExtractor.

        Args:
            factory: Optional LanguageExtractorFactory instance. If None, default factory service is used.
        """
        self._factory = factory if factory is not None else get_default_extractor_factory()
        logger.debug("Initialized RepositorySymbolExtractor orchestrator")

    def extract_symbols(self, parse_result: ParseResult) -> SymbolExtractionResult:
        """
        Extract semantic symbols from a single ParseResult.

        Args:
            parse_result: The ParseResult instance from Module 3.

        Returns:
            SymbolExtractionResult: Container with extracted symbols, timing, and error information.
        """
        file_path = parse_result.source_file.relative_path
        lang = parse_result.source_file.language

        logger.info(f"Extraction started for '{file_path}' ({lang})")
        start_time = time.perf_counter()

        # Check for parse result errors from Module 3
        if parse_result.has_errors and parse_result.tree is None:
            msg = f"Cannot extract symbols: ParseResult has syntax/AST errors: {parse_result.error_message}"
            logger.warning(msg)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return SymbolExtractionResult(
                parse_result=parse_result,
                symbols=(),
                extraction_time_ms=duration_ms,
                has_errors=True,
                error_message=msg,
            )

        try:
            extractor = self._factory.get_extractor(lang)
            logger.debug(f"Selected extractor {extractor.__class__.__name__} for {lang}")

            symbols = extractor.extract(parse_result)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            logger.info(
                f"Symbols extracted for '{file_path}': {len(symbols)} symbols in {duration_ms:.2f} ms"
            )

            return SymbolExtractionResult(
                parse_result=parse_result,
                symbols=tuple(symbols),
                extraction_time_ms=duration_ms,
                has_errors=False,
                error_message=None,
            )
        except (UnsupportedLanguageError, InvalidASTError) as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Extraction failed for '{file_path}': {e}")
            return SymbolExtractionResult(
                parse_result=parse_result,
                symbols=(),
                extraction_time_ms=duration_ms,
                has_errors=True,
                error_message=str(e),
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"Unexpected error during symbol extraction for '{file_path}': {e}")
            raise ExtractionFailureError(
                f"Failed to extract symbols for '{file_path}': {e}"
            ) from e

    def extract_repository(
        self, parse_results: List[ParseResult]
    ) -> List[SymbolExtractionResult]:
        """
        Extract semantic symbols for an entire list of ParseResult objects in a repository.

        Args:
            parse_results: List of ParseResult objects.

        Returns:
            List[SymbolExtractionResult]: Results for each ParseResult.
        """
        logger.info(f"Starting repository-wide symbol extraction for {len(parse_results)} files")
        start_time = time.perf_counter()

        results: List[SymbolExtractionResult] = []
        for pr in parse_results:
            res = self.extract_symbols(pr)
            results.append(res)

        total_time_ms = (time.perf_counter() - start_time) * 1000.0
        total_symbols = sum(len(r.symbols) for r in results)
        logger.info(
            f"Repository symbol extraction completed: {len(results)} files, {total_symbols} symbols extracted in {total_time_ms:.2f} ms"
        )

        return results
