from datetime import UTC, date, datetime

from scripts.cleaning import clean_actuals, clean_forecasts

WIN_START = datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
WIN_END = datetime(2026, 1, 2, 1, 30, tzinfo=UTC)  # 4 half-hours


def fuel(start: str, gen, publish: str | None = None, fuel_type: str = "WIND") -> dict:
    return {
        "startTime": start,
        "publishTime": publish or start,
        "generation": gen,
        "fuelType": fuel_type,
    }


def wf(publish: str, start: str, gen) -> dict:
    return {"publishTime": publish, "startTime": start, "generation": gen}


class TestCleanActuals:
    def test_keeps_latest_revision_per_start_time(self):
        records = [
            fuel("2026-01-02T00:00:00Z", 100, "2026-01-02T00:30:00Z"),
            fuel("2026-01-02T00:00:00Z", 120, "2026-01-02T01:00:00Z"),  # later revision
            fuel("2026-01-02T00:00:00Z", 90, "2026-01-02T00:15:00Z"),
        ]
        df, report = clean_actuals(records, WIN_START, WIN_END)
        assert df["generation_mw"].tolist() == [120]
        assert report.duplicates_removed == 2

    def test_filters_non_wind_nulls_and_out_of_window(self):
        records = [
            fuel("2026-01-02T00:00:00Z", 100),
            fuel("2026-01-02T00:30:00Z", 5000, fuel_type="CCGT"),
            fuel("2026-01-02T01:00:00Z", None),
            fuel("2026-01-01T23:30:00Z", 80),  # before window
        ]
        df, report = clean_actuals(records, WIN_START, WIN_END)
        assert len(df) == 1
        assert report.dropped_other_fuel == 1
        assert report.dropped_null == 1
        assert report.dropped_out_of_window == 1

    def test_reports_gaps_without_filling(self):
        records = [fuel("2026-01-02T00:00:00Z", 100), fuel("2026-01-02T01:30:00Z", 110)]
        df, report = clean_actuals(records, WIN_START, WIN_END)
        assert len(df) == 2  # no zero-filled rows
        assert report.missing_timestamps == [
            "2026-01-02T00:30:00+00:00",
            "2026-01-02T01:00:00+00:00",
        ]

    def test_timestamps_are_utc_aware(self):
        df, _ = clean_actuals([fuel("2026-01-02T00:00:00Z", 1)], WIN_START, WIN_END)
        assert str(df["start_time"].dt.tz) == "UTC"

    def test_empty_input(self):
        df, report = clean_actuals([], WIN_START, WIN_END)
        assert df.empty and report.rows_out == 0


class TestCleanForecasts:
    def test_drops_rows_at_or_before_publish_time(self):
        records = [
            wf("2026-01-02T00:30:00Z", "2026-01-02T00:00:00Z", 1),  # restated past value
            wf("2026-01-02T00:30:00Z", "2026-01-02T00:30:00Z", 2),  # zero lead time
            wf("2026-01-02T00:30:00Z", "2026-01-02T01:00:00Z", 3),
        ]
        df, report = clean_forecasts(records, WIN_START, WIN_END)
        assert df["generation_mw"].tolist() == [3]
        assert report.dropped_not_a_forecast == 2

    def test_duplicate_keys_resolve_independent_of_input_order(self):
        a = wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z", 100)
        b = wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z", 105)
        df1, r1 = clean_forecasts([a, b], WIN_START, WIN_END)
        df2, _ = clean_forecasts([b, a], WIN_START, WIN_END)
        assert df1.equals(df2)
        assert r1.duplicates_removed == 1

    def test_keeps_every_publish_for_the_same_target(self):
        records = [
            wf("2026-01-01T07:30:00Z", "2026-01-02T00:00:00Z", 100),
            wf("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z", 110),
        ]
        df, _ = clean_forecasts(records, WIN_START, WIN_END)
        assert len(df) == 2

    def test_filters_targets_outside_window(self):
        records = [wf("2026-01-01T09:30:00Z", "2026-01-03T00:00:00Z", 100)]
        df, report = clean_forecasts(records, WIN_START, WIN_END)
        assert df.empty and report.dropped_out_of_window == 1


class TestDeliveryWindow:
    def test_gmt_day_maps_to_same_utc_day(self):
        from scripts.ingest import delivery_window

        first, last = delivery_window(date(2026, 1, 2), date(2026, 1, 2))
        assert first == datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
        assert last == datetime(2026, 1, 2, 23, 30, tzinfo=UTC)

    def test_bst_day_starts_at_23_utc_previous_day(self):
        from scripts.ingest import delivery_window

        first, last = delivery_window(date(2026, 7, 1), date(2026, 7, 1))
        assert first == datetime(2026, 6, 30, 23, 0, tzinfo=UTC)
        assert last == datetime(2026, 7, 1, 22, 30, tzinfo=UTC)
