"""
MP3 Organizer — Lyrics Service  (syncedlyrics / LRCLIB)
"""
import os
import re
from pathlib import Path

from config import LYRICS_CACHE_DIR


class LyricsService:
    """
    Fetches lyrics for a given artist + title combination.
    Results are cached locally as .lrc files (synced) or .txt (plain).
    """

    def __init__(self):
        self._cache_dir = LYRICS_CACHE_DIR
        # Attempt to import syncedlyrics; gracefully degrade if not installed.
        try:
            import syncedlyrics as _sl
            self._sl = _sl
        except ImportError:
            self._sl = None

    # ── Public ────────────────────────────────────────────────────────────────

    def fetch(self, title: str, artist: str, synced: bool = True) -> str | None:
        """
        Return lyrics string (LRC format if synced, plain text otherwise).
        Returns None if not found.
        """
        if not title and not artist:
            return None

        # Cache key
        cache_key  = self._cache_key(title, artist, synced)
        cached     = self._load_cache(cache_key)
        if cached is not None:
            return cached

        # Fetch from network
        lyrics = None
        search_term = f"{artist} {title}".strip()

        if self._sl is not None:
            try:
                if synced:
                    lyrics = self._sl.search(
                        search_term,
                        synced_only=True,
                        providers=["Lrclib"],
                    )
                if not lyrics:
                    lyrics = self._sl.search(
                        search_term,
                        plain_only=True,
                        providers=["Lrclib"],
                    )
            except Exception as e:
                print(f"[lyrics] syncedlyrics error: {e}")
        
        if not lyrics:
            # Direct LRCLIB fallback
            lyrics = self._fetch_lrclib(title, artist, synced)

        if lyrics:
            self._save_cache(cache_key, lyrics)

        return lyrics

    def parse_lrc(self, lrc_text: str) -> list[tuple[float, str]]:
        """
        Parse an LRC string into a list of (timestamp_seconds, line) tuples.
        Returns an empty list for plain text or unparseable content.
        """
        pattern = re.compile(r'\[(\d+):(\d+(?:\.\d+)?)\](.*)')
        result  = []
        for line in lrc_text.splitlines():
            m = pattern.match(line)
            if m:
                minutes = float(m.group(1))
                seconds = float(m.group(2))
                text    = m.group(3).strip()
                ts      = minutes * 60 + seconds
                result.append((ts, text))
        result.sort(key=lambda x: x[0])
        return result

    # ── Private ───────────────────────────────────────────────────────────────

    def _cache_key(self, title: str, artist: str, synced: bool) -> str:
        safe = re.sub(r'[^\w\s-]', '', f"{artist}_{title}").strip().replace(' ', '_')
        ext  = '.lrc' if synced else '.txt'
        return safe[:80] + ext

    def _load_cache(self, key: str) -> str | None:
        path = self._cache_dir / key
        if path.exists():
            try:
                return path.read_text(encoding='utf-8')
            except Exception:
                return None
        return None

    def _save_cache(self, key: str, content: str):
        path = self._cache_dir / key
        try:
            path.write_text(content, encoding='utf-8')
        except Exception:
            pass

    def _fetch_lrclib(self, title: str, artist: str, synced: bool) -> str | None:
        try:
            import requests
            params = {}
            if title:  params['track_name']  = title
            if artist: params['artist_name'] = artist
            r = requests.get(
                "https://lrclib.net/api/get",
                params=params,
                headers={"User-Agent": "MP3Organizer/1.0"},
                timeout=8,
            )
            if r.status_code == 200:
                data = r.json()
                if synced and data.get('syncedLyrics'):
                    return data['syncedLyrics']
                if data.get('plainLyrics'):
                    return data['plainLyrics']
        except Exception as e:
            print(f"[lyrics] LRCLIB fallback error: {e}")
        return None
