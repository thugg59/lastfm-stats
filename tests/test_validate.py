import pandas as pd
import pytest
from src.validate import validate_scrobbles


def make_df(rows):
    return pd.DataFrame(rows)


def test_valid_row_passes_through():
    df = make_df([
        {"artist": "Radiohead", "track": "Videotape", "album": "In Rainbows",
         "timestamp": "2024-01-01T12:00:00Z"},
    ])

    valid, rejected = validate_scrobbles(df)

    assert len(valid) == 1
    assert len(rejected) == 0


def test_missing_artist_is_rejected():
    df = make_df([
        {"artist": "", "track": "Videotape", "album": "In Rainbows",
         "timestamp": "2024-01-01T12:00:00Z"},
    ])

    valid, rejected = validate_scrobbles(df)

    assert len(valid) == 0
    assert len(rejected) == 1
    assert rejected.iloc[0]["rejection_reason"] == "Missing artist"


def test_missing_track_is_rejected():
    df = make_df([
        {"artist": "Radiohead", "track": None, "album": "In Rainbows",
         "timestamp": "2024-01-01T12:00:00Z"},
    ])

    valid, rejected = validate_scrobbles(df)

    assert len(valid) == 0
    assert rejected.iloc[0]["rejection_reason"] == "Missing track"


def test_invalid_timestamp_is_rejected():
    df = make_df([
        {"artist": "Radiohead", "track": "Videotape", "album": "In Rainbows",
         "timestamp": "not-a-date"},
    ])

    valid, rejected = validate_scrobbles(df)

    assert len(valid) == 0
    assert rejected.iloc[0]["rejection_reason"] == "Invalid timestamp"


def test_future_timestamp_is_rejected():
    future = (pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1)).isoformat()
    df = make_df([
        {"artist": "Radiohead", "track": "Videotape", "album": "In Rainbows",
         "timestamp": future},
    ])

    valid, rejected = validate_scrobbles(df)

    assert len(valid) == 0
    assert rejected.iloc[0]["rejection_reason"] == "Future timestamp"


def test_multiple_reasons_are_combined():
    df = make_df([
        {"artist": "", "track": "", "album": "In Rainbows",
         "timestamp": "2024-01-01T12:00:00Z"},
    ])

    _, rejected = validate_scrobbles(df)

    reason = rejected.iloc[0]["rejection_reason"]
    assert "Missing artist" in reason
    assert "Missing track" in reason


def test_valid_and_rejected_counts_sum_to_input():
    df = make_df([
        {"artist": "Radiohead", "track": "Videotape", "album": "In Rainbows",
         "timestamp": "2024-01-01T12:00:00Z"},
        {"artist": "", "track": "Videotape", "album": "In Rainbows",
         "timestamp": "2024-01-01T12:00:00Z"},
        {"artist": "Radiohead", "track": "Videotape", "album": "In Rainbows",
         "timestamp": "garbage"},
    ])

    valid, rejected = validate_scrobbles(df)

    assert len(valid) + len(rejected) == len(df)


def test_missing_required_column_raises():
    df = make_df([{"artist": "Radiohead", "track": "Videotape"}])  # no album/timestamp

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_scrobbles(df)