from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    environment: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"

    # Spotify OAuth
    spotify_client_id: str = "CHANGE_ME"
    spotify_client_secret: str = "CHANGE_ME"
    spotify_redirect_uri: str = "http://127.0.0.1:8000/api/v1/auth/spotify/callback"
    spotify_scopes: str = (
        "user-read-private user-read-email user-top-read "
        "user-read-recently-played user-library-read"
    )

    # External APIs (Phase 2)
    genius_access_token: str = ""
    openai_api_key: str = ""

    # Database — SQLite for local dev, swap to postgresql+asyncpg:// for prod
    database_url: str = "sqlite+aiosqlite:///./spotify_intel.db"

    # JWT
    jwt_secret_key: str = "jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Frontend
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
