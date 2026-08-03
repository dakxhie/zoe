"""Conversation history panel backed by Sprint 11 storage."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from conversation.history import all_sessions, load_session, restore_message_cache
from conversation.storage import load_all_messages, write_messages
from desktop.preferences import DesktopPreferences


@dataclass
class SessionRow:
    """One row in the history list."""

    session_id: str
    title: str
    preview: str
    message_count: int


def build_session_rows(preferences: DesktopPreferences) -> list[SessionRow]:
    """Build session metadata from persisted history."""
    rows: list[SessionRow] = []
    for session_id in all_sessions():
        messages = load_session(session_id)
        if not messages:
            continue
        title = preferences.session_title(session_id) or f"Session {session_id[:8]}"
        preview = messages[-1].content[:120]
        rows.append(SessionRow(session_id, title, preview, len(messages)))
    rows.sort(key=lambda row: row.title.lower())
    return rows


def delete_session(session_id: str) -> None:
    """Remove one session from persisted history using storage APIs."""
    remaining = [message for message in load_all_messages() if message.session != session_id]
    write_messages(remaining)
    restore_message_cache()


class HistoryPanel(QWidget):
    """Dockable history browser with search and session actions."""

    open_session = Signal(str)
    refresh_requested = Signal()

    def __init__(self, preferences: DesktopPreferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.preferences = preferences

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Conversation History"))

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search conversations...")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._open_selected)
        layout.addWidget(self.list)

        actions = QHBoxLayout()
        self.open_btn = QPushButton("Open")
        self.open_btn.clicked.connect(self._open_selected)
        actions.addWidget(self.open_btn)

        self.rename_btn = QPushButton("Rename")
        self.rename_btn.clicked.connect(self._rename_selected)
        actions.addWidget(self.rename_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_selected)
        actions.addWidget(self.delete_btn)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        actions.addWidget(self.refresh_btn)
        layout.addLayout(actions)

        self._rows: list[SessionRow] = []
        self.refresh()

    def refresh(self) -> None:
        self._rows = build_session_rows(self.preferences)
        self._render(self._rows)
        self.refresh_requested.emit()

    def _render(self, rows: list[SessionRow]) -> None:
        self.list.clear()
        for row in rows:
            item = QListWidgetItem(f"{row.title}\n{row.preview}")
            item.setData(Qt.UserRole, row.session_id)
            self.list.addItem(item)

    def _selected_session_id(self) -> str | None:
        item = self.list.currentItem()
        if item is None:
            return None
        return str(item.data(Qt.UserRole))

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        if not needle:
            self._render(self._rows)
            return
        filtered = [
            row
            for row in self._rows
            if needle in row.title.lower() or needle in row.preview.lower()
        ]
        self._render(filtered)

    def _open_selected(self) -> None:
        session_id = self._selected_session_id()
        if session_id:
            self.open_session.emit(session_id)

    def _rename_selected(self) -> None:
        session_id = self._selected_session_id()
        if not session_id:
            return
        current = self.preferences.session_title(session_id) or session_id
        title, ok = QInputDialog.getText(self, "Rename Conversation", "Title:", text=current)
        if ok and title.strip():
            self.preferences.set_session_title(session_id, title.strip())
            self.refresh()

    def _delete_selected(self) -> None:
        session_id = self._selected_session_id()
        if not session_id:
            return
        answer = QMessageBox.question(self, "Delete Conversation", "Delete this session permanently?")
        if answer != QMessageBox.Yes:
            return
        delete_session(session_id)
        self.refresh()
