"""
MP3 Organizer — Now Playing Panel (right sidebar)
Displays album art, track info, and synchronized lyrics.
"""
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QScrollArea,
    QPushButton, QFrame, QSizePolicy, QHBoxLayout
)
from PyQt6.QtGui import QPixmap, QImage, QFont, QPainter, QColor


class _LyricsFetchThread(QThread):
    result = pyqtSignal(str)   # lyrics text or ''

    def __init__(self, service, title, artist, parent=None):
        super().__init__(parent)
        self._service = service
        self._title   = title
        self._artist  = artist

    def run(self):
        text = self._service.fetch(self._title, self._artist, synced=True)
        self.result.emit(text or '')


class NowPlayingPanel(QWidget):
    def __init__(self, lyrics_service, artwork_service, parent=None):
        super().__init__(parent)
        self._lyrics_svc   = lyrics_service
        self._artwork_svc  = artwork_service
        self._current_track = None
        self._lrc_lines    = []      # [(timestamp_sec, text), ...]
        self._fetch_thread  = None
        self._current_ms   = 0

        self.setObjectName("now_playing_panel")
        self.setMinimumWidth(250)
        self._build_ui()

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("now_playing_panel")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 20, 14, 14)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ── Section label ──────────────────────────────────────────────────
        now_lbl = QLabel("NOW PLAYING")
        now_lbl.setObjectName("section_header")
        layout.addWidget(now_lbl)

        # ── Album art ──────────────────────────────────────────────────────
        art_container = QWidget()
        ac_layout = QHBoxLayout(art_container)
        ac_layout.setContentsMargins(0, 0, 0, 0)
        ac_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.art_label = QLabel()
        self.art_label.setFixedSize(220, 220)
        self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_label.setStyleSheet(
            "border-radius:12px;"
            "background-color:#21262d;"
            "color:#6e7681;"
            "font-size:48px;"
        )
        self.art_label.setText("♪")
        ac_layout.addWidget(self.art_label)
        layout.addWidget(art_container)

        # ── Track info ─────────────────────────────────────────────────────
        self.title_lbl = QLabel("No track selected")
        self.title_lbl.setObjectName("now_playing_title")
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_lbl)

        self.artist_lbl = QLabel("")
        self.artist_lbl.setObjectName("now_playing_artist")
        self.artist_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.artist_lbl.setWordWrap(True)
        layout.addWidget(self.artist_lbl)

        self.album_lbl = QLabel("")
        self.album_lbl.setObjectName("now_playing_album")
        self.album_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_lbl.setWordWrap(True)
        layout.addWidget(self.album_lbl)

        # Fetch art button (shown when no embedded art)
        self.fetch_art_btn = QPushButton("Fetch Album Art")
        self.fetch_art_btn.setObjectName("icon_btn")
        self.fetch_art_btn.clicked.connect(self._fetch_art)
        self.fetch_art_btn.setVisible(False)
        layout.addWidget(self.fetch_art_btn)

        # ── Separator ──────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # ── Lyrics ─────────────────────────────────────────────────────────
        lyrics_header = QHBoxLayout()
        lyrics_lbl = QLabel("LYRICS")
        lyrics_lbl.setObjectName("section_header")
        lyrics_header.addWidget(lyrics_lbl)
        lyrics_header.addStretch()

        self.fetch_lyrics_btn = QPushButton("Fetch")
        self.fetch_lyrics_btn.setObjectName("icon_btn")
        self.fetch_lyrics_btn.setFixedWidth(46)
        self.fetch_lyrics_btn.clicked.connect(self._fetch_lyrics)
        lyrics_header.addWidget(self.fetch_lyrics_btn)
        layout.addLayout(lyrics_header)

        self.lyrics_display = QTextEdit()
        self.lyrics_display.setObjectName("lyrics_text")
        self.lyrics_display.setReadOnly(True)
        self.lyrics_display.setMinimumHeight(200)
        self.lyrics_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lyrics_display.setPlaceholderText("Lyrics will appear here…")
        layout.addWidget(self.lyrics_display)

    # ── Public slots ──────────────────────────────────────────────────────────

    def set_track(self, track):
        """Called when a new track starts playing."""
        self._current_track = track
        self._lrc_lines     = []
        self.lyrics_display.clear()

        # Track info
        self.title_lbl.setText(track.display_title())
        self.artist_lbl.setText(track.display_artist())
        self.album_lbl.setText(track.display_album())

        # Artwork
        if track.artwork_blob:
            self._set_art_from_bytes(bytes(track.artwork_blob))
            self.fetch_art_btn.setVisible(False)
        else:
            self.art_label.clear()
            self.art_label.setText("♪")
            self.fetch_art_btn.setVisible(True)

        # Auto-fetch lyrics
        self._fetch_lyrics()

    def update_position(self, ms: int):
        """Called as the track plays — highlights the current LRC line."""
        self._current_ms = ms
        if not self._lrc_lines:
            return
        sec = ms / 1000.0
        current_line = 0
        for i, (ts, _) in enumerate(self._lrc_lines):
            if ts <= sec:
                current_line = i
            else:
                break
        # Highlight current line
        self._highlight_line(current_line)

    # ── Private ───────────────────────────────────────────────────────────────

    def _set_art_from_bytes(self, data: bytes):
        img = QImage.fromData(data)
        if not img.isNull():
            pm = QPixmap.fromImage(img).scaled(
                220, 220,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.art_label.setPixmap(pm)
            self.art_label.setText('')
        else:
            self.art_label.clear()
            self.art_label.setText("♪")

    def _fetch_art(self):
        if not self._current_track:
            return
        self.fetch_art_btn.setEnabled(False)
        self.fetch_art_btn.setText("Fetching…")

        class _ArtThread(QThread):
            done = pyqtSignal(bytes)
            def __init__(self, svc, a, b, parent=None):
                super().__init__(parent)
                self._svc, self._a, self._b = svc, a, b
            def run(self):
                d = self._svc.fetch(self._a, self._b)
                if d: self.done.emit(d)

        t = _ArtThread(self._artwork_svc,
                       self._current_track.display_artist(),
                       self._current_track.display_album(),
                       self)
        t.done.connect(lambda d: (
            self._set_art_from_bytes(d),
            self.fetch_art_btn.setVisible(False),
        ))
        t.finished.connect(lambda: (
            self.fetch_art_btn.setEnabled(True),
            self.fetch_art_btn.setText("Fetch Album Art"),
        ))
        t.start()

    def _fetch_lyrics(self):
        if not self._current_track:
            return
        if self._fetch_thread and self._fetch_thread.isRunning():
            return

        self.lyrics_display.setPlaceholderText("Fetching lyrics…")
        self.fetch_lyrics_btn.setEnabled(False)
        self.fetch_lyrics_btn.setText("…")

        self._fetch_thread = _LyricsFetchThread(
            self._lyrics_svc,
            self._current_track.display_title(),
            self._current_track.display_artist(),
            self,
        )
        self._fetch_thread.result.connect(self._on_lyrics_received)
        self._fetch_thread.finished.connect(lambda: (
            self.fetch_lyrics_btn.setEnabled(True),
            self.fetch_lyrics_btn.setText("Fetch"),
        ))
        self._fetch_thread.start()

    def _on_lyrics_received(self, text: str):
        self.lyrics_display.setPlaceholderText("Lyrics will appear here…")
        if not text:
            self.lyrics_display.setPlainText("No lyrics found.")
            return

        # Try to parse as LRC
        lrc = self._lyrics_svc.parse_lrc(text)
        if lrc:
            self._lrc_lines = lrc
            plain = '\n'.join(line for _, line in lrc)
            self.lyrics_display.setPlainText(plain)
        else:
            self._lrc_lines = []
            self.lyrics_display.setPlainText(text)

    def _highlight_line(self, line_index: int):
        """Bold the current line in the lyrics display."""
        doc   = self.lyrics_display.document()
        total = doc.blockCount()
        if line_index >= total:
            return

        cursor = self.lyrics_display.textCursor()
        cursor.select(cursor.SelectionType.Document)

        # Reset all to normal
        fmt_normal = cursor.charFormat()
        fmt_normal.setFontWeight(QFont.Weight.Normal)
        from PyQt6.QtGui import QTextCharFormat, QTextCursor
        cur = self.lyrics_display.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.Start)
        cur.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        normal_fmt = QTextCharFormat()
        normal_fmt.setFontWeight(QFont.Weight.Normal)
        cur.setCharFormat(normal_fmt)

        # Bold the current line
        block = doc.findBlockByNumber(line_index)
        cur2  = self.lyrics_display.textCursor()
        cur2.setPosition(block.position())
        cur2.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        bold_fmt = QTextCharFormat()
        bold_fmt.setFontWeight(QFont.Weight.Bold)
        bold_fmt.setForeground(QColor("#4f9eff"))
        cur2.setCharFormat(bold_fmt)

        # Scroll to the highlighted line
        self.lyrics_display.setTextCursor(cur2)
        self.lyrics_display.ensureCursorVisible()
