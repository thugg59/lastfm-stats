import os
import random
import time
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
    logger.error(
        "Missing required Last.fm environment variables. "
        "Run auth.py first to create/update your .env file. "
        "If you already ran auth.py, check that .env exists in the "
        "project root and contains the required Last.fm variables."
    )
    raise SystemExit(1)


# Only used by the full-history path.
RATE_LIMIT_DELAY = 0.25
MAX_RETRIES = 5
RETRY_BASE_DELAY = 2.0


def _request_page(params, max_retries=MAX_RETRIES, base_delay=RETRY_BASE_DELAY):
    """Fetch one Last.fm API page with authentication and retry/backoff."""

    params = params.copy()

    # Personal Last.fm authentication.
    params["sk"] = SESSION_KEY
    params["api_sig"] = sign_request(params, API_SECRET)

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                API_URL,
                params=params,
                timeout=30,
            )
            response.raise_for_status()

        except requests.RequestException as e:
            if attempt == max_retries:
                logger.error(
                    "Request to Last.fm API failed after %d attempts: %s",
                    max_retries,
                    e,
                )
                raise SystemExit(1)

            delay = (
                base_delay * (2 ** (attempt - 1))
                + random.uniform(0, 0.5)
            )

            logger.warning(
                "Request failed (attempt %d/%d): %s - retrying in %.1fs",
                attempt,
                max_retries,
                e,
                delay,
            )

            time.sleep(delay)
            continue

        data = response.json()

        if "error" in data:
            if data["error"] == 29 and attempt < max_retries:
                delay = (
                    base_delay * (2 ** attempt)
                    + random.uniform(0, 1)
                )

                logger.warning(
                    "Rate limited by Last.fm (error 29) - "
                    "retrying in %.1fs",
                    delay,
                )

                time.sleep(delay)
                continue

            logger.error(
                "Last.fm API error %s: %s",
                data["error"],
                data.get("message", "Unknown error"),
            )
            raise SystemExit(1)

        return data

    logger.error("Exhausted retries without a successful response")
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
            "format": "json",
            "limit": 200,
            "page": page,
        }

        if since is not None:
            params["from"] = since

        data = _request_page(
            params,
            max_retries=1,
        )

        if "recenttracks" not in data:
            logger.error(
                "Last.fm API response is missing 'recenttracks'."
            )
            raise SystemExit(1)

        recenttracks = data["recenttracks"]
        tracks = recenttracks.get("track", [])

        if isinstance(tracks, dict):
            tracks = [tracks]

        all_tracks.extend(tracks)

        total_pages = int(
            recenttracks.get("@attr", {}).get("totalPages", 1)
        )

        logger.info(
            "Fetched page %d/%d (%d tracks)",
            page,
            total_pages,
            len(tracks),
        )

        page += 1

        if since is None and not full_history:
            logger.info(
                "No 'since' cursor and full_history=False - "
                "fetching newest page only"
            )
            break

    with open(
        SCROBBLES_JSON,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            {"recenttracks": {"track": all_tracks}},
            file,
            indent=4,
            ensure_ascii=False,
        )

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