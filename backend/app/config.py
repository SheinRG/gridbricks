from datetime import date, time
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime settings. Override any field with a WFM_-prefixed environment variable."""

    model_config = SettingsConfigDict(env_prefix="WFM_")

    data_path: Path = BACKEND_DIR / "data" / "wind_jan2026.sqlite"
    # Built frontend, served by the API in the production Docker image. Ignored if missing.
    static_dir: Path = BACKEND_DIR.parent / "frontend" / "dist"

    # Business timezone for gate closure and display. Never use naive datetimes.
    market_tz: str = "Europe/London"

    # D1: decisions made in January 2026 -> delivery days 2 Jan to 1 Feb.
    default_start: date = date(2026, 1, 2)
    default_end: date = date(2026, 2, 1)

    # D2: GB day-ahead auction gate closure (UK local time on D-1).
    default_cutoff_time: time = time(9, 50)
    default_horizon_hours: int = 24
    min_horizon_hours: int = 1
    max_horizon_hours: int = 48

    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
