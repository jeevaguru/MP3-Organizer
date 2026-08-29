"""
MP3 Organizer — Scan Dialog
Progress dialog for folder scanning with folder picker.
"""
import os
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QFileDialog, QLineEdit, QFrame, QSizePolicy,
    QCheckBox
)
from PyQt6.QtGui import QFont

from scanner.scanner import ScannerThread
from database.db_manager import DatabaseManager


class ScanDialog(QDialog):
    scan_completed = pyqtSignal()   # Emitted when scan finishes

    def __init__(self, db: DatabaseManager, initial_path: str = None, parent=None):
        super().__init__(parent)
        self.db      = db
        self._thread = None
        self.setWindowTitle("Scan Music Folder")
        self.setMinimumWidth(520)
        self.setModal(True)
        self._build_ui()
        if initial_path:
            self.folder_edit.setText(initial_path)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        title = QLabel("Scan Music Folder")
        title.setStyleSheet("font-size:17px;font-weight:700;")
        layout.addWidget(title)

        subtitle = QLabel("Select a folder to scan for audio files. All sub-folders will be included.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#8b949e;font-size:12px;")
        layout.addWidget(subtitle)

        # Separator
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # Folder picker row
        folder_label = QLabel("Folder")
        folder_label.setStyleSheet("font-weight:600;font-size:12px;")
        layout.addWidget(folder_label)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Choose a folder…")
        folder_row.addWidget(self.folder_edit, 1)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._browse)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        # Auto-watch checkbox
        self.watch_cb = QCheckBox("Auto-watch this folder for new/removed files")
        layout.addWidget(self.watch_cb)

        # Progress section (hidden until scan starts)
        self.progress_frame = QFrame()
        pf_layout = QVBoxLayout(self.progress_frame)
        pf_layout.setContentsMargins(0, 0, 0, 0)
        pf_layout.setSpacing(6)

        self.status_label = QLabel("Preparing…")
        self.status_label.setStyleSheet("color:#8b949e;font-size:12px;")
        pf_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        pf_layout.addWidget(self.progress_bar)

        self.file_label = QLabel("")
        self.file_label.setStyleSheet("color:#6e7681;font-size:11px;")
        self.file_label.setWordWrap(True)
        pf_layout.addWidget(self.file_label)

        self.progress_frame.setVisible(False)
        layout.addWidget(self.progress_frame)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self.cancel_btn)

        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.setObjectName("accent_btn")
        self.scan_btn.clicked.connect(self._start_scan)
        btn_row.addWidget(self.scan_btn)

        layout.addLayout(btn_row)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Music Folder", "")
        if folder:
            self.folder_edit.setText(folder)

    def _start_scan(self):
        folder = self.folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            self.status_label.setText("⚠ Please select a valid folder.")
            self.progress_frame.setVisible(True)
            return

        self.scan_btn.setEnabled(False)
        self.folder_edit.setEnabled(False)
        self.progress_frame.setVisible(True)
        self.status_label.setText("Scanning…")
        self.progress_bar.setRange(0, 0)   # indeterminate initially

        auto_watch = self.watch_cb.isChecked()
        self.db.add_scan_folder(folder, auto_watch)

        self._thread = ScannerThread(folder, self.db, self)
        self._thread.progress.connect(self._on_progress)
        self._thread.completed.connect(self._on_completed)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_progress(self, current: int, total: int, filename: str):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        pct = int(current / total * 100) if total else 0
        self.status_label.setText(f"Scanning… {current}/{total} files ({pct}%)")
        # Truncate long filenames
        short = filename if len(filename) <= 60 else "…" + filename[-57:]
        self.file_label.setText(short)

    def _on_completed(self, added: int, updated: int, skipped: int):
        self.status_label.setText(
            f"✔  Done! Added {added}, updated {updated}, skipped {skipped}."
        )
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.file_label.setText("")
        self.scan_btn.setText("Scan Again")
        self.scan_btn.setEnabled(True)
        self.folder_edit.setEnabled(True)
        self.cancel_btn.setText("Close")
        self.scan_completed.emit()

    def _on_error(self, message: str):
        self.status_label.setText(f"⚠ Error: {message}")
        self.scan_btn.setEnabled(True)
        self.folder_edit.setEnabled(True)

    def _cancel(self):
        if self._thread and self._thread.isRunning():
            self._thread.cancel()
            self._thread.wait(2000)
        self.reject()
