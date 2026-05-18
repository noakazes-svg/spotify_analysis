# System Architecture — HLD & LLD

## High Level Design (HLD)

### Spotify Connector
**Description:** Takes user login information, connects to Spotify, and extracts the user's liked songs list — including song title, artist/band name, album name, release year, and genre. Writes the data to the database.

- **Inputs:** Username/password or API key
- **Outputs:** List of song metadata
- **Dependencies:** Spotify API, database connection

---

### Shironet Connector
**Description:** Receives song-identifying data and connects to the Shironet website to retrieve the Hebrew lyrics for that song.

- **Inputs:** Song title, artist/band name, album name, release year, genre
- **Outputs:** Song lyrics (Hebrew)
- **Dependencies:** Shironet website, database connection

---

### Genius Connector
**Description:** Receives song-identifying data and connects to the Genius website to retrieve the English lyrics for that song.

- **Inputs:** Song title, artist/band name, album name, release year, genre
- **Outputs:** Song lyrics (English)
- **Dependencies:** Genius API, database connection

---

### Router
**Description:** Receives information about one song and decides which connector to use — Shironet (Hebrew) or Genius (English) — to retrieve the lyrics.

- **Inputs:** Song metadata (one song)
- **Outputs:** Name of the selected connector
- **Dependencies:** Main, Shironet Connector, Genius Connector

---

### Main
**Description:** Invokes the Spotify Connector with user information, retrieves song data from the database, and sends one song at a time to the Router to fetch lyrics.

- **Inputs:** User information
- **Outputs:** Lyrics for all songs
- **Dependencies:** Database connection, Router

---

## Low Level Design (LLD)

### Spotify Connector
**Flow:**
1. Get login details from the user and connect to their Spotify account
2. Navigate to the liked songs list
3. Copy song titles
4. For each song, retrieve: artist/band name, album name, release year, genre
5. Write all song data to the database (primary key: song ID)

---

### Shironet Connector
**Flow:**
1. Receive song-identifying data: title, artist/band, album, release year, genre
2. Find the song page on the Shironet website
3. Copy the lyrics and store them in the database

---

### Genius Connector
**Flow:**
1. Receive song-identifying data: title, artist/band, album, release year, genre
2. Find the song page on the Genius website
3. Copy the lyrics and store them in the database

---

### Router
**Flow:**
1. Receive information about one song
2. Choose which connector will handle the request — Shironet (Hebrew) or Genius (English)

---

### Main
**Flow:**
1. Get login details from the user
2. Contact the Spotify Connector to connect to their Spotify account
3. Retrieve the songs data from the database
4. Send one song at a time to the Router to fetch lyrics
5. Record the lyrics of each song to the database, one song at a time
6. Verify that lyrics were received for all songs; inform the user whether the process succeeded or failed, and how many songs had lyrics found
