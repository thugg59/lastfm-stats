SET client_min_messages = warning;

CREATE OR REPLACE VIEW top_artists AS
SELECT
    artist,
    COUNT(*) AS play_count
FROM scrobbles
GROUP BY artist
ORDER BY play_count DESC;

CREATE OR REPLACE VIEW top_tracks AS
SELECT
    artist,
    track,
    COUNT(*) AS play_count
FROM scrobbles
GROUP BY artist, track
ORDER BY play_count DESC;

CREATE OR REPLACE VIEW daily_listening AS
SELECT
    date_trunc('day', timestamp)::date AS day,
    COUNT(*) AS scrobble_count
FROM scrobbles
GROUP BY day
ORDER BY day;

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