"""Plugin discovery and module loading."""

from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import pkgutil
import sys
from pathlib import Path

from core.config import ROOT
from plugins.manifest import load_manifest, validate_manifest
from plugins.plugin import Plugin, PluginHealth
from plugins.plugin_api import PluginContext
from plugins.registry import ExtensionRecord, PluginRegistry, get_registry

logger = logging.getLogger(__name__)

BUILTIN_PACKAGE = "plugins.builtin"
COMMUNITY_DIR = ROOT / "plugins" / "community"
LOCAL_DIR = ROOT / "plugins" / "local"
PLUGINS_ROOT = ROOT / "plugins"

SKIP_DIRS = frozenset({"builtin", "community", "local", "__pycache__"})

_discovered = False


def reset_loader_for_tests() -> None:
    global _discovered
    _discovered = False


def discover_builtin_plugins(registry: PluginRegistry | None = None) -> list[Plugin]:
    """Import all modules in plugins.builtin."""
    target = registry or get_registry()
    loaded: list[Plugin] = []
    package = importlib.import_module(BUILTIN_PACKAGE)
    prefix = package.__name__ + "."

    for module_info in pkgutil.iter_modules(package.__path__, prefix):
        if not module_info.name.endswith("_plugin"):
            continue
        try:
            module = importlib.import_module(module_info.name)
        except Exception as exc:
            logger.error("Failed to import builtin plugin %s: %s", module_info.name, exc)
            continue
        plugin = _plugin_from_module(module, module_info.name)
        if plugin is None:
            continue
        target.register(plugin)
        loaded.append(plugin)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Plugin loaded: %s", plugin.id)
    return loaded


def discover_manifest_extensions(registry: PluginRegistry | None = None) -> list[ExtensionRecord]:
    """Discover extension packages containing plugin.json (disabled until enabled)."""
    target = registry or get_registry()
    found: list[ExtensionRecord] = []

    if not PLUGINS_ROOT.is_dir():
        return found

    for child in sorted(PLUGINS_ROOT.iterdir()):
        if not child.is_dir() or child.name in SKIP_DIRS or child.name.startswith("."):
            continue
        manifest_path = child / "plugin.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = load_manifest(child)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.error("Invalid manifest in %s: %s", child, exc)
            continue

        errors = validate_manifest(manifest, child)
        record = ExtensionRecord(
            manifest=manifest,
            plugin_dir=str(child),
            enabled=False,
            loaded=False,
            health=PluginHealth.FAILED if errors else PluginHealth.DISABLED,
            errors=errors,
        )
        target.register_extension(record)
        found.append(record)
    return found


def load_extension_plugin(extension_id: str) -> bool:
    """Load extension entry module and call register/setup."""
    registry = get_registry()
    record = registry.get_extension(extension_id)
    if record is None:
        return False
    if record.errors:
        record.health = PluginHealth.FAILED
        return False

    plugin_dir = Path(record.plugin_dir)
    manifest = record.manifest
    entry_path = plugin_dir / manifest.entry

    registry.unregister_extension(manifest.qualified_id)

    module_name = f"zoe_ext_{manifest.id.replace('.', '_')}"
    sys.modules.pop(module_name, None)

    try:
        spec = importlib.util.spec_from_file_location(module_name, entry_path)
        if spec is None or spec.loader is None:
            record.health = PluginHealth.FAILED
            return False
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as exc:
        logger.error("Extension %s failed to import: %s", manifest.qualified_id, exc)
        record.health = PluginHealth.CRASHED
        record.loaded = False
        return False

    context = PluginContext(manifest=manifest, plugin_dir=plugin_dir)
    register_fn = getattr(module, "register", None) or getattr(module, "setup", None)
    if not callable(register_fn):
        logger.error("Extension %s missing register() or setup()", manifest.qualified_id)
        record.health = PluginHealth.FAILED
        return False

    try:
        from plugins.permissions import normalize_permissions
        from plugins.sandbox import run_sandboxed

        run_sandboxed(
            manifest.qualified_id,
            normalize_permissions(manifest.permissions),
            lambda: register_fn(context),
        )
    except Exception as exc:
        logger.error("Extension %s crashed during register: %s", manifest.qualified_id, exc)
        registry.unregister_extension(manifest.qualified_id)
        record.health = PluginHealth.CRASHED
        record.loaded = False
        return False

    record.loaded = True
    record.health = PluginHealth.LOADED
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Plugin loaded: %s", manifest.qualified_id)
    return True


