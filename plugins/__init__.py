"""Plugin framework for Zoe AI."""

from plugins.events import Event, emit, on_event, subscribe
from plugins.lifecycle import (
    disable_plugin,
    enable_plugin,
    install_plugin,
    load_plugins,
    reload_plugin,
    remove_plugin,
    unload_plugin,
)
from plugins.manager import (
    PluginManager,
    get_plugin_manager,
    initialize_plugins,
    list_disabled_plugins,
    list_enabled_plugins,
    list_loaded_plugins,
    list_plugin_status,
    route_query,
    select_plugins_for_planner,
    shutdown_plugins,
    supervisor_may_use_plugin,
)
from plugins.manifest import PluginManifest, load_manifest
from plugins.metadata import PluginMetadata
from plugins.permissions import Permission
from plugins.plugin import Plugin, PluginHealth, ToolCategory
from plugins.plugin_api import PluginContext, apply_chat_hooks
from plugins.registry import get_registry

__all__ = [
    "Event",
    "Permission",
    "Plugin",
    "PluginContext",
    "PluginHealth",
    "PluginManager",
    "PluginManifest",
    "PluginMetadata",
    "ToolCategory",
    "apply_chat_hooks",
    "disable_plugin",
    "emit",
    "enable_plugin",
    "get_plugin_manager",
    "get_registry",
    "initialize_plugins",
    "install_plugin",
    "list_disabled_plugins",
    "list_enabled_plugins",
    "list_loaded_plugins",
    "list_plugin_status",
    "load_manifest",
    "load_plugins",
    "on_event",
    "reload_plugin",
    "remove_plugin",
    "route_query",
    "select_plugins_for_planner",
    "shutdown_plugins",
    "subscribe",
    "supervisor_may_use_plugin",
    "unload_plugin",
]
