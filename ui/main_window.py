"""
MP3 Organizer — Main Window
Orchestrates all UI components and application logic.
"""
import os
from pathlib import Path

from PyQt6.QtCore import Qt, QSettings, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QFileDialog, QMessageBox, QStatusBar, QLabel
)
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut

from config import (
    APP_NAME, APP_VERSION, SETTINGS_ORG, SETTINGS_APP,
    SIDEBAR_WIDTH, NOW_PLAYING_WIDTH, PLAYER_BAR_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT,
)
from database.db_manager import DatabaseManager
from player.audio_player import AudioPlayer, VLC_AVAILABLE
from services.lyrics_service import LyricsService
from services.artwork_service import ArtworkService
from scanner.watcher import FolderWatcher

from ui.sidebar_widget import SidebarWidget
from ui.library_view import LibraryView
from ui.player_widget import PlayerWidget
from ui.now_playing_panel import NowPlayingPanel
from ui.scan_dialog import ScanDialog
from ui.tag_editor_dialog import TagEditorDialog
from ui.equalizer_dialog import EqualizerDialog
from ui.duplicate_finder_dialog import DuplicateFinderDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        # ── Core services ─────────────────────────────────────────────────
        self.settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._theme   = self.settings.value("theme", "dark")

        self.db              = DatabaseManager()
        self.player          = AudioPlayer(self)
        self.lyrics_service  = LyricsService()
        self.artwork_service = ArtworkService()
        self._watchers: list[FolderWatcher] = []

        # ── UI ────────────────────────────────────────────────────────────
        self._build_ui()
        self._setup_shortcuts()
        self._connect_signals()

        # ── Apply theme & restore state ────────────────────────────────────
        self.apply_theme(self._theme)
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        # ── Load library & start watchers ──────────────────────────────────
        self._refresh_library()
        self._start_watchers()

        # Status bar
        if not VLC_AVAILABLE:
            self.statusBar().showMessage(
                "⚠ VLC not found — playing without equalizer (QtMultimedia fallback). "
                "Install 64-bit VLC for full features.", 0
            )

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Content area ───────────────────────────────────────────────────
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        self.sidebar = SidebarWidget(self.db)
        content_layout.addWidget(self.sidebar)

        # Library
        self.library_view = LibraryView(self.db)
        content_layout.addWidget(self.library_view, 1)

        # Now Playing
        self.now_playing = NowPlayingPanel(self.lyrics_service, self.artwork_service)
        self.now_playing.setFixedWidth(NOW_PLAYING_WIDTH)
        content_layout.addWidget(self.now_playing)

        root.addWidget(content, 1)

        # ── Player bar ─────────────────────────────────────────────────────
        self.player_widget = PlayerWidget(self.player)
        root.addWidget(self.player_widget)

        # ── Status bar ────────────────────────────────────────────────────
        self.setStatusBar(QStatusBar(self))

    # ── Shortcuts ─────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        # Space = play/pause
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self.player.toggle_play_pause)
        # Left/Right arrow = seek ±5 s
        QShortcut(QKeySequence(Qt.Key.Key_Right), self,
                  lambda: self.player.seek(self.player.get_position() + 5000))
        QShortcut(QKeySequence(Qt.Key.Key_Left),  self,
                  lambda: self.player.seek(self.player.get_position() - 5000))
        # Ctrl+F = focus search
        QShortcut(QKeySequence("Ctrl+F"), self, self.library_view.search_edit.setFocus)

    # ── Signal connections ────────────────────────────────────────────────────

    def _connect_signals(self):
        # Library → Player
        self.library_view.track_double_clicked.connect(self._play_track)
        self.library_view.add_to_queue_requested.connect(self._add_to_queue)
        self.library_view.tag_edit_requested.connect(self._open_tag_editor)

        # Player events → UI updates
        self.player.track_changed.connect(self._on_track_changed)
        self.player.state_changed.connect(self.player_widget.set_state)
        self.player.position_changed.connect(self.player_widget.set_position)
        self.player.position_changed.connect(self.now_playing.update_position)
        self.player.duration_changed.connect(self.player_widget.set_duration)
        self.player.volume_changed.connect(self.player_widget.set_volume)

        # Player widget → Player
        self.player_widget.play_pause_clicked.connect(self.player.toggle_play_pause)
        self.player_widget.next_clicked.connect(self.player.next)
        self.player_widget.prev_clicked.connect(self.player.prev)
        self.player_widget.seek_requested.connect(self.player.seek)
        self.player_widget.volume_changed.connect(self.player.set_volume)
        self.player_widget.eq_clicked.connect(self._open_equalizer)
        self.player_widget.shuffle_clicked.connect(self.player.set_shuffle)
        self.player_widget.repeat_clicked.connect(self.player.set_repeat)

        # Sidebar
        self.sidebar.scan_requested.connect(self._open_scan_dialog)
        self.sidebar.nav_changed.connect(self._on_nav_changed)
        self.sidebar.playlist_selected.connect(self.library_view.show_playlist)
        self.sidebar.duplicate_finder_requested.connect(self._open_duplicate_finder)
        self.sidebar.export_requested.connect(self._export_library)
        self.sidebar.theme_toggle_requested.connect(self._toggle_theme)

    # ── Player handlers ───────────────────────────────────────────────────────

    def _play_track(self, track_id: int):
        """Play the clicked track, using the visible library as the queue."""
        tracks = self.library_view.get_visible_tracks()
        idx    = next((i for i, t in enumerate(tracks) if t.id == track_id), 0)
        self.player.set_queue(tracks, idx)
        self.db.increment_play_count(track_id)

    def _add_to_queue(self, track_ids: list):
        tracks = [self.db.get_track(tid) for tid in track_ids if self.db.get_track(tid)]
        self.player.add_to_queue(tracks)
        self.statusBar().showMessage(f"Added {len(tracks)} track(s) to queue.", 3000)

    def _on_track_changed(self, track):
        """Update all UI surfaces when the player switches tracks."""
        self.player_widget.set_track(track)
        self.now_playing.set_track(track)
        self.library_view.set_playing(track.id)
        self.setWindowTitle(f"{track.display_title()} — {APP_NAME}")
        self.db.increment_play_count(track.id)

    # ── Dialogs ───────────────────────────────────────────────────────────────

    def _open_scan_dialog(self, folder_path: str = ''):
        dlg = ScanDialog(self.db, folder_path or None, self)
        dlg.scan_completed.connect(self._on_scan_completed)
        dlg.exec()

    def _on_scan_completed(self):
        self._refresh_library()
        self._start_watchers()   # Pick up any newly added watched folders
        self.statusBar().showMessage("Library updated.", 3000)

    def _open_tag_editor(self, track_id: int):
        track = self.db.get_track(track_id)
        if not track:
            return
        dlg = TagEditorDialog(track, self.artwork_service, self.db, self)
        if dlg.exec():
            self._refresh_library()
            # If editing the currently playing track, update displays
            if self.player.current_track and self.player.current_track.id == track_id:
                updated = self.db.get_track(track_id)
                if updated:
                    self.player_widget.set_track(updated)
                    self.now_playing.set_track(updated)

    def _open_equalizer(self):
        dlg = EqualizerDialog(self.player, self.settings, self)
        dlg.exec()

    def _open_duplicate_finder(self):
        dlg = DuplicateFinderDialog(self.db, self)
        dlg.exec()
        self._refresh_library()

    # ── Sidebar handlers ──────────────────────────────────────────────────────

    def _on_nav_changed(self, key: str):
        if key == 'library':
            self._refresh_library()

    def _toggle_theme(self):
        self._theme = 'light' if self._theme == 'dark' else 'dark'
        self.apply_theme(self._theme)
        self.settings.setValue("theme", self._theme)

    def apply_theme(self, theme: str):
        style_path = Path(__file__).parent / 'styles' / f'{theme}.qss'
        try:
            with open(style_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass
        self.sidebar.set_theme(theme)

    def _export_library(self, fmt: str):
        exts = {'csv': 'CSV Files (*.csv)', 'json': 'JSON Files (*.json)'}
        default_names = {'csv': 'library.csv', 'json': 'library.json'}
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Library", default_names[fmt], exts[fmt]
        )
        if path:
            tracks = self.library_view.get_visible_tracks()
            self.db.export_library(tracks, path, fmt)
            self.statusBar().showMessage(f"Exported {len(tracks)} tracks to {path}", 4000)

    # ── Library ───────────────────────────────────────────────────────────────

    def _refresh_library(self):
        tracks = self.db.get_all_tracks()
        self.library_view.set_tracks(tracks)
        self.sidebar.update_stats(len(tracks))
        self.sidebar.refresh_playlists()

    # ── File Watchers ─────────────────────────────────────────────────────────

    def _start_watchers(self):
        # Stop existing watchers
        for w in self._watchers:
            w.stop()
        self._watchers.clear()

        for folder in self.db.get_scan_folders():
            if folder.auto_watch and os.path.isdir(folder.path):
                w = FolderWatcher(folder.path)
                w.file_added.connect(self._on_file_added)
                w.file_removed.connect(self._on_file_removed)
                w.start()
                self._watchers.append(w)

    def _on_file_added(self, file_path: str):
        """Called from watchdog thread — schedule DB update on main thread."""
        QTimer.singleShot(500, lambda: self._handle_new_file(file_path))

    def _on_file_removed(self, file_path: str):
        QTimer.singleShot(100, lambda: self._handle_removed_file(file_path))

    def _handle_new_file(self, file_path: str):
        from scanner.metadata import read_metadata, get_file_hash
        from datetime import datetime
        try:
            meta = read_metadata(file_path)
            meta['file_hash']  = get_file_hash(file_path)
            meta['date_added'] = datetime.now()
            self.db.upsert_track(file_path, meta)
            self._refresh_library()
        except Exception as e:
            print(f"[watcher] Error adding {file_path}: {e}")

    def _handle_removed_file(self, file_path: str):
        self.db.delete_tracks_by_paths([file_path])
        self._refresh_library()

    # ── Close ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        self.player.stop()
        for w in self._watchers:
            w.stop()
        event.accept()
