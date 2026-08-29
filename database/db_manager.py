"""
MP3 Organizer — Database Manager
All CRUD, search, and export operations against the SQLite database.
"""
import csv
import json
import os
from datetime import datetime
from typing import List, Optional

from peewee import fn, DoesNotExist, IntegrityError

from database.models import db, create_tables, Artist, Album, Track, Playlist, PlaylistTrack, ScanFolder


class DatabaseManager:
    def __init__(self):
        db.connect(reuse_if_open=True)
        create_tables()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_or_create_artist(self, name: str) -> Optional[Artist]:
        if not name or not name.strip():
            return None
        artist, _ = Artist.get_or_create(name=name.strip())
        return artist

    def _get_or_create_album(self, name: str, artist: Optional[Artist], year: Optional[int]) -> Optional[Album]:
        if not name or not name.strip():
            return None
        album, created = Album.get_or_create(
            name=name.strip(),
            artist=artist,
            defaults={'year': year}
        )
        if not created and year and album.year is None:
            album.year = year
            album.save()
        return album

    # ── Tracks ────────────────────────────────────────────────────────────────

    def upsert_track(self, file_path: str, meta: dict) -> str:
        """Insert or update a track. Returns 'added' | 'updated' | 'skipped'."""
        artist = self._get_or_create_artist(meta.get('artist'))
        album  = self._get_or_create_album(meta.get('album'), artist, meta.get('year'))

        try:
            track = Track.get(Track.file_path == file_path)
            # Update existing
            track.title        = meta.get('title') or track.title
            track.artist       = artist or track.artist
            track.album        = album or track.album
            track.language     = meta.get('language') or track.language
            track.bitrate      = meta.get('bitrate') or track.bitrate
            track.file_name    = meta.get('file_name', os.path.basename(file_path))
            track.file_size    = meta.get('file_size', 0)
            track.duration     = meta.get('duration') or track.duration
            track.year         = meta.get('year') or track.year
            track.genre        = meta.get('genre') or track.genre
            track.track_number = meta.get('track_number') or track.track_number
            track.file_hash    = meta.get('file_hash') or track.file_hash
            if meta.get('artwork_bytes'):
                track.artwork_blob = meta['artwork_bytes']
                track.has_artwork  = True
            track.save()
            return 'updated'
        except DoesNotExist:
            # Insert new
            Track.create(
                title        = meta.get('title'),
                artist       = artist,
                album        = album,
                language     = meta.get('language'),
                bitrate      = meta.get('bitrate'),
                file_path    = file_path,
                file_name    = meta.get('file_name', os.path.basename(file_path)),
                file_size    = meta.get('file_size', 0),
                duration     = meta.get('duration'),
                year         = meta.get('year'),
                genre        = meta.get('genre'),
                track_number = meta.get('track_number'),
                has_artwork  = bool(meta.get('artwork_bytes')),
                artwork_blob = meta.get('artwork_bytes'),
                play_count   = 0,
                date_added   = meta.get('date_added', datetime.now()),
                file_hash    = meta.get('file_hash'),
            )
            return 'added'

    def get_track(self, track_id: int) -> Optional[Track]:
        try:
            return Track.get_by_id(track_id)
        except DoesNotExist:
            return None

    def get_all_tracks(self) -> List[Track]:
        # Use raw SQL for ordering by joined tables — avoids Peewee 4 join/alias quirks
        cursor = db.execute_sql("""
            SELECT t.id FROM track AS t
            LEFT JOIN artist AS ar ON t.artist_id = ar.id
            LEFT JOIN album  AS al ON t.album_id  = al.id
            ORDER BY
                LOWER(COALESCE(ar.name, '')),
                LOWER(COALESCE(al.name, '')),
                COALESCE(t.track_number, 0)
        """)
        ids = [row[0] for row in cursor.fetchall()]
        if not ids:
            return []
        tracks_by_id = {t.id: t for t in Track.select()}
        return [tracks_by_id[i] for i in ids if i in tracks_by_id]

    def search_tracks(self, query: str) -> List[Track]:
        q = f"%{query.lower()}%"
        cursor = db.execute_sql("""
            SELECT DISTINCT t.id FROM track AS t
            LEFT JOIN artist AS ar ON t.artist_id = ar.id
            LEFT JOIN album  AS al ON t.album_id  = al.id
            WHERE
                LOWER(COALESCE(t.title,    '')) LIKE ? OR
                LOWER(COALESCE(ar.name,   '')) LIKE ? OR
                LOWER(COALESCE(al.name,   '')) LIKE ? OR
                LOWER(COALESCE(t.genre,   '')) LIKE ? OR
                LOWER(COALESCE(t.language,'')) LIKE ? OR
                LOWER(COALESCE(t.file_name,'')) LIKE ?
            ORDER BY LOWER(COALESCE(ar.name, '')), LOWER(COALESCE(al.name, ''))
        """, [q, q, q, q, q, q])
        ids = [row[0] for row in cursor.fetchall()]
        if not ids:
            return []
        tracks_by_id = {t.id: t for t in Track.select().where(Track.id.in_(ids))}
        return [tracks_by_id[i] for i in ids if i in tracks_by_id]

    def update_track_tags(self, track_id: int, meta: dict) -> bool:
        """Update only the editable tag fields."""
        try:
            track = Track.get_by_id(track_id)
            if 'title' in meta:
                track.title = meta['title']
            if 'language' in meta:
                track.language = meta['language']
            if 'year' in meta:
                track.year = meta['year']
            if 'genre' in meta:
                track.genre = meta['genre']
            if 'track_number' in meta:
                track.track_number = meta['track_number']
            if 'artist_name' in meta:
                track.artist = self._get_or_create_artist(meta['artist_name'])
            if 'album_name' in meta:
                track.album = self._get_or_create_album(
                    meta['album_name'],
                    track.artist,
                    meta.get('year') or (track.year if hasattr(track, 'year') else None)
                )
            if 'artwork_bytes' in meta and meta['artwork_bytes']:
                track.artwork_blob = meta['artwork_bytes']
                track.has_artwork  = True
            track.save()
            return True
        except DoesNotExist:
            return False

    def delete_track(self, track_id: int):
        Track.delete_by_id(track_id)

    def delete_tracks_by_paths(self, paths: List[str]):
        Track.delete().where(Track.file_path.in_(paths)).execute()

    def increment_play_count(self, track_id: int):
        Track.update(play_count=Track.play_count + 1).where(Track.id == track_id).execute()

    def remove_missing_tracks(self) -> int:
        """Remove DB entries for files that no longer exist on disk."""
        removed = 0
        for track in Track.select(Track.id, Track.file_path):
            if not os.path.exists(track.file_path):
                track.delete_instance()
                removed += 1
        return removed

    # ── Duplicates ────────────────────────────────────────────────────────────

    def find_duplicate_hashes(self) -> dict:
        """Return dict of hash → [Track, ...] for any hash that appears more than once."""
        from peewee import fn
        dupes = {}
        # Find hashes that occur >1 times
        dup_hashes = (
            Track.select(Track.file_hash, fn.COUNT(Track.id).alias('cnt'))
            .where(Track.file_hash.is_null(False))
            .group_by(Track.file_hash)
            .having(fn.COUNT(Track.id) > 1)
        )
        for row in dup_hashes:
            tracks = list(Track.select().where(Track.file_hash == row.file_hash))
            dupes[row.file_hash] = tracks
        return dupes

    # ── Playlists ─────────────────────────────────────────────────────────────

    def get_all_playlists(self) -> List[Playlist]:
        return list(Playlist.select().order_by(Playlist.name))

    def create_playlist(self, name: str, is_smart: bool = False, criteria: str = None) -> Playlist:
        return Playlist.create(name=name, is_smart=is_smart, criteria=criteria)

    def rename_playlist(self, playlist_id: int, name: str):
        Playlist.update(name=name).where(Playlist.id == playlist_id).execute()

    def delete_playlist(self, playlist_id: int):
        PlaylistTrack.delete().where(PlaylistTrack.playlist == playlist_id).execute()
        Playlist.delete_by_id(playlist_id)

    def add_tracks_to_playlist(self, playlist_id: int, track_ids: List[int]):
        max_pos = (
            PlaylistTrack.select(fn.MAX(PlaylistTrack.position))
            .where(PlaylistTrack.playlist == playlist_id)
            .scalar() or 0
        )
        rows = []
        for i, tid in enumerate(track_ids):
            rows.append({'playlist': playlist_id, 'track': tid, 'position': max_pos + i + 1})
        with db.atomic():
            PlaylistTrack.insert_many(rows).on_conflict_ignore().execute()

    def remove_track_from_playlist(self, playlist_id: int, track_id: int):
        PlaylistTrack.delete().where(
            (PlaylistTrack.playlist == playlist_id) & (PlaylistTrack.track == track_id)
        ).execute()

    def get_playlist_tracks(self, playlist_id: int) -> List[Track]:
        cursor = db.execute_sql("""
            SELECT pt.track_id FROM playlisttrack AS pt
            WHERE pt.playlist_id = ?
            ORDER BY pt.position
        """, [playlist_id])
        ids = [row[0] for row in cursor.fetchall()]
        if not ids:
            return []
        tracks_by_id = {t.id: t for t in Track.select().where(Track.id.in_(ids))}
        return [tracks_by_id[i] for i in ids if i in tracks_by_id]

    def evaluate_smart_playlist(self, criteria_json: str) -> List[Track]:
        """Evaluate a smart playlist criteria JSON and return matching tracks."""
        import json as _json
        try:
            criteria = _json.loads(criteria_json)
        except Exception:
            return []

        wheres: list[str] = []
        params: list     = []

        col_map = {
            'title':    "LOWER(COALESCE(t.title, ''))",
            'artist':   "LOWER(COALESCE(ar.name, ''))",
            'album':    "LOWER(COALESCE(al.name, ''))",
            'genre':    "LOWER(COALESCE(t.genre, ''))",
            'language': "LOWER(COALESCE(t.language, ''))",
        }
        num_col_map = {
            'year':       "COALESCE(t.year, 0)",
            'play_count': "COALESCE(t.play_count, 0)",
            'bitrate':    "COALESCE(t.bitrate, 0)",
        }

        for rule in criteria:
            field = rule.get('field', '')
            op    = rule.get('op', 'contains')
            value = rule.get('value', '')
            if not value:
                continue

            if field in col_map:
                col = col_map[field]
                v   = value.lower()
                if op == 'contains':
                    wheres.append(f"{col} LIKE ?")
                    params.append(f"%{v}%")
                elif op == 'is':
                    wheres.append(f"{col} = ?")
                    params.append(v)
                elif op == 'is not':
                    wheres.append(f"{col} != ?")
                    params.append(v)
                elif op == 'starts with':
                    wheres.append(f"{col} LIKE ?")
                    params.append(f"{v}%")

            elif field in num_col_map:
                col = num_col_map[field]
                try:
                    num = int(value)
                except ValueError:
                    continue
                ops_map = {'>': '>', '<': '<', '>=': '>=', '<=': '<=', 'is': '='}
                if op in ops_map:
                    wheres.append(f"{col} {ops_map[op]} ?")
                    params.append(num)

        where_clause = " AND ".join(wheres) if wheres else "1=1"
        sql = f"""
            SELECT t.id FROM track AS t
            LEFT JOIN artist AS ar ON t.artist_id = ar.id
            LEFT JOIN album  AS al ON t.album_id  = al.id
            WHERE {where_clause}
            ORDER BY LOWER(COALESCE(ar.name, '')), LOWER(COALESCE(al.name, ''))
        """
        cursor = db.execute_sql(sql, params)
        ids    = [row[0] for row in cursor.fetchall()]
        if not ids:
            return []
        tracks_by_id = {t.id: t for t in Track.select().where(Track.id.in_(ids))}
        return [tracks_by_id[i] for i in ids if i in tracks_by_id]

    # ── Scan Folders ──────────────────────────────────────────────────────────

    def get_scan_folders(self) -> List[ScanFolder]:
        return list(ScanFolder.select())

    def add_scan_folder(self, path: str, auto_watch: bool = False) -> ScanFolder:
        folder, _ = ScanFolder.get_or_create(path=path, defaults={'auto_watch': auto_watch})
        return folder

    def update_scan_folder(self, path: str, last_scanned: datetime = None, auto_watch: bool = None):
        updates = {}
        if last_scanned is not None:
            updates['last_scanned'] = last_scanned
        if auto_watch is not None:
            updates['auto_watch'] = auto_watch
        if updates:
            ScanFolder.update(**updates).where(ScanFolder.path == path).execute()

    def remove_scan_folder(self, path: str):
        ScanFolder.delete().where(ScanFolder.path == path).execute()

    # ── Statistics ────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        total_tracks   = Track.select().count()
        total_artists  = Artist.select().count()
        total_albums   = Album.select().count()
        total_size     = Track.select(fn.SUM(Track.file_size)).scalar() or 0
        total_duration = Track.select(fn.SUM(Track.duration)).scalar() or 0
        return {
            'tracks': total_tracks,
            'artists': total_artists,
            'albums': total_albums,
            'size_bytes': total_size,
            'duration_seconds': total_duration,
        }

    # ── Export ────────────────────────────────────────────────────────────────

    def export_library(self, tracks: List[Track], path: str, fmt: str = 'csv'):
        """Export library to CSV or JSON file."""
        rows = []
        for t in tracks:
            rows.append({
                'title':     t.display_title(),
                'artist':    t.display_artist(),
                'album':     t.display_album(),
                'language':  t.language or '',
                'genre':     t.genre or '',
                'year':      t.year or '',
                'bitrate':   f"{t.bitrate} kbps" if t.bitrate else '',
                'duration':  _fmt_duration(t.duration),
                'file_name': t.file_name,
                'file_path': t.file_path,
                'file_size': t.file_size,
                'play_count': t.play_count,
            })

        if fmt == 'csv':
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
                writer.writeheader()
                writer.writerows(rows)
        elif fmt == 'json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(rows, f, indent=2, ensure_ascii=False)


def _fmt_duration(seconds):
    if seconds is None:
        return ''
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
