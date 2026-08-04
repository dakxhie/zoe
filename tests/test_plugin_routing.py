"""Integration-style routing through plugin manager."""

from __future__ import annotations

from plugins.manager import (
    execute_plugin_route,
    reset_plugins_for_tests,
    route_query,
    select_plugins_for_planner,
)
from plugins.loader import discover_all_plugins


def test_calculator_route_via_manager():
    reset_plugins_for_tests()
    discover_all_plugins(force=True)
    route = route_query("what is 2+2")
    assert route == "calculator"
    ok, answer = execute_plugin_route("what is 2+2", route)
    assert ok is True
    assert "4" in answer


def test_planner_selects_calculator_plugin():
    reset_plugins_for_tests()
    discover_all_plugins(force=True)
    plugins = select_plugins_for_planner("calculate 10 * 5")
    assert any(p.id == "builtin.calculator" for p in plugins)


def test_datetime_route():
    reset_plugins_for_tests()
    discover_all_plugins(force=True)
    route = route_query("what time is it")
    assert route == "datetime"
