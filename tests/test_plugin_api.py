"""PluginContext API tests (create only)."""

from __future__ import annotations

from pathlib import Path

from plugins.manifest import load_manifest
from plugins.plugin_api import PluginContext, PluginStorage


def test_plugin_storage_isolated(tmp_path, monkeypatch):
    monkeypatch.setattr("plugins.plugin_api.PLUGIN_DATA_ROOT", tmp_path)
    storage = PluginStorage("demo")
    storage.write_text("note.txt", "hello")
    assert storage.read_text("note.txt") == "hello"


def test_plugin_context_settings():
    manifest = load_manifest(Path("plugins/example_clock"))
    ctx = PluginContext(manifest=manifest, plugin_dir=Path("plugins/example_clock"))
    assert ctx.plugin_id == "ext.clock"
    assert ctx.settings().get("id") is None
    data = ctx.settings().as_dict()
    assert data["name"] == "Clock"
