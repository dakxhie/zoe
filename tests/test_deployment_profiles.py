"""Deployment profile tests (create only)."""

from __future__ import annotations

from deployment.environment import DeploymentProfile, apply_profile_defaults


def test_production_logging_level():
    defaults = apply_profile_defaults(DeploymentProfile.PRODUCTION)
    assert defaults["logging"]["level"] == "INFO"


def test_testing_telemetry_disabled():
    defaults = apply_profile_defaults(DeploymentProfile.TESTING)
    assert defaults["telemetry"]["enabled"] is False
