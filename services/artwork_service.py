"""
MP3 Organizer — Album Art Service
Fetches album artwork from MusicBrainz / Cover Art Archive, with an
iTunes Search API fallback. Results are cached locally as JPEG files.
"""
import hashlib
import re
from pathlib import Path

from config import ARTWORK_CACHE_DIR


class ArtworkService:
    """
    Fetch album artwork by artist + album (or artist + title for singles).
    Returns raw JPEG bytes or None.
    """

    def __init__(self):
        self._cache_dir = Path(ARTWORK_CACHE_DIR)

    # ── Public ────────────────────────────────────────────────────────────────

    def fetch(self, artist: str, album: str, title: str = '') -> bytes | None:
        """
        Return JPEG bytes for the best matching album art, or None.
        Tries (in order): local cache → MusicBrainz → iTunes.
        """
        key    = self._cache_key(artist, album or title)
        cached = self._load_cache(key)
        if cached:
            return cached

        data = self._fetch_musicbrainz(artist, album or title)
        if not data:
            data = self._fetch_itunes(artist, album or title)

        if data:
            self._save_cache(key, data)

        return data

    # ── Backends ──────────────────────────────────────────────────────────────

    def _fetch_musicbrainz(self, artist: str, album: str) -> bytes | None:
        try:
            import musicbrainzngs as mb
            mb.set_useragent("MP3Organizer", "1.0", "contact@mp3organizer.local")

            result = mb.search_releases(
                artist=artist,
                release=album,
                limit=5,
            )
            releases = result.get('release-list', [])
            for rel in releases:
                mbid = rel.get('id')
                if mbid:
                    art = self._fetch_caa(mbid)
                    if art:
                        return art
        except Exception as e:
            print(f"[artwork] MusicBrainz error: {e}")
        return None

    def _fetch_caa(self, mbid: str) -> bytes | None:
        """Cover Art Archive."""
        try:
            import requests
            url = f"https://coverartarchive.org/release/{mbid}/front"
            r   = requests.get(url, timeout=10, headers={"User-Agent": "MP3Organizer/1.0"})
            if r.status_code == 200 and r.content:
                return r.content
        except Exception as e:
            print(f"[artwork] CAA error for {mbid}: {e}")
        return None

    def _fetch_itunes(self, artist: str, album: str) -> bytes | None:
        """iTunes Search API fallback — no API key required."""
        try:
            import requests
            term = f"{artist} {album}".strip()
            r = requests.get(
                "https://itunes.apple.com/search",
                params={"term": term, "entity": "album", "limit": 5},
                timeout=8,
                headers={"User-Agent": "MP3Organizer/1.0"},
            )
            if r.status_code == 200:
                results = r.json().get('results', [])
                for item in results:
                    art_url = item.get('artworkUrl100', '')
                    if art_url:
                        # Upgrade to 600×600
                        art_url = art_url.replace('100x100bb', '600x600bb')
                        img_r = requests.get(art_url, timeout=8)
                        if img_r.status_code == 200:
                            return img_r.content
        except Exception as e:
            print(f"[artwork] iTunes error: {e}")
        return None

    # ── Cache ─────────────────────────────────────────────────────────────────

    def _cache_key(self, artist: str, album: str) -> str:
        raw  = f"{artist}_{album}".lower()
        safe = re.sub(r'[^\w]', '_', raw)[:60]
        h    = hashlib.md5(raw.encode()).hexdigest()[:8]
        return f"{safe}_{h}.jpg"

    def _load_cache(self, key: str) -> bytes | None:
        path = self._cache_dir / key
        if path.exists():
            try:
                return path.read_bytes()
            except Exception:
                return None
        return None

    def _save_cache(self, key: str, data: bytes):
        path = self._cache_dir / key
        try:
            path.write_bytes(data)
        except Exception:
            pass
