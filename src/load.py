import os
import logging

import pandas as pd
import psycopg
from dotenv import load_dotenv

from src.config import VALIDATED_CSV

logger = logging.getLogger(__name__)

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    logger.error("Missing required DB environment variables. Check your .env file.")
    raise SystemExit(1)

REQUIRED_COLUMNS = {"artist", "track", "album", "timestamp"}


def get_last_timestamp():
    logger.info("Checking for last scrobble timestamp in database")

    try:
        with psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT MAX(timestamp) FROM scrobbles;")
                result = cursor.fetchone()
    except psycopg.Error:
        logger.exception("Database error while checking last timestamp")
        raise SystemExit(1)

    if result is None or result[0] is None:
        logger.info("No existing scrobbles found; fetching newest scrobbles only")
        return None

    since = int(result[0].timestamp()) + 1
    logger.info("Last scrobble timestamp: %s (since=%d)", result[0], since)
    return since


def load_scrobbles() -> None:
    logger.info("Loading scrobbles into PostgreSQL")

    try:
        df = pd.read_csv(VALIDATED_CSV)
    except FileNotFoundError:
        logger.error("Input file not found: %s", VALIDATED_CSV)
        raise SystemExit(1)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        logger.error(
            "%s is missing required columns: %s",
            VALIDATED_CSV,
            missing,
        )
        raise SystemExit(1)

    df = df[["artist", "track", "album", "timestamp"]]
    df = df.astype(object).where(df.notna(), None)

    records = list(df.itertuples(index=False, name=None))

    if not records:
        logger.info("No records to insert.")
        return

    try:
        with psycopg.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        ) as conn:
            with conn.cursor() as cursor:

                cursor.execute(
                    """
                    CREATE TEMP TABLE staged_scrobbles (
                        artist TEXT,
                        track TEXT,
                        album TEXT,
                        timestamp TIMESTAMPTZ
                    ) ON COMMIT DROP
                    """
                )

                with cursor.copy(
                    "COPY staged_scrobbles (artist, track, album, timestamp) FROM STDIN"
                ) as copy:
                    for record in records:
                        copy.write_row(record)

                cursor.execute(
                    """
                    INSERT INTO scrobbles (artist, track, album, timestamp)
                    SELECT artist, track, album, timestamp FROM staged_scrobbles
                    ON CONFLICT (artist, track, timestamp) DO NOTHING
                    """
                )

                inserted = cursor.rowcount
                skipped = len(records) - inserted

                logger.info(
                    "Processed %d scrobbles: %d inserted, %d duplicates skipped",
                    len(records), inserted, skipped,
                )

    except psycopg.Error:
        logger.exception("Database error while loading scrobbles")
        raise SystemExit(1)


if __name__ == "__main__":
    from src.config import setup_logging

    setup_logging()
    load_scrobbles()