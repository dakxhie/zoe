"""Zoe Desktop entrypoint: python desktop/app.py"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QSplashScreen

from core.logging_config import configure_logging
from desktop.main_window import MainWindow
from desktop.preferences import DesktopPreferences
from desktop.theme import apply_theme
from desktop.workers import StartupWorker


def main() -> int:
    """Launch Zoe Desktop."""
    configure_logging()
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setApplicationName("Zoe Desktop")
    app.setOrganizationName("ZoeAI")

    preferences = DesktopPreferences()
    apply_theme(app, preferences.theme())

    splash = QSplashScreen()
    splash.showMessage("Starting Zoe Desktop...", Qt.AlignBottom | Qt.AlignCenter)
    splash.show()
    app.processEvents()

    startup = StartupWorker()

    def on_line(line: str) -> None:
        splash.showMessage(line, Qt.AlignBottom | Qt.AlignCenter)
        app.processEvents()

    def on_finished(_lines: list[str]) -> None:
        window = MainWindow(preferences)
        geometry = preferences.window_geometry()
        if geometry:
            window.restoreGeometry(geometry)
        window.show()
        splash.finish(window)

    startup.line_ready.connect(on_line)
    startup.finished_ok.connect(on_finished)
    startup.start()

    logging.getLogger(__name__).info("Zoe Desktop started")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
