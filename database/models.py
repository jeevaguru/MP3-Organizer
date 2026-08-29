"""
MP3 Organizer — Database Models (Peewee + SQLite)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from peewee import (
    SqliteDatabase, Model, AutoField, TextField, IntegerField,
    BooleanField, BlobField, DateTimeField, ForeignKeyField,
    CompositeKey, FloatField
)
from config import DB_PATH

db = SqliteDatabase(
    DB_PATH,
    pragmas={
        'journal_mode': 'wal',
        'cache_size': -64 * 1000,   # 64 MB cache
        'foreign_keys': 1,
        'synchronous': 'normal',
    }
)


class BaseModel(Model):
    class Meta:
        database = db


class Artist(BaseModel):
    id   = AutoField()
    name = TextField(unique=True)

    def __str__(self):
        return self.name


class Album(BaseModel):
    id     = AutoField()
    name   = TextField()
    year   = IntegerField(null=True)
    artist = ForeignKeyField(Artist, backref='albums', null=True, on_delete='SET NULL')

    def __str__(self):
        return self.name


class Track(BaseModel):
    id           = AutoField()
    title        = TextField(null=True)
    album        = ForeignKeyField(Album, backref='tracks', null=True, on_delete='SET NULL')
    artist       = ForeignKeyField(Artist, backref='tracks', null=True, on_delete='SET NULL')
    language     = TextField(null=True)
    bitrate      = IntegerField(null=True)    # kbps
    file_path    = TextField(unique=True)
    file_name    = TextField()
    file_size    = IntegerField(default=0)    # bytes
    duration     = IntegerField(null=True)    # seconds
    year         = IntegerField(null=True)
    genre        = TextField(null=True)
    track_number = IntegerField(null=True)
    has_artwork  = BooleanField(default=False)
    artwork_blob = BlobField(null=True)       # Compressed JPEG bytes
    play_count   = IntegerField(default=0)
    date_added   = DateTimeField()
    file_hash    = TextField(null=True, index=True)  # MD5 for duplicate detection

    def display_title(self):
        """Return title, or file stem if no title tag."""
        if self.title:
            return self.title
        return os.path.splitext(self.file_name)[0]

    def display_artist(self):
        try:
            return self.artist.name if self.artist else ''
        except Exception:
            return ''

    def display_album(self):
        try:
            return self.album.name if self.album else ''
        except Exception:
            return ''

    def __str__(self):
        return f"{self.display_artist()} — {self.display_title()}"


class Playlist(BaseModel):
    id       = AutoField()
    name     = TextField()
    is_smart = BooleanField(default=False)
    criteria = TextField(null=True)   # JSON string for smart playlists

    def __str__(self):
        return self.name


class PlaylistTrack(BaseModel):
    playlist = ForeignKeyField(Playlist, backref='playlist_tracks', on_delete='CASCADE')
    track    = ForeignKeyField(Track, backref='playlist_tracks', on_delete='CASCADE')
    position = IntegerField(default=0)

    class Meta:
        indexes = ((('playlist', 'track'), True),)   # unique together


class ScanFolder(BaseModel):
    id           = AutoField()
    path         = TextField(unique=True)
    auto_watch   = BooleanField(default=False)
    last_scanned = DateTimeField(null=True)

    def __str__(self):
        return self.path


def create_tables():
    """Create all tables if they don't exist."""
    with db:
        db.create_tables([Artist, Album, Track, Playlist, PlaylistTrack, ScanFolder], safe=True)
