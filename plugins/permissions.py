"""Plugin permissions and authorization checks."""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    FILESYSTEM = "filesystem"
    INTERNET = "internet"
    MEMORY = "memory"
    DESKTOP = "desktop"
    VOICE = "voice"
    SYSTEM = "system"
    UNSAFE = "unsafe"
    NOTES = "notes"
    WEB = "web"
    CODE = "code"
    CLIPBOARD = "clipboard"
    DATETIME = "datetime"


PERMISSION_SET: frozenset[str] = frozenset(p.value for p in Permission)


def normalize_permissions(values: tuple[str, ...] | list[str]) -> frozenset[str]:
    return frozenset(value.strip().lower() for value in values if value.strip())


def has_permission(granted: frozenset[str], required: Permission | str) -> bool:
    key = required.value if isinstance(required, Permission) else required.lower()
    if key in granted:
        return True
    if Permission.UNSAFE.value in granted:
        return True
    return False


def authorize_plugin_action(
    plugin_id: str,
    granted: frozenset[str],
    required: Permission | str,
    *,
    action: str = "",
) -> bool:
    """Return True when the plugin may perform an action requiring permission."""
    if has_permission(granted, required):
        return True
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "Permission denied: plugin=%s action=%s required=%s",
            plugin_id,
            action or "execute",
            required,
        )
    logger.warning(
        "Supervisor refused plugin %s action %s (missing %s permission)",
        plugin_id,
        action or "execute",
        required,
    )
    return False


def refuse_unauthorized(
    plugin_id: str,
    granted: frozenset[str],
    required: Permission | str,
    action: str = "",
) -> None:
    if not authorize_plugin_action(plugin_id, granted, required, action=action):
        raise PermissionError(
            f"Plugin '{plugin_id}' lacks '{required}' permission for {action or 'this action'}"
        )
