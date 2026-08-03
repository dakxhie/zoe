"""Chat message bubble widget with Markdown rendering."""

from __future__ import annotations

import re

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from desktop.theme import BUBBLE_COLORS

MESSAGE_LABELS = {
    "user": "You",
    "assistant": "Zoe",
    "tool": "Tool",
    "warning": "Warning",
    "error": "Error",
    "thinking": "Thinking",
    "system": "System",
}


class MessageBubble(QWidget):
    """One chat message with role styling and Markdown content."""

    def __init__(self, role: str, content: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.role = role if role in BUBBLE_COLORS else "assistant"

        bg, fg = BUBBLE_COLORS[self.role]
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)

        header_row = QHBoxLayout()
        header = QLabel(MESSAGE_LABELS.get(self.role, self.role.title()))
        header.setStyleSheet(f"color: {fg}; font-weight: 600;")
        header_row.addWidget(header)
        header_row.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("secondary")
        copy_btn.clicked.connect(self._copy_content)
        header_row.addWidget(copy_btn)
        root.addLayout(header_row)

        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setReadOnly(True)
        self.browser.setFrameShape(QTextBrowser.NoFrame)
        self.browser.document().setDefaultFont(QFont("Segoe UI", 10))
        self.browser.setStyleSheet(
            f"background-color: {bg}; color: {fg}; border-radius: 12px; padding: 10px;"
        )
        markdown = content
        if self._looks_like_project_report(content):
            markdown = self._project_report_markdown(content)
        self.browser.setMarkdown(self._normalize_markdown(markdown))
        self.browser.setMinimumHeight(40)
        root.addWidget(self.browser)

    def _copy_content(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.browser.toPlainText())

    @staticmethod
    def _normalize_markdown(content: str) -> str:
        return content.strip()

    @staticmethod
    def _looks_like_project_report(content: str) -> bool:
        markers = ("Structured Report:", "Project Analysis", "Complexity hotspots:")
        return any(marker in content for marker in markers)

    @staticmethod
    def _project_report_markdown(content: str) -> str:
        bullets: list[str] = []
        for line in content.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key in {
                "Language",
                "Framework",
                "Architecture",
                "Build system",
                "Test framework",
                "Dependency manager",
                "Folder structure",
                "Config files",
                "Entry points",
                "Large files",
                "Complexity hotspots",
                "Dead code candidates",
            }:
                bullets.append(f"- **{key}:** {value}")
        if bullets:
            return "## Project Analysis\n\n" + "\n".join(bullets)
        return content

    @staticmethod
    def extract_code_blocks(text: str) -> list[str]:
        return re.findall(r"```[\w]*\n(.*?)```", text, flags=re.DOTALL)
