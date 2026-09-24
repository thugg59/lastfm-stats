SET client_min_messages = warning;

CREATE TABLE IF NOT EXISTS scrobbles (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    artist TEXT NOT NULL,
    track TEXT NOT NULL,
    album TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    UNIQUE (artist, track, timestamp)
);

-- Tracks resume progress for a full-history backfill so an interrupted run
-- (a killed workflow timeout, a cancelled job, a dropped IAP tunnel, etc.)
-- picks up from the next unfetched page instead of restarting at page 1.
-- Single-row table, keyed to id=1; cleared automatically once a run finishes.
CREATE TABLE IF NOT EXISTS fullhistory_checkpoint (
    id INTEGER PRIMARY KEY DEFAULT 1,
    next_page INTEGER NOT NULL,
    total_pages INTEGER NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fullhistory_checkpoint_single_row CHECK (id = 1)
);