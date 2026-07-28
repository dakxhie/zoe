"""Smoke test for filesystem tools."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.filesystem import find_file, list_files, read_file, search_text

README_CANDIDATES = ("README.md", "readme.md")


def _find_readme_path() -> str:
    """Locate the project README file."""
    for candidate in README_CANDIDATES:
        result = find_file(candidate)
        if "(no files found" not in result:
            return result.splitlines()[0]
    raise RuntimeError("README file not found")


def main() -> None:
    """Run filesystem tool checks."""
    files = list_files(".")
    print("List files:")
    print(files.splitlines()[0] if files else "(empty)")

    readme_matches = find_file("README")
    print("\nFind README:")
    print(readme_matches.splitlines()[0] if readme_matches else "(empty)")

    readme_path = _find_readme_path()
    readme_content = read_file(readme_path, max_lines=5)
    print("\nRead README:")
    print(readme_content.splitlines()[0] if readme_content else "(empty)")

    search_results = search_text("generate_response")
    print("\nSearch generate_response:")
    print(search_results.splitlines()[0] if search_results else "(empty)")

    if "(no files found" in files:
        raise SystemExit(1)
    if "(no files found" in readme_matches:
        raise SystemExit(1)
    if not readme_content.strip():
        raise SystemExit(1)
    if "(no matches found" in search_results:
        raise SystemExit(1)

    print("\nFilesystem tests passed.")


if __name__ == "__main__":
    main()
