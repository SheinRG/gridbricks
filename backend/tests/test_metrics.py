import math

import numpy as np
import pandas as pd
import pytest

from app import metrics


def frame(errors: list[float | None], actual: float = 1000.0, start="2026-01-10T00:00Z"):
    """Series frame with hourly start times and a constant actual; forecast = actual + error."""
    n = len(errors)
    err = pd.Series(errors, dtype=float)
    return pd.DataFrame(
        {
            "start_time": pd.date_range(start, periods=n, freq="1h", tz="UTC"),
            "actual_mw": [actual] * n,
            "forecast_mw": actual + err,
            "error_mw": err,
            "publish_time": pd.Series(
                [pd.Timestamp("2026-01-09T09:30Z")] * n, dtype="datetime64[ns, UTC]"
            ),
            "lead_time_hours": np.linspace(14.5, 14.5 + n - 1, n),
        }
    )


class TestErrorStats:
    def test_hand_computed_values(self):
        # errors: -100, 0, 100, 200 -> MAE 100, bias 50, RMSE sqrt((1e4+0+1e4+4e4)/4)=sqrt(15000)
        s = metrics.error_stats(pd.Series([-100.0, 0.0, 100.0, 200.0]))
        assert s["n"] == 4
        assert s["mae_mw"] == 100.0
        assert s["bias_mw"] == 50.0
        assert s["rmse_mw"] == pytest.approx(math.sqrt(15000), abs=0.05)
        # numpy linear percentile: position 0.9*3 = 2.7 -> 100 + 0.7*100 = 170
        assert s["p90_mw"] == 170.0

    def test_empty_gives_nulls_not_zeros(self):
        s = metrics.error_stats(pd.Series([], dtype=float))
        assert s == {"n": 0, "mae_mw": None, "rmse_mw": None, "bias_mw": None, "p90_mw": None}

    def test_all_null_is_same_as_empty(self):
        assert metrics.error_stats(pd.Series([np.nan, np.nan]))["n"] == 0


class TestSummary:
    def test_headline_numbers(self):
        out = metrics.summary(frame([-100, 0, 100, 200]), expected=8)
        assert out["n"] == 4
        assert out["coverage_pct"] == 50.0
        assert out["shortfall_buffer_mw"] == 170.0
        assert out["nmae_pct"] == 10.0  # MAE 100 / mean actual 1000
        assert out["max_over_forecast"]["error_mw"] == 200.0
        assert out["max_under_forecast"]["error_mw"] == -100.0

    def test_buffer_is_zero_when_forecasts_always_too_low(self):
        out = metrics.summary(frame([-300, -200, -100]), expected=3)
        assert out["shortfall_buffer_mw"] == 0.0
        assert out["max_over_forecast"] is None

    def test_null_rows_are_excluded_and_counted(self):
        out = metrics.summary(frame([100, None, None, 100]), expected=4)
        assert out["n"] == 2
        assert out["coverage_pct"] == 50.0

    def test_empty_input(self):
        out = metrics.summary(frame([]), expected=0)
        assert out["n"] == 0
        assert out["mae_mw"] is None and out["coverage_pct"] is None
        assert out["shortfall_buffer_mw"] is None


class TestBreakdowns:
    def test_by_hour_returns_all_24_hours_in_uk_time(self):
        rows = metrics.by_hour(frame([10, 20, 30]))  # 00:00 to 02:00 UTC = GMT
        assert [r["hour"] for r in rows] == list(range(24))
        assert rows[0]["mae_mw"] == 10.0 and rows[0]["n"] == 1
        assert rows[5]["n"] == 0 and rows[5]["mae_mw"] is None

    def test_by_hour_converts_to_bst(self):
        rows = metrics.by_hour(frame([10], start="2026-07-01T12:00Z"))
        assert rows[13]["n"] == 1  # 12:00 UTC = 13:00 BST

    def test_by_lead_bucket(self):
        rows = metrics.by_lead_bucket(frame([10] * 12))  # leads 14.5 .. 25.5
        assert [r["label"] for r in rows] == ["12-18h", "18-24h", "24-30h"]
        assert sum(r["n"] for r in rows) == 12

    def test_by_day_keeps_days_without_scored_points(self):
        f = frame([10] * 30)  # 30 hours from 10 Jan 00:00 -> spills into 11 Jan
        f.loc[f["start_time"].dt.day == 11, "forecast_mw"] = np.nan
        rows = metrics.by_day(f)
        assert [str(r["date"]) for r in rows] == ["2026-01-10", "2026-01-11"]
        assert rows[1]["n"] == 0

    def test_worst_misses_sorted_by_absolute_error(self):
        rows = metrics.worst_misses(frame([5, -50, 20, None]), k=2)
        assert [r["error_mw"] for r in rows] == [-50.0, 20.0]
