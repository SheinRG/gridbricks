"""Which forecast did the trading team have? (DECISIONS D2, D3)

Both modes reduce to one rule: every target half-hour gets a cutoff timestamp, and we take the
forecast for that target with the latest publish_time <= cutoff. Only the cutoff differs:

- cutoff mode:  D-1 at `cutoff_time` (Europe/London), where D is the target's UK delivery day
- horizon mode: target - H hours

Keeping one selection path means the no-look-ahead guarantee lives (and is tested) in one place.
"""

from datetime import time
from enum import StrEnum

import pandas as pd

DTYPE = "datetime64[ns, UTC]"


class Mode(StrEnum):
    CUTOFF = "cutoff"
    HORIZON = "horizon"


def cutoffs_for_targets(
    targets: pd.Series,
    mode: Mode,
    *,
    cutoff_time: time | None = None,
    horizon_hours: int | None = None,
    tz: str = "Europe/London",
) -> pd.Series:
    """Cutoff timestamp (UTC) for each target startTime (UTC)."""
    if mode is Mode.HORIZON:
        if horizon_hours is None:
            raise ValueError("horizon mode needs horizon_hours")
        return targets - pd.Timedelta(hours=horizon_hours)

    if cutoff_time is None:
        raise ValueError("cutoff mode needs cutoff_time")
    # Work in local wall-clock time so "D-1 at 09:50" stays 09:50 across DST changes,
    # then localise. Adding 24h to an aware timestamp would drift by an hour on DST days.
    local_day = targets.dt.tz_convert(tz).dt.tz_localize(None).dt.normalize()
    wall = (
        local_day
        - pd.Timedelta(days=1)
        + pd.Timedelta(hours=cutoff_time.hour, minutes=cutoff_time.minute)
    )
    return (
        wall.dt.tz_localize(tz, ambiguous=False, nonexistent="shift_forward")
        .dt.tz_convert("UTC")
        .astype(DTYPE)
    )


def select_forecasts(
    targets: pd.Series, cutoffs: pd.Series, forecasts: pd.DataFrame
) -> pd.DataFrame:
    """For each target, the latest forecast published at or before its cutoff.

    Returns one row per target, in target order: start_time, cutoff, forecast_mw,
    publish_time, lead_time_hours. Targets with no eligible forecast keep NaN/NaT rather
    than being dropped, so gaps stay visible downstream.
    """
    left = pd.DataFrame(
        {
            "start_time": targets.astype(DTYPE).reset_index(drop=True),
            "cutoff": cutoffs.astype(DTYPE).reset_index(drop=True),
        }
    )
    left["_order"] = range(len(left))
    right = forecasts[["start_time", "publish_time", "generation_mw"]].astype(
        {"start_time": DTYPE, "publish_time": DTYPE}
    )

    merged = pd.merge_asof(
        left.sort_values("cutoff"),
        right.sort_values("publish_time"),
        left_on="cutoff",
        right_on="publish_time",
        by="start_time",
        direction="backward",  # latest publish_time <= cutoff
        allow_exact_matches=True,
    )
    merged = merged.sort_values("_order").drop(columns="_order").reset_index(drop=True)
    merged = merged.rename(columns={"generation_mw": "forecast_mw"})
    merged["lead_time_hours"] = (
        merged["start_time"] - merged["publish_time"]
    ).dt.total_seconds() / 3600
    return merged[["start_time", "cutoff", "forecast_mw", "publish_time", "lead_time_hours"]]


def build_series(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
    mode: Mode,
    *,
    cutoff_time: time | None = None,
    horizon_hours: int | None = None,
    tz: str = "Europe/London",
) -> pd.DataFrame:
    """Half-hourly grid over the window with actual, selected forecast and error.

    The grid is complete, so missing actuals show up as NaN rather than vanishing.
    Forecasts are hourly, so :30 rows never have a forecast; error is only defined where
    both values exist (an inner join in effect, D3).
    """
    grid = pd.Series(pd.date_range(window_start, window_end, freq="30min").astype(DTYPE))
    cutoffs = cutoffs_for_targets(
        grid, mode, cutoff_time=cutoff_time, horizon_hours=horizon_hours, tz=tz
    )
    selected = select_forecasts(grid, cutoffs, forecasts)

    actual = actuals[["start_time", "generation_mw"]].astype({"start_time": DTYPE})
    out = selected.merge(
        actual.rename(columns={"generation_mw": "actual_mw"}), on="start_time", how="left"
    )
    out["error_mw"] = out["forecast_mw"] - out["actual_mw"]
    return out
