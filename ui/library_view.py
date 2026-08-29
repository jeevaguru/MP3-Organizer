"""
MP3 Organizer — Library View  (central track browser)
"""
import os

from PyQt6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, pyqtSignal
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QLineEdit,
    QLabel, QPushButton, QComboBox, QMenu, QHeaderView,
    QAbstractItemView, QFrame, QSizePolicy
)
from PyQt6.QtGui import QAction, QFont, QColor, QPalette


# ── Table Model ───────────────────────────────────────────────────────────────

COLUMNS = ['#', 'Title', 'Artist', 'Album', 'Language', 'Duration', 'Bitrate', 'Size', 'Genre']
COL_IDX = {name: i for i, name in enumerate(COLUMNS)}


class TrackTableModel(QAbstractTableModel):
    def __init__(self, tracks=None, parent=None):
        super().__init__(parent)
        self._tracks = tracks or []
        self._playing_id = -1

    def set_tracks(self, tracks):
        self.beginResetModel()
        self._tracks = list(tracks)
        self.endResetModel()

    def set_playing(self, track_id: int):
        old = self._playing_id
        self._playing_id = track_id
        # Refresh rows for both old and new
        for i, t in enumerate(self._tracks):
            if t.id in (old, track_id):
                self.dataChanged.emit(self.index(i, 0), self.index(i, len(COLUMNS) - 1))

    def track_at(self, row: int):
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None

    def all_tracks(self):
        return list(self._tracks)

    # ── QAbstractTableModel interface ─────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()):
        return len(self._tracks)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return COLUMNS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._tracks)):
            return None
        track = self._tracks[index.row()]
        col   = index.column()
        is_playing = (track.id == self._playing_id)

        if role == Qt.ItemDataRole.DisplayRole:
            return _cell_text(track, col, index.row())

        elif role == Qt.ItemDataRole.UserRole:
            return track

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (0, 5, 6, 7):
                return int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        elif role == Qt.ItemDataRole.ForegroundRole:
            if is_playing:
                return QColor("#4f9eff")
            if col == 0:
                return QColor("#6e7681")

        elif role == Qt.ItemDataRole.FontRole:
            if is_playing:
                f = QFont()
                f.setBold(True)
                return f

        return None


def _cell_text(track, col: int, row: int) -> str:
    if col == 0:
        return str(row + 1)
    elif col == 1:
        return track.display_title()
    elif col == 2:
        return track.display_artist()
    elif col == 3:
        return track.display_album()
    elif col == 4:
        return track.language or ''
    elif col == 5:
        return _fmt_dur(track.duration)
    elif col == 6:
        return f"{track.bitrate}" if track.bitrate else ''
    elif col == 7:
        return _fmt_size(track.file_size)
    elif col == 8:
        return track.genre or ''
    return ''


def _fmt_dur(s):
    if s is None: return ''
    m, sec = divmod(int(s), 60)
    h, m   = divmod(m, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def _fmt_size(b):
    if not b: return ''
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024: return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} GB"


# ── Filter Proxy ──────────────────────────────────────────────────────────────

class TrackFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._query = ''
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def set_query(self, query: str):
        self._query = query.strip().lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._query:
            return True
        model = self.sourceModel()
        track = model.track_at(source_row)
        if track is None:
            return False
        haystack = ' '.join([
            track.display_title(),
            track.display_artist(),
            track.display_album(),
            track.genre or '',
            track.language or '',
            track.file_name,
        ]).lower()
        return self._query in haystack


# ── Library View Widget ───────────────────────────────────────────────────────

