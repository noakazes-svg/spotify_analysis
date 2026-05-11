-- ============================================================
-- TABLE: tracks
-- One row per unique song.
-- Lyrics are stored directly on the track row.
-- ============================================================

CREATE TABLE tracks (
    -- Primary key
    id              TEXT PRIMARY KEY,       -- UUID, e.g. "3f2a1b..."

    -- Spotify identity
    spotify_id      TEXT UNIQUE NOT NULL,   -- Spotify track ID, e.g. "6rqhFgbbKwnb9MLmUQDhG6"

    -- Song metadata
    name            TEXT NOT NULL,          -- Song title
    artist          TEXT NOT NULL,          -- Artist / band name (comma-separated if multiple)
    artist_id       TEXT,                   -- Spotify ID of the primary artist
    album           TEXT,                   -- Album name
    release_year    INTEGER,                -- e.g. 2019

    -- Spotify audio data
    duration_ms     INTEGER,                -- Track length in milliseconds
    popularity      INTEGER,                -- 0–100 Spotify popularity score
    preview_url     TEXT,                   -- 30-second preview MP3 URL (may be null)
    image_url       TEXT,                   -- Album cover image URL
    audio_features  TEXT,                   -- JSON: danceability, energy, valence, tempo, etc.

    -- Lyrics (populated by the lyrics pipeline)
    lyrics_raw          TEXT,               -- Full lyrics as fetched (Shironet or Genius)
    lyrics_cleaned      TEXT,               -- Cleaned version: lowercase, no punctuation
    lyrics_fetched_at   TEXT,               -- ISO timestamp of when lyrics were fetched
    nlp_processed       INTEGER DEFAULT 0   -- 0 = not yet processed, 1 = NLP done (Phase 3)
);

-- ============================================================
-- HELPER: latest report ID (used in all queries below)
-- ============================================================
-- Replace <YOUR_USER_ID> with your actual user UUID from the users table:
--   SELECT id, display_name FROM users;

-- ============================================================
-- LIKED SONGS QUERIES
-- All queries below filter to YOUR liked songs only,
-- ignoring the top-tracks data also stored in the DB.
-- ============================================================

-- How many liked songs are stored?
SELECT COUNT(DISTINCT t.id) AS liked_songs
FROM tracks t
INNER JOIN user_tracks ut ON ut.track_id = t.id
WHERE ut.term = 'liked';

-- How many liked songs have lyrics?
SELECT
    COUNT(DISTINCT t.id) AS total_liked,
    SUM(CASE WHEN t.lyrics_raw IS NOT NULL THEN 1 ELSE 0 END) AS with_lyrics,
    SUM(CASE WHEN t.lyrics_raw IS NULL    THEN 1 ELSE 0 END) AS without_lyrics
FROM tracks t
INNER JOIN user_tracks ut ON ut.track_id = t.id
WHERE ut.term = 'liked';

-- Show liked songs with their lyrics status
SELECT DISTINCT
    t.name,
    t.artist,
    t.album,
    t.release_year,
    CASE WHEN t.lyrics_raw IS NOT NULL THEN 'YES' ELSE 'NO' END AS has_lyrics,
    t.lyrics_fetched_at
FROM tracks t
INNER JOIN user_tracks ut ON ut.track_id = t.id
WHERE ut.term = 'liked'
ORDER BY t.artist, t.name;

-- Show liked songs that have lyrics
SELECT DISTINCT t.name, t.artist, t.album, t.release_year, t.lyrics_fetched_at
FROM tracks t
INNER JOIN user_tracks ut ON ut.track_id = t.id
WHERE ut.term = 'liked'
  AND t.lyrics_raw IS NOT NULL
ORDER BY t.lyrics_fetched_at DESC;

-- Show liked songs still missing lyrics
SELECT DISTINCT t.name, t.artist, t.album
FROM tracks t
INNER JOIN user_tracks ut ON ut.track_id = t.id
WHERE ut.term = 'liked'
  AND t.lyrics_raw IS NULL
ORDER BY t.artist;

-- Show the full lyrics of a specific liked song
SELECT t.name, t.artist, t.lyrics_raw
FROM tracks t
INNER JOIN user_tracks ut ON ut.track_id = t.id
WHERE ut.term = 'liked'
  AND t.name = 'Song Title Here';

-- Search liked songs by name
SELECT DISTINCT t.name, t.artist, t.lyrics_raw
FROM tracks t
INNER JOIN user_tracks ut ON ut.track_id = t.id
WHERE ut.term = 'liked'
  AND t.name LIKE '%love%';

-- Most represented artists in liked songs
SELECT DISTINCT t.artist, COUNT(DISTINCT t.id) AS track_count
FROM tracks t
INNER JOIN user_tracks ut ON ut.track_id = t.id
WHERE ut.term = 'liked'
GROUP BY t.artist
ORDER BY track_count DESC
LIMIT 20;

-- Liked songs grouped by decade
SELECT
    (t.release_year / 10 * 10) || 's' AS decade,
    COUNT(DISTINCT t.id) AS track_count
FROM tracks t
INNER JOIN user_tracks ut ON ut.track_id = t.id
WHERE ut.term = 'liked'
  AND t.release_year IS NOT NULL
GROUP BY decade
ORDER BY decade;
