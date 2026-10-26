"""Forecast error metrics (DECISIONS D4, D5). Pure functions over the frame from build_series.

error_mw = forecast_mw - actual_mw. Positive = over-forecast = shortfall risk.
Only rows with both forecast and actual are scored. Every result carries n.
"""

import math

import numpy as np
import pandas as pd

# Lead-time buckets in hours, [lo, hi), 6h wide. Cutoff mode lands in 12 to 42h.
LEAD_BUCKETS: list[tuple[int, int]] = [(lo, lo + 6) for lo in range(0, 48, 6)] + [(48, 72)]


def _r(x: float | None) -> float | None:
    """Round for JSON; NaN becomes None so it serialises as null."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    return round(float(x), 1)


def scored(series: pd.DataFrame) -> pd.DataFrame:
    """Rows where both forecast and actual exist."""
    return series.dropna(subset=["forecast_mw", "actual_mw"])


def error_stats(errors: pd.Series) -> dict:
    """Core stats for a set of errors. Empty input gives n=0 and nulls, not zeros."""
    e = errors.dropna().to_numpy(dtype=float)
    if e.size == 0:
        return {"n": 0, "mae_mw": None, "rmse_mw": None, "bias_mw": None, "p90_mw": None}
    return {
        "n": int(e.size),
        "mae_mw": _r(np.mean(np.abs(e))),
        "rmse_mw": _r(np.sqrt(np.mean(e**2))),
        "bias_mw": _r(np.mean(e)),
        "p90_mw": _r(np.percentile(e, 90)),
    }


def _extreme(rows: pd.DataFrame, idx) -> dict:
    row = rows.loc[idx]
    return {
        "start_time": row["start_time"],
        "error_mw": _r(row["error_mw"]),
        "forecast_mw": _r(row["forecast_mw"]),
        "actual_mw": _r(row["actual_mw"]),
    }


def summary(series: pd.DataFrame, expected: int) -> dict:
    """Headline metrics. `expected` is how many points could have been scored (for coverage)."""
    rows = scored(series)
    stats = error_stats(rows["error_mw"])
    out = {
        **stats,
        "expected": expected,
        "coverage_pct": _r(100 * stats["n"] / expected) if expected else None,
        "p10_mw": None,
        "p50_mw": None,
        "shortfall_buffer_mw": None,
        "mean_actual_mw": None,
        "nmae_pct": None,
        "max_over_forecast": None,
        "max_under_forecast": None,
    }
    if rows.empty:
        return out

    e = rows["error_mw"].to_numpy(dtype=float)
    mean_actual = float(rows["actual_mw"].mean())
    p10, p50 = np.percentile(e, [10, 50])
    over, under = rows["error_mw"].idxmax(), rows["error_mw"].idxmin()
    out.update(
        {
            "p10_mw": _r(p10),
            "p50_mw": _r(p50),
            # P90 of all errors: buying this much above forecast covers 90% of hours (D5).
            "shortfall_buffer_mw": _r(max(stats["p90_mw"], 0.0)),
            "mean_actual_mw": _r(mean_actual),
            "nmae_pct": _r(100 * stats["mae_mw"] / mean_actual) if mean_actual > 0 else None,
            "max_over_forecast": _extreme(rows, over) if rows.loc[over, "error_mw"] > 0 else None,
            "max_under_forecast": _extreme(rows, under)
            if rows.loc[under, "error_mw"] < 0
            else None,
        }
    )
    return out


def by_hour(series: pd.DataFrame, tz: str = "Europe/London") -> list[dict]:
    """Stats per UK hour of day, 0 to 23. Hours with no data are returned with n=0."""
    rows = scored(series)
    hours = rows["start_time"].dt.tz_convert(tz).dt.hour
    groups = dict(tuple(rows.groupby(hours)["error_mw"]))
    return [{"hour": h, **error_stats(groups.get(h, pd.Series(dtype=float)))} for h in range(24)]


def by_lead_bucket(series: pd.DataFrame) -> list[dict]:
    """Stats per lead-time bucket. Empty buckets are omitted (they depend on mode)."""
    rows = scored(series)
    out = []
    for lo, hi in LEAD_BUCKETS:
        mask = (rows["lead_time_hours"] >= lo) & (rows["lead_time_hours"] < hi)
        if mask.any():
            out.append(
                {
                    "label": f"{lo}-{hi}h",
                    "lead_min_h": lo,
                    "lead_max_h": hi,
                    **error_stats(rows.loc[mask, "error_mw"]),
                }
            )
    return out


def by_day(series: pd.DataFrame, tz: str = "Europe/London") -> list[dict]:
    """Stats per UK delivery day, including days with no scored points (n=0)."""
    days = series["start_time"].dt.tz_convert(tz).dt.date
    rows = scored(series)
    groups = dict(tuple(rows.groupby(days.loc[rows.index])["error_mw"]))
    return [
        {"date": d, **error_stats(groups.get(d, pd.Series(dtype=float)))}
        for d in sorted(days.unique())
    ]


def worst_misses(series: pd.DataFrame, k: int = 10) -> list[dict]:
    """Top k scored points by absolute error."""
    rows = scored(series)
    top = rows.loc[rows["error_mw"].abs().nlargest(k).index]
    return [
        {
            "start_time": r.start_time,
            "actual_mw": _r(r.actual_mw),
            "forecast_mw": _r(r.forecast_mw),
            "error_mw": _r(r.error_mw),
            "publish_time": r.publish_time,
            "lead_time_hours": _r(r.lead_time_hours),
        }
        for r in top.itertuples()
    ]
