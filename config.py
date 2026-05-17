"""
CybEarn - Centralized Configuration
All environment-driven settings for the Telegram Mini App.
"""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    # ── App Meta ─────────────────────────────────────────────────────────────
    APP_NAME: str = "CybEarn"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    BASE_URL: str = "https://yourdomain.com"          # Public-facing URL

    # ── Telegram Bot ──────────────────────────────────────────────────────────
    BOT_TOKEN: str = "YOUR_BOT_TOKEN_HERE"
    BOT_USERNAME: str = "cybearn_bot"
    TELEGRAM_API_URL: str = "https://api.telegram.org"

    # ── Admin Access ──────────────────────────────────────────────────────────
    # Comma-separated Telegram IDs that can access the admin panel
    ADMIN_IDS: List[int] = [123456789]

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./cybearn.db"
    # For production use PostgreSQL:
    # DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/cybearn"

    # ── JWT Authentication ────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE_THIS_TO_A_RANDOM_256BIT_SECRET"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080           # 7 days

    # ── Referral System ───────────────────────────────────────────────────────
    REFERRAL_BONUS_REFERRER: float = 50.0     # Coins earned by referrer per signup
    REFERRAL_BONUS_REFEREE: float = 25.0      # Coins earned by new user on signup
    # Multi-level commission: [level1%, level2%] as decimals
    REFERRAL_COMMISSION_RATES: List[float] = [0.10, 0.05]

    # ── Earn Rates ────────────────────────────────────────────────────────────
    DEFAULT_TASK_REWARD: float = 100.0        # Default coins for a new task
    MIN_WITHDRAW_AMOUNT: float = 500.0        # Minimum balance to withdraw
    COIN_SYMBOL: str = "⚡"                   # Display symbol

    # ── File Uploads ──────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]

    # ── Montage SDK (Ad Network) ──────────────────────────────────────────────
    MONTAGE_APP_ID: str = "YOUR_MONTAGE_APP_ID"
    MONTAGE_API_KEY: str = "YOUR_MONTAGE_API_KEY"
    MONTAGE_SDK_URL: str = "https://sdk.montageads.io/v2/montage.min.js"
    MONTAGE_REWARD_MULTIPLIER: float = 1.0    # Scale ad rewards

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["https://yourdomain.com", "https://web.telegram.org"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance – call this everywhere instead of Settings()."""
    return Settings()


settings = get_settings()
