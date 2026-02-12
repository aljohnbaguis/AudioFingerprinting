from collections import defaultdict
from audio_fingerprinting.fingerprint.engine import (
    generate_spectogram,
    find_peaks,
    generate_hashes,
)
from audio_fingerprinting.database.db import get_songs_db
from logging import getLogger

logger = getLogger(__name__)

# Minimum number of aligned hash hits to consider a match valid
MIN_MATCH_THRESHOLD = 10


def match_fingerprints(wav_path):
    """
    Fingerprint a query audio clip and match it against the database.

    Algorithm:
        1. Generate hashes from the query audio.
        2. For each query hash, look up matching entries in the DB.
        3. For each (song_id, db_time_offset) hit, compute the time delta
           between the DB offset and the query offset. If the query truly
           belongs to that song, these deltas will cluster around a single
           value (the point in the song where the query starts).
        4. Build a histogram of (song_id, time_delta) counts.
        5. The song with the highest peak in the histogram is the match.

    Returns:
        (song_id, confidence) if a match is found, else None.
        confidence = number of aligned hash hits for the best match.
    """

    # Fingerprint the query clip
    sg = generate_spectogram(wav_path)
    peaks = find_peaks(sg)
    query_hashes = generate_hashes(peaks)

    if not query_hashes:
        logger.warning("No hashes generated from query audio")
        return None

    logger.info(f"Query produced {len(query_hashes)} hashes")

    # offset_hits[(song_id, time_delta)] -> count
    offset_hits = defaultdict(int)

    db = get_songs_db()

    query_hash_map = defaultdict(list)

    # Build a map: hash_value -> [query_time, ...]
    for hash_value, query_time in query_hashes:
        query_hash_map[hash_value].append(int(query_time))
    

    # Retrieve all hits for the query hashes
    all_hits = db.get_hashes_bulk(list(query_hash_map.keys()))

    for db_hash, song_id, db_time in all_hits:
        for query_time in query_hash_map[db_hash]:
            time_delta = int(db_time) - query_time
            offset_hits[(song_id, time_delta)] += 1

    if not offset_hits:
        logger.info("No matching hashes found in database")
        return None

    # Find the (song_id, time_delta) pair with the most hits
    best_key = max(offset_hits.items(), key=lambda x: x[1])
    best_song_id, best_delta = best_key[0]
    confidence = best_key[1]

    logger.info(
        f"Best match: song_id={best_song_id}, "
        f"time_delta={best_delta}, confidence={confidence}"
    )

    if confidence < MIN_MATCH_THRESHOLD:
        logger.info(f"Confidence {confidence} below threshold {MIN_MATCH_THRESHOLD}")
        return None

    return best_song_id, confidence
