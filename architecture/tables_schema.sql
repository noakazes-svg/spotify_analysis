-- ============================================================
-- DATABASE SCHEMA — Spotify Analysis App
-- ============================================================

-- ============================================================
-- TABLE: tracks
-- One row per unique song (raw Spotify metadata only).
-- Lyrics are stored separately in track_lyrics.
-- ============================================================

CREATE TABLE tracks (
    id              TEXT PRIMARY KEY,       -- UUID, e.g. "3f2a1b..."
    spotify_id      TEXT UNIQUE NOT NULL,   -- Spotify track ID
    name            TEXT NOT NULL,          -- Song title
    artist          TEXT NOT NULL,          -- Artist name (comma-separated if multiple)
    artist_id       TEXT,                   -- Spotify ID of the primary artist
    album           TEXT,                   -- Album name
    release_year    INTEGER,                -- e.g. 2019
    duration_ms     INTEGER,                -- Track length in milliseconds
    popularity      INTEGER,                -- 0–100 Spotify popularity score
    preview_url     TEXT,                   -- 30-second preview MP3 URL (may be null)
    image_url       TEXT,                   -- Album cover image URL
    audio_features  TEXT                    -- JSON: danceability, energy, valence, tempo, etc.
);

-- ============================================================
-- TABLE: track_lyrics
-- One row per song that has lyrics (1:1 with tracks).
-- Separated from tracks so raw metadata stays clean.
-- ============================================================

CREATE TABLE track_lyrics (
    id                TEXT PRIMARY KEY,     -- UUID
    track_id          TEXT UNIQUE NOT NULL  -- FK → tracks.id
        REFERENCES tracks(id),
    lyrics_raw        TEXT,                 -- Full lyrics as fetched from Genius
    lyrics_cleaned    TEXT,                 -- Cleaned version: lowercase, no punctuation
    lyrics_fetched_at TEXT,                 -- ISO timestamp of when lyrics were fetched
    nlp_processed     INTEGER DEFAULT 0     -- 0 = not yet processed, 1 = NLP done
);

-- ============================================================
-- TABLE: listening_snapshot
-- One row per song per listening context per report.
-- term values: 'short_term' | 'medium_term' | 'long_term' | 'liked' | 'playlist'
-- play_weight: short_term=3.0, medium_term=2.0, long_term=1.0, liked/playlist=1.0
-- ============================================================

CREATE TABLE listening_snapshot (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id),
    track_id    TEXT NOT NULL REFERENCES tracks(id),
    report_id   TEXT NOT NULL REFERENCES reports(id),
    term        TEXT,                       -- listening context
    rank        INTEGER,                    -- position within term (NULL for liked/playlist)
    play_weight REAL DEFAULT 1.0            -- recency weight used for scoring
);

