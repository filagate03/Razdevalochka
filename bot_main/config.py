from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    main_bot_token: str = Field(..., alias="MAIN_BOT_TOKEN")
    ai_api_url: str = Field(..., alias="AI_API_URL")
    ai_api_key: str = Field(..., alias="AI_API_KEY")

    admin_ids: List[int] = Field(default_factory=list, alias="ADMIN_IDS")

    yookassa_shop_id: str = Field(..., alias="YOOKASSA_SHOP_ID")
    yookassa_secret_key: str = Field(..., alias="YOOKASSA_SECRET_KEY")

    cloudpayments_public_id: str = Field(..., alias="CLOUDPAYMENTS_PUBLIC_ID")
    cloudpayments_api_secret: str = Field(..., alias="CLOUDPAYMENTS_API_SECRET")

    cryptobot_api_token: str = Field(..., alias="CRYPTOBOT_API_TOKEN")

    database_url: str = Field(..., alias="DATABASE_URL")

    webhook_base_url: str = Field(..., alias="WEBHOOK_BASE_URL")
    webhook_secret: str = Field(..., alias="WEBHOOK_SECRET")
    stars_bot_username: str = Field("stars_payment_bot", alias="STARS_BOT_USERNAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("admin_ids", pre=True)
    def parse_admin_ids(cls, value: str | List[int]) -> List[int]:  # type: ignore[override]
        if isinstance(value, list):
            return [int(v) for v in value]
        if not value:
            return []
        return [int(v.strip()) for v in value.split(",") if v.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
