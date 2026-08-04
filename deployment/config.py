"""Unified configuration loader for Zoe AI."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.config import ROOT, SETTINGS_FILE
from deployment.environment import (
    DeploymentProfile,
    RuntimeMode,
    apply_profile_defaults,
    detect_deployment_profile,
    detect_runtime_mode,
    profile_yaml_filename,
)

logger = logging.getLogger(__name__)

_CONFIG: "ZoeConfig | None" = None

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-untyped]

        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except ImportError:
        return _parse_minimal_yaml(text)
    except Exception as exc:
        logger.warning("Failed to parse YAML %s: %s", path, exc)
        return {}


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    """Parse simple nested key: value YAML without external deps."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [( -1, root)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if value == "":
            node: dict[str, Any] = {}
            parent[key] = node
            stack.append((indent, node))
        else:
            if value.lower() in {"true", "false"}:
                parent[key] = value.lower() == "true"
            elif value.isdigit():
                parent[key] = int(value)
            else:
                parent[key] = value.strip('"').strip("'")
    return root


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_legacy_settings_txt() -> dict[str, str]:
    settings: dict[str, str] = {}
    if not SETTINGS_FILE.is_file():
        return settings
    with SETTINGS_FILE.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip()
    return settings


def _env_overrides() -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    profile = os.environ.get("ZOE_PROFILE")
    if profile:
        mapping.setdefault("zoe", {})["profile"] = profile
    if os.environ.get("ZOE_PORTABLE"):
        mapping.setdefault("zoe", {})["mode"] = "portable"
    log_level = os.environ.get("ZOE_LOG_LEVEL") or os.environ.get("LOG_LEVEL")
    if log_level:
        mapping.setdefault("logging", {})["level"] = log_level.upper()
    model = os.environ.get("ZOE_MODEL_NAME") or os.environ.get("MODEL_NAME")
    if model:
        mapping.setdefault("model", {})["name"] = model
    memory_db = os.environ.get("ZOE_MEMORY_DB") or os.environ.get("MEMORY_DB")
    if memory_db:
        mapping.setdefault("paths", {})["memory_db"] = memory_db
    notes = os.environ.get("NOTES_FOLDER")
    if notes:
        mapping.setdefault("paths", {})["notes_folder"] = notes
    pdf = os.environ.get("PDF_FOLDER")
    if pdf:
        mapping.setdefault("paths", {})["pdf_folder"] = pdf
    return mapping


@dataclass
class ZoeConfig:
    """Effective deployment configuration."""

    profile: DeploymentProfile
    mode: RuntimeMode
    raw: dict[str, Any] = field(default_factory=dict)
    legacy_settings: dict[str, str] = field(default_factory=dict)
    cli_overrides: dict[str, Any] = field(default_factory=dict)
    _effective_settings_cache: dict[str, str] | None = field(default=None, repr=False)

    def logging_level(self) -> int:
        level_name = str(
            self.raw.get("logging", {}).get("level", "INFO")
        ).upper()
        return LOG_LEVELS.get(level_name, logging.INFO)

    def startup_verbose(self) -> bool:
        return bool(self.raw.get("logging", {}).get("startup_verbose", False))

    def telemetry_enabled(self) -> bool:
        return bool(self.raw.get("telemetry", {}).get("enabled", True))

    def cache_enabled(self) -> bool:
        return bool(self.raw.get("cache", {}).get("enabled", True))

    def rich_diagnostics(self) -> bool:
        return bool(self.raw.get("diagnostics", {}).get("rich", True))

    def effective_settings(self) -> dict[str, str]:
        """Map to legacy settings.txt keys for backward compatibility."""
        if self._effective_settings_cache is not None:
            return dict(self._effective_settings_cache)

        paths = self.raw.get("paths", {})
        model = self.raw.get("model", {})
        merged = dict(self.legacy_settings)
        if model.get("name"):
            merged["MODEL_NAME"] = str(model["name"])
        if paths.get("memory_db"):
            merged["MEMORY_DB"] = str(paths["memory_db"])
        if paths.get("notes_folder"):
            merged["NOTES_FOLDER"] = str(paths["notes_folder"])
        if paths.get("pdf_folder"):
            merged["PDF_FOLDER"] = str(paths["pdf_folder"])
        for key, value in self.legacy_settings.items():
            merged.setdefault(key, value)
        self._effective_settings_cache = dict(merged)
        return dict(merged)


def load_config(
    *,
    cli_overrides: dict[str, Any] | None = None,
    profile: DeploymentProfile | None = None,
) -> ZoeConfig:
    """
    Load configuration.

    Priority: CLI overrides > environment > YAML (profile) > default.yaml > legacy settings.txt
    """
    global _CONFIG
    config_dir = ROOT / "config"
    detected_profile = profile or detect_deployment_profile()
    mode = detect_runtime_mode()

    merged: dict[str, Any] = {}
    merged = _deep_merge(merged, _load_yaml(config_dir / "default.yaml"))
    merged = _deep_merge(merged, _load_yaml(config_dir / profile_yaml_filename(detected_profile)))
    merged = _deep_merge(merged, apply_profile_defaults(detected_profile))
    merged = _deep_merge(merged, _env_overrides())
    if cli_overrides:
        merged = _deep_merge(merged, cli_overrides)

    legacy = _load_legacy_settings_txt()
    if legacy.get("MODEL_NAME") and not merged.get("model", {}).get("name"):
        merged.setdefault("model", {})["name"] = legacy["MODEL_NAME"]
    if legacy.get("MEMORY_DB"):
        merged.setdefault("paths", {})["memory_db"] = legacy["MEMORY_DB"]
    if legacy.get("NOTES_FOLDER"):
        merged.setdefault("paths", {})["notes_folder"] = legacy["NOTES_FOLDER"]
    if legacy.get("PDF_FOLDER"):
        merged.setdefault("paths", {})["pdf_folder"] = legacy["PDF_FOLDER"]

    merged.setdefault("zoe", {})
    merged["zoe"]["profile"] = detected_profile.value
    merged["zoe"]["mode"] = mode.value

    _CONFIG = ZoeConfig(
        profile=detected_profile,
        mode=mode,
        raw=merged,
        legacy_settings=legacy,
        cli_overrides=cli_overrides or {},
    )
    return _CONFIG


def get_config() -> ZoeConfig:
    global _CONFIG
    if _CONFIG is None:
        return load_config()
    return _CONFIG


def reset_config_for_tests() -> None:
    global _CONFIG
    _CONFIG = None


def invalidate_settings_cache() -> None:
    """Clear cached effective settings after import/export."""
    global _CONFIG
    if _CONFIG is not None:
        _CONFIG._effective_settings_cache = None


def get_effective_settings(legacy_fallback: dict[str, str] | None = None) -> dict[str, str]:
    """Merge deployment config into settings.txt-compatible dict."""
    try:
        cfg = get_config()
        effective = cfg.effective_settings()
        if legacy_fallback:
            for key, value in legacy_fallback.items():
                effective.setdefault(key, value)
        return effective
    except Exception:
        return dict(legacy_fallback or {})
