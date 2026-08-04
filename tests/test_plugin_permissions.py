"""Plugin permission tests (create only)."""

from __future__ import annotations

from plugins.permissions import Permission, authorize_plugin_action, has_permission


def test_datetime_permission():
    granted = frozenset({Permission.DATETIME.value})
    assert has_permission(granted, Permission.DATETIME)
    assert not has_permission(granted, Permission.MEMORY)


def test_notes_permission_denied_without_grant():
    assert not authorize_plugin_action(
        "ext.notes",
        frozenset(),
        Permission.NOTES,
        action="read",
    )


def test_clipboard_alias():
    granted = frozenset({"clipboard"})
    assert has_permission(granted, Permission.CLIPBOARD)
