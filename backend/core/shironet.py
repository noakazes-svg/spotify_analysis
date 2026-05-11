"""
Shironet (שירונט) lyrics scraper.
Searches shironet.mako.co.il and extracts Hebrew song lyrics.
"""

import urllib.parse

import httpx
from bs4 import BeautifulSoup

SHIRONET_BASE = "https://shironet.mako.co.il"
SEARCH_URL = f"{SHIRONET_BASE}/search"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
    "Accept-Charset": "utf-8",
}


class ShironetClient:
    async def get_lyrics(self, title: str, artist: str) -> str | None:
        """Search for a song on Shironet and return its lyrics, or None if not found."""
        song_url = await self._find_song_url(title, artist)
        if not song_url:
            return None
        return await self._scrape_lyrics(song_url)

    async def _find_song_url(self, title: str, artist: str) -> str | None:
        query = urllib.parse.quote(f"{title} {artist}")
        search_url = f"{SEARCH_URL}?q={query}&lang=1&type=lyrics"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            try:
                r = await client.get(search_url, headers=_HEADERS)
                r.raise_for_status()
            except httpx.HTTPError:
                return None

        soup = BeautifulSoup(r.text, "html.parser")

        # Shironet search results: links whose href contains "artist?type=lyrics"
        for link in soup.find_all("a", href=True):
            href: str = link["href"]
            if "artist?type=lyrics" in href:
                if href.startswith("http"):
                    return href
                return f"{SHIRONET_BASE}/{href.lstrip('/')}"
        return None

    async def _scrape_lyrics(self, url: str) -> str | None:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            try:
                r = await client.get(url, headers=_HEADERS)
                r.raise_for_status()
            except httpx.HTTPError:
                return None

        soup = BeautifulSoup(r.text, "html.parser")

        # Try known Shironet lyrics containers in order of specificity
        for selector in [
            {"class": "artist_lyrics_text"},
            {"class": "wrd_inr"},
            {"id": "lyrics"},
        ]:
            container = soup.find(True, selector)
            if container:
                text = container.get_text(separator="\n").strip()
                if text:
                    return text

        return None
