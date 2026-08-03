"""Multiline chat input bar."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget


class InputBar(QWidget):
    """Message input with send/attach/clear/stop controls."""

    send_requested = Signal(str)
    attach_image_requested = Signal()
    clear_requested = Signal()
    stop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Message Zoe... (Enter to send, Shift+Enter for newline)")
        self.editor.setMinimumHeight(80)
        layout.addWidget(self.editor)

        row = QHBoxLayout()
        self.attach_btn = QPushButton("Attach Image")
        self.attach_btn.setObjectName("secondary")
        self.attach_btn.clicked.connect(self.attach_image_requested.emit)
        row.addWidget(self.attach_btn)

        row.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("secondary")
        self.clear_btn.clicked.connect(self.clear_requested.emit)
        row.addWidget(self.clear_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("secondary")
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        row.addWidget(self.stop_btn)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._emit_send)
        row.addWidget(self.send_btn)
        layout.addLayout(row)

        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._emit_send)
        self.editor.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self.editor and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                self._emit_send()
                return True
        return super().eventFilter(obj, event)

    def _emit_send(self) -> None:
        text = self.editor.toPlainText().strip()
        if not text:
            return
        self.send_requested.emit(text)
        self.editor.clear()

    def set_enabled(self, enabled: bool) -> None:
        self.editor.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
        self.attach_btn.setEnabled(enabled)
