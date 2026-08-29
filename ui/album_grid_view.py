"""
MP3 Organizer — Album / Artist Grid View
Responsive cover-art tile grid for browsing albums and artists.
"""
import hashlib

from PyQt6.QtCore import Qt, pyqtSignal, QRect, QTimer
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QSizePolicy, QGridLayout, QLineEdit,
    QPushButton, QAbstractScrollArea,
)
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QPainterPath,
    QColor, QFont, QFontMetrics, QLinearGradient,
)

# ── Tile geometry ──────────────────────────────────────────────────────────────
TILE_W    = 190    # total tile width
ART_SIZE  = 164    # square art side length
TILE_GAP  = 16     # gap between tiles
PAD       = 18     # content area padding

# Placeholder gradient palettes: (dark_bg, accent)
_PALETTES = [
    ('#0d2a4e', '#4f9eff'),
    ('#0d3a1e', '#3fb950'),
    ('#3a0d1e', '#f78166'),
    ('#260d3a', '#bc8cff'),
    ('#3a250d', '#e3b341'),
    ('#0d3a3a', '#39d353'),
    ('#3a180d', '#ff7b72'),
    ('#1e2a0d', '#79c0ff'),
]


# ── Rounded-corner art label ──────────────────────────────────────────────────

class _ArtLabel(QLabel):
    """QLabel that draws a pixmap clipped to rounded corners."""

    def __init__(self, size: int, radius: int = 10, parent=None):
        super().__init__(parent)
        self._radius = radius
        self._pm: QPixmap | None = None
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_pixmap(self, pm: QPixmap) -> None:
        # Scale + centre-crop to fill the square exactly
        scaled = pm.scaled(
            self.width(), self.height(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (scaled.width() - self.width()) // 2
        y = (scaled.height() - self.height()) // 2
        self._pm = scaled.copy(x, y, self.width(), self.height())
        self.update()

    def paintEvent(self, event):
        if not self._pm:
            super().paintEvent(event)
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(),
                            self._radius, self._radius)
        p.setClipPath(path)
        p.drawPixmap(0, 0, self._pm)


# ── Single tile ───────────────────────────────────────────────────────────────

class AlbumTile(QFrame):
    """
    A single album or artist tile: rounded-corner art + title + subtitle + meta.

    Signals
    -------
    clicked(item_id: int)
    """
    clicked = pyqtSignal(int)

    def __init__(self, item_id: int, artwork: bytes | None,
                 title: str, subtitle: str, meta: str = '',
                 parent=None):
        super().__init__(parent)

        self._id       = item_id
        self._title    = title      # stored for search filtering
        self._subtitle = subtitle

        self.setFixedWidth(TILE_W)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("album_tile")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 12)
        layout.setSpacing(6)

        # ── Art ───────────────────────────────────────────────────────────
        self._art = _ArtLabel(ART_SIZE, radius=10)
        self._art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._art.set_pixmap(self._load_art(title, artwork))
        layout.addWidget(self._art, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ── Title (bold, single line with ellipsis) ────────────────────────
        title_lbl = QLabel()
        title_lbl.setObjectName("tile_title")
        title_lbl.setMaximumWidth(ART_SIZE)
        f = QFont()
        f.setWeight(QFont.Weight.DemiBold)
        title_lbl.setFont(f)
        title_lbl.setText(
            QFontMetrics(f).elidedText(title or 'Unknown',
                                       Qt.TextElideMode.ElideRight, ART_SIZE)
        )
        layout.addWidget(title_lbl)

        # ── Subtitle (artist / album count, single line) ──────────────────
        if subtitle:
            sub = QLabel()
            sub.setObjectName("tile_subtitle")
            sub.setMaximumWidth(ART_SIZE)
            sub.setText(
                QFontMetrics(sub.font()).elidedText(
                    subtitle, Qt.TextElideMode.ElideRight, ART_SIZE)
            )
            layout.addWidget(sub)

        # ── Meta (track count etc.) ───────────────────────────────────────
        if meta:
            meta_lbl = QLabel(meta)
            meta_lbl.setObjectName("tile_count")
            layout.addWidget(meta_lbl)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_art(self, name: str, raw: bytes | None) -> QPixmap:
        if raw:
            try:
                img = QImage.fromData(bytes(raw))
                if not img.isNull():
                    return QPixmap.fromImage(img)
            except Exception:
                pass
        return self._placeholder(name, ART_SIZE)

    def _placeholder(self, text: str, size: int) -> QPixmap:
        idx = int(hashlib.md5((text or '?').encode()).hexdigest(), 16) % len(_PALETTES)
        bg_hex, fg_hex = _PALETTES[idx]

        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)

        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0, QColor(bg_hex).lighter(130))
        grad.setColorAt(1, QColor(bg_hex))
        p.setBrush(grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, size, size)

        letter = text.strip()[0].upper() if text.strip() else '♪'
        font = p.font()
        font.setPointSize(size // 3)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor(fg_hex))
        p.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, letter)
        p.end()
        return pm

    # ── Events ────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._id)


# ── Grid view container ───────────────────────────────────────────────────────

