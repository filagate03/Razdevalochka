from __future__ import annotations

from functools import lru_cache

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    stars_bot_token: str = Field(..., alias="STARS_BOT_TOKEN")
    database_url: str = Field(..., alias="DATABASE_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
