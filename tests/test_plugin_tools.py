"""Extension tool registration tests (create only)."""

from __future__ import annotations

from plugins.manager import PluginManager, reset_plugins_for_tests, route_query
from plugins.state import set_extension_enabled


def test_enabled_clock_tool_routes():
    reset_plugins_for_tests()
    set_extension_enabled("ext.clock", True)
    PluginManager().discover(force=True)
    route = route_query("clock")
    assert route == "ext_clock"
