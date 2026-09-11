import logging
import pandas as pd
from src.config import SCROBBLES_CSV, VALIDATED_CSV, REJECTED_CSV

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"artist", "track", "album", "timestamp"}

def validate_scrobbles(df):
    logger.info("Validating %d scrobbles", len(df))
    
    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        logger.error("Missing required columns: %s", missing)
        raise ValueError(f"Missing required columns: {missing}")

    df = df.reset_index(drop=True)

    rejected = []

    # Check missing artist
    missing_artist = (
        df["artist"].fillna("").astype(str).str.strip().eq("")
    )

    for index in df[missing_artist].index:
        rejected.append((index, "Missing artist"))

    # Check missing track
    missing_track = (
        df["track"].fillna("").astype(str).str.strip().eq("")
    )

    for index in df[missing_track].index:
        rejected.append((index, "Missing track"))

    # Check invalid timestamp
    parsed_timestamp = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
        utc=True
    )
    invalid_timestamp = parsed_timestamp.isna()

    for index in df[invalid_timestamp].index:
        rejected.append((index, "Invalid timestamp"))

    # Check future timestamp
    future_timestamp = parsed_timestamp > pd.Timestamp.now(tz="UTC")

    for index in df[future_timestamp & ~invalid_timestamp].index:
        rejected.append((index, "Future timestamp"))

    # Create rejected dataframe
    rejected_indexes = set(index for index, reason in rejected)

    rejected_df = df.loc[sorted(rejected_indexes)].copy()

    reasons = {}

    for index, reason in rejected:
        if index in reasons:
            reasons[index] += f"; {reason}"
        else:
            reasons[index] = reason

    rejected_df["rejection_reason"] = rejected_df.index.map(reasons)

    # Valid rows = everything not rejected
    valid_df = df.drop(index=rejected_indexes).copy()

    return valid_df, rejected_df


if __name__ == "__main__":
    from src.config import setup_logging
    setup_logging()

    try:
        df = pd.read_csv(SCROBBLES_CSV)
    except FileNotFoundError:
        logger.error("Input file not found: %s", SCROBBLES_CSV)
        raise SystemExit(1)

    valid, rejected = validate_scrobbles(df)

    logger.info("Rows read: %d", len(df))
    logger.info("Valid rows: %d", len(valid))
    logger.info("Rejected rows: %d", len(rejected))

    valid.to_csv(
        VALIDATED_CSV,
        index=False
    )

    rejected.to_csv(
        REJECTED_CSV,
        index=False
    )
    