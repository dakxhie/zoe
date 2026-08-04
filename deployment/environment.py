"""Runtime environment and deployment profile detection."""

from __future__ import annotations

import os
import sys
from enum import Enum
from pathlib import Path


class DeploymentProfile(str, Enum):
    DEVELOPER = "developer"
    PRODUCTION = "production"
    PORTABLE = "portable"
    TESTING = "testing"


class RuntimeMode(str, Enum):
    LOCAL = "local"
    PORTABLE = "portable"


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def detect_runtime_mode() -> RuntimeMode:
    if _truthy(os.environ.get("ZOE_PORTABLE")):
        return RuntimeMode.PORTABLE
    if _truthy(os.environ.get("ZOE_LOCAL", "1")):
        return RuntimeMode.LOCAL
    return RuntimeMode.LOCAL


def detect_deployment_profile(explicit: str | None = None) -> DeploymentProfile:
    if explicit:
        try:
            return DeploymentProfile(explicit.strip().lower())
        except ValueError:
            pass

    env_profile = os.environ.get("ZOE_PROFILE", "").strip().lower()
    if env_profile:
        try:
            return DeploymentProfile(env_profile)
        except ValueError:
            pass

    if _truthy(os.environ.get("CI")) or _truthy(os.environ.get("GITHUB_ACTIONS")):
        return DeploymentProfile.TESTING

    if _truthy(os.environ.get("ZOE_PORTABLE")):
        return DeploymentProfile.PORTABLE

    if "pytest" in sys.modules:
        return DeploymentProfile.TESTING

    return DeploymentProfile.DEVELOPER


def profile_yaml_filename(profile: DeploymentProfile) -> str:
    if profile == DeploymentProfile.PRODUCTION:
        return "production.yaml"
    if profile in {DeploymentProfile.TESTING, DeploymentProfile.PORTABLE}:
        return "development.yaml"
    return "development.yaml"


def apply_profile_defaults(profile: DeploymentProfile) -> dict[str, object]:
    """Adjust subsystem defaults per deployment profile."""
    base: dict[str, object] = {
        "logging": {"level": "INFO", "startup_verbose": False},
        "cache": {"enabled": True},
        "telemetry": {"enabled": True, "local_only": True},
        "diagnostics": {"rich": True},
    }
    if profile == DeploymentProfile.DEVELOPER:
        base["logging"] = {"level": "DEBUG", "startup_verbose": True}
        base["diagnostics"] = {"rich": True}
    elif profile == DeploymentProfile.PRODUCTION:
        base["logging"] = {"level": "INFO", "startup_verbose": False}
        base["diagnostics"] = {"rich": False}
    elif profile == DeploymentProfile.PORTABLE:
        base["cache"] = {"enabled": False}
        base["logging"] = {"level": "INFO", "startup_verbose": False}
    elif profile == DeploymentProfile.TESTING:
        base["telemetry"] = {"enabled": False, "local_only": True}
        base["logging"] = {"level": "WARNING", "startup_verbose": False}
    return base


def detect_environment(config_root: Path | None = None) -> dict[str, str]:
    """Return a summary of detected environment flags."""
    profile = detect_deployment_profile()
    mode = detect_runtime_mode()
    return {
        "profile": profile.value,
        "mode": mode.value,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "config_root": str(config_root or ""),
    }
