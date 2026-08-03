"""Desktop UI preferences (Qt settings), separate from backend config."""

from __future__ import annotations

from PySide6.QtCore import QSettings

ORG = "ZoeAI"
APP = "Desktop"


class DesktopPreferences:
    """Persist window layout, theme, and session display metadata."""

    def __init__(self) -> None:
        self._settings = QSettings(ORG, APP)

    def window_geometry(self) -> bytes | None:
        value = self._settings.value("window/geometry")
        return value if isinstance(value, (bytes, bytearray)) else None

    def set_window_geometry(self, data: bytes) -> None:
        self._settings.setValue("window/geometry", data)

    def splitter_state(self) -> bytes | None:
        value = self._settings.value("window/splitter")
        return value if isinstance(value, (bytes, bytearray)) else None

    def set_splitter_state(self, data: bytes) -> None:
        self._settings.setValue("window/splitter", data)

    def theme(self) -> str:
        return str(self._settings.value("ui/theme", "system"))

    def set_theme(self, theme: str) -> None:
        self._settings.setValue("ui/theme", theme)

    def sidebar_collapsed(self) -> bool:
        return str(self._settings.value("ui/sidebar_collapsed", "false")).lower() == "true"

    def set_sidebar_collapsed(self, collapsed: bool) -> None:
        self._settings.setValue("ui/sidebar_collapsed", collapsed)

    def session_title(self, session_id: str) -> str:
        return str(self._settings.value(f"sessions/{session_id}/title", ""))

    def set_session_title(self, session_id: str, title: str) -> None:
        self._settings.setValue(f"sessions/{session_id}/title", title)

    def context_size(self) -> int:
        return int(self._settings.value("chat/context_size", 6000))

    def set_context_size(self, size: int) -> None:
        self._settings.setValue("chat/context_size", size)

    def memory_limit(self) -> int:
        return int(self._settings.value("chat/memory_limit", 20))

    def set_memory_limit(self, limit: int) -> None:
        self._settings.setValue("chat/memory_limit", limit)

    def log_level(self) -> str:
        return str(self._settings.value("logging/level", "INFO"))

    def set_log_level(self, level: str) -> None:
        self._settings.setValue("logging/level", level)

    def default_notes_folder(self) -> str:
        return str(self._settings.value("paths/notes", "data/notes"))

    def set_default_notes_folder(self, path: str) -> None:
        self._settings.setValue("paths/notes", path)

    def default_pdf_folder(self) -> str:
        return str(self._settings.value("paths/pdfs", "data/pdfs"))

    def set_default_pdf_folder(self, path: str) -> None:
        self._settings.setValue("paths/pdfs", path)

    def default_code_folder(self) -> str:
        return str(self._settings.value("paths/code", "data/code"))

    def set_default_code_folder(self, path: str) -> None:
        self._settings.setValue("paths/code", path)
