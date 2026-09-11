import os
import requests
import json
import logging
from dotenv import load_dotenv
from src.config import SCROBBLES_JSON, RAW_DIR
from src.lastfm import sign_request


logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("LASTFM_API_KEY")
API_SECRET = os.getenv("LASTFM_API_SECRET")
USERNAME = os.getenv("LASTFM_USERNAME")
SESSION_KEY = os.getenv("LASTFM_SESSION_KEY")
API_URL = "https://ws.audioscrobbler.com/2.0/"

if not all([API_KEY, API_SECRET, USERNAME, SESSION_KEY]):
    logger.error("Missing required Last.fm env vars. Run auth.py first.")
    raise SystemExit(1)


def fetch_scrobbles(since=None, full_history=False):
    logger.info("Fetching scrobbles from Last.fm")

    all_tracks = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        params = {
            "method": "user.getrecenttracks",
            "user": USERNAME,
            "api_key": API_KEY,
            "sk": SESSION_KEY,
            "format": "json",
            "limit": 200,
            "page": page,
        }

        if since is not None:
            params["from"] = since

        api_sig = sign_request(params, API_SECRET)
        params["api_sig"] = api_sig

        try:
            response = requests.get(API_URL, params=params)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Request to Last.fm API failed: %s", e)
            raise SystemExit(1)

        data = response.json()

        if "error" in data:
            logger.error(
                "Last.fm API error %s: %s",
                data["error"],
                data.get("message", "Unknown error"),
            )
            raise SystemExit(1)

        if "recenttracks" not in data:
            logger.error("Last.fm API response is missing 'recenttracks'.")
            raise SystemExit(1)

        recenttracks = data["recenttracks"]
        tracks = recenttracks.get("track", [])

        if isinstance(tracks, dict):
            tracks = [tracks]

        all_tracks.extend(tracks)

        total_pages = int(recenttracks.get("@attr", {}).get("totalPages", 1))
        logger.info("Fetched page %d/%d (%d tracks)", page, total_pages, len(tracks))

        page += 1

        if since is None and not full_history:
            logger.info("No 'since' cursor and full_history=False — fetching newest page only")
            break

    with open(SCROBBLES_JSON, "w", encoding="utf-8") as file:
        json.dump({"recenttracks": {"track": all_tracks}}, file, indent=4, ensure_ascii=False)

    logger.info("Saved %d scrobbles total", len(all_tracks))


if __name__ == "__main__":
    import argparse
    from src.config import setup_logging
    from src.load import get_last_timestamp

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--incremental",
        action="store_true",
        help="Fetch scrobbles since the last timestamp stored in the database",
    )
    group.add_argument(
        "--full-history",
        action="store_true",
        help="Fetch the complete scrobble history",
    )

    args = parser.parse_args()

    setup_logging()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    since = get_last_timestamp() if args.incremental else None

    fetch_scrobbles(
        since=since,
        full_history=args.full_history,
    )