"""
MP3 Organizer — Tag Editor Dialog
Edit ID3 tags and album art for a single track.
"""
import io
import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFrame, QSpinBox, QFormLayout, QScrollArea,
    QWidget, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QPixmap, QImage

from database.db_manager import DatabaseManager
from scanner.metadata import write_metadata


class _ArtworkFetchThread(QThread):
    """Background thread for fetching online artwork."""
    result = pyqtSignal(bytes)

    def __init__(self, artwork_service, artist, album, parent=None):
        super().__init__(parent)
        self._svc    = artwork_service
        self._artist = artist
        self._album  = album

    def run(self):
        data = self._svc.fetch(self._artist, self._album)
        if data:
            self.result.emit(data)


class TagEditorDialog(QDialog):
    def __init__(self, track, artwork_service, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.track           = track
        self.artwork_service = artwork_service
        self.db              = db
        self._artwork_bytes  = bytes(track.artwork_blob) if track.artwork_blob else None
        self._artwork_changed = False
        self._fetch_thread   = None

        self.setWindowTitle("Edit Tags")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._build_ui()
        self._load_values()

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(16)
        main.setContentsMargins(24, 24, 24, 24)

        # ── Title ─────────────────────────────────────────────────────────
        header = QLabel("Edit Track Tags")
        header.setStyleSheet("font-size:17px;font-weight:700;")
        main.addWidget(header)

        path_lbl = QLabel(self.track.file_path)
        path_lbl.setStyleSheet("color:#8b949e;font-size:11px;")
        path_lbl.setWordWrap(True)
        main.addWidget(path_lbl)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        main.addWidget(sep)

        # ── Content row: form + artwork ────────────────────────────────────
        content = QHBoxLayout()
        content.setSpacing(20)

        # Form
        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def make_edit(placeholder=''):
            e = QLineEdit()
            e.setPlaceholderText(placeholder)
            return e

        self.title_edit    = make_edit("Song title")
        self.artist_edit   = make_edit("Artist name")
        self.album_edit    = make_edit("Album name")
        self.genre_edit    = make_edit("Genre")
        self.language_edit = make_edit("e.g. eng, tam, hin")
        self.year_spin     = QSpinBox()
        self.year_spin.setRange(0, 2099)
        self.year_spin.setSpecialValueText(" ")
        self.track_spin    = QSpinBox()
        self.track_spin.setRange(0, 999)
        self.track_spin.setSpecialValueText(" ")

        form.addRow("Title:", self.title_edit)
        form.addRow("Artist:", self.artist_edit)
        form.addRow("Album:", self.album_edit)
        form.addRow("Genre:", self.genre_edit)
        form.addRow("Language:", self.language_edit)
        form.addRow("Year:", self.year_spin)
        form.addRow("Track #:", self.track_spin)

        content.addWidget(form_widget, 1)

        # Artwork panel
        art_panel = QVBoxLayout()
        art_panel.setSpacing(8)
        art_panel.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.art_label = QLabel()
        self.art_label.setFixedSize(160, 160)
        self.art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.art_label.setStyleSheet(
            "border:1px solid #30363d;border-radius:8px;background-color:#21262d;"
        )
        self.art_label.setText("No\nArtwork")
        art_panel.addWidget(self.art_label)

        load_art_btn = QPushButton("Load from file…")
        load_art_btn.clicked.connect(self._load_artwork_from_file)
        art_panel.addWidget(load_art_btn)

        self.fetch_art_btn = QPushButton("Fetch online…")
        self.fetch_art_btn.clicked.connect(self._fetch_artwork_online)
        art_panel.addWidget(self.fetch_art_btn)

        clear_art_btn = QPushButton("Remove art")
        clear_art_btn.setObjectName("danger_btn")
        clear_art_btn.clicked.connect(self._clear_artwork)
        art_panel.addWidget(clear_art_btn)

        art_panel.addStretch()
        content.addLayout(art_panel)
        main.addLayout(content)

        # ── Buttons ────────────────────────────────────────────────────────
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        main.addWidget(sep2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("accent_btn")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        main.addLayout(btn_row)

    # ── Load values ───────────────────────────────────────────────────────────

    def _load_values(self):
        self.title_edit.setText(self.track.title or '')
        self.artist_edit.setText(self.track.display_artist())
        self.album_edit.setText(self.track.display_album())
        self.genre_edit.setText(self.track.genre or '')
        self.language_edit.setText(self.track.language or '')
        if self.track.year:
            self.year_spin.setValue(self.track.year)
        if self.track.track_number:
            self.track_spin.setValue(self.track.track_number)

        self._display_artwork(self._artwork_bytes)

    def _display_artwork(self, data: bytes | None):
        if data:
            img = QImage.fromData(data)
            if not img.isNull():
                pm = QPixmap.fromImage(img).scaled(
                    160, 160,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.art_label.setPixmap(pm)
                self.art_label.setText('')
                return
        self.art_label.clear()
        self.art_label.setText("No\nArtwork")

    # ── Artwork actions ───────────────────────────────────────────────────────

    def _load_artwork_from_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.jpg *.jpeg *.png *.bmp *.webp)"
        )
        if path:
            with open(path, 'rb') as f:
                raw = f.read()
            # Compress to JPEG for storage
            img = QImage.fromData(raw)
            if not img.isNull():
                buf = io.BytesIO()
                img.save(buf := io.BytesIO(), 'JPEG', quality=90)
                # Use Qt bytes
                buf = io.BytesIO()
                pix = QPixmap.fromImage(img)
                ba  = pix.toImage()
                out = io.BytesIO()
                import struct
                # Save via Qt to bytes
                from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
                qba = QByteArray()
                qbuf = QBuffer(qba)
                qbuf.open(QIODevice.OpenModeFlag.WriteOnly)
                pix.save(qbuf, 'JPEG', 90)
                qbuf.close()
                self._artwork_bytes   = bytes(qba)
                self._artwork_changed = True
                self._display_artwork(self._artwork_bytes)

    def _fetch_artwork_online(self):
        if self._fetch_thread and self._fetch_thread.isRunning():
            return
        self.fetch_art_btn.setEnabled(False)
        self.fetch_art_btn.setText("Fetching…")
        self._fetch_thread = _ArtworkFetchThread(
            self.artwork_service,
            self.artist_edit.text(),
            self.album_edit.text(),
            self,
        )
        self._fetch_thread.result.connect(self._on_artwork_fetched)
        self._fetch_thread.finished.connect(lambda: (
            self.fetch_art_btn.setEnabled(True),
            self.fetch_art_btn.setText("Fetch online…"),
        ))
        self._fetch_thread.start()

    def _on_artwork_fetched(self, data: bytes):
        self._artwork_bytes   = data
        self._artwork_changed = True
        self._display_artwork(data)

    def _clear_artwork(self):
        self._artwork_bytes   = None
        self._artwork_changed = True
        self._display_artwork(None)

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save(self):
        meta = {
            'title':        self.title_edit.text().strip() or None,
            'artist':       self.artist_edit.text().strip() or None,
            'album':        self.album_edit.text().strip() or None,
            'genre':        self.genre_edit.text().strip() or None,
            'language':     self.language_edit.text().strip() or None,
            'year':         self.year_spin.value() or None,
            'track_number': self.track_spin.value() or None,
        }
        db_meta = {
            'title':        meta['title'],
            'language':     meta['language'],
            'genre':        meta['genre'],
            'year':         meta['year'],
            'track_number': meta['track_number'],
            'artist_name':  meta['artist'],
            'album_name':   meta['album'],
        }

        # File-level write (for title/artist/album/etc.)
        file_meta = dict(meta)
        if self._artwork_changed:
            file_meta['artwork_bytes'] = self._artwork_bytes
            db_meta['artwork_bytes']   = self._artwork_bytes

        # Write to MP3 file
        ok = write_metadata(self.track.file_path, file_meta)
        if not ok:
            QMessageBox.warning(self, "Warning",
                "Tags saved to database but could not write to the MP3 file.\n"
                "The file may be read-only.")

        # Update DB
        self.db.update_track_tags(self.track.id, db_meta)
        self.accept()
