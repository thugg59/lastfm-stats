from src.extract import fetch_scrobbles
from src.transform import transform_scrobbles
from src.validate import validate_scrobbles
from src.load import load_scrobbles, get_last_timestamp

import logging
import argparse
import pandas as pd

from src.config import (
    RAW_DIR,
    PROCESSED_DIR,
    QUARANTINE_DIR,
    SCROBBLES_CSV,
    VALIDATED_CSV,
    REJECTED_CSV,
    setup_logging,
)

logger = logging.getLogger(__name__)


def run_pipeline(full_history=False):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("[1/4] Extracting...")
    since = None if full_history else get_last_timestamp()
    fetch_scrobbles(since=since, full_history=full_history)

    logger.info("[2/4] Transforming...")
    transform_scrobbles()

    logger.info("[3/4] Validating...")

    try:
        df = pd.read_csv(SCROBBLES_CSV)
    except FileNotFoundError:
        logger.error("Input file not found: %s", SCROBBLES_CSV)
        raise SystemExit(1)
    
    valid, rejected = validate_scrobbles(df)

    valid.to_csv(
        VALIDATED_CSV,
        index=False
    )

    rejected.to_csv(
        REJECTED_CSV,
        index=False
    )

    logger.info("Rows read: %d", len(df))
    logger.info("Valid rows: %d", len(valid))
    logger.info("Rejected rows: %d", len(rejected))

    logger.info("[4/4] Loading...")
    load_scrobbles()

    logger.info("Pipeline completed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full-history",
        action="store_true",
        help="Fetch the complete scrobble history instead of only the newest scrobbles",
    )
    args = parser.parse_args()

    setup_logging()
    run_pipeline(full_history=args.full_history)