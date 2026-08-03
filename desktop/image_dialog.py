"""Image attachment dialog for vision chat."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class ImageDialog(QDialog):
    """Preview an image and optional prompt before sending to vision pipeline."""

    def __init__(self, image_path: str, parent=None) -> None:
        super().__init__(parent)
        self.image_path = image_path
        self.setWindowTitle("Attach Image")

        layout = QVBoxLayout(self)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.preview.setPixmap(pixmap.scaled(480, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.preview.setText(f"Could not preview: {image_path}")
        layout.addWidget(self.preview)

        form = QFormLayout()
        self.path_label = QLineEdit(str(Path(image_path)))
        self.path_label.setReadOnly(True)
        form.addRow("Path", self.path_label)

        self.prompt = QLineEdit()
        self.prompt.setPlaceholderText("Optional question about this image")
        form.addRow("Prompt", self.prompt)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def prompt_text(self) -> str:
        return self.prompt.text().strip()
