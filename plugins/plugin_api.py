"""Stable plugin API — extensions must use PluginContext only."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from core.config import ROOT
from plugins.events import Event, subscribe
from plugins.manifest import PluginManifest
from plugins.permissions import Permission, authorize_plugin_action, normalize_permissions
from plugins.plugin import Plugin, ToolCategory
from plugins.registry import get_registry
from plugins.sandbox import wrap_execute

PLUGIN_DATA_ROOT = ROOT / "data" / "plugins"

ExecuteFn = Callable[[str], tuple[bool, str]]
MatchFn = Callable[[str], bool]
ChatHookFn = Callable[[dict[str, Any]], dict[str, Any] | None]
MemoryHookFn = Callable[[dict[str, Any]], None]
VoiceHookFn = Callable[[dict[str, Any]], dict[str, Any] | None]


@dataclass
class PluginSettingsView:
    """Read-only manifest fields plus optional plugin settings file."""

    manifest: PluginManifest
    _settings_path: Path

    def get(self, key: str, default: Any = None) -> Any:
        if self._settings_path.is_file():
            try:
                data = json.loads(self._settings_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and key in data:
                    return data[key]
            except (json.JSONDecodeError, OSError):
                pass
        return default

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.manifest.id,
            "name": self.manifest.name,
            "version": self.manifest.version,
            "permissions": list(self.manifest.permissions),
        }


class PluginStorage:
    """Per-plugin isolated storage under data/plugins/<plugin_id>/."""

    def __init__(self, plugin_id: str) -> None:
        self._root = (PLUGIN_DATA_ROOT / plugin_id).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, name: str) -> Path:
        cleaned = name.replace("\\", "/").lstrip("/")
        if ".." in cleaned.split("/"):
            raise PermissionError("Path traversal is not allowed in plugin storage")
        target = (self._root / cleaned).resolve()
        if not str(target).startswith(str(self._root)):
            raise PermissionError("Storage path outside plugin directory")
        return target

    def read_text(self, name: str, default: str = "") -> str:
        path = self._safe_path(name)
        if not path.is_file():
            return default
        return path.read_text(encoding="utf-8")

    def write_text(self, name: str, content: str) -> None:
        path = self._safe_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def path(self) -> Path:
        return self._root


@dataclass
class PluginContext:
    """Context passed to extension plugins at load time."""

    manifest: PluginManifest
    plugin_dir: Path
    _permissions: frozenset[str] = field(init=False)
    _logger: logging.Logger = field(init=False)

    def __post_init__(self) -> None:
        self._permissions = normalize_permissions(self.manifest.permissions)
        self._logger = logging.getLogger(f"plugin.{self.manifest.qualified_id}")

    @property
    def plugin_id(self) -> str:
        return self.manifest.qualified_id

    def logger(self) -> logging.Logger:
        return self._logger

    def settings(self) -> PluginSettingsView:
        settings_path = PLUGIN_DATA_ROOT / self.manifest.id / "settings.json"
        return PluginSettingsView(self.manifest, settings_path)

    def storage(self) -> PluginStorage:
        return PluginStorage(self.manifest.id)

    def _check(self, permission: Permission | str, action: str) -> bool:
        return authorize_plugin_action(
            self.plugin_id,
            self._permissions,
            permission,
            action=action,
        )

    def register_tool(
        self,
        *,
        name: str,
        route_id: str,
        match_query: MatchFn,
        execute_query: ExecuteFn,
        priority: int = 40,
        category: ToolCategory = ToolCategory.UTILITIES,
        description: str = "",
    ) -> None:
        wrapped = wrap_execute(self.plugin_id, self._permissions, execute_query)
        plugin = Plugin(
            id=f"{self.plugin_id}.tool.{route_id}",
            name=name,
            version=self.manifest.version,
            author=self.manifest.author or "extension",
            description=description or name,
            category=category,
            permissions=self._permissions,
            enabled=True,
            priority=priority,
            route_id=route_id,
            match_query=match_query,
            execute_query=wrapped,
            extension_id=self.plugin_id,
        )
        get_registry().register(plugin)
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug("Registered tool route_id=%s", route_id)

    def register_command(self, command: str, handler: Callable[[], str]) -> None:
        """Register a simple named command (stored for future CLI extension)."""
        registry = get_registry()
        registry.register_extension_command(self.plugin_id, command, handler)

    def register_memory_hook(self, handler: MemoryHookFn) -> None:
        if not self._check(Permission.MEMORY, "memory_hook"):
            return
        get_registry().register_memory_hook(self.plugin_id, handler)

    def register_chat_hook(self, handler: ChatHookFn) -> None:
        get_registry().register_chat_hook(self.plugin_id, handler)

    def register_voice_hook(self, handler: VoiceHookFn) -> None:
        if not self._check(Permission.VOICE, "voice_hook"):
            return
        get_registry().register_voice_hook(self.plugin_id, handler)

    def register_event(self, event: Event | str, handler: Callable[[dict[str, Any]], None]) -> None:
        subscribe(event, handler)


def apply_chat_hooks(
    user_message: str,
    assistant_reply: str,
    *,
    tool_result: str = "",
) -> str:
    """Run chat hooks; core reply always wins, hooks may append or annotate."""
    payload_base = {
        "user_message": user_message,
        "assistant_reply": assistant_reply,
        "tool_result": tool_result,
    }
    reply = assistant_reply
    for plugin_id, handler in get_registry().chat_hooks():
        data = dict(payload_base)
        data["assistant_reply"] = reply
        try:
            result = handler(data)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Chat hook failed for %s: %s", plugin_id, exc
            )
            continue
        if not result:
            continue
        new_reply = result.get("assistant_reply")
        append = result.get("append", "")
        if append and isinstance(append, str):
            reply = f"{reply.rstrip()}\n{append}".strip()
        elif isinstance(new_reply, str) and new_reply.strip():
            if new_reply.startswith(reply):
                reply = new_reply
            else:
                reply = f"{reply.rstrip()}\n{new_reply}".strip()
    return reply


def run_memory_hooks(payload: dict[str, Any]) -> None:
    for plugin_id, handler in get_registry().memory_hooks():
        try:
            handler(payload)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Memory hook failed for %s: %s", plugin_id, exc
            )


def run_voice_hooks(phase: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Run voice hooks for a pipeline phase; returns possibly modified payload."""
    data = dict(payload)
    data["phase"] = phase
    for plugin_id, handler in get_registry().voice_hooks():
        try:
            result = handler(data)
            if isinstance(result, dict):
                data.update(result)
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Voice hook failed for %s: %s", plugin_id, exc
            )
    return data
