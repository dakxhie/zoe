"""Settings and preferences tests."""

from __future__ import annotations

from desktop.preferences import DesktopPreferences


def test_preferences_defaults() -> None:
    """Desktop preferences expose sane defaults."""
    prefs = DesktopPreferences()
    assert prefs.theme() in {"system", "dark", "light"}
    assert prefs.context_size() >= 1000
    assert prefs.memory_limit() >= 5
    assert prefs.default_notes_folder()


def test_preferences_roundtrip(tmp_path, qapp) -> None:
    """Preferences persist values via QSettings."""
    from PySide6.QtCore import QSettings

    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    prefs = DesktopPreferences()
    prefs.set_theme("dark")
    prefs.set_context_size(7000)
    prefs.set_session_title("session-1", "My chat")

    reloaded = DesktopPreferences()
    assert reloaded.theme() == "dark"
    assert reloaded.context_size() == 7000
    assert reloaded.session_title("session-1") == "My chat"
