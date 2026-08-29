"""
MP3 Organizer — Metadata Reader / Writer  (Mutagen)
"""
import os
import hashlib
from typing import Optional, Dict, Any

from mutagen.mp3 import MP3
from mutagen.id3 import (
    ID3, ID3NoHeaderError,
    TIT2, TALB, TPE1, TLAN, TRCK, TDRC, TCON, APIC, PictureType
)


# ── Read ──────────────────────────────────────────────────────────────────────

def read_metadata(file_path: str) -> Dict[str, Any]:
    """Extract all metadata from an MP3 file. Returns a flat dict."""
    result: Dict[str, Any] = {
        'title':        None,
        'album':        None,
        'artist':       None,
        'language':     None,
        'bitrate':      None,
        'duration':     None,
        'year':         None,
        'genre':        None,
        'track_number': None,
        'artwork_bytes': None,
        'has_artwork':  False,
        'file_size':    0,
        'file_name':    '',
    }

    try:
        result['file_size'] = os.path.getsize(file_path)
        result['file_name'] = os.path.basename(file_path)

        # ── Audio info ─────────────────────────────────────────────────────
        try:
            audio = MP3(file_path)
            if audio.info:
                result['bitrate']  = int(audio.info.bitrate / 1000)
                result['duration'] = int(audio.info.length)
        except Exception:
            pass

        # ── ID3 tags ───────────────────────────────────────────────────────
        try:
            tags = ID3(file_path)

            result['title']  = _first(tags, 'TIT2')
            result['album']  = _first(tags, 'TALB')
            result['artist'] = _first(tags, 'TPE1')
            result['language'] = _first(tags, 'TLAN')
            result['genre']  = _first(tags, 'TCON')

            trck = _first(tags, 'TRCK')
            if trck:
                try:
                    result['track_number'] = int(str(trck).split('/')[0])
                except ValueError:
                    pass

            tdrc = _first(tags, 'TDRC')
            if tdrc:
                try:
                    result['year'] = int(str(tdrc)[:4])
                except ValueError:
                    pass

            # Album art (first APIC frame)
            for key in tags.keys():
                if key.startswith('APIC'):
                    apic = tags[key]
                    result['artwork_bytes'] = bytes(apic.data)
                    result['has_artwork']   = True
                    break

        except ID3NoHeaderError:
            pass   # File has no ID3 header — silently ignore

    except Exception as e:
        print(f"[metadata] Error reading '{file_path}': {e}")

    return result


def _first(tags, frame_id: str) -> Optional[str]:
    """Return string value of first matching frame, or None."""
    if frame_id in tags:
        v = str(tags[frame_id])
        return v.strip() if v.strip() else None
    return None


# ── Write ─────────────────────────────────────────────────────────────────────

def write_metadata(file_path: str, meta: dict) -> bool:
    """
    Write editable fields back to the MP3 ID3 tag.
    Only keys present in `meta` are updated.
    Returns True on success.
    """
    try:
        try:
            tags = ID3(file_path)
        except ID3NoHeaderError:
            tags = ID3()

        if 'title' in meta and meta['title'] is not None:
            tags['TIT2'] = TIT2(encoding=3, text=str(meta['title']))
        if 'album' in meta and meta['album'] is not None:
            tags['TALB'] = TALB(encoding=3, text=str(meta['album']))
        if 'artist' in meta and meta['artist'] is not None:
            tags['TPE1'] = TPE1(encoding=3, text=str(meta['artist']))
        if 'language' in meta and meta['language'] is not None:
            tags['TLAN'] = TLAN(encoding=3, text=str(meta['language']))
        if 'genre' in meta and meta['genre'] is not None:
            tags['TCON'] = TCON(encoding=3, text=str(meta['genre']))
        if 'year' in meta and meta['year'] is not None:
            tags['TDRC'] = TDRC(encoding=3, text=str(meta['year']))
        if 'track_number' in meta and meta['track_number'] is not None:
            tags['TRCK'] = TRCK(encoding=3, text=str(meta['track_number']))

        # Artwork
        if 'artwork_bytes' in meta and meta['artwork_bytes']:
            tags.delall('APIC')
            mime = 'image/jpeg'
            data = meta['artwork_bytes']
            if data[:4] == b'\x89PNG':
                mime = 'image/png'
            tags['APIC:Cover'] = APIC(
                encoding=3,
                mime=mime,
                type=PictureType.COVER_FRONT,
                desc='Cover',
                data=data,
            )

        tags.save(file_path, v2_version=3)
        return True

    except Exception as e:
        print(f"[metadata] Error writing '{file_path}': {e}")
        return False


# ── Hash ──────────────────────────────────────────────────────────────────────

def get_file_hash(file_path: str) -> str:
    """Return hex MD5 digest of the entire file (for duplicate detection)."""
    h = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
    except OSError:
        pass
    return h.hexdigest()
