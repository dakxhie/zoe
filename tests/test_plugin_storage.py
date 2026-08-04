"""Plugin storage tests (create only)."""

from __future__ import annotations

from plugins.plugin_api import PluginStorage


def test_storage_rejects_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr("plugins.plugin_api.PLUGIN_DATA_ROOT", tmp_path)
    storage = PluginStorage("safe")
    try:
        storage.read_text("../secrets.txt")
        raised = False
    except PermissionError:
        raised = True
    assert raised
