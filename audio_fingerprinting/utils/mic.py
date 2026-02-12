import uuid
import wave
from pathlib import Path
from logging import getLogger

logger = getLogger(__name__)

SAMPLE_RATE = 22050
CHANNELS = 1
SAMPLE_WIDTH = 2


def record_from_mic(duration=7, output_dir="data/queries"):
    """
    Record audio from the default microphone for `duration` seconds,
    save as a WAV file, and return the file path.

    Uses sounddevice for cross-platform mic access.
    """
    import sounddevice as sd

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{uuid.uuid4()}.wav"

    logger.info(f"Recording {duration}s of audio from microphone...")
    print(f"Listening for {duration} seconds...")

    audio_data = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
    )
    sd.wait()

    print("Recording complete.")
    logger.info(f"Recording finished. Shape: {audio_data.shape}")

    # Write to WAV
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())

    logger.info(f"Saved recording to {output_path}")
    return str(output_path)
