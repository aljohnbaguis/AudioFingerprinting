import sqlite3
from typing import Optional


class SongDatabase:
    """
    Singleton SQLite-backed store for song metadata and fingerprint hashes.

    Tables:
        songs  - (song_id, title, artist, url, duration)
        hashes - (hash, song_id, time_offset)  with an index on hash.
    """

    _instance = None
    _is_initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SongDatabase, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if self._is_initialized:
            return
        self.cursor = sqlite3.connect("data.db", check_same_thread=False).cursor()
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS songs (song_id TEXT PRIMARY KEY, title TEXT, artist TEXT, url TEXT, duration REAL)"
        )
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS hashes (hash TEXT , song_id TEXT, time_offset REAL)"
        )
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON hashes (hash)")
        self._is_initialized = True

    @classmethod
    def dispose(cls):
        if cls._instance is None:
            return
        cls._instance.cursor.connection.close()
        cls._instance = None

    def insert_song(self, song_id, title, artist, url, duration):
        """Insert a single song's metadata into the songs table."""
        self.cursor.execute(
            "INSERT INTO songs (song_id, title, artist, url, duration) VALUES (?, ?, ?, ?, ?)",
            (song_id, title, artist, url, duration),
        )
        self.cursor.connection.commit()

    def insert_hash(self, hash_value, song_id, time_offset):
        """Insert a single fingerprint hash with its song_id and time offset."""
        self.cursor.execute(
            "INSERT INTO hashes (hash, song_id, time_offset) VALUES (?, ?, ?)",
            (hash_value, song_id, time_offset),
        )
        self.cursor.connection.commit()

    def insert_hashes_bulk(self, rows):
        """Bulk-insert fingerprint hashes. rows: list of (hash, song_id, time_offset)."""
        self.cursor.executemany(
            "INSERT INTO hashes (hash, song_id, time_offset) VALUES (?, ?, ?)",
            rows,
        )
        self.cursor.connection.commit()

    def get_hash(self, hash_value):
        """Look up a single hash. Returns list of (song_id, time_offset) matches."""
        self.cursor.execute(
            "SELECT song_id, time_offset FROM hashes WHERE hash = ?", (hash_value,)
        )
        return self.cursor.fetchall()

    def get_hashes_bulk(self, hash_values):
        """Look up multiple hashes in batched queries (batch_size=900 for SQLite variable limit). Returns list of (hash, song_id, time_offset)."""
        results = []
        batch_size = 900
        for i in range(0, len(hash_values), batch_size):
            batch = hash_values[i : i + batch_size]
            placeholders = ",".join("?" for _ in batch)
            self.cursor.execute(
                f"SELECT hash, song_id, time_offset FROM hashes WHERE hash IN ({placeholders})",
                batch,
            )
            results.extend(self.cursor.fetchall())
        return results

    def get_song(self, song_id):
        """Fetch a single song's metadata by song_id. Returns (song_id, title, artist, url, duration) or None."""
        self.cursor.execute(
            "SELECT song_id, title, artist, url, duration FROM songs WHERE song_id = ?",
            (song_id,),
        )
        return self.cursor.fetchone()

    def get_songs(self):
        """Return all songs as a list of (song_id, title, artist, url, duration) tuples."""
        self.cursor.execute("SELECT song_id, title, artist, url, duration FROM songs")
        return self.cursor.fetchall()


_songs_db: Optional[SongDatabase] = None


def get_songs_db():
    global _songs_db
    if _songs_db is None:
        _songs_db = SongDatabase()
    return _songs_db
