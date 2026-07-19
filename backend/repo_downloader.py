import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
import git

from backend.config import REPOS_DIR

logger = logging.getLogger(__name__)


class RepoIngestionError(Exception):
    """Base exception for Repository Ingestion module."""
    pass


class InvalidGitHubURLError(RepoIngestionError):
    """Exception raised when the provided URL is not a valid GitHub repository URL."""
    pass


class CloneFailureError(RepoIngestionError):
    """Exception raised when cloning the repository fails."""
    pass


class CorruptedRepositoryError(RepoIngestionError):
    """Exception raised when the repository directory exists but is corrupted."""
    pass


@dataclass(frozen=True)
class RepositoryInfo:
    """Dataclass representing cloned repository details."""
    url: str
    owner: str
    name: str
    local_path: Path


class RepositoryDownloader:
    """Class responsible for cloning and acquiring GitHub repositories."""

    def __init__(self, base_dir: Path = REPOS_DIR) -> None:
        """
        Initialize the downloader with a base directory for storing repositories.

        Args:
            base_dir: The base directory where repositories will be cloned.
        """
        self.base_dir = Path(base_dir)

    def _validate_and_extract_repo_info(self, url: str) -> Tuple[str, str]:
        """
        Validate the GitHub URL and extract the owner and repository name.

        Supported formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git
        - git@github.com:owner/repo

        Args:
            url: The GitHub repository URL.

        Returns:
            A tuple of (owner, repo_name).

        Raises:
            InvalidGitHubURLError: If the URL is not a valid GitHub repository URL.
        """
        url = url.strip()
        
        # Regex matches valid HTTPS and SSH formats of github.com
        # Supports letters, numbers, hyphens, periods, and underscores in owner/repo names
        pattern = r"^(?:https://github\.com/|git@github\.com:)(?P<owner>[a-zA-Z0-9_.-]+)/(?P<repo>[a-zA-Z0-9_.-]+?)(?:\.git)?/?$"
        
        match = re.match(pattern, url, re.IGNORECASE)
        if not match:
            logger.error(f"URL validation failed for: '{url}'")
            raise InvalidGitHubURLError(
                f"Invalid GitHub URL: '{url}'. Expected formats: "
                "https://github.com/owner/repo[.git] or git@github.com:owner/repo[.git]"
            )

        owner = match.group("owner")
        repo = match.group("repo")
        return owner, repo

    def clone(self, url: str) -> RepositoryInfo:
        """
        Clone a GitHub repository to the local filesystem.

        If the repository already exists and is a valid git repository, it returns
        the RepositoryInfo without cloning it again. If the path exists but is not
        a valid repository, it raises a CorruptedRepositoryError.

        Args:
            url: The GitHub repository URL.

        Returns:
            RepositoryInfo: A dataclass containing repository metadata and local path.

        Raises:
            InvalidGitHubURLError: If the URL is not a valid GitHub URL.
            CloneFailureError: If git clone fails.
            CorruptedRepositoryError: If the repository directory exists but is corrupted.
        """
        owner, repo_name = self._validate_and_extract_repo_info(url)
        target_path = self.base_dir / owner / repo_name

        logger.debug(f"Resolved target path for cloning: {target_path}")

        if target_path.exists():
            if not target_path.is_dir():
                logger.error(f"Path '{target_path}' exists but is not a directory.")
                raise CorruptedRepositoryError(
                    f"Path '{target_path}' exists but is not a directory. Repository is corrupted."
                )

            try:
                # Validate that it is a valid Git repository
                repo = git.Repo(target_path)
                if repo.bare:
                    logger.error(f"Directory at '{target_path}' is a bare repository.")
                    raise CorruptedRepositoryError(
                        f"Directory at '{target_path}' is a bare repository, which is not supported."
                    )
                
                logger.info(f"Repository already exists locally and is valid: '{target_path}'")
                return RepositoryInfo(
                    url=url,
                    owner=owner,
                    name=repo_name,
                    local_path=target_path
                )
            except (git.exc.InvalidGitRepositoryError, git.exc.NoSuchPathError) as e:
                logger.error(f"Directory at '{target_path}' exists but is not a valid git repository: {e}")
                raise CorruptedRepositoryError(
                    f"Directory at '{target_path}' exists but is not a valid Git repository."
                ) from e
            except Exception as e:
                logger.error(f"Error accessing repository at '{target_path}': {e}")
                raise CorruptedRepositoryError(
                    f"Directory at '{target_path}' exists but is corrupted: {str(e)}"
                ) from e

        # Create parent directory if it doesn't exist
        target_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Cloning repository from '{url}' to '{target_path}'...")
        try:
            git.Repo.clone_from(url, target_path)
            logger.info(f"Successfully cloned repository to '{target_path}'")
            return RepositoryInfo(
                url=url,
                owner=owner,
                name=repo_name,
                local_path=target_path
            )
        except Exception as e:
            logger.error(f"Failed to clone repository from '{url}': {e}")
            # Clean up partial directory if clone fails to avoid leaving a corrupted state
            if target_path.exists():
                try:
                    logger.info(f"Cleaning up partial clone directory at '{target_path}'")
                    shutil.rmtree(target_path)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to clean up path '{target_path}': {cleanup_err}")
            raise CloneFailureError(f"Failed to clone repository from '{url}': {str(e)}") from e
