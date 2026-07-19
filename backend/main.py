import argparse
import logging
import sys
from pathlib import Path

from backend.config import REPOS_DIR
from backend.repo_downloader import RepositoryDownloader, RepoIngestionError

# Set up main module logger
logger = logging.getLogger("backend.main")


def main() -> None:
    """CLI entry point for Repository Downloader."""
    parser = argparse.ArgumentParser(description="RepoMind Mini - Repository Ingestion Tool")
    parser.add_argument("url", help="GitHub repository URL to clone (HTTPS or SSH)")
    parser.add_argument(
        "--output-dir",
        help=f"Optional base directory to clone the repository into (defaults to '{REPOS_DIR}')"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging"
    )

    args = parser.parse_args()

    # Dynamically adjust the root logger level if verbose logging is requested
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.getLogger().setLevel(log_level)

    try:
        base_dir = Path(args.output_dir) if args.output_dir else REPOS_DIR
        downloader = RepositoryDownloader(base_dir=base_dir)

        logger.info(f"Attempting to ingest: {args.url}")
        repo_info = downloader.clone(args.url)

        logger.info("Ingestion successful!")
        logger.info(f"Repository Details:")
        logger.info(f"  Owner:      {repo_info.owner}")
        logger.info(f"  Name:       {repo_info.name}")
        logger.info(f"  URL:        {repo_info.url}")
        logger.info(f"  Local Path: {repo_info.local_path.resolve()}")
    except RepoIngestionError as e:
        logger.error(f"Ingestion failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred during ingestion: {e}", exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