class AlbumGridView(QWidget):
    """
    Responsive tile grid.  Handles Albums → (click) → drill into album tracks,
    and Artists → (click) → artist's Albums → (click) → drill into tracks.

    Signals
    -------
    album_clicked(album_id)          — user clicked an album tile
    artist_clicked(artist_id, name)  — user clicked an artist tile
    """
    album_clicked  = pyqtSignal(int)
    artist_clicked = pyqtSignal(int, str)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self._db    = db
        self._tiles: list[AlbumTile] = []
        self._mode  = 'albums'   # 'albums' | 'artists'
        self._cols  = 4

        # Debounce the resize → relayout
        self._relayout_timer = QTimer(self)
        self._relayout_timer.setSingleShot(True)
        self._relayout_timer.setInterval(60)
        self._relayout_timer.timeout.connect(self._do_relayout)

        self._build_ui()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ───────────────────────────────────────────────────────
        top = QWidget()
        top.setStyleSheet("background: transparent;")
        top_row = QHBoxLayout(top)
        top_row.setContentsMargins(PAD, 14, PAD, 8)
        top_row.setSpacing(10)

        self._back_btn = QPushButton("← Artists")
        self._back_btn.setObjectName("icon_btn")
        self._back_btn.setFixedHeight(30)
        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self._go_back)
        top_row.addWidget(self._back_btn)

        self._title_lbl = QLabel("Albums")
        self._title_lbl.setObjectName("grid_view_title")
        top_row.addWidget(self._title_lbl)

        top_row.addStretch()

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("grid_count_label")
        top_row.addWidget(self._count_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search…")
        self._search.setFixedWidth(220)
        self._search.setFixedHeight(32)
        self._search.textChanged.connect(self._on_search)
        top_row.addWidget(self._search)

        root.addWidget(top)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── Scroll area ───────────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)

        self._content = QWidget()
        self._content.setObjectName("grid_content")

        self._grid = QGridLayout(self._content)
        self._grid.setSpacing(TILE_GAP)
        self._grid.setContentsMargins(PAD, PAD, PAD, PAD)
        self._grid.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._scroll.setWidget(self._content)
        root.addWidget(self._scroll, 1)

    # ── Public API ────────────────────────────────────────────────────────────

    def show_albums(self, filter_artist_id: int = None,
                    filter_artist_name: str = None):
        """Show all albums, optionally filtered to a single artist."""
        self._mode = 'albums'
        self._search.clear()

        if filter_artist_id is not None:
            self._title_lbl.setText(filter_artist_name or 'Albums')
            self._back_btn.setVisible(True)
            items = self._db.get_albums_with_stats(filter_artist_id)
        else:
            self._title_lbl.setText('Albums')
            self._back_btn.setVisible(False)
            items = self._db.get_albums_with_stats()

        self._populate('album', items)

    def show_artists(self):
        """Show all artists."""
        self._mode = 'artists'
        self._search.clear()
        self._back_btn.setVisible(False)
        self._title_lbl.setText('Artists')
        self._populate('artist', self._db.get_artists_with_stats())

    def refresh(self):
        """Re-load whatever is currently displayed (call after library changes)."""
        if self._mode == 'artists':
            self.show_artists()
        else:
            self.show_albums()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _populate(self, item_type: str, items: list[dict]):
        # Clear grid, then delete old tiles
        while self._grid.count():
            self._grid.takeAt(0)
        for tile in self._tiles:
            tile.deleteLater()
        self._tiles.clear()

        for item in items:
            art = item.get('artwork_blob')
            if art is not None:
                art = bytes(art)

            if item_type == 'album':
                tc = item.get('track_count', 0)
                tile = AlbumTile(
                    item['id'],
                    art,
                    item.get('name') or 'Unknown Album',
                    item.get('artist_name') or '',
                    f"{tc} track{'s' if tc != 1 else ''}",
                )
                tile.clicked.connect(self.album_clicked)

            else:  # artist
                alb = item.get('album_count', 0)
                tc  = item.get('track_count', 0)
                name = item.get('name') or 'Unknown Artist'
                tile = AlbumTile(
                    item['id'],
                    art,
                    name,
                    f"{alb} album{'s' if alb != 1 else ''}",
                    f"{tc} tracks",
                )
                # Capture name in default arg to avoid closure-capture bug
                tile.clicked.connect(
                    lambda aid, n=name: self.artist_clicked.emit(aid, n)
                )

            tile._search_hidden = False   # not hidden by the search filter
            self._tiles.append(tile)

        n    = len(self._tiles)
        noun = 'artist' if item_type == 'artist' else 'album'
        self._count_lbl.setText(f"{n:,} {noun}{'s' if n != 1 else ''}")
        self._do_relayout()

    def _on_search(self, query: str):
        q = query.lower().strip()
        for tile in self._tiles:
            show = (not q
                    or q in tile._title.lower()
                    or q in tile._subtitle.lower())
            tile._search_hidden = not show
            tile.setVisible(show)
        n = sum(1 for t in self._tiles if not t._search_hidden)
        noun = 'artist' if self._mode == 'artists' else 'album'
        self._count_lbl.setText(
            f"{n:,} result{'s' if n != 1 else ''}" if q
            else f"{len(self._tiles):,} {noun}{'s' if len(self._tiles) != 1 else ''}"
        )
        self._do_relayout()

    def _go_back(self):
        self.show_artists()

    def _calc_cols(self) -> int:
        avail = max(TILE_W + TILE_GAP,
                    self._scroll.viewport().width() - PAD * 2)
        return max(2, avail // (TILE_W + TILE_GAP))

    def _do_relayout(self):
        cols = self._calc_cols()
        # Detach all widgets from grid (tiles remain alive as content children)
        while self._grid.count():
            self._grid.takeAt(0)

        # Use explicit _search_hidden flag — isVisible() is unreliable for
        # newly created widgets that haven't been parented/shown yet.
        visible = [t for t in self._tiles if not getattr(t, '_search_hidden', False)]
        for i, tile in enumerate(visible):
            self._grid.addWidget(
                tile,
                i // cols,
                i % cols,
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            )
        # Push everything up
        if visible:
            self._grid.setRowStretch(len(visible) // cols + 1, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout_timer.start()
