import asyncio
from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
from audio_fingerprinting.utils.youtube import download_youtube_audio, download_playlist
from audio_fingerprinting.utils.audio import convert_to_wav
from audio_fingerprinting.fingerprint.engine import fingerprint_and_hash
from audio_fingerprinting.fingerprint.matcher import match_fingerprints
from audio_fingerprinting.database.db import get_songs_db
from audio_fingerprinting.utils.mic import record_from_mic
from logging import getLogger
from pathlib import Path

logger = getLogger(__name__)

app = FastAPI(
    title="Audio Fingerprinting API",
    description="API for audio fingerprinting and matching.",
    version="1.0.0",
)

songs_db = get_songs_db()


class IngestRequest(BaseModel):
    url: HttpUrl


@app.post("/ingest_one")
async def ingest(request: IngestRequest):
    try:
        # Download the raw audio
        raw_path, song_id, metadata = download_youtube_audio(
            request.url, output_dir="data/raw"
        )

        # Convert to wav
        normalized_wav_path = convert_to_wav(raw_path, output_dir="data/normalized")

        # Store the song metadata
        songs_db.insert_song(
            song_id,
            metadata.get("title"),
            metadata.get("artist"),
            metadata.get("url"),
            metadata.get("duration"),
        )

        # Store the hashes with song_id and time_offsets
        num_hashes = fingerprint_and_hash(normalized_wav_path, song_id)

        # Remove raw and normalized audio files
        Path(raw_path).unlink()
        Path(normalized_wav_path).unlink()

        return {
            "status": "ok",
            "song_id": song_id,
            "title": metadata.get("title"),
            "artist": metadata.get("artist"),
            "num_hashes": num_hashes,
        }

    except Exception as e:
        logger.error(f"Ingest failed: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}

@app.post("/ingest_playlist")
async def ingest_playlist(request: IngestRequest):
    results = []
    try:
        for raw_path, song_id, metadata in download_playlist(
            request.url, output_dir="data/raw"
        ):
            try:
                normalized_wav_path = convert_to_wav(raw_path, output_dir="data/normalized")

                songs_db.insert_song(
                    song_id,
                    metadata.get("title"),
                    metadata.get("artist"),
                    metadata.get("url"),
                    metadata.get("duration"),
                )

                num_hashes = fingerprint_and_hash(normalized_wav_path, song_id)

                Path(raw_path).unlink(missing_ok=True)
                Path(normalized_wav_path).unlink(missing_ok=True)

                results.append({
                    "status": "ok",
                    "song_id": song_id,
                    "title": metadata.get("title"),
                    "artist": metadata.get("artist"),
                    "num_hashes": num_hashes,
                })

            except Exception as e:
                logger.error(f"Failed to process {metadata.get('title')}: {e}", exc_info=True)
                results.append({
                    "status": "error",
                    "title": metadata.get("title"),
                    "detail": str(e),
                })

        return {"status": "ok", "total": len(results), "results": results}

    except Exception as e:
        logger.error(f"Playlist ingest failed: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}


@app.post("/query")
async def query(duration: int = 7):
    """Record from microphone, fingerprint, and match against the database."""
    try:
        wav_path = record_from_mic(duration=duration, output_dir="data/queries")

        result = match_fingerprints(wav_path)

        # Remove query audio file
        Path(wav_path).unlink()

        if result is None:
            return {"status": "no_match"}

        song_id, confidence = result
    
        return {
            "status": "match",
            "song_id": song_id,
            "confidence": confidence,
            "title": songs_db.get_song(song_id)[1],
            "artist": songs_db.get_song(song_id)[2],
            "url": songs_db.get_song(song_id)[3],
        }

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        return {"status": "error", "detail": str(e)}


@app.get("/songs")
async def list_songs():
    return songs_db.get_songs()
