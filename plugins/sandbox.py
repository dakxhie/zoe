"""Restricted execution environment for unsafe plugins."""

from __future__ import annotations

import logging
from typing import Callable, TypeVar

from plugins.permissions import Permission, has_permission, normalize_permissions

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_sandboxed(
    plugin_id: str,
    permissions: frozenset[str],
    fn: Callable[[], T],
    *,
    requires: Permission | str | None = None,
) -> T:
    """Execute plugin logic with permission checks (architecture hook, no Docker)."""
    if requires is not None and not has_permission(permissions, requires):
        raise PermissionError(f"Plugin {plugin_id} blocked in sandbox (requires {requires})")
    try:
        return fn()
    except Exception as exc:
        logger.warning("Sandboxed plugin %s raised: %s", plugin_id, exc)
        raise


def run_plugin_entry(
    plugin_id: str,
    permissions: tuple[str, ...] | list[str],
    fn: Callable[[], T],
) -> T | None:
    """Execute plugin setup; isolate failures."""
    granted = normalize_permissions(permissions)
    try:
        return run_sandboxed(plugin_id, granted, fn)
    except Exception as exc:
        logger.error("Plugin %s crashed during entry: %s", plugin_id, exc)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Plugin crashed: %s", plugin_id)
        return None


def wrap_execute(
    plugin_id: str,
    permissions: frozenset[str],
    execute: Callable[[str], tuple[bool, str]],
) -> Callable[[str], tuple[bool, str]]:
    """Wrap execute so failures never escape uncaught to the host."""

    def _wrapped(query: str) -> tuple[bool, str]:
        try:
            return run_sandboxed(plugin_id, permissions, lambda: execute(query))
        except PermissionError:
            return False, ""
        except Exception as exc:
            logger.error("Plugin %s crashed; disabling path via manager", plugin_id)
            return False, f"Plugin error: {exc}"

    return _wrapped
