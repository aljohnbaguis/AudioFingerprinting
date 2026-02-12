import librosa
import numpy as np
from scipy.ndimage import generate_binary_structure, iterate_structure, maximum_filter
from logging import getLogger
import hashlib
from audio_fingerprinting.database.db import get_songs_db

logger = getLogger(__name__)


def generate_spectogram(file_path):
    """
    Load an audio file and compute its log-scaled magnitude spectrogram.

    Applies STFT (Short-Time Fourier Transform) to convert the time-domain
    signal y(n) into a time-frequency representation Y(k), then converts
    the magnitude to decibels.

    Args:
        file_path: Path to a WAV audio file.

    Returns:
        S_db: 2D numpy array (freq_bins x time_frames) - the log-scaled
              magnitude spectrogram in dB.
    """
    # y(n) is the audio signal. It's in time domain
    y_n, sample_rate = librosa.load(file_path, sr=None)

    logger.debug(f"Shape of Audio: {y_n.shape}")
    logger.debug(f"Sampling rate of audio: {sample_rate}")

    # FFT window size
    n_fft = 2048
    # Frames size to step over
    hop_length = 512
    # Window length
    window_length = 2048

    # Type of window to be used for the fourier transform.
    # "hann" is a raised cosine window, which is adequate for most audio signal processing.
    window_type = "hann"

    # STFT (Short time fourier transform) represents a signal in time-frequency domain by computing DFT (discrete fourier transofmr) over short overlapping windows.
    # It returns a complex valued matrix D such that np.abs(D[....,f,t]) is the magnitute of frequency bin 'f' at frame 't'
    # Y(k) is in time-frequency domain.
    Y_k = librosa.stft(
        y_n,
        n_fft=n_fft,
        hop_length=hop_length,
        win_length=window_length,
        window=window_type,
    )

    # Magnitude Spectogram of Y(k)
    # Represents the constellation mapping of (f,t)
    S = np.abs(Y_k)

    # Convert to decibels from raw amplitude (log_scale)
    S_db = librosa.amplitude_to_db(S, ref=np.max)

    return S_db


def find_peaks(S_db, neighborhood_size=15, threshold=-35):
    """
    Detect spectral peaks (constellation points) in a spectrogram.

    Uses a local maximum filter over a neighborhood to find points that
    are louder than all their neighbors and above a dB threshold.

    Args:
        S_db: Log-scaled magnitude spectrogram (2D numpy array).
        neighborhood_size: Radius of the local max filter. Larger values
                          produce fewer, more prominent peaks.
        threshold: Minimum dB level for a peak to be considered.

    Returns:
        List of (freq_bin, time_bin) tuples representing peak locations.
    """
    # Generate the binary structure representation
    struct = generate_binary_structure(2, 1)

    # Iterate over the neighborhood structures
    neighborhood = iterate_structure(struct, neighborhood_size)

    # Local maxima
    local_max = maximum_filter(S_db, footprint=neighborhood) == S_db

    # Detected peaks based on threshold
    detected_peaks = local_max & (S_db > threshold)

    # Peaks (f_i, t_i) -> represents the peaks with frequency and time mapping.
    freq_bins, time_bins = np.where(detected_peaks)
    return list(zip(freq_bins, time_bins))


def stable_hash(f1, f2, delta_t):
    """
    Generate a stable fingerprint hash from a peak pair.

    Encodes two frequency values and their time difference into a
    truncated SHA-1 hex digest (20 chars). Deterministic for the
    same inputs.

    Args:
        f1: Frequency bin of the anchor peak.
        f2: Frequency bin of the target peak.
        delta_t: Time difference (in frames) between the two peaks.

    Returns:
        20-character hex string.
    """
    # packed integers and hashing them using SHA1 (it's a bit on the slower end, but ensures very less probability of hash collisions)
    hash_str = f"{f1}|{f2}|{delta_t}".encode()
    return hashlib.sha1(hash_str).hexdigest()[:20]


def generate_hashes(peaks, target_peaks=10, min_time_delta=0, max_time_delta=200):
    """
    Generate combinatorial fingerprint hashes from a list of peaks.

    For each anchor peak, pairs it with up to `target_peaks` subsequent
    peaks within a time delta window [min_time_delta, max_time_delta].
    Each pair produces a hash from (f1, f2, delta_t) and is stored
    alongside the anchor's time offset.

    Args:
        peaks: List of (freq_bin, time_bin) tuples.
        target_peaks: Number of forward-looking peaks to pair with each anchor.
        min_time_delta: Minimum allowed time gap (in frames) between paired peaks.
        max_time_delta: Maximum allowed time gap (in frames) between paired peaks.

    Returns:
        List of (hash_value, anchor_time_offset) tuples.
    """
    # Sort the peaks based on time
    peaks = sorted(peaks, key=lambda x: x[1])

    # List of hashes.
    # This will come from the tuple (f1, f2, delta_t), which is the difference between the anchor peaks and nearby target peaks in a given time threshold
    hashes = []

    for i in range(len(peaks)):
        # Finding out nearby target peaks to pair with anchor peak
        for j in range(1, target_peaks):
            if i + j < len(peaks):
                f1, t1 = peaks[i]
                f2, t2 = peaks[i + j]

                # time difference between two points
                delta_t = t2 - t1

                # If time difference is within time_delta threshold, we consider this as a valid pairing.
                if min_time_delta <= delta_t <= max_time_delta:
                    hash_value = stable_hash(f1, f2, delta_t)
                    hashes.append((hash_value, t1))

    return hashes


def fingerprint_and_hash(wav_file, song_id):
    """
    Full fingerprinting pipeline: spectrogram -> peaks -> hashes -> store in DB.

    Takes a normalized WAV file, generates its spectrogram, extracts
    constellation peaks, computes combinatorial hashes, and bulk-inserts
    them into the database keyed by song_id.

    Args:
        wav_file: Path to a normalized mono WAV file.
        song_id: Unique identifier for the song.

    Returns:
        Number of hashes stored.
    """
    # Step 1: Loading the wav file, applying STFT and generating the spectogram (log_scale)
    sg = generate_spectogram(wav_file)

    # Step 2: Find peaks in the spectogram, using local maximma
    peaks = find_peaks(sg)

    # Step 3: Find nearby peaks, taking the previous peaks as anchor point and generate hashes
    hashes = generate_hashes(peaks)

    db = get_songs_db()

    rows = []
    for hash_value, time_offset in hashes:
        rows.append((hash_value, song_id, int(time_offset)))

    db.insert_hashes_bulk(rows)

    logger.info(f"Stored {len(hashes)} hashes for song_id={song_id}")
    return len(hashes)
