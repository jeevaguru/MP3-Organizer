"""
MP3 Organizer — Audio Player  (python-vlc + QtMultimedia fallback)
"""
import os

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

# ── VLC detection ─────────────────────────────────────────────────────────────
VLC_AVAILABLE = False
try:
    import vlc as _vlc
    # Quick smoke-test: instantiate a throw-away VLC instance
    _test = _vlc.Instance()
    if _test:
        VLC_AVAILABLE = True
        del _test
except Exception:
    pass


class AudioPlayer(QObject):
    """
    Full-featured audio player built on python-vlc (with graceful fallback to
    QtMultimedia if VLC is not installed).

    Signals
    -------
    position_changed(int)   current playback position in milliseconds
    duration_changed(int)   total track duration in milliseconds
    state_changed(str)      one of: 'playing' | 'paused' | 'stopped' | 'ended'
    track_changed(object)   Track model instance
    volume_changed(int)     volume 0–100
    """

    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    state_changed    = pyqtSignal(str)
    track_changed    = pyqtSignal(object)
    volume_changed   = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._queue          = []
        self._current_index  = -1
        self._current_track  = None
        self._volume         = 80
        self._shuffle        = False
        self._repeat         = False          # repeat-one
        self._repeat_all     = False          # repeat-queue
        self._end_reached    = False          # flag from VLC callback thread

        # ── Poll timer ────────────────────────────────────────────────────
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._poll)

        # ── Backend setup ─────────────────────────────────────────────────
        if VLC_AVAILABLE:
            self._setup_vlc()
        else:
            self._setup_qt()

    # ── VLC backend ──────────────────────────────────────────────────────────

    def _setup_vlc(self):
        self._backend  = 'vlc'
        self._instance = _vlc.Instance('--no-xlib', '--quiet')
        self._player   = self._instance.media_player_new()
        self._eq       = _vlc.AudioEqualizer()
        self._player.audio_set_volume(self._volume)

        em = self._player.event_manager()
        em.event_attach(_vlc.EventType.MediaPlayerEndReached, self._vlc_end_cb)

    def _vlc_end_cb(self, event):
        """Called on VLC's thread — just set a flag."""
        self._end_reached = True

    def _vlc_load(self, file_path: str):
        media = self._instance.media_new(file_path)
        self._player.set_media(media)
        self._player.play()
        # Duration becomes available shortly after play starts
        QTimer.singleShot(600, self._emit_duration)

    # ── QtMultimedia fallback ─────────────────────────────────────────────────

    def _setup_qt(self):
        self._backend = 'qt'
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
        self._qt_player = QMediaPlayer(self)
        self._qt_audio  = QAudioOutput(self)
        self._qt_player.setAudioOutput(self._qt_audio)
        self._qt_audio.setVolume(self._volume / 100.0)
        self._qt_player.playbackStateChanged.connect(self._qt_state_cb)
        self._qt_player.positionChanged.connect(self.position_changed)
        self._qt_player.durationChanged.connect(self.duration_changed)

    def _qt_state_cb(self, state):
        from PyQt6.QtMultimedia import QMediaPlayer
        map_ = {
            QMediaPlayer.PlaybackState.PlayingState: 'playing',
            QMediaPlayer.PlaybackState.PausedState:  'paused',
            QMediaPlayer.PlaybackState.StoppedState: 'stopped',
        }
        self.state_changed.emit(map_.get(state, 'stopped'))

    def _qt_load(self, file_path: str):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtMultimedia import QMediaPlayer
        self._qt_player.setSource(QUrl.fromLocalFile(file_path))
        self._qt_player.play()

    # ── Common poll ──────────────────────────────────────────────────────────

    def _poll(self):
        if self._backend == 'vlc':
            if self._end_reached:
                self._end_reached = False
                self._handle_track_end()
                return
            pos = self._player.get_time()
            if pos >= 0:
                self.position_changed.emit(pos)

    def _emit_duration(self):
        if self._backend == 'vlc':
            dur = self._player.get_length()
            if dur > 0:
                self.duration_changed.emit(dur)

    def _handle_track_end(self):
        if self._repeat:
            # Replay same track
            self.seek(0)
            if self._backend == 'vlc':
                self._player.play()
        elif self._current_index < len(self._queue) - 1:
            self.next()
        elif self._repeat_all:
            self.set_queue(self._queue, 0)
        else:
            self.state_changed.emit('ended')

    # ── Public API ────────────────────────────────────────────────────────────

    def load_track(self, track):
        self._current_track = track
        if self._backend == 'vlc':
            self._vlc_load(track.file_path)
        else:
            self._qt_load(track.file_path)
        self._timer.start()
        self.track_changed.emit(track)
        self.state_changed.emit('playing')

    def play(self):
        if self._backend == 'vlc':
            self._player.play()
        else:
            self._qt_player.play()
        self._timer.start()
        self.state_changed.emit('playing')

    def pause(self):
        if self._backend == 'vlc':
            self._player.pause()
            self.state_changed.emit('paused')
        else:
            self._qt_player.pause()

    def toggle_play_pause(self):
        if self._backend == 'vlc':
            state = self._player.get_state()
            if state == _vlc.State.Playing:
                self.pause()
            else:
                self.play()
        else:
            from PyQt6.QtMultimedia import QMediaPlayer
            if self._qt_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.pause()
            else:
                self.play()

    def stop(self):
        if self._backend == 'vlc':
            self._player.stop()
        else:
            self._qt_player.stop()
        self._timer.stop()
        self.state_changed.emit('stopped')
        self.position_changed.emit(0)

    def seek(self, ms: int):
        if self._backend == 'vlc':
            self._player.set_time(max(0, ms))
        else:
            self._qt_player.setPosition(max(0, ms))

    def set_volume(self, vol: int):
        self._volume = max(0, min(100, vol))
        if self._backend == 'vlc':
            self._player.audio_set_volume(self._volume)
        else:
            self._qt_audio.setVolume(self._volume / 100.0)
        self.volume_changed.emit(self._volume)

    def get_position(self) -> int:
        if self._backend == 'vlc':
            return max(0, self._player.get_time())
        return self._qt_player.position()

    def get_duration(self) -> int:
        if self._backend == 'vlc':
            return max(0, self._player.get_length())
        return self._qt_player.duration()

    def is_playing(self) -> bool:
        if self._backend == 'vlc':
            return self._player.get_state() == _vlc.State.Playing
        from PyQt6.QtMultimedia import QMediaPlayer
        return self._qt_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    # ── Queue management ─────────────────────────────────────────────────────

    def set_queue(self, tracks, start_index: int = 0):
        self._queue = list(tracks)
        self._current_index = start_index
        if self._queue and 0 <= self._current_index < len(self._queue):
            self.load_track(self._queue[self._current_index])

    def add_to_queue(self, tracks):
        self._queue.extend(tracks)
        # If nothing playing, start immediately
        if self._current_index < 0 and self._queue:
            self._current_index = len(self._queue) - len(tracks)
            self.load_track(self._queue[self._current_index])

    def next(self):
        if not self._queue:
            return
        if self._current_index < len(self._queue) - 1:
            self._current_index += 1
            self.load_track(self._queue[self._current_index])

    def prev(self):
        if not self._queue:
            return
        # If > 3 s in, restart current track
        if self.get_position() > 3000:
            self.seek(0)
            return
        if self._current_index > 0:
            self._current_index -= 1
            self.load_track(self._queue[self._current_index])

    def set_shuffle(self, enabled: bool):
        self._shuffle = enabled

    def set_repeat(self, mode: str):
        """mode: 'none' | 'one' | 'all'"""
        self._repeat     = (mode == 'one')
        self._repeat_all = (mode == 'all')

    # ── Equalizer (VLC only) ──────────────────────────────────────────────────

    @property
    def eq_available(self) -> bool:
        return self._backend == 'vlc'

    def set_eq_band(self, band_index: int, amp: float):
        if self._backend == 'vlc':
            self._eq.set_amp_at_index(float(amp), band_index)
            self._player.set_equalizer(self._eq)

    def set_eq_preamp(self, amp: float):
        if self._backend == 'vlc':
            self._eq.set_preamp(float(amp))
            self._player.set_equalizer(self._eq)

    def get_eq_band(self, band_index: int) -> float:
        if self._backend == 'vlc':
            return self._eq.get_amp_at_index(band_index)
        return 0.0

    def get_eq_preamp(self) -> float:
        if self._backend == 'vlc':
            return self._eq.get_preamp()
        return 0.0

    def reset_eq(self):
        if self._backend == 'vlc':
            self._eq = _vlc.AudioEqualizer()
            self._player.set_equalizer(self._eq)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def current_track(self):
        return self._current_track

    @property
    def queue(self):
        return list(self._queue)

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def backend(self) -> str:
        return self._backend
