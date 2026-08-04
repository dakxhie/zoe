"""Configuration loader tests (create only)."""

from __future__ import annotations

from deployment.config import load_config, reset_config_for_tests
from deployment.environment import DeploymentProfile, detect_deployment_profile


def test_load_config_merges_legacy():
    reset_config_for_tests()
    cfg = load_config()
    settings = cfg.effective_settings()
    assert "MODEL_NAME" in settings or cfg.raw.get("model")


def test_detect_profile_default():
    profile = detect_deployment_profile("production")
    assert profile == DeploymentProfile.PRODUCTION
