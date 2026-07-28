"""Dependency inspection helpers for Zoe AI."""

from __future__ import annotations

import importlib
import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from core.config import ROOT

REQUIREMENTS_FILE = ROOT / "requirements.txt"

PACKAGE_IMPORTS: dict[str, str] = {
    "torch": "torch",
    "transformers": "transformers",
    "sentence-transformers": "sentence_transformers",
    "chromadb": "chromadb",
    "typer": "typer",
    "Pillow": "PIL",
    "easyocr": "easyocr",
    "requests": "requests",
    "beautifulsoup4": "bs4",
    "duckduckgo-search": "duckduckgo_search",
    "pypdf": "pypdf",
    "pytest": "pytest",
}


def parse_requirements() -> list[str]:
    """Return package names declared in requirements.txt."""
    if not REQUIREMENTS_FILE.exists():
        return []

    packages: list[str] = []
    for line in REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        package = re.split(r"[<>=!~]", line, maxsplit=1)[0].strip()
        if package:
            packages.append(package)
    return packages


def check_package(package_name: str) -> tuple[bool, str]:
    """Verify one package is installed and importable."""
    import_name = PACKAGE_IMPORTS.get(package_name, package_name.replace("-", "_"))

    try:
        installed_version = version(package_name)
    except PackageNotFoundError:
        return False, f"{package_name} not installed"

    try:
        importlib.import_module(import_name)
    except Exception as exc:
        return False, f"{package_name} {installed_version} installed but import failed ({exc})"

    return True, f"{package_name} {installed_version}"


def check_required_packages() -> tuple[bool, list[str]]:
    """Check runtime packages from requirements.txt."""
    details: list[str] = []
    failed = False

    for package_name in parse_requirements():
        if package_name == "pytest":
            continue

        ok, message = check_package(package_name)
        status = "PASS" if ok else "FAIL"
        details.append(f"{package_name} ............... {status} ({message})")
        if not ok:
            failed = True

    return not failed, details
