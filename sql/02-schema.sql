SET client_min_messages = warning;

CREATE TABLE IF NOT EXISTS scrobbles (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    artist TEXT NOT NULL,
    track TEXT NOT NULL,
    album TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    UNIQUE (artist, track, timestamp)
);