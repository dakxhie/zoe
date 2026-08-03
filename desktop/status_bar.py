"""Application status bar with backend index counts."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar


class ZoeStatusBar(QStatusBar):
    """Status bar showing model, index counts, device, and response time."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.model_label = QLabel("Model: —")
        self.memory_label = QLabel("Memory: 0")
        self.notes_label = QLabel("Notes: 0")
        self.pdf_label = QLabel("PDF: 0")
        self.code_label = QLabel("Code: 0")
        self.device_label = QLabel("Device: CPU")
        self.time_label = QLabel("Response: —")
        self.error_label = QLabel("")

        for widget in (
            self.model_label,
            self.memory_label,
            self.notes_label,
            self.pdf_label,
            self.code_label,
            self.device_label,
            self.time_label,
            self.error_label,
        ):
            self.addPermanentWidget(widget)

    def refresh_counts(self) -> None:
        """Pull latest counts from existing backend helpers."""
        try:
            from core.chroma import collection_count
            from core.config import load_settings
            from core.index_status import COLLECTION_CODE, COLLECTION_MEMORY, COLLECTION_NOTES, COLLECTION_PDF

            self.model_label.setText(f"Model: {load_settings().get('MODEL_NAME', '—')}")
            self.memory_label.setText(f"Memory: {collection_count(COLLECTION_MEMORY)}")
            self.notes_label.setText(f"Notes: {collection_count(COLLECTION_NOTES)}")
            self.pdf_label.setText(f"PDF: {collection_count(COLLECTION_PDF)}")
            self.code_label.setText(f"Code: {collection_count(COLLECTION_CODE)}")
        except Exception as exc:
            self.error_label.setText(str(exc))

        try:
            import torch

            device = "GPU" if torch.cuda.is_available() else "CPU"
            self.device_label.setText(f"Device: {device}")
        except Exception:
            self.device_label.setText("Device: CPU")

    def set_response_time(self, seconds: float | None) -> None:
        if seconds is None:
            self.time_label.setText("Response: —")
        else:
            self.time_label.setText(f"Response: {seconds:.2f}s")

    def set_error(self, message: str) -> None:
        self.error_label.setText(message)
