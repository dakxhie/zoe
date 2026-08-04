"""Plugin loader tests (create only — not executed in sprint)."""

from __future__ import annotations

from pathlib import Path

from plugins.loader import discover_manifest_extensions
from plugins.manager import reset_plugins_for_tests
from plugins.registry import get_registry


def test_discover_example_manifests():
    reset_plugins_for_tests()
    discover_manifest_extensions(get_registry())
    ext_ids = {r.manifest.qualified_id for r in get_registry().list_extensions()}
    assert "ext.clock" in ext_ids
    assert "ext.notes" in ext_ids
    assert "ext.translate" in ext_ids


def test_example_clock_manifest_valid():
    reset_plugins_for_tests()
    discover_manifest_extensions(get_registry())
    record = get_registry().get_extension("clock")
    assert record is not None
    assert not record.errors
    assert Path(record.plugin_dir, "main.py").is_file()
