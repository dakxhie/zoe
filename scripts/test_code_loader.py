"""Smoke test for code file loading."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codebase.loader import CodeLoaderError, load_code


def main() -> None:
    """Load code files from the Zoe project and print a summary."""
    project_path = ROOT

    try:
        files = load_code(project_path)
    except CodeLoaderError as exc:
        print(f"Code loader test failed: {exc}")
        raise SystemExit(1) from exc

    print(f"Loaded files: {len(files)}\n")

    for code_file in files[:10]:
        print(f"Path: {code_file['path']}")
        print(f"Language: {code_file['language']}")
        print(f"Characters: {len(code_file['content'])}")
        print(f"Preview:\n{code_file['content'][:200]}\n")


if __name__ == "__main__":
    main()
