"""Plugin manifest schema and validation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ZOE_VERSION = "2.10"
MANIFEST_FILENAME = "plugin.json"
REQUIRED_KEYS = ("id", "name", "version", "entry", "permissions")


@dataclass(frozen=True)
class PluginManifest:
    """Parsed plugin.json descriptor."""

    id: str
    name: str
    version: str
    entry: str
    permissions: tuple[str, ...]
    minimum_zoe_version: str = "2.10"
    description: str = ""
    author: str = ""

    @property
    def qualified_id(self) -> str:
        return self.id if self.id.startswith("ext.") else f"ext.{self.id}"


def _parse_version(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.strip().split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


def version_compatible(manifest_version: str, runtime_version: str = ZOE_VERSION) -> bool:
    """Return True when runtime meets manifest minimum_zoe_version."""
    return _parse_version(runtime_version) >= _parse_version(manifest_version)


def load_manifest(plugin_dir: Path) -> PluginManifest:
    """Load and parse plugin.json from a plugin directory."""
    path = plugin_dir / MANIFEST_FILENAME
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid manifest in {path}")

    missing = [key for key in REQUIRED_KEYS if key not in raw]
    if missing:
        raise ValueError(f"Manifest {path} missing keys: {missing}")

    permissions_raw = raw.get("permissions", [])
    if not isinstance(permissions_raw, list):
        raise ValueError("permissions must be a list")

    return PluginManifest(
        id=str(raw["id"]).strip(),
        name=str(raw["name"]).strip(),
        version=str(raw["version"]).strip(),
        entry=str(raw["entry"]).strip(),
        permissions=tuple(str(p).strip().lower() for p in permissions_raw),
        minimum_zoe_version=str(raw.get("minimum_zoe_version", ZOE_VERSION)).strip(),
        description=str(raw.get("description", "")).strip(),
        author=str(raw.get("author", "")).strip(),
    )


def validate_manifest(manifest: PluginManifest, plugin_dir: Path) -> list[str]:
    """Return human-readable validation errors (empty when valid)."""
    errors: list[str] = []
    if not manifest.id:
        errors.append("id is required")
    if ".." in manifest.entry or manifest.entry.startswith("/"):
        errors.append("entry must be a relative path")
    entry_path = (plugin_dir / manifest.entry).resolve()
    if not entry_path.is_file():
        errors.append(f"entry file not found: {manifest.entry}")
    try:
        plugin_dir.resolve().relative_to(plugin_dir.resolve().anchor)
    except ValueError:
        errors.append("invalid plugin directory")
    if not version_compatible(manifest.minimum_zoe_version):
        errors.append(
            f"requires Zoe {manifest.minimum_zoe_version} (runtime {ZOE_VERSION})"
        )
    return errors
