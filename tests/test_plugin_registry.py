"""Plugin registry unit tests (not run in CI by default — execute manually)."""

from __future__ import annotations

from plugins.plugin import Plugin, PluginHealth, ToolCategory
from plugins.manager import reset_plugins_for_tests
from plugins.registry import get_registry


def _make_plugin(
    plugin_id: str,
    *,
    route_id: str = "",
    priority: int = 50,
    match: bool = True,
) -> Plugin:
    def _match(_query: str) -> bool:
        return match

    def _execute(_query: str) -> tuple[bool, str]:
        return True, plugin_id

    return Plugin(
        id=plugin_id,
        name=plugin_id,
        version="1.0.0",
        author="test",
        description="test",
        category=ToolCategory.UTILITIES,
        permissions=frozenset(),
        priority=priority,
        route_id=route_id or plugin_id,
        match_query=_match,
        execute_query=_execute,
    )


def test_register_and_resolve_route():
    reset_plugins_for_tests()
    registry = get_registry()
    registry.register(_make_plugin("test.a", route_id="route_a", priority=100))
    registry.register(_make_plugin("test.b", route_id="route_b", priority=10))
    assert registry.resolve_route("anything") == "route_a"
    assert registry.resolve_route("anything") == "route_a"


def test_route_cache_cleared_on_unregister():
    reset_plugins_for_tests()
    registry = get_registry()
    registry.register(_make_plugin("test.cache", route_id="cached"))
    registry.resolve_route("q")
    registry.unregister("test.cache")
    registry.register(
        _make_plugin("test.cache2", route_id="other", priority=200)
    )
    assert registry.resolve_route("q") == "other"


def test_execute_route_marks_crashed_on_failure():
    reset_plugins_for_tests()
    registry = get_registry()

    def _boom(_q: str) -> tuple[bool, str]:
        raise RuntimeError("fail")

    plugin = _make_plugin("test.crash", route_id="crash_route")
    plugin.execute_query = _boom
    registry.register(plugin)
    ok, text = registry.execute_route("x", "crash_route")
    assert ok is False
    assert text == ""
    assert registry.get("test.crash").health == PluginHealth.CRASHED


def test_select_plugins_for_query_orders_by_priority():
    reset_plugins_for_tests()
    registry = get_registry()
    registry.register(_make_plugin("low", priority=1))
    registry.register(_make_plugin("high", priority=99))
    ordered = registry.select_plugins_for_query("x")
    assert [p.id for p in ordered] == ["high", "low"]
