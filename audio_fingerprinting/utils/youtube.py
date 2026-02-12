from yt_dlp import YoutubeDL
from pathlib import Path
import uuid


def download_youtube_audio(url, output_dir):
    """
    Download the best-quality audio from a single YouTube video.

    Uses yt-dlp to fetch the audio stream and extract metadata
    (title, artist, duration, thumbnail, URL).

    Args:
        url: YouTube video URL.
        output_dir: Directory to save the downloaded audio file.

    Returns:
        Tuple of (file_path, song_id, metadata) where metadata is a dict
        with keys: title, artist, duration, thumbnail, url.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / f"{file_id}.%(ext)s"),
        "quiet": True,
        "noplaylist": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(str(url), download=True)

    if info:
        metadata = {
            "title": info.get("title"),
            "artist": info.get("artist") or info.get("uploader"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "url": str(url),
        }
    else:
        raise RuntimeError("Failed to retrieve Metadata.")

    # find downloaded file
    for file in output_dir.glob(f"{file_id}.*"):
        return str(file), file_id, metadata

    raise RuntimeError("Download failed")

def download_playlist(url, output_dir):
    """Extract all video URLs from a playlist, then download each one.
    
    Yields (file_path, song_id, metadata) for each successfully downloaded video.
    """
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "noplaylist": False,
    }

    with YoutubeDL(ydl_opts) as ydl:
        playlist_info = ydl.extract_info(str(url), download=False)

    if not playlist_info or "entries" not in playlist_info:
        raise RuntimeError("Failed to extract playlist entries")

    for entry in playlist_info["entries"]:
        video_url = entry.get("url") or entry.get("webpage_url")
        if video_url:
            yield download_youtube_audio(video_url, output_dir)