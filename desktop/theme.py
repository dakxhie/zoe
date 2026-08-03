"""Centralized theming for Zoe Desktop."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

DARK_STYLESHEET = """
QWidget {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
}
QMainWindow, QDialog {
    background-color: #111827;
    color: #e5e7eb;
}
QSplitter::handle {
    background-color: #374151;
    width: 2px;
}
QTextBrowser, QPlainTextEdit, QLineEdit, QListWidget, QTreeWidget {
    background-color: #1f2937;
    color: #f3f4f6;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 8px;
}
QPushButton {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
}
QPushButton:hover { background-color: #1d4ed8; }
QPushButton:disabled { background-color: #4b5563; }
QPushButton#secondary {
    background-color: #374151;
}
QStatusBar {
    background: #0f172a;
    color: #cbd5e1;
}
"""

LIGHT_STYLESHEET = """
QWidget {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
}
QMainWindow, QDialog {
    background-color: #f8fafc;
    color: #0f172a;
}
QSplitter::handle {
    background-color: #cbd5e1;
    width: 2px;
}
QTextBrowser, QPlainTextEdit, QLineEdit, QListWidget, QTreeWidget {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px;
}
QPushButton {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
}
QPushButton:hover { background-color: #1d4ed8; }
QPushButton:disabled { background-color: #94a3b8; }
QPushButton#secondary {
    background-color: #e2e8f0;
    color: #0f172a;
}
QStatusBar {
    background: #e2e8f0;
    color: #334155;
}
"""


def apply_theme(app: QApplication, mode: str) -> None:
    """Apply dark, light, or system theme."""
    resolved = mode
    if mode == "system":
        resolved = "dark" if app.styleHints().colorScheme().name().lower() == "dark" else "light"

    if resolved == "dark":
        app.setStyleSheet(DARK_STYLESHEET)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#111827"))
        palette.setColor(QPalette.WindowText, QColor("#e5e7eb"))
        app.setPalette(palette)
    else:
        app.setStyleSheet(LIGHT_STYLESHEET)
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#f8fafc"))
        palette.setColor(QPalette.WindowText, QColor("#0f172a"))
        app.setPalette(palette)


BUBBLE_COLORS = {
    "user": ("#2563eb", "#ffffff"),
    "assistant": ("#374151", "#f9fafb"),
    "tool": ("#065f46", "#ecfdf5"),
    "warning": ("#92400e", "#fffbeb"),
    "error": ("#991b1b", "#fef2f2"),
    "thinking": ("#4b5563", "#f3f4f6"),
    "system": ("#1e3a8a", "#eff6ff"),
}
