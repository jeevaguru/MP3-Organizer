"""
MP3 Organizer — Player Widget (bottom bar)
Transport controls, seek bar, volume, and EQ button.
"""
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QSlider, QSizePolicy, QFrame
)
from PyQt6.QtGui import QPixmap, QImage, QIcon


def _fmt(ms: int) -> str:
    s   = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class PlayerWidget(QWidget):
    """
    Bottom player bar.

    Signals emitted:
        play_pause_clicked()
        next_clicked()
        prev_clicked()
        seek_requested(ms: int)
        volume_changed(vol: int)
        eq_clicked()
        shuffle_clicked(bool)
        repeat_clicked(str)   # 'none'|'one'|'all'
    """
    play_pause_clicked = pyqtSignal()
    next_clicked       = pyqtSignal()
    prev_clicked       = pyqtSignal()
    seek_requested     = pyqtSignal(int)
    volume_changed     = pyqtSignal(int)
    eq_clicked         = pyqtSignal()
    shuffle_clicked    = pyqtSignal(bool)
    repeat_clicked     = pyqtSignal(str)

    def __init__(self, player, parent=None):
        super().__init__(parent)
        self._player         = player
        self._duration_ms    = 0
        self._seeking        = False
        self._is_playing     = False
        self._repeat_mode    = 'none'   # 'none' | 'one' | 'all'
        self._shuffle        = False

        self.setObjectName("player_bar")
        self.setFixedHeight(90)
        self._build_ui()

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 8)
        root.setSpacing(0)

        # ── Left: Now playing info ─────────────────────────────────────────
        info_widget = QWidget()
        info_widget.setFixedWidth(240)
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(10)

        # Thumbnail
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(52, 52)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet(
            "border-radius:6px;background-color:#21262d;color:#6e7681;font-size:10px;"
        )
        self.thumb_label.setText("♪")
        info_layout.addWidget(self.thumb_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel("No track loaded")
        self.title_lbl.setObjectName("track_title_label")
        self.title_lbl.setMaximumWidth(165)
        font = self.title_lbl.font()
        font.setPointSize(10)
        self.title_lbl.setFont(font)
        self.title_lbl.setWordWrap(False)
        text_col.addWidget(self.title_lbl)

        self.artist_lbl = QLabel("")
        self.artist_lbl.setObjectName("track_artist_label")
        self.artist_lbl.setMaximumWidth(165)
        text_col.addWidget(self.artist_lbl)

        info_layout.addLayout(text_col, 1)
        root.addWidget(info_widget)

        # ── Center: Transport + seek ───────────────────────────────────────
        center = QVBoxLayout()
        center.setSpacing(4)
        center.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Transport row
        transport = QHBoxLayout()
        transport.setSpacing(6)
        transport.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.shuffle_btn = QPushButton("⇌")
        self.shuffle_btn.setObjectName("icon_btn")
        self.shuffle_btn.setCheckable(True)
        self.shuffle_btn.setToolTip("Shuffle")
        self.shuffle_btn.clicked.connect(self._on_shuffle)
        transport.addWidget(self.shuffle_btn)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setObjectName("transport_btn")
        self.prev_btn.setToolTip("Previous (or restart if >3s)")
        self.prev_btn.clicked.connect(self.prev_clicked)
        transport.addWidget(self.prev_btn)

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("play_btn")
        self.play_btn.setToolTip("Play / Pause  [Space]")
        self.play_btn.clicked.connect(self.play_pause_clicked)
        transport.addWidget(self.play_btn)

        self.next_btn = QPushButton("⏭")
        self.next_btn.setObjectName("transport_btn")
        self.next_btn.setToolTip("Next")
        self.next_btn.clicked.connect(self.next_clicked)
        transport.addWidget(self.next_btn)

        self.repeat_btn = QPushButton("↻")
        self.repeat_btn.setObjectName("icon_btn")
        self.repeat_btn.setCheckable(True)
        self.repeat_btn.setToolTip("Repeat: none → one → all")
        self.repeat_btn.clicked.connect(self._on_repeat)
        transport.addWidget(self.repeat_btn)

        center.addLayout(transport)

        # Seek row
        seek_row = QHBoxLayout()
        seek_row.setSpacing(8)

        self.pos_label = QLabel("0:00")
        self.pos_label.setObjectName("time_label")
        self.pos_label.setFixedWidth(40)
        self.pos_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        seek_row.addWidget(self.pos_label)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.sliderPressed.connect(self._on_seek_press)
        self.seek_slider.sliderReleased.connect(self._on_seek_release)
        seek_row.addWidget(self.seek_slider, 1)

        self.dur_label = QLabel("0:00")
        self.dur_label.setObjectName("time_label")
        self.dur_label.setFixedWidth(40)
        self.dur_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        seek_row.addWidget(self.dur_label)

        center.addLayout(seek_row)
        root.addLayout(center, 1)

        # ── Right: Volume + EQ ────────────────────────────────────────────
        right = QHBoxLayout()
        right.setSpacing(8)
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right.setContentsMargins(10, 0, 0, 0)

        self.vol_icon_btn = QPushButton("🔊")
        self.vol_icon_btn.setObjectName("icon_btn")
        self.vol_icon_btn.setToolTip("Mute / Unmute")
        self.vol_icon_btn.clicked.connect(self._toggle_mute)
        right.addWidget(self.vol_icon_btn)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(90)
        self.vol_slider.setToolTip("Volume")
        self.vol_slider.valueChanged.connect(self.volume_changed)
        right.addWidget(self.vol_slider)

        self.vol_label = QLabel("80%")
        self.vol_label.setObjectName("time_label")
        self.vol_label.setFixedWidth(32)
        right.addWidget(self.vol_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedHeight(24)
        right.addWidget(sep)

        self.eq_btn = QPushButton("EQ")
        self.eq_btn.setObjectName("icon_btn")
        self.eq_btn.setToolTip("Equalizer")
        self.eq_btn.clicked.connect(self.eq_clicked)
        right.addWidget(self.eq_btn)

        right_widget = QWidget()
        right_widget.setFixedWidth(230)
        right_widget.setLayout(right)
        root.addWidget(right_widget)

        # Connect volume slider to label
        self.vol_slider.valueChanged.connect(
            lambda v: self.vol_label.setText(f"{v}%")
        )

        self._prev_vol = 80
        self._muted    = False

    # ── Public slots ──────────────────────────────────────────────────────────

    def set_state(self, state: str):
        self._is_playing = (state == 'playing')
        self.play_btn.setText("⏸" if self._is_playing else "▶")

    def set_position(self, ms: int):
        if self._seeking or self._duration_ms == 0:
            return
        self.pos_label.setText(_fmt(ms))
        ratio = ms / self._duration_ms
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(int(ratio * 1000))
        self.seek_slider.blockSignals(False)

    def set_duration(self, ms: int):
        self._duration_ms = ms
        self.dur_label.setText(_fmt(ms))

    def set_volume(self, vol: int):
        self.vol_slider.blockSignals(True)
        self.vol_slider.setValue(vol)
        self.vol_slider.blockSignals(False)
        self.vol_label.setText(f"{vol}%")

    def set_track(self, track):
        self.title_lbl.setText(track.display_title())
        self.artist_lbl.setText(track.display_artist())
        # Thumbnail
        if track.artwork_blob:
            img = QImage.fromData(bytes(track.artwork_blob))
            if not img.isNull():
                pm = QPixmap.fromImage(img).scaled(
                    52, 52,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.thumb_label.setPixmap(pm)
                return
        self.thumb_label.clear()
        self.thumb_label.setText("♪")

    # ── Private ───────────────────────────────────────────────────────────────

    def _on_seek_press(self):
        self._seeking = True

    def _on_seek_release(self):
        if self._duration_ms > 0:
            ratio = self.seek_slider.value() / 1000.0
            ms    = int(ratio * self._duration_ms)
            self.seek_requested.emit(ms)
        self._seeking = False

    def _toggle_mute(self):
        if self._muted:
            self.vol_slider.setValue(self._prev_vol)
            self.vol_icon_btn.setText("🔊")
            self._muted = False
        else:
            self._prev_vol = self.vol_slider.value()
            self.vol_slider.setValue(0)
            self.vol_icon_btn.setText("🔇")
            self._muted = True

    def _on_shuffle(self, checked: bool):
        self._shuffle = checked
        self.shuffle_clicked.emit(checked)

    def _on_repeat(self, _checked: bool):
        modes = ['none', 'one', 'all']
        idx   = modes.index(self._repeat_mode)
        self._repeat_mode = modes[(idx + 1) % 3]
        labels = {'none': '↻', 'one': '🔂', 'all': '🔁'}
        self.repeat_btn.setText(labels[self._repeat_mode])
        self.repeat_btn.setChecked(self._repeat_mode != 'none')
        self.repeat_clicked.emit(self._repeat_mode)
