"""Fetch FUELHH (wind actuals) and WINDFOR (wind forecasts) from Elexon, clean, write SQLite.

Run once; the API only reads the committed output. Re-running is idempotent: the file is
rebuilt from scratch and swapped in atomically.

    python backend/scripts/ingest.py                      # default: January 2026 decisions
    python backend/scripts/ingest.py --start 2026-01-02 --end 2026-02-01
"""

import argparse
import asyncio
import logging
import os
import sqlite3
import sys
import tempfile
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.logging import configure_logging  # noqa: E402
from scripts.cleaning import CleaningReport, clean_actuals, clean_forecasts  # noqa: E402

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
LONDON = ZoneInfo("Europe/London")
CHUNK = timedelta(days=7)  # a month in one call works but WINDFOR takes ~40s; weekly is polite
MAX_CONCURRENCY = 4
# Horizon mode looks back up to 48h before each target, plus slack for publish spacing.
FORECAST_LOOKBACK = timedelta(hours=60)

log = logging.getLogger("ingest")


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def _get(client: httpx.AsyncClient, path: str, params: dict) -> list[dict]:
    res = await client.get(path, params=params)
    res.raise_for_status()
    body = res.json()
    # Stream endpoints return a bare list; non-stream ones wrap it in {"data": [...]}.
    return body if isinstance(body, list) else body.get("data", [])


async def _fetch_chunks(client: httpx.AsyncClient, path: str, params_list: list[dict]) -> list:
    sem = asyncio.Semaphore(MAX_CONCURRENCY)

    async def one(params: dict) -> list[dict]:
        async with sem:
            rows = await _get(client, path, params)
            log.info("fetched", extra={"path": path, "params": params, "rows": len(rows)})
            return rows

    chunks = await asyncio.gather(*(one(p) for p in params_list))
    return [row for chunk in chunks for row in chunk]


def _date_chunks(start: date, end: date) -> list[tuple[date, date]]:
    out, cur = [], start
    while cur <= end:
        nxt = min(cur + CHUNK - timedelta(days=1), end)
        out.append((cur, nxt))
        cur = nxt + timedelta(days=1)
    return out


def _datetime_chunks(start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    out, cur = [], start
    while cur < end:
        nxt = min(cur + CHUNK, end)
        out.append((cur, nxt))
        cur = nxt
    return out


def _iso(ts: datetime) -> str:
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def delivery_window(start: date, end: date) -> tuple[datetime, datetime]:
    """UK delivery days [start, end] -> first and last half-hour start, in UTC."""
    first = datetime.combine(start, time(0), tzinfo=LONDON).astimezone(UTC)
    after_last = datetime.combine(end + timedelta(days=1), time(0), tzinfo=LONDON)
    return first, (after_last - timedelta(minutes=30)).astimezone(UTC)


async def fetch_all(start: date, end: date) -> tuple[list[dict], list[dict]]:
    window_start, window_end = delivery_window(start, end)
    # Settlement dates are UK-local; pad a day each side and filter on startTime when cleaning.
    actual_params = [
        {"settlementDateFrom": a.isoformat(), "settlementDateTo": b.isoformat(), "fuelType": "WIND"}
        for a, b in _date_chunks(start - timedelta(days=1), end + timedelta(days=1))
    ]
    forecast_params = [
        {"publishDateTimeFrom": _iso(a), "publishDateTimeTo": _iso(b)}
        for a, b in _datetime_chunks(window_start - FORECAST_LOOKBACK, window_end)
    ]
    timeout = httpx.Timeout(90.0, connect=10.0)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=timeout) as client:
        actuals, forecasts = await asyncio.gather(
            _fetch_chunks(client, "/datasets/FUELHH/stream", actual_params),
            _fetch_chunks(client, "/datasets/WINDFOR/stream", forecast_params),
        )
    return actuals, forecasts


def _log_report(name: str, report: CleaningReport, df: pd.DataFrame) -> None:
    extra = {k: v for k, v in vars(report).items() if k != "missing_timestamps"}
    extra["missing_count"] = len(report.missing_timestamps)
    extra["missing_sample"] = report.missing_timestamps[:10]
    if not df.empty:
        extra["min_start_time"] = df["start_time"].min().isoformat()
        extra["max_start_time"] = df["start_time"].max().isoformat()
    log.info(f"cleaned {name}", extra=extra)


def write_sqlite(path: Path, actuals: pd.DataFrame, forecasts: pd.DataFrame, meta: dict) -> None:
    def iso(col: pd.Series) -> pd.Series:
        return col.dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".sqlite", dir=path.parent)
    os.close(fd)
    try:
        with sqlite3.connect(tmp) as conn:
            conn.executescript(
                """
                CREATE TABLE actuals (
                    start_time TEXT PRIMARY KEY,
                    generation_mw REAL NOT NULL,
                    publish_time TEXT NOT NULL
                );
                CREATE TABLE forecasts (
                    publish_time TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    generation_mw REAL NOT NULL,
                    PRIMARY KEY (publish_time, start_time)
                );
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                """
            )
            conn.executemany(
                "INSERT INTO actuals VALUES (?, ?, ?)",
                zip(
                    iso(actuals["start_time"]),
                    actuals["generation_mw"],
                    iso(actuals["publish_time"]),
                    strict=True,
                ),
            )
            conn.executemany(
                "INSERT INTO forecasts VALUES (?, ?, ?)",
                zip(
                    iso(forecasts["publish_time"]),
                    iso(forecasts["start_time"]),
                    forecasts["generation_mw"],
                    strict=True,
                ),
            )
            conn.executemany("INSERT INTO meta VALUES (?, ?)", meta.items())
        conn.close()
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 1, 2))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2026, 2, 1))
    parser.add_argument("--out", type=Path, default=BACKEND_DIR / "data" / "wind_jan2026.sqlite")
    args = parser.parse_args()
    configure_logging()
    logging.getLogger("httpx").setLevel(logging.WARNING)  # our "fetched" line is enough

    raw_actuals, raw_forecasts = asyncio.run(fetch_all(args.start, args.end))
    window_start, window_end = delivery_window(args.start, args.end)

    actuals, a_report = clean_actuals(raw_actuals, window_start, window_end)
    forecasts, f_report = clean_forecasts(raw_forecasts, window_start, window_end)
    _log_report("actuals", a_report, actuals)
    _log_report("forecasts", f_report, forecasts)

    meta = {
        "source": BASE_URL,
        "ingested_at": _iso(datetime.now(UTC)),
        "delivery_start": args.start.isoformat(),
        "delivery_end": args.end.isoformat(),
        "actuals_missing": str(len(a_report.missing_timestamps)),
    }
    write_sqlite(args.out, actuals, forecasts, meta)
    log.info("wrote", extra={"path": str(args.out), "bytes": args.out.stat().st_size})


if __name__ == "__main__":
    main()
