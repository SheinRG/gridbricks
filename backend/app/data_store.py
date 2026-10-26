"""Loads the processed SQLite file once per process and keeps it in memory (DECISIONS D7)."""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.config import get_settings

DTYPE = "datetime64[ns, UTC]"
log = logging.getLogger("app.data")


@dataclass(frozen=True)
class DataStore:
    actuals: pd.DataFrame  # start_time, generation_mw, publish_time
    forecasts: pd.DataFrame  # publish_time, start_time, generation_mw
    meta: dict[str, str]

    @property
    def delivery_start(self) -> date:
        return date.fromisoformat(self.meta["delivery_start"])

    @property
    def delivery_end(self) -> date:
        return date.fromisoformat(self.meta["delivery_end"])


def load_store(path: Path) -> DataStore:
    if not path.is_file():
        raise FileNotFoundError(f"Processed data not found at {path}. Run scripts/ingest.py.")
    # Read-only URI so a serverless filesystem (read-only) is never written to.
    with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as conn:
        actuals = pd.read_sql("SELECT * FROM actuals ORDER BY start_time", conn)
        forecasts = pd.read_sql("SELECT * FROM forecasts ORDER BY publish_time, start_time", conn)
        meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    conn.close()

    for df in (actuals, forecasts):
        for col in ("start_time", "publish_time"):
            df[col] = pd.to_datetime(df[col], utc=True).astype(DTYPE)

    log.info(
        "data loaded",
        extra={"path": str(path), "actuals": len(actuals), "forecasts": len(forecasts)},
    )
    return DataStore(actuals=actuals, forecasts=forecasts, meta=meta)


@lru_cache
def get_store() -> DataStore:
    return load_store(get_settings().data_path)
