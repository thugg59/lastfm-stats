import logging
import time

import pandas as pd
import psycopg

from src.extract import API_KEY, USERNAME, RATE_LIMIT_DELAY, _request_page
from src.transform import _clean_tracks, COLUMNS
from src.validate import validate_scrobbles
from src.load import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, load_batch

logger = logging.getLogger(__name__)


def _connect():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def _ensure_checkpoint_table(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS fullhistory_checkpoint (
                id INTEGER PRIMARY KEY DEFAULT 1,
                next_page INTEGER NOT NULL,
                total_pages INTEGER NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT fullhistory_checkpoint_single_row CHECK (id = 1)
            )
            """
        )
    conn.commit()


def _get_checkpoint(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT next_page, total_pages FROM fullhistory_checkpoint WHERE id = 1")
        return cur.fetchone()


def _set_checkpoint(cur, next_page, total_pages):
    cur.execute(
        """
        INSERT INTO fullhistory_checkpoint (id, next_page, total_pages, updated_at)
        VALUES (1, %s, %s, now())
        ON CONFLICT (id) DO UPDATE
        SET next_page = EXCLUDED.next_page,
            total_pages = EXCLUDED.total_pages,
            updated_at = now()
        """,
        (next_page, total_pages),
    )


def _clear_checkpoint(conn):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM fullhistory_checkpoint WHERE id = 1")
    conn.commit()


def run_full_history():
    """Fetch, transform, validate and load the complete scrobble history,
    one page at a time. Each page's data and the checkpoint advance are
    committed together, so an interrupted run — on this machine or a
    completely different one — resumes from the next unfetched page instead
    of starting over.
    """
    logger.info("Starting full-history streaming pipeline")

    conn = _connect()

    try:
        _ensure_checkpoint_table(conn)

        state = _get_checkpoint(conn)
        if state:
            page, total_pages = state
            logger.info("Resuming full-history fetch from page %d/%d", page, total_pages)
        else:
            page, total_pages = 1, 1

        total_inserted = 0
        total_rejected = 0

        while page <= total_pages:
            params = {
                "method": "user.getrecenttracks",
                "user": USERNAME,
                "api_key": API_KEY,
                "format": "json",
                "limit": 200,
                "page": page,
            }

            data = _request_page(params)
            recenttracks = data.get("recenttracks")

            if recenttracks is None:
                logger.error("Last.fm API response is missing 'recenttracks'.")
                raise SystemExit(1)

            tracks = recenttracks.get("track", [])
            total_pages = int(recenttracks.get("@attr", {}).get("totalPages", 1))

            clean = _clean_tracks(tracks)
            df = pd.DataFrame(clean, columns=COLUMNS)
            valid, rejected = validate_scrobbles(df)

            with conn.cursor() as cur:
                inserted = load_batch(cur, valid)
                _set_checkpoint(cur, next_page=page + 1, total_pages=total_pages)
            conn.commit()

            total_inserted += inserted
            total_rejected += len(rejected)

            logger.info(
                "Page %d/%d: %d tracks fetched, %d inserted, %d rejected",
                page, total_pages, len(tracks), inserted, len(rejected),
            )

            page += 1

            if page <= total_pages:
                time.sleep(RATE_LIMIT_DELAY)

        _clear_checkpoint(conn)

        logger.info(
            "Full-history ingestion complete: %d inserted, %d rejected across %d pages",
            total_inserted, total_rejected, total_pages,
        )

    except psycopg.Error:
        logger.exception(
            "Database error during full-history load - progress up to the last "
            "committed page is safe; re-run to resume from the checkpoint."
        )
        raise SystemExit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    from src.config import setup_logging
    setup_logging()
    run_full_history()