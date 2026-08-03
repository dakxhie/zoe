"""Main window for Zoe Desktop (view + controller)."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from conversation.history import load_session
from conversation.session import create_session
from core.config import ROOT
from desktop.chat_widget import ChatWidget
from desktop.history_panel import HistoryPanel
from desktop.image_dialog import ImageDialog
from desktop.input_bar import InputBar
from desktop.preferences import DesktopPreferences
from desktop.settings_dialog import SettingsDialog
from desktop.sidebar import Sidebar
from desktop.status_bar import ZoeStatusBar
from desktop.theme import apply_theme
from desktop.voice_widget import VoiceWidget
from desktop.workers import (
    ChatWorker,
    VisionWorker,
    run_index_code,
    run_index_notes,
    run_index_pdfs,
    run_doctor_report,
    submit_pool,
)

from voice.commands import VoiceAction
from voice.manager import VoiceManager
from voice.settings import VoiceSettings
PDF_SUFFIXES = {".pdf"}
TEXT_SUFFIXES = {".txt", ".md"}


class MainWindow(QMainWindow):
    """Primary Zoe Desktop window."""

    def __init__(self, preferences: DesktopPreferences) -> None:
        super().__init__()
        self.preferences = preferences
        self.setWindowTitle("Zoe Desktop")
        self.setAcceptDrops(True)

        self.chat = ChatWidget()
        self.input_bar = InputBar()
        self.sidebar = Sidebar()
        self.status = ZoeStatusBar()
        self.setStatusBar(self.status)

        self.history_panel = HistoryPanel(preferences)
        self.history_dock = QDockWidget("History", self)
        self.history_dock.setWidget(self.history_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.history_dock)
        self.history_dock.hide()

        splitter = QSplitter()
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.chat)
        splitter.setStretchFactor(1, 1)
        self._splitter = splitter

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(splitter)

        self.voice_settings = VoiceSettings.load()
        self.voice_manager = VoiceManager(self.voice_settings, self)
        self.voice_manager.set_prepare_session(self._ensure_chat_session)
        self.voice_widget = VoiceWidget()
        layout.addWidget(self.voice_widget)

        layout.addWidget(self.input_bar)
        self.setCentralWidget(central)

        self._chat_worker: ChatWorker | None = None
        self._chat_session_ready = False

        self.input_bar.send_requested.connect(self._send_message)
        self.input_bar.attach_image_requested.connect(self._pick_image)
        self.input_bar.clear_requested.connect(self._clear_chat)
        self.input_bar.stop_requested.connect(self._stop_generation)
        self.sidebar.action_triggered.connect(self._handle_sidebar)
        self.history_panel.open_session.connect(self._open_session)

        self.voice_widget.microphone.push_to_talk.connect(self.voice_manager.toggle_push_to_talk)
        self.voice_manager.state_changed.connect(self.voice_widget.set_state)
        self.voice_manager.transcript_ready.connect(self._on_voice_transcript)
        self.voice_manager.response_ready.connect(self._on_voice_response)
        self.voice_manager.error_occurred.connect(self._on_voice_error)
        self.voice_manager.desktop_action_requested.connect(self._on_voice_action)

        QShortcut(QKeySequence(Qt.Key_Space), self, activated=self.voice_manager.toggle_push_to_talk)
        QShortcut(QKeySequence("Ctrl+Shift+V"), self, activated=self._toggle_voice_enabled)
        QShortcut(QKeySequence(Qt.Key_Escape), self, activated=self.voice_manager.cancel_speech)

        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._new_chat)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_history_search)
        QShortcut(QKeySequence("Ctrl+,"), self, activated=self._open_settings)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self._clear_chat)

        geometry = self.preferences.window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        splitter_state = self.preferences.splitter_state()
        if splitter_state:
            splitter.restoreState(splitter_state)

        self.chat.add_message("system", "Welcome to Zoe Desktop. The model loads on your first message.")
        self.status.refresh_counts()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.preferences.set_window_geometry(bytes(self.saveGeometry()))
        self.preferences.set_splitter_state(bytes(self._splitter.saveState()))
        super().closeEvent(event)

    def _ensure_chat_session(self) -> None:
        if self._chat_session_ready:
            return
        from brain.pipeline import _prepare_chat_session

        _prepare_chat_session()
        self._chat_session_ready = True

    def _send_message(self, text: str) -> None:
        self._ensure_chat_session()
        self.chat.add_message("user", text)
        self.chat.show_typing(True)
        self.input_bar.set_enabled(False)
        start = time.perf_counter()
        self._chat_worker = ChatWorker(text, self)
        self._chat_worker.completed.connect(lambda reply: self._on_reply(reply, start))
        self._chat_worker.failed.connect(self._on_worker_failed)
        self._chat_worker.start()

    def _on_reply(self, reply: str, start: float) -> None:
        self.chat.show_typing(False)
        self.input_bar.set_enabled(True)
        self.status.set_response_time(time.perf_counter() - start)
        self.chat.add_message("assistant", reply)
        self.status.refresh_counts()
        self._notify("Response ready", "Zoe finished generating a reply.")

    def _on_worker_failed(self, message: str) -> None:
        self.chat.show_typing(False)
        self.input_bar.set_enabled(True)
        self.chat.add_message("error", message)
        self.status.set_error(message)
        QMessageBox.critical(self, "Operation Failed", message)

    def _stop_generation(self) -> None:
        self.voice_manager.cancel_speech()
        if self._chat_worker and self._chat_worker.isRunning():
            self._chat_worker.cancel()
            self._chat_worker.wait(1000)
            self.chat.add_message("warning", "Generation stopped.")
            self.input_bar.set_enabled(True)
            self.chat.show_typing(False)

    def _pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", str(ROOT), "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self._open_image_dialog(path)

    def _open_image_dialog(self, path: str) -> None:
        dialog = ImageDialog(path, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        prompt = dialog.prompt_text() or f"Explain this image: {path}"
        self._ensure_chat_session()
        self.chat.add_message("user", f"[Image] {path}\n{prompt}")
        self.chat.show_typing(True)
        self.input_bar.set_enabled(False)
        start = time.perf_counter()
        worker = VisionWorker(path, prompt, self)
        worker.completed.connect(lambda reply: self._on_reply(reply, start))
        worker.failed.connect(self._on_worker_failed)
        worker.start()

    def _new_chat(self) -> None:
        create_session()
        self._chat_session_ready = False
        self.chat.clear_messages()
        self.chat.add_message("system", "Started a new chat session.")

    def _clear_chat(self) -> None:
        self.chat.clear_messages()

    def _focus_history_search(self) -> None:
        self.history_dock.show()
        self.history_panel.search.setFocus()

    def _open_session(self, session_id: str) -> None:
        self.chat.clear_messages()
        for message in load_session(session_id):
            role = message.role if message.role in {"user", "assistant", "system"} else "assistant"
            self.chat.add_message(role, message.content)

    def _handle_sidebar(self, action: str) -> None:
        if action == "new_chat":
            self._new_chat()
        elif action == "history":
            self.history_dock.setVisible(not self.history_dock.isVisible())
        elif action == "settings":
            self._open_settings()
        elif action == "about":
            QMessageBox.information(self, "About Zoe", "Zoe Desktop — PySide6 UI over the existing Zoe backend.")
        elif action == "doctor":
            self._show_doctor()
        elif action in {"index", "notes", "pdfs", "code"}:
            self._show_index_manager()
        elif action == "images":
            self._pick_image()
        elif action == "memory":
            self.chat.add_message("tool", 'Ask in chat: "What do you know about me?"')

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.preferences, self, voice_settings=self.voice_settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            from PySide6.QtWidgets import QApplication

            self.voice_settings = dialog.voice_settings
            self.voice_manager.refresh_settings(self.voice_settings)
            apply_theme(QApplication.instance(), self.preferences.theme())

    def _toggle_voice_enabled(self) -> None:
        self.voice_settings.enabled = not self.voice_settings.enabled
        self.voice_settings.save()
        self.voice_manager.refresh_settings(self.voice_settings)
        state = "enabled" if self.voice_settings.enabled else "disabled"
        self.chat.add_message("system", f"Voice {state}.")

    def _on_voice_transcript(self, text: str, confidence: float) -> None:
        self.chat.add_message("user", text)
        self.chat.show_typing(True)

    def _on_voice_response(self, text: str) -> None:
        self.chat.show_typing(False)
        self.chat.add_message("assistant", text)
        self.status.refresh_counts()

    def _on_voice_error(self, message: str) -> None:
        self.chat.show_typing(False)
        self.chat.add_message("warning", message)

    def _on_voice_action(self, action: VoiceAction) -> None:
        if action == VoiceAction.OPEN_SETTINGS:
            self._open_settings()
        elif action == VoiceAction.CLEAR_CHAT:
            self._clear_chat()
        elif action == VoiceAction.RUN_DOCTOR:
            self._show_doctor()
        elif action == VoiceAction.INDEX_PDFS:
            submit_pool("pdf-index", run_index_pdfs)
        elif action == VoiceAction.INDEX_NOTES:
            submit_pool("notes-index", run_index_notes)
        elif action == VoiceAction.ANALYZE_PROJECT:
            self._send_message("Analyze this Python project and tell me how to improve it.")

    def _show_doctor(self) -> None:
        worker = submit_pool("doctor", run_doctor_report)

        def render_report(result) -> None:
            dialog = QDialog(self)
            dialog.setWindowTitle("System Doctor")
            dialog.resize(720, 560)
            layout = QVBoxLayout(dialog)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            container = QWidget()
            container_layout = QVBoxLayout(container)
            report = result.data
            for check in report.checks:
                card = QFrame()
                card.setFrameShape(QFrame.StyledPanel)
                color = {"PASS": "#065f46", "WARN": "#92400e", "FAIL": "#991b1b"}.get(check.status.value, "#374151")
                card.setStyleSheet(f"border-left: 6px solid {color}; margin: 4px; padding: 8px;")
                card_layout = QVBoxLayout(card)
                card_layout.addWidget(QLabel(f"{check.name} — {check.status.value}"))
                for detail in check.details[:6]:
                    card_layout.addWidget(QLabel(detail))
                container_layout.addWidget(card)
            scroll.setWidget(container)
            layout.addWidget(scroll)
            close = QDialogButtonBox(QDialogButtonBox.Close)
            close.rejected.connect(dialog.reject)
            layout.addWidget(close)
            dialog.exec()

        worker.signals.finished.connect(render_report)
        worker.signals.failed.connect(lambda msg: QMessageBox.critical(self, "Doctor failed", msg))

    def _show_index_manager(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Index Manager")
        layout = QVBoxLayout(dialog)
        output = QLabel("Ready.")
        layout.addWidget(output)

        def _run(name: str, fn, label: str) -> None:
            worker = submit_pool(name, fn)

            def _done(result) -> None:
                output.setText(f"{label}: {result.data}")
                self.status.refresh_counts()
                self._notify("Indexing complete", f"{name} finished.")

            worker.signals.finished.connect(_done)
            worker.signals.failed.connect(lambda msg: QMessageBox.critical(dialog, "Index failed", msg))

        notes_btn = QPushButton("Index Notes")
        notes_btn.clicked.connect(lambda: _run("notes", run_index_notes, "Indexed notes"))
        layout.addWidget(notes_btn)
        pdf_btn = QPushButton("Index PDFs")
        pdf_btn.clicked.connect(lambda: _run("pdfs", run_index_pdfs, "Indexed PDF chunks"))
        layout.addWidget(pdf_btn)
        code_btn = QPushButton("Index Project")
        code_btn.clicked.connect(lambda: _run("code", lambda: run_index_code(str(ROOT)), "Indexed project"))
        layout.addWidget(code_btn)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(lambda: (self.status.refresh_counts(), output.setText("Counts refreshed.")))
        layout.addWidget(refresh_btn)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)
        dialog.exec()

    def _notify(self, title: str, message: str) -> None:
        self.status.showMessage(message, 5000)
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray = QSystemTrayIcon(self)
            tray.showMessage(title, message)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            suffix = path.suffix.lower()
            if suffix in IMAGE_SUFFIXES:
                self._open_image_dialog(str(path))
            elif suffix in PDF_SUFFIXES:
                if QMessageBox.question(self, "Index PDF", f"Index '{path.name}'?") == QMessageBox.Yes:
                    submit_pool("pdf-index", run_index_pdfs)
            elif suffix in TEXT_SUFFIXES:
                if QMessageBox.question(self, "Notes", f"Ingest '{path.name}' into notes?") == QMessageBox.Yes:
                    dest = ROOT / self.preferences.default_notes_folder() / path.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
                    submit_pool("notes-index", run_index_notes)
