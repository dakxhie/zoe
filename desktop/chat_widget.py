"""Scrollable chat area with message bubbles."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from desktop.message_bubble import MessageBubble


class ChatWidget(QScrollArea):
    """Chat transcript view."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setAlignment(Qt.AlignTop)
        self.setWidget(self._container)

        self._typing_label = QLabel("Zoe is thinking...")
        self._typing_label.setStyleSheet("color: #94a3b8; font-style: italic; padding: 8px;")
        self._typing_label.hide()

    def add_message(self, role: str, content: str) -> None:
        bubble = MessageBubble(role, content)
        self._layout.addWidget(bubble)
        self._scroll_to_bottom()

    def show_typing(self, visible: bool) -> None:
        if visible:
            if self._typing_label.parent() is None:
                self._layout.addWidget(self._typing_label)
            self._typing_label.show()
        else:
            self._typing_label.hide()
        self._scroll_to_bottom()

    def clear_messages(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _scroll_to_bottom(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())
