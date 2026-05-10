"""
Genius lyrics client — uses the public search API + page scraping.
No third-party library needed; pure httpx.
"""

import re
from html.parser import HTMLParser

import httpx

GENIUS_API = "https://api.genius.com"
GENIUS_BASE = "https://genius.com"

_STOP_WORDS = {
    # English
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it", "they",
    "them", "his", "her", "its", "the", "a", "an", "and", "or", "but", "in",
    "on", "at", "to", "for", "of", "with", "by", "from", "is", "are", "was",
    "were", "be", "been", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "that", "this", "these",
    "those", "what", "so", "if", "as", "not", "no", "yeah", "oh", "uh",
    "ooh", "ah", "la", "na", "da", "de", "em", "im", "dont", "can", "just",
    "all", "up", "out", "when", "more", "like", "get", "got", "let", "go",
    "know", "think", "want", "say", "see", "come", "keep", "make", "take",
    "give", "find", "tell", "back", "way", "time", "now", "here", "there",
    "then", "than", "too", "into", "over", "own", "down", "never", "every",
    "still", "between", "each", "before", "after", "without", "through",
    "about", "again", "right", "need", "how", "who", "him",
    # Hebrew common words
    "את", "של", "על", "עם", "אני", "לא", "הוא", "היא", "הם", "אנחנו",
    "כי", "אבל", "גם", "כבר", "עוד", "רק", "כן", "לי", "לך", "לו",
    "לה", "אם", "כל", "זה", "זו", "זאת", "מה", "שם", "כאן", "אז",
    "עד", "אחרי", "לפני", "בין", "תחת", "שלי", "שלך", "שלו", "שלה",
    "היה", "הייתה", "יהיה", "תהיה", "הם", "הן", "אותי", "אותך", "אותו",
}


class _LyricsParser(HTMLParser):
    """Extracts text from Genius lyrics containers."""
    def __init__(self):
        super().__init__()
        self._in_lyrics = False
        self._depth = 0
        self.text_parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        data_attr = attrs_dict.get("data-lyrics-container", "")
        if data_attr == "true":
            self._in_lyrics = True
            self._depth = 1
        elif self._in_lyrics:
            self._depth += 1

    def handle_endtag(self, tag):
        if self._in_lyrics:
            self._depth -= 1
            if self._depth <= 0:
                self._in_lyrics = False

    def handle_data(self, data):
        if self._in_lyrics:
            self.text_parts.append(data)

    def handle_entityref(self, name):
        if self._in_lyrics and name == "amp":
            self.text_parts.append("&")


def _clean_lyrics(raw: str) -> str:
    # Remove section headers like [Verse 1], [Chorus], etc.
    text = re.sub(r"\[.*?\]", " ", raw)
    # Remove punctuation
    text = re.sub(r"[^\w\s']", " ", text)
    return text.lower()


def _word_frequency(lyrics: str, top_n: int = 60) -> list[dict]:
    from collections import Counter
    words = [
        w.strip("'")
        for w in _clean_lyrics(lyrics).split()
        if len(w) > 2 and w.strip("'") not in _STOP_WORDS
    ]
    counts = Counter(words)
    return [{"word": w, "count": c} for w, c in counts.most_common(top_n)]


class GeniusClient:
    def __init__(self, access_token: str):
        self._token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

    async def search(self, title: str, artist: str) -> str | None:
        """Return Genius song URL or None if not found."""
        query = f"{title} {artist}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{GENIUS_API}/search",
                params={"q": query},
                headers=self._headers,
            )
            if r.status_code != 200:
                return None
            hits = r.json().get("response", {}).get("hits", [])
            for hit in hits:
                if hit.get("type") == "song":
                    return hit["result"]["url"]
        return None

    async def get_lyrics(self, url: str) -> str | None:
        """Scrape lyrics text from a Genius page URL."""
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                return None
        parser = _LyricsParser()
        parser.feed(r.text)
        raw = "\n".join(parser.text_parts).strip()
        return raw if raw else None

    async def get_word_frequency(self, title: str, artist: str, top_n: int = 60) -> list[dict] | None:
        url = await self.search(title, artist)
        if not url:
            return None
        lyrics = await self.get_lyrics(url)
        if not lyrics:
            return None
        return _word_frequency(lyrics, top_n)
