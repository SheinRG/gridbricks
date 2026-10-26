"""Composes the data store, selection and metrics. Results are cached per parameter set.

The data is immutable, so a cache entry never goes stale. Cached frames are shared:
callers must treat them as read-only.
"""

from dataclasses import dataclass
from datetime import date, time
from functools import lru_cache

import pandas as pd

from app import metrics
from app.config import get_settings
from app.data_store import get_store
from app.selection import Mode, build_series, delivery_window


@dataclass(frozen=True)
class Query:
    """Validated, hashable request parameters (the lru_cache key)."""

    start: date
    end: date
    mode: Mode
    cutoff_time: time | None = None
    horizon_hours: int | None = None


@lru_cache(maxsize=256)
def series(q: Query) -> pd.DataFrame:
    store = get_store()
    window_start, window_end = delivery_window(q.start, q.end, get_settings().market_tz)
    return build_series(
        store.actuals,
        store.forecasts,
        window_start,
        window_end,
        q.mode,
        cutoff_time=q.cutoff_time,
        horizon_hours=q.horizon_hours,
        tz=get_settings().market_tz,
    )


def expected_points(s: pd.DataFrame) -> int:
    """Forecasts are hourly, so only on-the-hour targets can be scored (D3)."""
    return int((s["start_time"].dt.minute == 0).sum())


@lru_cache(maxsize=256)
def metrics_report(q: Query) -> dict:
    s = series(q)
    tz = get_settings().market_tz
    return {
        "summary": metrics.summary(s, expected=expected_points(s)),
        "by_hour": metrics.by_hour(s, tz),
        "by_lead_bucket": metrics.by_lead_bucket(s),
        "by_day": metrics.by_day(s, tz),
        "worst_misses": metrics.worst_misses(s, k=10),
    }


@lru_cache(maxsize=32)
def accuracy_by_horizon(start: date, end: date) -> list[dict]:
    settings = get_settings()
    out = []
    for h in range(settings.min_horizon_hours, settings.max_horizon_hours + 1):
        s = series(Query(start=start, end=end, mode=Mode.HORIZON, horizon_hours=h))
        rows = metrics.scored(s)
        expected = expected_points(s)
        out.append(
            {
                "horizon_hours": h,
                **metrics.error_stats(rows["error_mw"]),
                "coverage_pct": round(100 * len(rows) / expected, 1) if expected else None,
                # Publishes are ~3h apart, so the real lead is H plus up to a few hours.
                "mean_lead_hours": round(float(rows["lead_time_hours"].mean()), 1)
                if len(rows)
                else None,
            }
        )
    return out
