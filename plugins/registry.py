"""Central plugin registry with cached routing."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from plugins.manifest import PluginManifest
from plugins.plugin import Plugin, PluginHealth

logger = logging.getLogger(__name__)

_route_cache: dict[str, str] = {}
_registry_lock = threading.RLock()


@dataclass
class ExtensionRecord:
    """Installed extension package metadata."""

    manifest: PluginManifest
    plugin_dir: str
    enabled: bool = False
    loaded: bool = False
    health: PluginHealth = PluginHealth.NOT_LOADED
    errors: list[str] = field(default_factory=list)


ChatHookFn = Callable[[dict[str, Any]], dict[str, Any] | None]
MemoryHookFn = Callable[[dict[str, Any]], None]
VoiceHookFn = Callable[[dict[str, Any]], dict[str, Any] | None]
CommandFn = Callable[[], str]


class PluginRegistry:
    """Thread-safe registry of loaded plugins and extension hooks."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._route_cache: dict[str, str] = {}
        self._extensions: dict[str, ExtensionRecord] = {}
        self._chat_hooks: list[tuple[str, ChatHookFn]] = []
        self._memory_hooks: list[tuple[str, MemoryHookFn]] = []
        self._voice_hooks: list[tuple[str, VoiceHookFn]] = []
        self._commands: dict[str, tuple[str, CommandFn]] = {}

    def register(self, plugin: Plugin) -> None:
        with _registry_lock:
            self._plugins[plugin.id] = plugin
            plugin.health = PluginHealth.LOADED if plugin.enabled else PluginHealth.DISABLED
            self._route_cache.clear()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Plugin registered: %s (%s)", plugin.id, plugin.name)

    def register_extension(self, record: ExtensionRecord) -> None:
        with _registry_lock:
            self._extensions[record.manifest.qualified_id] = record

    def get_extension(self, plugin_id: str) -> ExtensionRecord | None:
        key = plugin_id if plugin_id.startswith("ext.") else f"ext.{plugin_id}"
        return self._extensions.get(key) or self._extensions.get(plugin_id)

    def list_extensions(self) -> list[ExtensionRecord]:
        return list(self._extensions.values())

    def unregister(self, plugin_id: str) -> None:
        with _registry_lock:
            self._plugins.pop(plugin_id, None)
            self._route_cache.clear()

    def unregister_extension(self, extension_id: str) -> None:
        """Remove tools and hooks owned by an extension."""
        key = extension_id if extension_id.startswith("ext.") else f"ext.{extension_id}"
        with _registry_lock:
            to_remove = [
                pid
                for pid, plugin in self._plugins.items()
                if plugin.extension_id == key or pid.startswith(f"{key}.")
            ]
            for pid in to_remove:
                self._plugins.pop(pid, None)
            self._chat_hooks = [(p, h) for p, h in self._chat_hooks if p != key]
            self._memory_hooks = [(p, h) for p, h in self._memory_hooks if p != key]
            self._voice_hooks = [(p, h) for p, h in self._voice_hooks if p != key]
            self._commands = {
                name: pair for name, pair in self._commands.items() if pair[0] != key
            }
            record = self._extensions.get(key)
            if record:
                record.loaded = False
                record.health = PluginHealth.DISABLED
            self._route_cache.clear()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Plugin unloaded: %s", key)

    def register_chat_hook(self, plugin_id: str, handler: ChatHookFn) -> None:
        self._chat_hooks.append((plugin_id, handler))

    def register_memory_hook(self, plugin_id: str, handler: MemoryHookFn) -> None:
        self._memory_hooks.append((plugin_id, handler))

    def register_voice_hook(self, plugin_id: str, handler: VoiceHookFn) -> None:
        self._voice_hooks.append((plugin_id, handler))

    def register_extension_command(self, plugin_id: str, command: str, handler: CommandFn) -> None:
        self._commands[command] = (plugin_id, handler)

    def chat_hooks(self) -> list[tuple[str, ChatHookFn]]:
        return list(self._chat_hooks)

    def memory_hooks(self) -> list[tuple[str, MemoryHookFn]]:
        return list(self._memory_hooks)

    def voice_hooks(self) -> list[tuple[str, VoiceHookFn]]:
        return list(self._voice_hooks)

    def get(self, plugin_id: str) -> Plugin | None:
        return self._plugins.get(plugin_id)

    def all_plugins(self) -> list[Plugin]:
        return list(self._plugins.values())

    def enabled_plugins(self) -> list[Plugin]:
        return [
            plugin
            for plugin in self._plugins.values()
            if plugin.enabled and plugin.health == PluginHealth.LOADED
        ]

    def resolve_route(self, query: str) -> str:
        """Return route id for a query using plugin priority order."""
        cache_key = query.strip().lower()[:512]
        with _registry_lock:
            cached = self._route_cache.get(cache_key)
            if cached is not None:
                return cached

        ordered = sorted(
            self.enabled_plugins(),
            key=lambda item: (-item.priority, item.id),
        )
        for plugin in ordered:
            if plugin.matches(query):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Plugin selected for routing: %s", plugin.id)
                with _registry_lock:
                    self._route_cache[cache_key] = plugin.route_id
                return plugin.route_id

        with _registry_lock:
            self._route_cache[cache_key] = "chat"
        return "chat"

    def find_executor_for_route(self, route_id: str) -> Plugin | None:
        for plugin in self.enabled_plugins():
            if plugin.route_id == route_id:
                return plugin
        return None

    def execute_route(self, query: str, route_id: str) -> tuple[bool, str]:
        plugin = self.find_executor_for_route(route_id)
        if plugin is None or plugin.execute_query is None:
            return False, ""
        try:
            return plugin.run(query)
        except Exception as exc:
            plugin.health = PluginHealth.CRASHED
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Plugin crashed: %s (%s)", plugin.id, exc)
            return False, ""

    def select_plugins_for_query(self, query: str) -> list[Plugin]:
        """Return plugins that match a query (for planner/supervisor discovery)."""
        matches = [p for p in self.enabled_plugins() if p.matches(query)]
        matches.sort(key=lambda item: (-item.priority, item.id))
        return matches

    def clear_cache(self) -> None:
        with _registry_lock:
            self._route_cache.clear()


_global_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def reset_registry_for_tests() -> None:
    global _global_registry
    _global_registry = PluginRegistry()