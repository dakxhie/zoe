"""Plugin lifecycle: install, load, enable, disable, reload, unload, remove."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from core.config import ROOT
from plugins.loader import LOCAL_DIR, discover_all_plugins, reload_plugin_module
from plugins.plugin import PluginHealth
from plugins.registry import get_registry

logger = logging.getLogger(__name__)

COMMUNITY_DIR = ROOT / "plugins" / "community"


def install_plugin(source_file: Path, *, target: str = "local") -> Path:
    """Copy a plugin file into community or local folder."""
    dest_root = LOCAL_DIR if target == "local" else COMMUNITY_DIR
    dest_root.mkdir(parents=True, exist_ok=True)
    destination = dest_root / source_file.name
    shutil.copy2(source_file, destination)
    logger.info("Plugin installed to %s", destination)
    return destination


def load_plugins(*, force: bool = False) -> None:
    discover_all_plugins(force=force)


def enable_plugin(plugin_id: str) -> bool:
    registry = get_registry()
    plugin = registry.get(plugin_id)
    if plugin is None:
        return False
    plugin.enabled = True
    plugin.health = PluginHealth.LOADED
    registry.clear_cache()
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Plugin enabled: %s", plugin_id)
    return True


def disable_plugin(plugin_id: str) -> bool:
    registry = get_registry()
    plugin = registry.get(plugin_id)
    if plugin is None:
        return False
    plugin.enabled = False
    plugin.health = PluginHealth.DISABLED
    registry.clear_cache()
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Plugin disabled: %s", plugin_id)
    return True


def reload_plugin(plugin_id: str) -> bool:
    registry = get_registry()
    registry.clear_cache()
    ok = reload_plugin_module(plugin_id)
    if ok and logger.isEnabledFor(logging.DEBUG):
        logger.debug("Plugin reloaded: %s", plugin_id)
    return ok


def unload_plugin(plugin_id: str) -> bool:
    registry = get_registry()
    if registry.get(plugin_id) is None:
        return False
    registry.unregister(plugin_id)
    registry.clear_cache()
    return True


def remove_plugin(plugin_id: str) -> bool:
    registry = get_registry()
    plugin = registry.get(plugin_id)
    if plugin is None:
        return False
    path = Path(plugin.source_path) if plugin.source_path else None
    unload_plugin(plugin_id)
    if path and path.is_file() and LOCAL_DIR in path.parents:
        path.unlink(missing_ok=True)
    return True
