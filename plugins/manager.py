"""High-level plugin manager API."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from plugins.events import Event, emit
from plugins.lifecycle import (
    disable_plugin,
    enable_plugin,
    install_plugin,
    load_plugins,
    reload_plugin,
    remove_plugin,
    unload_plugin,
)
from plugins.loader import (
    discover_all_plugins,
    load_extension_plugin,
    reload_plugin_module,
)
from plugins.permissions import Permission, authorize_plugin_action
from plugins.plugin import Plugin, PluginHealth
from plugins.registry import ExtensionRecord, get_registry
from plugins.state import load_enabled_extension_ids, set_extension_enabled

logger = logging.getLogger(__name__)

_initialized = False
_manager: "PluginManager | None" = None


def reset_plugins_for_tests() -> None:
    """Clear startup caches for unit tests."""
    global _initialized, _manager
    _initialized = False
    _manager = None
    from plugins.events import clear_subscribers_for_tests
    from plugins.loader import reset_loader_for_tests
    from plugins.registry import reset_registry_for_tests

    clear_subscribers_for_tests()
    reset_loader_for_tests()
    reset_registry_for_tests()


@dataclass(frozen=True)
class PluginStatusRow:
    """Summary row for desktop helper APIs."""

    plugin_id: str
    name: str
    version: str
    enabled: bool
    health: str
    category: str


@dataclass(frozen=True)
class InstalledPluginRow:
    """Installed extension or builtin summary."""

    plugin_id: str
    name: str
    version: str
    enabled: bool
    loaded: bool
    kind: str
    errors: tuple[str, ...] = ()


class PluginManager:
    """Discover, validate, load, and isolate extension plugins."""

    def discover(self, *, force: bool = False) -> None:
        load_plugins(force=force)

    def list_installed(self) -> list[InstalledPluginRow]:
        self.discover()
        rows: list[InstalledPluginRow] = []
        for plugin in get_registry().all_plugins():
            if plugin.extension_id:
                continue
            if not plugin.id.startswith("builtin."):
                continue
            rows.append(
                InstalledPluginRow(
                    plugin_id=plugin.id,
                    name=plugin.name,
                    version=plugin.version,
                    enabled=plugin.enabled,
                    loaded=plugin.health == PluginHealth.LOADED,
                    kind="builtin",
                )
            )
        for record in get_registry().list_extensions():
            manifest = record.manifest
            rows.append(
                InstalledPluginRow(
                    plugin_id=manifest.qualified_id,
                    name=manifest.name,
                    version=manifest.version,
                    enabled=record.enabled,
                    loaded=record.loaded,
                    kind="extension",
                    errors=tuple(record.errors),
                )
            )
        return rows

    def enable(self, plugin_id: str) -> bool:
        registry = get_registry()
        ext = registry.get_extension(plugin_id)
        if ext is not None:
            qid = ext.manifest.qualified_id
            if ext.errors:
                return False
            set_extension_enabled(qid, True)
            ext.enabled = True
            ok = load_extension_plugin(qid)
            if ok:
                emit(Event.PLUGIN_LOADED, {"plugin_id": qid})
            registry.clear_cache()
            return ok

        if enable_plugin(plugin_id):
            registry.clear_cache()
            return True
        return False

    def disable(self, plugin_id: str) -> bool:
        registry = get_registry()
        ext = registry.get_extension(plugin_id)
        if ext is not None:
            qid = ext.manifest.qualified_id
            set_extension_enabled(qid, False)
            ext.enabled = False
            registry.unregister_extension(qid)
            ext.loaded = False
            ext.health = PluginHealth.DISABLED
            emit(Event.PLUGIN_UNLOADED, {"plugin_id": qid})
            registry.clear_cache()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Plugin unloaded: %s", qid)
            return True

        return disable_plugin(plugin_id)

    def reload(self, plugin_id: str) -> bool:
        registry = get_registry()
        ext = registry.get_extension(plugin_id)
        if ext is not None:
            qid = ext.manifest.qualified_id
            if not ext.enabled:
                return False
            registry.unregister_extension(qid)
            ok = load_extension_plugin(qid)
            if ok and logger.isEnabledFor(logging.DEBUG):
                logger.debug("Plugin reloaded: %s", qid)
            registry.clear_cache()
            return ok
        registry.clear_cache()
        return reload_plugin_module(plugin_id)

    def uninstall(self, plugin_id: str) -> bool:
        ext = get_registry().get_extension(plugin_id)
        if ext is None:
            return remove_plugin(plugin_id)
        self.disable(ext.manifest.qualified_id)
        plugin_dir = Path(ext.plugin_dir)
        if plugin_dir.is_dir() and plugin_dir.name.startswith("example_"):
            return False
        if plugin_dir.is_dir():
            shutil.rmtree(plugin_dir, ignore_errors=True)
        return True

    def startup(self) -> None:
        if _initialized:
            return
        self.discover()
        emit(Event.STARTUP, {})

    def shutdown(self) -> None:
        emit(Event.SHUTDOWN, {})


def get_plugin_manager() -> PluginManager:
    global _manager
    if _manager is None:
        _manager = PluginManager()
    return _manager


def initialize_plugins(*, force: bool = False) -> None:
    """Discover plugins once during startup."""
    global _initialized
    if _initialized and not force:
        return
    get_plugin_manager().discover(force=force)
    emit(Event.STARTUP, {})
    _initialized = True


def shutdown_plugins() -> None:
    get_plugin_manager().shutdown()


def list_plugin_status() -> list[PluginStatusRow]:
    initialize_plugins()
    rows: list[PluginStatusRow] = []
    for plugin in get_registry().all_plugins():
        rows.append(
            PluginStatusRow(
                plugin_id=plugin.id,
                name=plugin.name,
                version=plugin.version,
                enabled=plugin.enabled,
                health=plugin.health.value,
                category=plugin.category.value,
            )
        )
    for record in get_registry().list_extensions():
        rows.append(
            PluginStatusRow(
                plugin_id=record.manifest.qualified_id,
                name=record.manifest.name,
                version=record.manifest.version,
                enabled=record.enabled,
                health=record.health.value,
                category="extension",
            )
        )
    return rows


def list_loaded_plugins() -> list[str]:
    return [row.plugin_id for row in list_plugin_status() if row.health == PluginHealth.LOADED.value]


def list_enabled_plugins() -> list[str]:
    return [row.plugin_id for row in list_plugin_status() if row.enabled]


def list_disabled_plugins() -> list[str]:
    return [row.plugin_id for row in list_plugin_status() if not row.enabled]


def route_query(query: str) -> str:
    """Cached plugin-based routing."""
    initialize_plugins()
    return get_registry().resolve_route(query)


def execute_plugin_route(query: str, route_id: str) -> tuple[bool, str]:
    initialize_plugins()
    from plugins.events import Event, emit

    handled, result = get_registry().execute_route(query, route_id)
    if handled and logger.isEnabledFor(logging.DEBUG):
        logger.debug("Plugin tool executed: route=%s", route_id)
    emit(Event.TOOL_CALLED, {"route": route_id, "handled": handled})
    return handled, result


def supervisor_may_use_plugin(plugin_id: str, permission: Permission, *, action: str = "") -> bool:
    """Supervisor gate for plugin capabilities."""
    initialize_plugins()
    plugin = get_registry().get(plugin_id)
    if plugin is None:
        ext = get_registry().get_extension(plugin_id)
        if ext is None:
            return False
        granted = frozenset(ext.manifest.permissions)
        return authorize_plugin_action(ext.manifest.qualified_id, granted, permission, action=action)
    return authorize_plugin_action(plugin_id, plugin.permissions, permission, action=action)


def select_plugins_for_planner(query: str) -> list[Plugin]:
    initialize_plugins()
    return get_registry().select_plugins_for_query(query)
