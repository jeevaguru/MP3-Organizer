"""
MP3 Organizer — Sidebar Widget
Navigation, scan folder, playlists, stats.
"""
import json

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QFrame, QHBoxLayout, QInputDialog, QMenu,
    QSizePolicy, QMessageBox
)
from PyQt6.QtGui import QAction

from database.db_manager import DatabaseManager


class SidebarWidget(QWidget):
    # ── Signals ───────────────────────────────────────────────────────────────
    scan_requested             = pyqtSignal(str)   # folder path (or '')
    nav_changed                = pyqtSignal(str)   # 'library' | 'albums' | 'artists'
    playlist_selected          = pyqtSignal(list)  # List[Track]
    duplicate_finder_requested = pyqtSignal()
    export_requested           = pyqtSignal(str)   # 'csv' | 'json'
    theme_toggle_requested     = pyqtSignal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setObjectName("sidebar")
        self.setFixedWidth(220)
        self._build_ui()
        self.refresh_playlists()

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── App logo ───────────────────────────────────────────────────────
        logo_widget = QWidget()
        logo_widget.setStyleSheet("background:transparent;")
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(16, 20, 16, 12)
        logo_layout.setSpacing(2)

        logo = QLabel("🎵 MP3 Organizer")
        logo.setObjectName("app_logo_label")
        logo_layout.addWidget(logo)

        self.stats_label = QLabel("0 tracks")
        self.stats_label.setObjectName("sidebar_stats_label")
        logo_layout.addWidget(self.stats_label)

        root.addWidget(logo_widget)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep1)

        # ── Library section ────────────────────────────────────────────────
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("nav_list")
        self.nav_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        item_lib = QListWidgetItem("  📚  Library")
        item_lib.setData(Qt.ItemDataRole.UserRole, 'library')
        self.nav_list.addItem(item_lib)

        item_albums = QListWidgetItem("  💿  Albums")
        item_albums.setData(Qt.ItemDataRole.UserRole, 'albums')
        self.nav_list.addItem(item_albums)

        item_artists = QListWidgetItem("  👤  Artists")
        item_artists.setData(Qt.ItemDataRole.UserRole, 'artists')
        self.nav_list.addItem(item_artists)

        root.addWidget(self.nav_list)

        # ── Scan button ────────────────────────────────────────────────────
        scan_widget = QWidget()
        scan_layout = QVBoxLayout(scan_widget)
        scan_layout.setContentsMargins(10, 8, 10, 4)

        scan_btn = QPushButton("＋  Scan Folder")
        scan_btn.setObjectName("accent_btn")
        scan_btn.clicked.connect(lambda: self.scan_requested.emit(''))
        scan_layout.addWidget(scan_btn)

        root.addWidget(scan_widget)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep2)

        # ── Playlists section ──────────────────────────────────────────────
        pl_header_widget = QWidget()
        pl_header_layout = QHBoxLayout(pl_header_widget)
        pl_header_layout.setContentsMargins(16, 10, 8, 4)

        pl_hdr = QLabel("PLAYLISTS")
        pl_hdr.setObjectName("section_header")
        pl_header_layout.addWidget(pl_hdr)
        pl_header_layout.addStretch()

        add_pl_btn = QPushButton("+")
        add_pl_btn.setObjectName("icon_btn")
        add_pl_btn.setFixedSize(22, 22)
        add_pl_btn.setToolTip("New Playlist")
        add_pl_btn.clicked.connect(self._create_playlist)
        pl_header_layout.addWidget(add_pl_btn)

        root.addWidget(pl_header_widget)

        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("nav_list")
        self.playlist_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.playlist_list.itemClicked.connect(self._on_playlist_clicked)
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self._playlist_context_menu)
        root.addWidget(self.playlist_list, 1)

        # ── Smart playlist section ─────────────────────────────────────────
        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep3)

        sm_header = QWidget()
        sm_layout = QHBoxLayout(sm_header)
        sm_layout.setContentsMargins(16, 10, 8, 4)
        sm_hdr = QLabel("SMART PLAYLISTS")
        sm_hdr.setObjectName("section_header")
        sm_layout.addWidget(sm_hdr)
        sm_layout.addStretch()
        add_sm_btn = QPushButton("+")
        add_sm_btn.setObjectName("icon_btn")
        add_sm_btn.setFixedSize(22, 22)
        add_sm_btn.setToolTip("New Smart Playlist")
        add_sm_btn.clicked.connect(self._create_smart_playlist)
        sm_layout.addWidget(add_sm_btn)
        root.addWidget(sm_header)

        self.smart_list = QListWidget()
        self.smart_list.setObjectName("nav_list")
        self.smart_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.smart_list.setMaximumHeight(130)
        self.smart_list.itemClicked.connect(self._on_smart_clicked)
        self.smart_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.smart_list.customContextMenuRequested.connect(self._playlist_context_menu)
        root.addWidget(self.smart_list)

        # ── Bottom buttons ─────────────────────────────────────────────────
        sep4 = QFrame(); sep4.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep4)

        bottom = QWidget()
        bot_layout = QVBoxLayout(bottom)
        bot_layout.setContentsMargins(10, 8, 10, 12)
        bot_layout.setSpacing(4)

        tools_lbl = QLabel("TOOLS")
        tools_lbl.setObjectName("section_header")
        bot_layout.addWidget(tools_lbl)

        dup_btn = QPushButton("🔍  Duplicate Finder")
        dup_btn.clicked.connect(self.duplicate_finder_requested)
        bot_layout.addWidget(dup_btn)

        export_btn = QPushButton("⬇  Export Library")
        export_btn.clicked.connect(self._export_menu)
        bot_layout.addWidget(export_btn)

        self.theme_btn = QPushButton("☀  Light Mode")
        self.theme_btn.clicked.connect(self.theme_toggle_requested)
        bot_layout.addWidget(self.theme_btn)

        root.addWidget(bottom)

        # Nav list click
        self.nav_list.itemClicked.connect(self._on_nav_clicked)
        # Select library by default
        self.nav_list.setCurrentRow(0)

    # ── Public ────────────────────────────────────────────────────────────────

    def update_stats(self, track_count: int):
        stats = self.db.get_stats()
        self.stats_label.setText(
            f"{stats['tracks']:,} tracks  •  {stats['artists']:,} artists"
        )

    def refresh_playlists(self):
        self.playlist_list.clear()
        self.smart_list.clear()
        for pl in self.db.get_all_playlists():
            if pl.is_smart:
                item = QListWidgetItem(f"  ✦ {pl.name}")
            else:
                item = QListWidgetItem(f"  ♬ {pl.name}")
            item.setData(Qt.ItemDataRole.UserRole, pl)
            if pl.is_smart:
                self.smart_list.addItem(item)
            else:
                self.playlist_list.addItem(item)

    def set_theme(self, theme: str):
        if theme == 'dark':
            self.theme_btn.setText("☀  Light Mode")
        else:
            self.theme_btn.setText("🌙  Dark Mode")

    # ── Private ───────────────────────────────────────────────────────────────

    def _on_nav_clicked(self, item):
        key = item.data(Qt.ItemDataRole.UserRole)
        if key in ('library', 'albums', 'artists'):
            self.nav_changed.emit(key)

    def _on_playlist_clicked(self, item):
        pl = item.data(Qt.ItemDataRole.UserRole)
        if pl:
            tracks = self.db.get_playlist_tracks(pl.id)
            self.playlist_selected.emit(tracks)

    def _on_smart_clicked(self, item):
        pl = item.data(Qt.ItemDataRole.UserRole)
        if pl and pl.criteria:
            tracks = self.db.evaluate_smart_playlist(pl.criteria)
            self.playlist_selected.emit(tracks)

    def _create_playlist(self):
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name.strip():
            self.db.create_playlist(name.strip())
            self.refresh_playlists()

    def _create_smart_playlist(self):
        from ui.smart_playlist_dialog import SmartPlaylistDialog
        dlg = SmartPlaylistDialog(self.db, self)
        if dlg.exec():
            self.refresh_playlists()

    def _playlist_context_menu(self, pos):
        sender = self.sender()
        item   = sender.itemAt(pos)
        if not item:
            return
        pl = item.data(Qt.ItemDataRole.UserRole)
        if not pl:
            return
        menu = QMenu(self)
        menu.addAction("✏  Rename", lambda: self._rename_playlist(pl))
        menu.addAction("🗑  Delete", lambda: self._delete_playlist(pl))
        menu.exec(sender.mapToGlobal(pos))

    def _rename_playlist(self, pl):
        name, ok = QInputDialog.getText(self, "Rename Playlist", "New name:", text=pl.name)
        if ok and name.strip():
            self.db.rename_playlist(pl.id, name.strip())
            self.refresh_playlists()

    def _delete_playlist(self, pl):
        reply = QMessageBox.question(self, "Delete Playlist",
            f"Delete '{pl.name}'? Tracks will not be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_playlist(pl.id)
            self.refresh_playlists()

    def _export_menu(self):
        menu = QMenu(self)
        menu.addAction("Export as CSV",  lambda: self.export_requested.emit('csv'))
        menu.addAction("Export as JSON", lambda: self.export_requested.emit('json'))
        menu.exec(self.cursor().pos())
