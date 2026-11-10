from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "DIYAR COMPASS"
    secret_key: str = "dev-only-change-this-secret"
    access_token_minutes: int = 60
    refresh_token_days: int = 7
    database_url: str = f"sqlite:///{BACKEND_DIR / 'diyar_compass.db'}"
    cors_origins: str = "http://localhost:3000"
    storage_path: str = str(BACKEND_DIR / "storage")
    seed_sample_data: bool = True
    testing: bool = False

    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
