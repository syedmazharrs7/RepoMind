import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import git
from backend.repo_downloader import (
    RepositoryDownloader,
    RepositoryInfo,
    InvalidGitHubURLError,
    CloneFailureError,
    CorruptedRepositoryError,
)


@pytest.mark.parametrize(
    "url,expected_owner,expected_repo",
    [
        ("https://github.com/octocat/Spoon-Knife", "octocat", "Spoon-Knife"),
        ("https://github.com/octocat/Spoon-Knife.git", "octocat", "Spoon-Knife"),
        ("https://github.com/octocat/Spoon-Knife/", "octocat", "Spoon-Knife"),
        ("git@github.com:octocat/Spoon-Knife", "octocat", "Spoon-Knife"),
        ("git@github.com:octocat/Spoon-Knife.git", "octocat", "Spoon-Knife"),
        ("git@github.com:octocat/Spoon-Knife/", "octocat", "Spoon-Knife"),
    ],
)
def test_extract_repo_info_success(url, expected_owner, expected_repo):
    downloader = RepositoryDownloader()
    owner, repo = downloader._validate_and_extract_repo_info(url)
    assert owner == expected_owner
    assert repo == expected_repo


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/octocat",
        "https://github.com/octocat/",
        "https://google.com/octocat/Spoon-Knife",
        "git@gitlab.com:octocat/Spoon-Knife.git",
        "not-a-url",
        "",
    ],
)
def test_extract_repo_info_invalid_url(url):
    downloader = RepositoryDownloader()
    with pytest.raises(InvalidGitHubURLError):
        downloader._validate_and_extract_repo_info(url)


@patch("git.Repo.clone_from")
def test_clone_success(mock_clone, tmp_path):
    downloader = RepositoryDownloader(base_dir=tmp_path)
    url = "https://github.com/octocat/Spoon-Knife"

    repo_info = downloader.clone(url)

    # Check return type and values
    assert isinstance(repo_info, RepositoryInfo)
    assert repo_info.url == url
    assert repo_info.owner == "octocat"
    assert repo_info.name == "Spoon-Knife"
    assert repo_info.local_path == tmp_path / "octocat" / "Spoon-Knife"

    # Check that clone_from was called correctly
    mock_clone.assert_called_once_with(url, tmp_path / "octocat" / "Spoon-Knife")


@patch("git.Repo")
@patch("git.Repo.clone_from")
def test_clone_already_exists_success(mock_clone, mock_repo_class, tmp_path):
    downloader = RepositoryDownloader(base_dir=tmp_path)
    url = "https://github.com/octocat/Spoon-Knife"

    # Create the directory so it exists
    repo_dir = tmp_path / "octocat" / "Spoon-Knife"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Mock git.Repo return value
    mock_repo = MagicMock()
    mock_repo.bare = False
    mock_repo_class.return_value = mock_repo

    repo_info = downloader.clone(url)

    # Verify return values
    assert repo_info.local_path == repo_dir

    # Verify clone_from was NOT called
    mock_clone.assert_not_called()
    mock_repo_class.assert_called_once_with(repo_dir)


def test_clone_exists_not_a_directory(tmp_path):
    downloader = RepositoryDownloader(base_dir=tmp_path)
    url = "https://github.com/octocat/Spoon-Knife"

    # Create a file at the destination path
    repo_dir = tmp_path / "octocat" / "Spoon-Knife"
    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    repo_dir.touch()

    with pytest.raises(CorruptedRepositoryError) as excinfo:
        downloader.clone(url)
    assert "exists but is not a directory" in str(excinfo.value)


@patch("git.Repo")
def test_clone_exists_invalid_git_repo(mock_repo_class, tmp_path):
    downloader = RepositoryDownloader(base_dir=tmp_path)
    url = "https://github.com/octocat/Spoon-Knife"

    repo_dir = tmp_path / "octocat" / "Spoon-Knife"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Mock git.Repo raising InvalidGitRepositoryError
    mock_repo_class.side_effect = git.exc.InvalidGitRepositoryError("Invalid repo")

    with pytest.raises(CorruptedRepositoryError) as excinfo:
        downloader.clone(url)
    assert "exists but is not a valid Git repository" in str(excinfo.value)


@patch("git.Repo")
def test_clone_exists_bare_repo(mock_repo_class, tmp_path):
    downloader = RepositoryDownloader(base_dir=tmp_path)
    url = "https://github.com/octocat/Spoon-Knife"

    repo_dir = tmp_path / "octocat" / "Spoon-Knife"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Mock bare repository
    mock_repo = MagicMock()
    mock_repo.bare = True
    mock_repo_class.return_value = mock_repo

    with pytest.raises(CorruptedRepositoryError) as excinfo:
        downloader.clone(url)
    assert "bare repository, which is not supported" in str(excinfo.value)


@patch("git.Repo.clone_from")
def test_clone_failure_cleans_up_directory(mock_clone, tmp_path):
    downloader = RepositoryDownloader(base_dir=tmp_path)
    url = "https://github.com/octocat/Spoon-Knife"

    repo_dir = tmp_path / "octocat" / "Spoon-Knife"

    # Simulate directory being created partially during clone, then clone failing
    def side_effect_clone(url, path):
        Path(path).mkdir(parents=True, exist_ok=True)
        raise git.exc.GitCommandError("clone", "some error")

    mock_clone.side_effect = side_effect_clone

    with pytest.raises(CloneFailureError) as excinfo:
        downloader.clone(url)

    # Verify directory was cleaned up
    assert not repo_dir.exists()
    assert "Failed to clone repository" in str(excinfo.value)
