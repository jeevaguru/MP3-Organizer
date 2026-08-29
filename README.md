# 🎵 MP3 Organizer

**A modern, lightweight desktop application to organize, browse, and play your local MP3 collection.**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6%2B-green?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-informational?logo=windows)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📖 Overview

MP3 Organizer is a **standalone desktop application** that brings order to large, messy local MP3 libraries. It scans folders you choose, reads all available metadata from your files (title, artist, album, language, bitrate, file size, and more), stores everything in a local database, and gives you a clean, modern interface to browse, search, edit tags, and play your music — all without needing an internet connection or a subscription.

### Why MP3 Organizer?

- 📂 You have thousands of MP3s scattered across folders with no consistent tagging
- 🔍 You want to quickly search and filter your library by artist, album, genre, or language
- ✏️ You need to fix missing or incorrect tags (title, artist, album art, etc.)
- 🎧 You want a simple player built right into the organizer — no switching apps
- 🔁 You want smart playlists and duplicate detection without paying for a service

---

## ✨ Features

| Feature | Description |
|---|---|
| **Folder Scanning** | Recursively scans any folder for MP3 files and reads all ID3 tags |
| **Local Database** | Stores your library in a fast local SQLite database |
| **Library Browser** | Sortable, searchable table view of your entire collection |
| **Full-text Search** | Instant search across title, artist, album, genre, language, and filename |
| **Tag Editor** | Edit title, artist, album, genre, year, language, track number, and album art |
| **Album Art** | Displays embedded art; fetch missing art from MusicBrainz / iTunes online |
| **Music Player** | Built-in playback with play, pause, next, previous, seek, and volume control |
| **Lyrics** | Auto-fetches synced (LRC) or plain lyrics from LRCLIB; highlights current line |
| **Equalizer** | 10-band EQ with presets (Rock, Pop, Jazz, Bass Boost, etc.) via VLC |
| **Playlists** | Create and manage manual playlists |
| **Smart Playlists** | Rule-based playlists (e.g., "Language = Tamil AND Genre = Pop") |
| **Duplicate Finder** | Detects exact duplicate files using MD5 hash comparison |
| **Auto-watch** | Automatically picks up new/removed files in watched folders |
| **Dark & Light Mode** | Toggle between a dark GitHub-style theme and a clean light theme |
| **Export** | Export your library to CSV or JSON |

---

## 🖥️ Screenshots

> _Coming soon_

---

## ⚙️ Requirements

### System Requirements

