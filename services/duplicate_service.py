"""
MP3 Organizer — Duplicate Detection Service  (MD5 hash-based)
"""
from PyQt6.QtCore import QThread, pyqtSignal
from database.db_manager import DatabaseManager
from scanner.metadata import get_file_hash
from database.models import Track


class DuplicateScanThread(QThread):
    """
    Re-computes file hashes for all tracks missing a hash, then finds duplicates.

    Signals
    -------
    progress(current, total)
    completed(groups)   – list of lists of Track objects
    error(str)
    """
    progress  = pyqtSignal(int, int)
    completed = pyqtSignal(list)
    error     = pyqtSignal(str)

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db

    def run(self):
        try:
            # ── Hash any un-hashed tracks ─────────────────────────────────
            tracks_no_hash = list(Track.select().where(Track.file_hash.is_null(True)))
            total_rehash   = len(tracks_no_hash)

            for i, track in enumerate(tracks_no_hash):
                self.progress.emit(i + 1, total_rehash)
                try:
                    import os
                    if os.path.exists(track.file_path):
                        track.file_hash = get_file_hash(track.file_path)
                        track.save()
                except Exception:
                    pass

            # ── Find duplicates ────────────────────────────────────────────
            dup_map = self.db.find_duplicate_hashes()
            groups  = list(dup_map.values())

            self.completed.emit(groups)

        except Exception as e:
            self.error.emit(str(e))
