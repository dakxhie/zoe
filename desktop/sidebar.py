"""Application sidebar navigation."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class Sidebar(QWidget):
    """Primary navigation sidebar."""

    action_triggered = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(180)
        self.setMaximumWidth(280)

        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(self._layout.AlignmentFlag.AlignTop)

        self._toggle_btn = QPushButton("Collapse")
        self._toggle_btn.setObjectName("secondary")
        self._toggle_btn.clicked.connect(self._toggle)
        self._layout.addWidget(self._toggle_btn)

        self._buttons: list[QPushButton] = []
        for key, label in (
            ("new_chat", "New Chat"),
            ("history", "Conversation History"),
            ("memory", "Memory"),
            ("notes", "Notes"),
            ("pdfs", "PDFs"),
            ("code", "Code Projects"),
            ("images", "Images"),
            ("index", "Index Manager"),
            ("doctor", "Doctor"),
            ("settings", "Settings"),
            ("about", "About"),
        ):
            button = QPushButton(label)
            button.setObjectName("secondary")
            button.clicked.connect(lambda checked=False, k=key: self.action_triggered.emit(k))
            self._buttons.append(button)
            self._layout.addWidget(button)

        self._layout.addStretch()
        self._collapsed = False

    def _toggle(self) -> None:
        self._collapsed = not self._collapsed
        for button in self._buttons:
            button.setVisible(not self._collapsed)
        self._toggle_btn.setText("Expand" if self._collapsed else "Collapse")
