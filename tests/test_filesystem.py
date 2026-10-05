"""Pytest coverage for filesystem tools."""

from __future__ import annotations

import pytest

import tools.fs_policy as fs_policy
from tools.filesystem import find_file, list_files, read_file, search_text

README_CANDIDATES = ("README.md", "readme.md")


@pytest.fixture(autouse=True)
def _workspace_is_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """These tests read Zoe's own files, so point WORKSPACE_ROOT at the repo explicitly."""
    monkeypatch.setenv(fs_policy.WORKSPACE_ROOT_ENV, str(fs_policy.ROOT))
    fs_policy.clear_workspace_cache()
    yield
    fs_policy.clear_workspace_cache()


def _find_readme_path() -> str:
    """Locate the project README file."""
    for candidate in README_CANDIDATES:
        result = find_file(candidate)
        if "(no files found" not in result:
            return result.splitlines()[0]
    raise RuntimeError("README file not found")


def test_list_files() -> None:
    """List files in the project root."""
    files = list_files(".")
    assert files
    assert "(no files found" not in files


def test_find_readme() -> None:
    """Find the README file by name."""
    readme_matches = find_file("README")
    assert readme_matches
    assert "(no files found" not in readme_matches


def test_read_readme() -> None:
    """Read the first lines of the README."""
    readme_path = _find_readme_path()
    readme_content = read_file(readme_path, max_lines=5)
    assert readme_content.strip()


def test_search_text() -> None:
    """Search project files for a known symbol."""
    search_results = search_text("generate_response")
    assert search_results
    assert "(no matches found" not in search_results
