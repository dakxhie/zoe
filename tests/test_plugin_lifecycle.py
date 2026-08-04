"""Plugin lifecycle enable/disable/reload tests."""

from __future__ import annotations

from plugins.manager import reset_plugins_for_tests
from plugins.lifecycle import disable_plugin, enable_plugin, unload_plugin
from plugins.loader import discover_all_plugins
from plugins.plugin import PluginHealth
from plugins.registry import get_registry


def test_enable_disable_plugin():
    reset_plugins_for_tests()
    discover_all_plugins(force=True)
    plugin_id = "builtin.calculator"
    assert disable_plugin(plugin_id) is True
    plugin = get_registry().get(plugin_id)
    assert plugin.enabled is False
    assert plugin.health == PluginHealth.DISABLED
    assert enable_plugin(plugin_id) is True
    assert get_registry().get(plugin_id).enabled is True


def test_unload_removes_from_registry():
    reset_plugins_for_tests()
    discover_all_plugins(force=True)
    plugin_id = "builtin.datetime"
    assert unload_plugin(plugin_id) is True
    assert get_registry().get(plugin_id) is None
