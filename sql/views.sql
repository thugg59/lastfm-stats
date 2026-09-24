
SET client_min_messages = warning;

CREATE OR REPLACE VIEW top_artists AS
SELECT
    artist,
    COUNT(*) AS play_count
FROM scrobbles
GROUP BY artist
ORDER BY play_count DESC, artist
LIMIT 10;

CREATE OR REPLACE VIEW top_tracks AS
SELECT
    artist,
    track,
    COUNT(*) AS play_count
FROM scrobbles
GROUP BY artist, track
ORDER BY play_count DESC, artist, track
LIMIT 10;

CREATE OR REPLACE VIEW hourly_listening_pattern AS
SELECT
    EXTRACT(HOUR FROM timestamp)::int AS hour_of_day,
    COUNT(*) AS scrobble_count
FROM scrobbles
GROUP BY hour_of_day
ORDER BY hour_of_day;

CREATE OR REPLACE VIEW monthly_summary AS
SELECT
    date_trunc('month', timestamp)::date AS month,
    COUNT(*) AS scrobble_count,
    COUNT(DISTINCT artist) AS distinct_artists
FROM scrobbles
GROUP BY month
ORDER BY month;

CREATE OR REPLACE VIEW yearly_summary AS
SELECT
    EXTRACT(YEAR FROM timestamp)::int AS year,
    COUNT(*) AS scrobble_count,
    COUNT(DISTINCT artist) AS distinct_artists
FROM scrobbles
GROUP BY year
ORDER BY year;

CREATE OR REPLACE VIEW overview AS
WITH totals AS (
    SELECT
        COUNT(*)               AS total_scrobbles,
        COUNT(DISTINCT artist) AS unique_artists,
        MIN(timestamp)::date   AS first_scrobble,
        MAX(timestamp)::date   AS last_scrobble
    FROM scrobbles
),
top_artist AS (
    SELECT artist
    FROM scrobbles
    GROUP BY artist
    ORDER BY COUNT(*) DESC, artist
    LIMIT 1
),
top_track AS (
    SELECT artist, track
    FROM scrobbles
    GROUP BY artist, track
    ORDER BY COUNT(*) DESC, artist, track
    LIMIT 1
)
SELECT
    t.total_scrobbles,
    t.unique_artists,
    t.first_scrobble,
    t.last_scrobble,
    a.artist AS top_artist,
    k.artist AS top_track_artist,
    k.track  AS top_track
FROM totals t, top_artist a, top_track k;

