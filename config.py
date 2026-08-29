"""
MP3 Organizer — Application Configuration
"""
import os
from pathlib import Path

# ── Application Info ─────────────────────────────────────────────────────────
APP_NAME = "MP3 Organizer"
APP_VERSION = "1.0.0"
SETTINGS_ORG = "MP3Organizer"
SETTINGS_APP = "MP3Organizer"

# ── Data Directories ─────────────────────────────────────────────────────────
DATA_DIR = Path.home() / ".mp3organizer"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = str(DATA_DIR / "library.db")

ARTWORK_CACHE_DIR = DATA_DIR / "artwork_cache"
ARTWORK_CACHE_DIR.mkdir(parents=True, exist_ok=True)

LYRICS_CACHE_DIR = DATA_DIR / "lyrics_cache"
LYRICS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Supported Formats ─────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {'.mp3', '.m4a', '.flac', '.ogg', '.wav', '.wma', '.aac'}

# ── Scanner ───────────────────────────────────────────────────────────────────
SCAN_CHUNK_SIZE = 50  # Emit DB commit every N files

# ── Artwork Sizes ─────────────────────────────────────────────────────────────
THUMBNAIL_SIZE      = (50, 50)
ARTWORK_DISPLAY_SIZE = (260, 260)
ARTWORK_MAX_STORE   = (600, 600)   # Max resolution stored in DB

# ── Player ────────────────────────────────────────────────────────────────────
DEFAULT_VOLUME = 80                 # 0–100
POSITION_UPDATE_MS = 500           # Timer interval for seek bar

# ── Window Layout ─────────────────────────────────────────────────────────────
SIDEBAR_WIDTH      = 220
NOW_PLAYING_WIDTH  = 290
PLAYER_BAR_HEIGHT  = 90
WINDOW_MIN_WIDTH   = 1150
WINDOW_MIN_HEIGHT  = 680

# ── Equalizer ─────────────────────────────────────────────────────────────────
EQ_BANDS = [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
EQ_BAND_LABELS = ["31", "62", "125", "250", "500", "1K", "2K", "4K", "8K", "16K"]

EQ_PRESETS = {
    "Flat":        [0,  0,  0,  0,  0,  0,  0,  0,  0,  0],
    "Rock":        [5,  4,  3,  0, -1, -1,  0,  3,  4,  5],
    "Pop":         [-1,-1,  0,  2,  4,  4,  2,  0, -1, -1],
    "Classical":   [5,  4,  3,  2, -1, -1,  0,  2,  3,  4],
    "Jazz":        [4,  3,  1,  2, -1, -1,  0,  1,  3,  4],
    "Electronic":  [5,  4,  1, -1, -3, -1,  0,  1,  4,  5],
    "Bass Boost":  [8,  6,  4,  2,  0,  0,  0,  0,  0,  0],
    "Treble Boost":[0,  0,  0,  0,  0,  0,  2,  4,  6,  8],
    "Vocal Boost": [-2,-1,  0,  3,  5,  5,  3,  1,  0, -1],
    "Loudness":    [6,  4,  0,  0, -2,  0,  0,  0,  4,  6],
}

# ── Smart Playlist Fields ─────────────────────────────────────────────────────
SMART_CRITERIA_FIELDS = [
    "title", "artist", "album", "genre", "language",
    "year", "bitrate", "play_count", "duration",
]

SMART_CRITERIA_OPS = ["contains", "is", "is not", "starts with", ">", "<", ">=", "<="]
