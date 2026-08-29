"""
MP3 Organizer — File System Watcher  (Watchdog)
Monitors a folder for new/deleted audio files and emits Qt signals.
"""
import os
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import SUPPORTED_EXTENSIONS


class _MP3EventHandler(FileSystemEventHandler):
    """Bridge between watchdog callbacks (background thread) and Qt signals."""

    def __init__(self, signals):
        super().__init__()
        self._signals = signals

    def on_created(self, event):
        if not event.is_directory:
            path = event.src_path
            if Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
                self._signals.file_added.emit(path)

    def on_deleted(self, event):
        if not event.is_directory:
            path = event.src_path
            if Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
                self._signals.file_removed.emit(path)

    def on_moved(self, event):
        if not event.is_directory:
            src  = event.src_path
            dest = event.dest_path
            if Path(src).suffix.lower() in SUPPORTED_EXTENSIONS:
                self._signals.file_removed.emit(src)
            if Path(dest).suffix.lower() in SUPPORTED_EXTENSIONS:
                self._signals.file_added.emit(dest)


class _WatcherSignals(QObject):
    file_added   = pyqtSignal(str)  # absolute path
    file_removed = pyqtSignal(str)


class FolderWatcher:
    """
    Wraps a Watchdog observer to watch a single folder recursively.

    Usage:
        watcher = FolderWatcher(folder_path)
        watcher.file_added.connect(handler)
        watcher.file_removed.connect(handler)
        watcher.start()
        ...
        watcher.stop()
    """

    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self._signals    = _WatcherSignals()
        self._handler    = _MP3EventHandler(self._signals)
        self._observer   = Observer()
        self._observer.schedule(self._handler, self.folder_path, recursive=True)

    @property
    def file_added(self):
        return self._signals.file_added

    @property
    def file_removed(self):
        return self._signals.file_removed

    def start(self):
        if not self._observer.is_alive():
            self._observer.start()

    def stop(self):
        if self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=2)
