# Audio Fingerprinting

A Shazam-like audio recognition system built in Python. Ingest songs from YouTube, fingerprint them using spectral analysis, and identify them later by recording a short clip from your microphone.

## How It Works

The system uses a **constellation-based audio fingerprinting** algorithm:

1. **Spectrogram** — Audio is converted to a time-frequency representation using STFT (Short-Time Fourier Transform).
2. **Peak Detection** — Local maxima (constellation points) are extracted from the spectrogram using a neighborhood filter.
3. **Combinatorial Hashing** — Pairs of nearby peaks are combined into fingerprint hashes using `(freq1, freq2, time_delta)`. Each hash is stored alongside the song ID and time offset.
4. **Matching** — A query clip goes through the same pipeline. Its hashes are looked up in the database, and a **time-offset histogram** is built. The song with the most aligned hash hits is the match.

```
Audio File
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐
│  STFT        │ ──► │  Find Peaks  │ ──► │  Hash Pairs  │ ──► │ Store/   │
│  Spectrogram │     │  (local max) │     │  (f1,f2,Δt)  │     │ Match DB │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────┘
```

## Project Structure

```
audio_fingerprinting/
├── database/
│   └── db.py              # SQLite singleton — songs + hashes tables
├── fingerprint/
│   ├── engine.py          # Spectrogram, peak detection, hash generation
│   └── matcher.py         # Query matching via time-offset histogram
├── rest/
│   └── api.py             # FastAPI endpoints (ingest, query, songs)
└── utils/
    ├── audio.py           # ffmpeg WAV conversion
    ├── mic.py             # Microphone recording via sounddevice
    └── youtube.py         # yt-dlp download + metadata extraction
```

## Prerequisites

- **Python 3.10+**
- **ffmpeg** — for audio conversion (`brew install ffmpeg` on macOS)
- A working **microphone** for the query endpoint

## Setup

```bash
# Clone the repo
git clone https://github.com/ankitjosh78/AudioFingerprinting.git
cd AudioFingerprinting

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install the package in editable mode
pip install -e .
```

## Usage

### Start the server

```bash
uvicorn audio_fingerprinting.rest.api:app --reload
```

The API will be available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### Ingest a song

```bash
curl -X POST http://localhost:8000/ingest_one \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=VIDEO_ID"}'
```

Response:
```json
{
  "status": "ok",
  "song_id": "uuid",
  "title": "Song Title",
  "artist": "Artist Name",
  "num_hashes": 54321
}
```

### Ingest a playlist

```bash
curl -X POST http://localhost:8000/ingest_playlist \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/playlist?list=PLAYLIST_ID"}'
```

### Query (identify a song)

Records from your microphone for `duration` seconds (default 7), fingerprints the clip, and matches it against the database.

```bash
curl -X POST "http://localhost:8000/query?duration=7"
```

Response (match found):
```json
{
  "status": "match",
  "song_id": "uuid",
  "confidence": 142,
  "title": "Song Title",
  "artist": "Artist Name",
  "url": "https://youtube.com/watch?v=..."
}
```

Response (no match):
```json
{
  "status": "no_match"
}
```

### List all ingested songs

```bash
curl http://localhost:8000/songs
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest_one` | Ingest a single YouTube video |
| `POST` | `/ingest_playlist` | Ingest all videos from a YouTube playlist |
| `POST` | `/query?duration=7` | Record from mic and identify the song |
| `GET` | `/songs` | List all ingested songs |

## Tech Stack

- **FastAPI** — REST API framework
- **librosa** — Audio analysis, STFT, spectrogram
- **scipy** — Peak detection via local maximum filter
- **SQLite** — Fingerprint hash + song metadata storage (indexed)
- **yt-dlp** — YouTube audio download + metadata extraction
- **ffmpeg** — Audio format conversion to normalized mono WAV
- **sounddevice** — Microphone recording

## Notes

- The database (`data.db`) is created automatically on first run.
- Audio files are cleaned up after fingerprinting — only the hashes are stored.
- The microphone query endpoint requires mic permissions on macOS (System Settings → Privacy → Microphone).
- For best results, query in a relatively quiet environment with the song playing clearly.
