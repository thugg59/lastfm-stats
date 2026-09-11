import json
import pandas as pd
import logging
from datetime import datetime, timezone
from src.config import SCROBBLES_JSON, SCROBBLES_CSV


logger = logging.getLogger(__name__)


def _clean_tracks(tracks):
    if isinstance(tracks, dict):
        tracks = [tracks]

    clean_tracks = []

    for track in tracks:
        if "@attr" in track:
            continue

        try:
            clean_track = {
                "artist": track["artist"]["#text"],
                "album": track.get("album", {}).get("#text"),
                "track": track["name"],
                "timestamp": datetime.fromtimestamp(
                    int(track["date"]["uts"]),
                    tz=timezone.utc,
                )
            }
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("Skipping malformed track record: %s", e)
            continue

        clean_tracks.append(clean_track)

    return clean_tracks

COLUMNS = ["artist", "album", "track", "timestamp"]

def transform_scrobbles():
    logger.info("Transforming scrobbles")

    try:
        with open(SCROBBLES_JSON, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.error("Input file not found: %s", SCROBBLES_JSON)
        raise SystemExit(1)
    except json.JSONDecodeError as e:
        logger.error("Malformed JSON in %s: %s", SCROBBLES_JSON, e)
        raise SystemExit(1)

    try:
        tracks = data["recenttracks"]["track"]
    except KeyError:
        logger.error("%s is missing 'recenttracks.track'.", SCROBBLES_JSON)
        raise SystemExit(1)

    clean_tracks = _clean_tracks(tracks)

    df = pd.DataFrame(clean_tracks, columns=COLUMNS)

    df.to_csv(
        SCROBBLES_CSV,
        index=False,
        encoding="utf-8"
    )

    logger.info("Saved %d transformed tracks", len(df))


if __name__ == "__main__":
    from src.config import setup_logging
    setup_logging()
    transform_scrobbles()