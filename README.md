# Spotify Data Analysis

A data engineering project that collects, cleans, and analyzes personal Spotify listening data — including lyrics from both English (Genius) and Hebrew (Shironet) sources.

---

## Project Structure

```
├── 01_data_collection.ipynb     # Pipeline design and data ingestion
├── 02_data_cleaning.ipynb       # Data quality checks and cleaning
├── 03_data_visualization.ipynb  # 20 SQL-driven insights and charts
├── spotify_intel.db             # SQLite database with all collected data
│
├── backend/                     # Data pipeline source code
│   ├── core/
│   │   ├── spotify.py           # Spotify API connector
│   │   ├── genius.py            # Genius lyrics connector (English)
│   │   ├── shironet.py          # Shironet scraper (Hebrew)
│   │   ├── lyrics_router.py     # Language-aware routing (Hebrew / English)
│   │   └── config.py
│   ├── db/
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   └── database.py
│   └── pipelines/
│       ├── spotify_ingest.py    # Top-tracks ingestion
│       ├── liked_songs_pipeline.py  # Liked-songs ingestion
│       └── lyrics_pipeline.py   # Lyrics enrichment
│
└── architecture/
    ├── HLD_LLD.md               # System design — high & low level
    └── tables_schema.sql        # Database table definitions
```

## The Three Parts

### Part 1 — Data Collection (`01_data_collection.ipynb`)
Implements a five-component pipeline following the system architecture:
1. **Spotify Connector** — OAuth 2.0, fetches top tracks and liked songs via Spotify Web API
2. **Router** — Detects Hebrew vs. English song titles/artists using Unicode range analysis
3. **Genius Connector** — Fetches English lyrics via the Genius REST API
4. **Shironet Connector** — Scrapes Hebrew lyrics from Shironet using BeautifulSoup
5. **Main Pipeline** — Orchestrates all components; persists data to SQLite

### Part 2 — Data Cleaning (`02_data_cleaning.ipynb`)
- Missing value analysis across all track fields
- Release year distribution and outlier detection
- Duration analysis and normalization
- Hebrew/English language distribution
- Lyrics cleaning (stripping annotations, normalizing whitespace)
- Final data quality summary

### Part 3 — Data Visualizations (`03_data_visualization.ipynb`)
20 SQL queries with visualizations exploring listening habits:
- Top artists, albums, and decades
- Audio feature analysis (danceability, energy, valence, etc.)
- Cross-term listening patterns (short / medium / long term)
- Lyrics coverage and language breakdown
- Temporal trends and popularity distributions

## Tech Stack
- **Python** — httpx, BeautifulSoup4, SQLAlchemy, pandas, matplotlib, seaborn
- **Database** — SQLite (`spotify_intel.db`)
- **APIs** — Spotify Web API, Genius API
- **Scraping** — Shironet (Hebrew lyrics)

## Running the Notebooks
```bash
pip install -r backend/requirements.txt
jupyter notebook
```
Open notebooks in order: `01` → `02` → `03`.
The database (`spotify_intel.db`) is already populated and ready to query.
