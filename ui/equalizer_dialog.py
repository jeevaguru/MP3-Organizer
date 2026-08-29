"""
MP3 Organizer — Equalizer Dialog  (python-vlc 10-band EQ)
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QComboBox, QFrame, QGroupBox, QWidget, QSizePolicy
)

from config import EQ_BANDS, EQ_BAND_LABELS, EQ_PRESETS
from player.audio_player import AudioPlayer


class _BandSlider(QWidget):
    """Vertical slider + Hz label for one EQ band."""
    changed = pyqtSignal(int, float)   # band_index, amp

    def __init__(self, band_index: int, label: str, parent=None):
        super().__init__(parent)
        self._index = band_index
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.value_lbl = QLabel("+0.0")
        self.value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_lbl.setStyleSheet("font-size:10px;color:#8b949e;font-family:Consolas,monospace;")
        layout.addWidget(self.value_lbl)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setRange(-200, 200)   # ×0.1 dB → −20 … +20
        self.slider.setValue(0)
        self.slider.setFixedWidth(20)
        self.slider.setMinimumHeight(140)
        self.slider.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.slider.valueChanged.connect(self._on_change)
        layout.addWidget(self.slider, alignment=Qt.AlignmentFlag.AlignHCenter)

        hz_lbl = QLabel(label)
        hz_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hz_lbl.setStyleSheet("font-size:10px;color:#6e7681;")
        layout.addWidget(hz_lbl)

    def _on_change(self, raw: int):
        amp = raw / 10.0
        self.value_lbl.setText(f"{amp:+.1f}")
        self.changed.emit(self._index, amp)

    def set_value(self, amp: float):
        self.slider.blockSignals(True)
        self.slider.setValue(int(amp * 10))
        self.value_lbl.setText(f"{amp:+.1f}")
        self.slider.blockSignals(False)

    def get_value(self) -> float:
        return self.slider.value() / 10.0


class EqualizerDialog(QDialog):
    def __init__(self, player: AudioPlayer, settings, parent=None):
        super().__init__(parent)
        self._player   = player
        self._settings = settings
        self.setWindowTitle("Equalizer")
        self.setMinimumWidth(560)
        self.setModal(False)   # Non-modal so you can hear changes live
        self._build_ui()
        self._load_settings()

        if not player.eq_available:
            for b in self._bands:
                b.slider.setEnabled(False)
            self._preamp.setEnabled(False)
            self._preset_cb.setEnabled(False)

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(16)
        main.setContentsMargins(20, 20, 20, 20)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("Equalizer")
        title.setStyleSheet("font-size:17px;font-weight:700;")
        header_row.addWidget(title)

        if not self._player.eq_available:
            warn = QLabel("⚠ VLC not found — EQ disabled")
            warn.setStyleSheet("color:#d29922;font-size:12px;")
            header_row.addWidget(warn)

        header_row.addStretch()
        main.addLayout(header_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        main.addWidget(sep)

        # Preset row
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))
        self._preset_cb = QComboBox()
        self._preset_cb.addItems(list(EQ_PRESETS.keys()))
        self._preset_cb.currentTextChanged.connect(self._apply_preset)
        preset_row.addWidget(self._preset_cb)
        preset_row.addStretch()

        reset_btn = QPushButton("Reset")
        reset_btn.setFixedWidth(70)
        reset_btn.clicked.connect(self._reset)
        preset_row.addWidget(reset_btn)
        main.addLayout(preset_row)

        # Preamp
        preamp_row = QHBoxLayout()
        preamp_row.addWidget(QLabel("Preamp"))
        self._preamp = QSlider(Qt.Orientation.Horizontal)
        self._preamp.setRange(-200, 200)
        self._preamp.setValue(0)
        self._preamp.valueChanged.connect(self._on_preamp)
        preamp_row.addWidget(self._preamp, 1)
        self._preamp_lbl = QLabel("+0.0 dB")
        self._preamp_lbl.setFixedWidth(60)
        self._preamp_lbl.setStyleSheet("font-family:Consolas,monospace;font-size:12px;")
        preamp_row.addWidget(self._preamp_lbl)
        main.addLayout(preamp_row)

        # Zero reference line label
        ref_lbl = QLabel("0 dB")
        ref_lbl.setStyleSheet("color:#6e7681;font-size:10px;")
        ref_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Bands
        bands_box = QGroupBox("Frequency Bands (dB)")
        bands_layout = QHBoxLayout(bands_box)
        bands_layout.setSpacing(4)
        self._bands: list[_BandSlider] = []
        for i, label in enumerate(EQ_BAND_LABELS):
            bs = _BandSlider(i, label)
            bs.changed.connect(self._on_band_changed)
            self._bands.append(bs)
            bands_layout.addWidget(bs)
        main.addWidget(bands_box)

        # Buttons
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        main.addWidget(sep2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Save & Close")
        save_btn.setObjectName("accent_btn")
        save_btn.clicked.connect(self._save_and_close)
        btn_row.addWidget(save_btn)
        main.addLayout(btn_row)

    # ── Handlers ─────────────────────────────────────────────────────────────

    def _on_band_changed(self, band_index: int, amp: float):
        self._player.set_eq_band(band_index, amp)

    def _on_preamp(self, raw: int):
        amp = raw / 10.0
        self._preamp_lbl.setText(f"{amp:+.1f} dB")
        self._player.set_eq_preamp(amp)

    def _apply_preset(self, name: str):
        amps = EQ_PRESETS.get(name, [0] * 10)
        for i, band in enumerate(self._bands):
            band.set_value(amps[i])
            self._player.set_eq_band(i, amps[i])

    def _reset(self):
        self._preset_cb.blockSignals(True)
        self._preset_cb.setCurrentText("Flat")
        self._preset_cb.blockSignals(False)
        self._apply_preset("Flat")
        self._preamp.setValue(0)

    def _save_and_close(self):
        self._save_settings()
        self.accept()

    def _save_settings(self):
        self._settings.setValue("eq_preset", self._preset_cb.currentText())
        amps = [b.get_value() for b in self._bands]
        self._settings.setValue("eq_bands", amps)
        self._settings.setValue("eq_preamp", self._preamp.value() / 10.0)

    def _load_settings(self):
        preset = self._settings.value("eq_preset", "Flat")
        bands  = self._settings.value("eq_bands", None)
        preamp = float(self._settings.value("eq_preamp", 0.0))

        if bands and len(bands) == 10:
            for i, b in enumerate(self._bands):
                amp = float(bands[i])
                b.set_value(amp)
                self._player.set_eq_band(i, amp)
            self._preset_cb.setCurrentText(preset)
        else:
            self._preset_cb.setCurrentText(preset)
            self._apply_preset(preset)

        self._preamp.setValue(int(preamp * 10))
        self._player.set_eq_preamp(preamp)
