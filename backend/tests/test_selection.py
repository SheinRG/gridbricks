from datetime import time

import numpy as np
import pandas as pd
import pytest

from app.selection import Mode, build_series, cutoffs_for_targets, select_forecasts

UTC = "UTC"


def ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz=UTC)


def series(*values: str) -> pd.Series:
    return pd.Series([ts(v) for v in values]).astype("datetime64[ns, UTC]")


def fc(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """(publish_time, start_time, mw) tuples -> forecasts frame."""
    return pd.DataFrame(
        {
            "publish_time": [ts(p) for p, _, _ in rows],
            "start_time": [ts(s) for _, s, _ in rows],
            "generation_mw": [mw for _, _, mw in rows],
        }
    )


class TestCutoffs:
    def test_cutoff_mode_is_previous_day_at_cutoff_time_gmt(self):
        out = cutoffs_for_targets(
            series("2026-01-10T00:00Z", "2026-01-10T23:30Z"), Mode.CUTOFF, cutoff_time=time(9, 50)
        )
        assert list(out) == [ts("2026-01-09T09:50Z"), ts("2026-01-09T09:50Z")]

    def test_cutoff_mode_uses_uk_delivery_day_in_bst(self):
        # 23:30 UTC on 30 Jun is 00:30 BST on 1 Jul, so delivery day is 1 Jul.
        # Cutoff is 30 Jun 09:50 BST = 08:50 UTC.
        out = cutoffs_for_targets(series("2026-06-30T23:30Z"), Mode.CUTOFF, cutoff_time=time(9, 50))
        assert out.iloc[0] == ts("2026-06-30T08:50Z")

    def test_cutoff_mode_across_spring_forward(self):
        # Clocks go forward 29 Mar 2026. Delivery day 30 Mar (BST), cutoff 29 Mar 09:50 BST.
        out = cutoffs_for_targets(series("2026-03-30T12:00Z"), Mode.CUTOFF, cutoff_time=time(9, 50))
        assert out.iloc[0] == ts("2026-03-29T08:50Z")
        # Delivery day 29 Mar itself: cutoff 28 Mar 09:50 GMT.
        out = cutoffs_for_targets(series("2026-03-29T12:00Z"), Mode.CUTOFF, cutoff_time=time(9, 50))
        assert out.iloc[0] == ts("2026-03-28T09:50Z")

    def test_horizon_mode_subtracts_hours(self):
        out = cutoffs_for_targets(series("2026-01-10T12:00Z"), Mode.HORIZON, horizon_hours=6)
        assert out.iloc[0] == ts("2026-01-10T06:00Z")

    def test_missing_parameter_raises(self):
        with pytest.raises(ValueError):
            cutoffs_for_targets(series("2026-01-10T12:00Z"), Mode.CUTOFF)
        with pytest.raises(ValueError):
            cutoffs_for_targets(series("2026-01-10T12:00Z"), Mode.HORIZON)


class TestSelect:
    TARGET = "2026-01-10T12:00Z"

    def test_picks_latest_eligible_publish(self):
        forecasts = fc(
            [
                ("2026-01-09T04:30Z", self.TARGET, 100),
                ("2026-01-09T09:30Z", self.TARGET, 110),  # latest before cutoff
                ("2026-01-09T11:30Z", self.TARGET, 999),  # after cutoff: must not leak
            ]
        )
        out = select_forecasts(series(self.TARGET), series("2026-01-09T09:50Z"), forecasts)
        assert out.loc[0, "forecast_mw"] == 110
        assert out.loc[0, "publish_time"] == ts("2026-01-09T09:30Z")
        assert out.loc[0, "lead_time_hours"] == pytest.approx(26.5)

    def test_publish_exactly_at_cutoff_is_eligible(self):
        forecasts = fc([("2026-01-09T09:50Z", self.TARGET, 120)])
        out = select_forecasts(series(self.TARGET), series("2026-01-09T09:50Z"), forecasts)
        assert out.loc[0, "forecast_mw"] == 120

    def test_no_eligible_forecast_gives_null_not_dropped(self):
        forecasts = fc([("2026-01-09T11:30Z", self.TARGET, 999)])
        out = select_forecasts(series(self.TARGET), series("2026-01-09T09:50Z"), forecasts)
        assert len(out) == 1
        assert pd.isna(out.loc[0, "forecast_mw"]) and pd.isna(out.loc[0, "publish_time"])

    def test_does_not_borrow_forecast_for_a_different_target(self):
        forecasts = fc([("2026-01-09T09:30Z", "2026-01-10T13:00Z", 500)])
        out = select_forecasts(series(self.TARGET), series("2026-01-09T09:50Z"), forecasts)
        assert pd.isna(out.loc[0, "forecast_mw"])

    def test_preserves_target_order(self):
        targets = series("2026-01-10T13:00Z", "2026-01-10T12:00Z")
        cutoffs = series("2026-01-10T12:00Z", "2026-01-09T00:00Z")
        forecasts = fc(
            [
                ("2026-01-08T00:00Z", "2026-01-10T12:00Z", 1),
                ("2026-01-10T11:00Z", "2026-01-10T13:00Z", 2),
            ]
        )
        out = select_forecasts(targets, cutoffs, forecasts)
        assert list(out["start_time"]) == list(targets)
        assert list(out["forecast_mw"]) == [2, 1]

    def test_no_look_ahead_property(self):
        """Randomised check against a brute-force reference: never after cutoff, always latest."""
        rng = np.random.default_rng(42)
        base = ts("2026-01-05T00:00Z")
        for _ in range(25):
            targets = pd.Series(
                [base + pd.Timedelta(hours=int(h)) for h in rng.integers(0, 72, 30)]
            ).astype("datetime64[ns, UTC]")
            rows = []
            for t in targets.unique():
                for p_off in rng.integers(1, 80, rng.integers(0, 6)):
                    rows.append(
                        (t - pd.Timedelta(hours=int(p_off)), t, float(rng.integers(0, 20000)))
                    )
            forecasts = pd.DataFrame(rows, columns=["publish_time", "start_time", "generation_mw"])
            forecasts = forecasts.drop_duplicates(["publish_time", "start_time"])
            if forecasts.empty:
                forecasts = forecasts.astype(
                    {"publish_time": "datetime64[ns, UTC]", "start_time": "datetime64[ns, UTC]"}
                )
            mode = Mode.CUTOFF if rng.random() < 0.5 else Mode.HORIZON
            cutoffs = cutoffs_for_targets(
                targets,
                mode,
                cutoff_time=time(int(rng.integers(0, 24)), int(rng.integers(0, 60))),
                horizon_hours=int(rng.integers(1, 49)),
            )
            out = select_forecasts(targets, cutoffs, forecasts)

            for i, (t, c) in enumerate(zip(targets, cutoffs, strict=True)):
                eligible = forecasts[(forecasts.start_time == t) & (forecasts.publish_time <= c)]
                got = out.iloc[i]
                if eligible.empty:
                    assert pd.isna(got.publish_time)
                else:
                    assert got.publish_time <= c, "look-ahead leakage"
                    assert got.publish_time == eligible.publish_time.max()


class TestBuildSeries:
    def test_half_hour_grid_with_hourly_forecasts(self):
        actuals = pd.DataFrame(
            {
                "start_time": [ts("2026-01-10T00:00Z"), ts("2026-01-10T00:30Z")],
                "generation_mw": [1000.0, 1100.0],
            }
        )
        forecasts = fc([("2026-01-09T09:30Z", "2026-01-10T00:00Z", 1200)])
        out = build_series(
            actuals,
            forecasts,
            ts("2026-01-10T00:00Z"),
            ts("2026-01-10T01:00Z"),
            Mode.CUTOFF,
            cutoff_time=time(9, 50),
        )
        assert len(out) == 3  # 00:00, 00:30, 01:00
        assert out.loc[0, "error_mw"] == 200  # forecast 1200 - actual 1000: over-forecast
        assert pd.isna(out.loc[1, "error_mw"])  # :30 has no forecast; not interpolated
        assert pd.isna(out.loc[2, "actual_mw"])  # missing actual stays missing
