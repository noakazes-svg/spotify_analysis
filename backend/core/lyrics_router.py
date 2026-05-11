"""
Lyrics router — decides whether to fetch lyrics from Shironet or Genius.
Rule: if the song title or artist name contains Hebrew characters → Shironet,
otherwise → Genius.
"""

# Hebrew Unicode block: U+05D0 (א) through U+05EA (ת), plus vowels/marks above.
_HEBREW_START = "֐"
_HEBREW_END = "׿"


def _contains_hebrew(text: str) -> bool:
    return any(_HEBREW_START <= ch <= _HEBREW_END for ch in text)


def route_lyrics(title: str, artist: str) -> str:
    """Return 'shironet' if the song is Hebrew, otherwise 'genius'."""
    if _contains_hebrew(title) or _contains_hebrew(artist):
        return "shironet"
    return "genius"