def discover_folder_plugins(folder: Path, registry: PluginRegistry | None = None) -> list[Plugin]:
    """Discover legacy single-file plugins from community/local directories."""
    target = registry or get_registry()
    loaded: list[Plugin] = []
    if not folder.is_dir():
        folder.mkdir(parents=True, exist_ok=True)
        return loaded

    for path in sorted(folder.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module_name = f"zoe_plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)  # type: ignore[attr-defined]
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            logger.error("Community plugin %s failed: %s", path.name, exc)
            continue
        plugin = _plugin_from_module(module, str(path))
        if plugin is None:
            continue
        plugin.source_path = str(path)
        target.register(plugin)
        loaded.append(plugin)
    return loaded


def _plugin_from_module(module: object, source: str) -> Plugin | None:
    plugin = getattr(module, "PLUGIN", None)
    if isinstance(plugin, Plugin):
        plugin.source_path = source
        return plugin
    build = getattr(module, "build_plugin", None)
    if callable(build):
        built = build()
        if isinstance(built, Plugin):
            built.source_path = source
            return built
    return None


def discover_all_plugins(*, force: bool = False) -> None:
    """Run discovery once at startup (cached)."""
    global _discovered
    if _discovered and not force:
        return
    registry = get_registry()
    discover_builtin_plugins(registry)
    discover_folder_plugins(COMMUNITY_DIR, registry)
    discover_folder_plugins(LOCAL_DIR, registry)
    discover_manifest_extensions(registry)
    _load_enabled_extensions()
    _resolve_dependencies(registry)
    _discovered = True
    logger.info(
        "Plugin discovery complete: %s plugin(s) registered",
        len(registry.all_plugins()),
    )


def _load_enabled_extensions() -> None:
    from plugins.state import load_enabled_extension_ids

    enabled_ids = load_enabled_extension_ids()
    registry = get_registry()
    for record in registry.list_extensions():
        qid = record.manifest.qualified_id
        record.enabled = qid in enabled_ids
        if record.enabled and not record.errors:
            load_extension_plugin(qid)
        elif not record.enabled:
            record.loaded = False
            record.health = PluginHealth.DISABLED


def _resolve_dependencies(registry: PluginRegistry) -> None:
    """Enable plugins only when dependencies are present."""
    by_id = {p.id: p for p in registry.all_plugins()}
    for plugin in registry.all_plugins():
        missing = [dep for dep in plugin.dependencies if dep not in by_id]
        if missing:
            plugin.health = PluginHealth.MISSING_DEPENDENCY
            plugin.enabled = False
            logger.warning("Plugin %s missing dependencies: %s", plugin.id, missing)


def reload_plugin_module(plugin_id: str) -> bool:
    """Hot-reload a plugin module or extension."""
    registry = get_registry()
    ext = registry.get_extension(plugin_id)
    if ext is not None:
        registry.unregister_extension(ext.manifest.qualified_id)
        return load_extension_plugin(ext.manifest.qualified_id)

    plugin = registry.get(plugin_id)
    if plugin is None or not plugin.source_path:
        return False
    registry.unregister(plugin_id)
    if plugin.source_path.startswith("plugins."):
        importlib.invalidate_caches()
        importlib.reload(importlib.import_module(plugin.source_path))
        discover_builtin_plugins(registry)
    else:
        discover_folder_plugins(Path(plugin.source_path).parent, registry)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Plugin reloaded: %s", plugin_id)
    return registry.get(plugin_id) is not None
