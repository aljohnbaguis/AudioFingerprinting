import uuid
import subprocess
from pathlib import Path


def convert_to_wav(input_path, output_dir):
    """
    Convert any audio file to a normalized mono WAV using ffmpeg.

    Output is single-channel, 22050 Hz sample rate, 16-bit PCM — the
    format expected by the fingerprinting engine.

    Args:
        input_path: Path to the source audio file (any format ffmpeg supports).
        output_dir: Directory to write the converted WAV file.

    Returns:
        Path to the output WAV file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{uuid.uuid4()}.wav"

    # Convert to mono audio with fixed bit rate.
    cmd = [
        "ffmpeg",
        "-i",
        input_path,
        "-ac",
        "1",
        "-ar",
        "22050",
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-y",
        str(output_path),
    ]

    subprocess.run(cmd, check=True)
    return str(output_path)
