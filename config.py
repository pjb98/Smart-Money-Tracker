"""
Configuration management for Pumpfun -> Raydium Prediction Agent
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Solana RPC (Helius)
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"
    solana_rpc_wss: str = "wss://api.mainnet-beta.solana.com"
    helius_api_key: Optional[str] = None  # Extracted from RPC URL or set directly
    helius_api_url: str = "https://api.helius.xyz/v0"

    # Pumpfun API
    pumpfun_api_url: str = "https://api.pumpfun.io"
    pumpfun_api_key: Optional[str] = None

    # Raydium
    raydium_api_url: str = "https://api.raydium.io"

    # Telegram
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_phone: Optional[str] = None
    phanes_channel_id: Optional[int] = None

    # Twitter (optional)
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_bearer_token: Optional[str] = None

    # Claude AI
    anthropic_api_key: Optional[str] = None

    # Birdeye API (wallet intelligence)
    birdeye_api_key: str = "public"

    # Database
    database_url: str = "sqlite:///./data/pumpfun_agent.db"

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/agent.log"

    # Model settings
    model_retrain_interval_hours: int = 24
    prediction_threshold: float = 0.6

    # Alert settings
    telegram_bot_token: Optional[str] = None
    alert_chat_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None

    # Paths
    feature_store_path: str = "./data/features"
    model_save_path: str = "./models"
    data_cache_path: str = "./data/cache"

    # Backtesting
    backtest_start_date: str = "2024-01-01"
    backtest_end_date: str = "2025-01-01"

    # Feature engineering windows
    lookback_windows: list = [60, 300, 900, 3600, 21600, 86400]  # 1m, 5m, 15m, 1h, 6h, 24h

    # Label windows (seconds)
    label_windows: dict = {
        "1h": 3600,
        "6h": 21600,
        "24h": 86400,
        "7d": 604800
    }

    # Prediction thresholds
    pump_threshold_1h: float = 0.10  # 10% gain
    pump_threshold_24h: float = 0.20  # 20% gain
    rug_threshold: float = -0.50  # 50% loss

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()


# Create necessary directories
def setup_directories():
    """Create required directories if they don't exist"""
    dirs = [
        "data",
        "data/cache",
        "data/features",
        "data/raw",
        "models",
        "logs",
        "notebooks",
        "scripts"
    ]

    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    setup_directories()
    print(f"Configuration loaded successfully")
    print(f"Solana RPC: {settings.solana_rpc_url}")
    print(f"Database: {settings.database_url}")