class LibraryView(QWidget):
    track_double_clicked   = pyqtSignal(int)          # track.id
    tracks_selected        = pyqtSignal(list)          # [track.id, ...]
    tag_edit_requested     = pyqtSignal(int)          # track.id
    add_to_queue_requested = pyqtSignal(list)          # [track.id, ...]
    show_in_explorer_requested = pyqtSignal(str)      # file_path

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._model  = TrackTableModel(parent=self)
        self._proxy  = TrackFilterProxy(self)
        self._proxy.setSourceModel(self._model)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ────────────────────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setStyleSheet("background:transparent;")
        top_row = QHBoxLayout(top_bar)
        top_row.setContentsMargins(14, 12, 14, 8)
        top_row.setSpacing(10)

        # Search
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍  Search title, artist, album…")
        self.search_edit.textChanged.connect(self._on_search)
        self.search_edit.setFixedHeight(36)
        top_row.addWidget(self.search_edit, 1)

        # Filter combobox
        self.filter_cb = QComboBox()
        self.filter_cb.addItems(["All", "Has Artwork", "No Artwork", "Has Language"])
        self.filter_cb.currentTextChanged.connect(self._refresh_filter)
        top_row.addWidget(self.filter_cb)

        self.count_label = QLabel("0 tracks")
        self.count_label.setStyleSheet("color:#6e7681;font-size:12px;")
        top_row.addWidget(self.count_label)

        root.addWidget(top_bar)

        # ── Separator ──────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── Table ──────────────────────────────────────────────────────────
        self.table = QTableView()
        self.table.setModel(self._proxy)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)

        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(COL_IDX['Title'],  QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(COL_IDX['Artist'], QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(COL_IDX['Album'],  QHeaderView.ResizeMode.Interactive)
        hdr.setDefaultSectionSize(110)
        hdr.resizeSection(COL_IDX['#'],        40)
        hdr.resizeSection(COL_IDX['Duration'], 72)
        hdr.resizeSection(COL_IDX['Bitrate'],  70)
        hdr.resizeSection(COL_IDX['Size'],     76)
        hdr.resizeSection(COL_IDX['Language'], 80)
        hdr.resizeSection(COL_IDX['Genre'],    90)
        hdr.resizeSection(COL_IDX['Artist'],   150)
        hdr.resizeSection(COL_IDX['Album'],    140)
        hdr.setStretchLastSection(False)
        hdr.setHighlightSections(True)
        hdr.setSortIndicatorShown(True)

        self.table.doubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)

        root.addWidget(self.table, 1)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_tracks(self, tracks):
        self._all_tracks = list(tracks)
        self._model.set_tracks(tracks)
        self._update_count()

    def get_visible_tracks(self):
        """Return tracks currently shown (after filter/sort)."""
        result = []
        for row in range(self._proxy.rowCount()):
            src_row = self._proxy.mapToSource(self._proxy.index(row, 0)).row()
            t = self._model.track_at(src_row)
            if t:
                result.append(t)
        return result

    def show_playlist(self, tracks):
        self._model.set_tracks(tracks)
        self._update_count()

    def set_playing(self, track_id: int):
        self._model.set_playing(track_id)

    # ── Private ───────────────────────────────────────────────────────────────

    def _on_search(self, text: str):
        self._proxy.set_query(text)
        self._update_count()

    def _refresh_filter(self, _):
        self._on_search(self.search_edit.text())

    def _update_count(self):
        visible = self._proxy.rowCount()
        total   = self._model.rowCount()
        if visible == total:
            self.count_label.setText(f"{total:,} track{'s' if total != 1 else ''}")
        else:
            self.count_label.setText(f"{visible:,} of {total:,} tracks")

    def _on_double_click(self, proxy_index):
        src_row = self._proxy.mapToSource(proxy_index).row()
        track   = self._model.track_at(src_row)
        if track:
            self.track_double_clicked.emit(track.id)

    def _selected_tracks(self):
        rows = set()
        for idx in self.table.selectedIndexes():
            rows.add(self._proxy.mapToSource(idx).row())
        tracks = [self._model.track_at(r) for r in sorted(rows)]
        return [t for t in tracks if t]

    def _context_menu(self, pos):
        tracks = self._selected_tracks()
        if not tracks:
            return
        menu = QMenu(self)
        if len(tracks) == 1:
            menu.addAction("▶  Play Now",          lambda: self.track_double_clicked.emit(tracks[0].id))
        menu.addAction("➕  Add to Queue",          lambda: self.add_to_queue_requested.emit([t.id for t in tracks]))
        menu.addSeparator()
        if len(tracks) == 1:
            menu.addAction("✏  Edit Tags",          lambda: self.tag_edit_requested.emit(tracks[0].id))
            menu.addAction("📁  Open File Location", lambda: self._open_location(tracks[0]))
        menu.addSeparator()
        menu.addAction("ℹ  Properties",            lambda: self._show_properties(tracks[0]) if tracks else None)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _open_location(self, track):
        import subprocess
        if os.path.exists(track.file_path):
            subprocess.Popen(f'explorer /select,"{track.file_path}"')

    def _show_properties(self, track):
        from PyQt6.QtWidgets import QMessageBox
        info = (
            f"<b>Title:</b>    {track.display_title()}<br>"
            f"<b>Artist:</b>   {track.display_artist()}<br>"
            f"<b>Album:</b>    {track.display_album()}<br>"
            f"<b>Year:</b>     {track.year or 'N/A'}<br>"
            f"<b>Genre:</b>    {track.genre or 'N/A'}<br>"
            f"<b>Language:</b> {track.language or 'N/A'}<br>"
            f"<b>Bitrate:</b>  {track.bitrate} kbps<br>"
            f"<b>Duration:</b> {_fmt_dur(track.duration)}<br>"
            f"<b>File:</b>     {track.file_name}<br>"
            f"<b>Path:</b>     {track.file_path}<br>"
            f"<b>Size:</b>     {_fmt_size(track.file_size)}<br>"
            f"<b>Play Count:</b> {track.play_count}"
        )
        mb = QMessageBox(self)
        mb.setWindowTitle("Track Properties")
        mb.setTextFormat(Qt.TextFormat.RichText)
        mb.setText(info)
        mb.exec()
