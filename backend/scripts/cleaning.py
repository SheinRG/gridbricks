"""Pure cleaning functions for raw Elexon records. No I/O, so they are unit tested directly."""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

HALF_HOUR = pd.Timedelta(minutes=30)


@dataclass
class CleaningReport:
    rows_in: int = 0
    rows_out: int = 0
    dropped_null: int = 0
    dropped_other_fuel: int = 0
    dropped_out_of_window: int = 0
    dropped_not_a_forecast: int = 0
    duplicates_removed: int = 0
    missing_timestamps: list[str] = field(default_factory=list)


def _to_utc(series: pd.Series) -> pd.Series:
    # Pin resolution: pandas 3 infers it per input, and merge_asof needs identical key dtypes.
    return pd.to_datetime(series, utc=True).astype("datetime64[ns, UTC]")


def clean_actuals(
    records: list[dict], window_start: datetime, window_end: datetime
) -> tuple[pd.DataFrame, CleaningReport]:
    """FUELHH -> one WIND row per half-hour in [window_start, window_end].

    Revisions of the same startTime are resolved by keeping the latest publishTime (D6).
    Missing half-hours are reported, never filled.
    """
    report = CleaningReport(rows_in=len(records))
    cols = ["start_time", "generation_mw", "publish_time"]
    if not records:
        return pd.DataFrame(columns=cols), report

    df = pd.DataFrame.from_records(records)
    is_wind = df["fuelType"] == "WIND"
    report.dropped_other_fuel = int((~is_wind).sum())
    df = df[is_wind]

    df = pd.DataFrame(
        {
            "start_time": _to_utc(df["startTime"]),
            "generation_mw": pd.to_numeric(df["generation"], errors="coerce"),
            "publish_time": _to_utc(df["publishTime"]),
        }
    )
    null = df["generation_mw"].isna()
    report.dropped_null = int(null.sum())
    df = df[~null]

    in_window = df["start_time"].between(window_start, window_end)
    report.dropped_out_of_window = int((~in_window).sum())
    df = df[in_window]

    before = len(df)
    df = df.sort_values(["start_time", "publish_time"]).drop_duplicates("start_time", keep="last")
    report.duplicates_removed = before - len(df)

    expected = pd.date_range(window_start, window_end, freq=HALF_HOUR)
    missing = expected.difference(pd.DatetimeIndex(df["start_time"]))
    report.missing_timestamps = [ts.isoformat() for ts in missing]

    df = df.reset_index(drop=True)
    report.rows_out = len(df)
    return df, report


def clean_forecasts(
    records: list[dict], target_start: datetime, target_end: datetime
) -> tuple[pd.DataFrame, CleaningReport]:
    """WINDFOR -> one row per (publish_time, start_time) targeting [target_start, target_end].

    Rows whose startTime is not after publishTime are dropped: each publish also restates
    ~25h of past values, which are not forecasts and could never be selected anyway.
    Duplicate keys (none observed) resolve deterministically: highest value wins after a
    stable sort, independent of API response order.
    """
    report = CleaningReport(rows_in=len(records))
    cols = ["publish_time", "start_time", "generation_mw"]
    if not records:
        return pd.DataFrame(columns=cols), report

    raw = pd.DataFrame.from_records(records)
    df = pd.DataFrame(
        {
            "publish_time": _to_utc(raw["publishTime"]),
            "start_time": _to_utc(raw["startTime"]),
            "generation_mw": pd.to_numeric(raw["generation"], errors="coerce"),
        }
    )
    null = df["generation_mw"].isna()
    report.dropped_null = int(null.sum())
    df = df[~null]

    not_forecast = df["start_time"] <= df["publish_time"]
    report.dropped_not_a_forecast = int(not_forecast.sum())
    df = df[~not_forecast]

    in_window = df["start_time"].between(target_start, target_end)
    report.dropped_out_of_window = int((~in_window).sum())
    df = df[in_window]

    key = ["publish_time", "start_time"]
    before = len(df)
    df = df.sort_values([*key, "generation_mw"], kind="stable").drop_duplicates(key, keep="last")
    report.duplicates_removed = before - len(df)

    df = df.reset_index(drop=True)
    report.rows_out = len(df)
    return df, report
