"""
MP3 Organizer — Recursive Folder Scanner  (runs in a QThread)
"""
import os
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from scanner.metadata import read_metadata, get_file_hash
from database.db_manager import DatabaseManager
from config import SUPPORTED_EXTENSIONS


class ScannerThread(QThread):
    """
    Scans a folder recursively for audio files and upserts them in the DB.

    Signals:
        progress(current, total, filename)  – emitted per file
        completed(added, updated, skipped)  – emitted when done
        error(message)                      – emitted on fatal error
    """
    progress  = pyqtSignal(int, int, str)      # current, total, filename
    completed = pyqtSignal(int, int, int)      # added, updated, skipped
    error     = pyqtSignal(str)

    def __init__(self, folder_path: str, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.db          = db
        self._cancel     = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            # ── Discover files ────────────────────────────────────────────
            audio_files = []
            for root, _, files in os.walk(self.folder_path):
                for fname in files:
                    if Path(fname).suffix.lower() in SUPPORTED_EXTENSIONS:
                        audio_files.append(os.path.join(root, fname))

            total   = len(audio_files)
            added   = 0
            updated = 0
            skipped = 0

            # ── Process files ─────────────────────────────────────────────
            for i, file_path in enumerate(audio_files):
                if self._cancel:
                    break

                self.progress.emit(i + 1, total, os.path.basename(file_path))

                try:
                    meta             = read_metadata(file_path)
                    meta['file_hash'] = get_file_hash(file_path)
                    meta['date_added'] = datetime.now()

                    result = self.db.upsert_track(file_path, meta)
                    if result == 'added':
                        added += 1
                    elif result == 'updated':
                        updated += 1
                    else:
                        skipped += 1

                except Exception as e:
                    print(f"[scanner] Error processing '{file_path}': {e}")
                    skipped += 1

            self.completed.emit(added, updated, skipped)

        except Exception as e:
            self.error.emit(str(e))
