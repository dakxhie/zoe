"""Plugin reload tests (create only)."""

from __future__ import annotations

from plugins.manager import PluginManager, reset_plugins_for_tests
from plugins.state import set_extension_enabled


def test_reload_enabled_extension():
    reset_plugins_for_tests()
    manager = PluginManager()
    manager.discover(force=True)
    set_extension_enabled("ext.clock", True)
    manager.discover(force=True)
    assert manager.reload("clock") or manager.reload("ext.clock")