| Requirement | Details |
|---|---|
| **Operating System** | Windows 10 / 11 (64-bit) |
| **Python** | 3.10 or newer ([Download](https://www.python.org/downloads/)) |
| **VLC Media Player** | 64-bit version — for the Equalizer and best playback quality ([Download](https://www.videolan.org/vlc/)) |

> **Note:** VLC is optional. If it is not installed, the app falls back to Qt's built-in audio player (playback works, but the Equalizer is disabled).

### Python Dependencies

All Python dependencies are listed in `requirements.txt` and installed automatically (see Installation below):

```
PyQt6            >= 6.6.0   — GUI framework
mutagen          >= 1.47.0  — MP3 tag reading & writing
peewee           >= 3.17.0  — SQLite ORM
watchdog         >= 4.0.0   — Folder auto-watch
syncedlyrics     >= 0.4.0   — Lyrics fetching
musicbrainzngs   >= 0.7.1   — Album art from MusicBrainz
python-vlc       >= 3.0.x   — VLC bindings for playback & EQ
requests         >= 2.31.0  — HTTP client for online art/lyrics
```

---

## 🚀 Installation

### Step 1 — Install Python

Download and install **Python 3.10 or newer** from [python.org](https://www.python.org/downloads/).

> ✅ During installation, check **"Add Python to PATH"**.

### Step 2 — Install VLC (Recommended)

Download and install the **64-bit** version of VLC from [videolan.org](https://www.videolan.org/vlc/).

> ⚠️ Make sure you install the **64-bit** version to match the Python architecture.

### Step 3 — Download MP3 Organizer

**Option A — Clone with Git:**

```bash
git clone https://github.com/YOUR_USERNAME/mp3-organizer.git
cd mp3-organizer
```

**Option B — Download ZIP:**

1. Click the green **"Code"** button on this page
2. Select **"Download ZIP"**
3. Extract the ZIP to any folder (e.g., `C:\mp3-organizer\`)
4. Open a terminal and `cd` into that folder

### Step 4 — Install Python Dependencies

Open a **Command Prompt** or **PowerShell** in the project folder and run:

```bash
pip install -r requirements.txt
```

This will automatically download and install all required libraries.

### Step 5 — Run the App

```bash
python main.py
```

The MP3 Organizer window will open. You're ready to go!

> **Tip:** You can create a shortcut to `python main.py` on your Desktop for quick access.

---

## 🎬 Quick Start Guide

### 1. Scan Your Music Folder

- Click **"＋ Scan Folder"** in the left sidebar
- Browse to your music folder (e.g., `D:\Music`)
- Optionally enable **"Auto-watch"** to automatically detect new/removed files
- Click **"Start Scan"** — your library will populate in seconds

### 2. Browse & Search

- Your library appears in the main table, sorted by artist → album → track
- Use the **search bar** at the top to instantly filter by title, artist, album, genre, language, or filename
- Click any **column header** to sort

### 3. Play Music

- **Double-click** any track to start playing
- Use the **player bar** at the bottom to:
  - ▶ / ⏸ Play & Pause (or press **Space**)
  - ⏮ / ⏭ Previous / Next track
  - Drag the **seek bar** to jump to any position
  - Adjust the **volume slider**
  - Toggle **Shuffle** (⇌) and **Repeat** (↻ → 🔂 → 🔁)

### 4. Edit Tags

- **Right-click** any track → **"Edit Tags"**
- Edit title, artist, album, genre, year, language, track number
- Load or fetch album art automatically
- Click **Save** — changes are written both to the database and to the MP3 file

### 5. Fetch Lyrics

- The **Now Playing** panel on the right shows the current track's lyrics
- Lyrics are fetched automatically from [LRCLIB](https://lrclib.net) when a track plays
- The current line is highlighted as the song progresses
- Click **"Fetch"** to manually re-fetch if needed

### 6. Equalizer

- Click **"EQ"** in the player bar (requires VLC installed)
- Choose from built-in presets: Flat, Rock, Pop, Jazz, Classical, Bass Boost, Vocal, etc.
- Drag individual band sliders to fine-tune
- Settings are saved between sessions

### 7. Find Duplicates

- In the sidebar, click **"🔍 Duplicate Finder"**
- The tool scans your library for exact file duplicates (MD5 hash comparison)
- Review groups of duplicates and choose which copies to delete

### 8. Smart Playlists

- Click the **"+"** next to **SMART PLAYLISTS** in the sidebar
- Add rules like:
  - `Language` → `contains` → `Tamil`
  - `Genre` → `contains` → `Rock`
  - `Year` → `>` → `2000`
- All matching rules apply (AND logic)
- The playlist updates dynamically each time you click it

---

## 📁 Project Structure

```
mp3-organizer/
│
├── main.py                  # Entry point — run this to launch the app
├── config.py                # App-wide constants, paths, EQ presets
├── requirements.txt         # Python dependencies
├── README.md
├── LICENSE
├── .gitignore
│
├── database/
│   ├── models.py            # Database schema (Track, Artist, Album, Playlist…)
│   └── db_manager.py        # All database read/write operations
│
├── scanner/
│   ├── metadata.py          # MP3 tag reading & writing (Mutagen)
│   ├── scanner.py           # Background folder scanner (QThread)
│   └── watcher.py           # File system auto-watch (Watchdog)
│
├── player/
│   └── audio_player.py      # Playback engine (VLC primary, Qt fallback)
│
├── services/
│   ├── lyrics_service.py    # Lyrics fetching & LRC parsing
│   ├── artwork_service.py   # Online album art fetching
│   └── duplicate_service.py # MD5 hash duplicate detection
│
└── ui/
    ├── main_window.py           # Main application window
    ├── sidebar_widget.py        # Navigation sidebar
    ├── library_view.py          # Track browser table
    ├── player_widget.py         # Bottom player bar
    ├── now_playing_panel.py     # Right panel: art + lyrics
    ├── scan_dialog.py           # Folder scan progress dialog
    ├── tag_editor_dialog.py     # Tag editing dialog
    ├── equalizer_dialog.py      # 10-band EQ dialog
    ├── duplicate_finder_dialog.py
    ├── smart_playlist_dialog.py
    └── styles/
        ├── dark.qss             # Dark theme stylesheet
        └── light.qss            # Light theme stylesheet
```

---

## 🗂️ What Gets Stored Locally

The app stores data in your user profile — **nothing is uploaded anywhere**:

| Data | Location |
|---|---|
| Music database | `%APPDATA%\MP3Organizer\library.db` |
| Lyrics cache | `%APPDATA%\MP3Organizer\cache\lyrics\` |
| Artwork cache | `%APPDATA%\MP3Organizer\cache\artwork\` |
| App settings | Windows Registry (`HKCU\Software\MP3Organizer`) |

---

## ❓ Troubleshooting

**App doesn't open / crashes immediately**

- Make sure Python 3.10+ is installed and on your PATH: `python --version`
- Re-run `pip install -r requirements.txt` to ensure all dependencies are installed

**No sound / playback not working**

- Install 64-bit VLC from [videolan.org](https://www.videolan.org/vlc/)
- Ensure VLC is installed in its default location (`C:\Program Files\VideoLAN\VLC`)

**Equalizer button is greyed out**

- The EQ requires VLC. Install 64-bit VLC and restart the app.

**Tags not saving to file**

- The MP3 file may be read-only or in a protected folder. Check file permissions.

**Lyrics not found**

- LRCLIB may not have lyrics for that track. Try editing the title/artist in Tag Editor for better matching, then click "Fetch" again.

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

- 🐛 Report bugs by opening an [Issue](../../issues)
- 💡 Suggest features in [Discussions](../../discussions)
- 🔧 Submit a [Pull Request](../../pulls)

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

Made with ❤️ and Python
