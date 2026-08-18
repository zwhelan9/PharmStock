from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "Pharmacy Stock Prediction System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/pharmacy.db"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    # Alert thresholds (days before expiry)
    EXPIRY_CRITICAL_DAYS: int = 30
    EXPIRY_WARNING_DAYS: int = 60
    EXPIRY_WATCH_DAYS: int = 90

    # Prediction horizon options
    FORECAST_HORIZONS: list[int] = [7, 14, 30]

    # Pack / Write-Off settings
    COUNTERSIGN_WINDOW_HOURS: int = 24
    WRITEOFF_LOSS_RATE_THRESHOLD: float = 0.1
    TOUCHSTORE_QTY_TOLERANCE: int = 0
    PACK_EXPIRY_ALERT_DAYS: int = 90

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
