"""
MP3 Organizer — Application Entry Point
"""
import sys
import os

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow


def main():
    # ── High-DPI support ──────────────────────────────────────────────────────
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("MP3 Organizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("MP3Organizer")

    # ── Default font ──────────────────────────────────────────────────────────
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # ── Launch main window ────────────────────────────────────────────────────
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
