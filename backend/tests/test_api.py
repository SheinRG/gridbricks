"""API tests against the committed January 2026 data file (local, deterministic, no network)."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def test_health(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok" and body["data_loaded"] is True
    assert body["actuals_count"] == 1488
    assert body["data_range"] == {"start": "2026-01-02", "end": "2026-02-01"}
    assert "X-Response-Time" in res.headers and "X-Request-ID" in res.headers
    assert "Cache-Control" not in res.headers


def test_meta_defaults(client):
    body = client.get("/api/v1/meta").json()
    assert body["defaults"]["cutoff_time"] == "09:50"
    assert body["defaults"]["mode"] == "cutoff"
    assert body["timezone"] == "Europe/London"


class TestSeries:
    def test_default_range_is_31_days_of_half_hours(self, client):
        res = client.get("/api/v1/series")
        assert res.status_code == 200
        assert res.headers["Cache-Control"].startswith("public")
        body = res.json()
        assert len(body["points"]) == 31 * 48
        assert body["params"] == {
            "start": "2026-01-02",
            "end": "2026-02-01",
            "mode": "cutoff",
            "cutoff_time": "09:50",
            "horizon_hours": None,
        }

    def test_points_never_use_a_forecast_published_after_the_cutoff(self, client):
        body = client.get("/api/v1/series?start=2026-01-10&end=2026-01-10&cutoff_time=09:50").json()
        for p in body["points"]:
            if p["publish_time"]:
                assert datetime.fromisoformat(p["publish_time"]) <= datetime.fromisoformat(
                    "2026-01-09T09:50:00+00:00"
                )

    def test_half_hour_points_have_null_forecast_not_zero(self, client):
        body = client.get("/api/v1/series?start=2026-01-10&end=2026-01-10").json()
        half = [p for p in body["points"] if p["start_time"].endswith(":30:00Z")]
        assert half and all(p["forecast_mw"] is None and p["error_mw"] is None for p in half)
        assert all(p["actual_mw"] is not None for p in half)

    def test_horizon_mode_echoes_horizon_not_cutoff(self, client):
        body = client.get(
            "/api/v1/series?mode=horizon&horizon_hours=6&start=2026-01-10&end=2026-01-10"
        ).json()
        assert body["params"]["horizon_hours"] == 6
        assert body["params"]["cutoff_time"] is None
        leads = [p["lead_time_hours"] for p in body["points"] if p["lead_time_hours"] is not None]
        assert min(leads) >= 6


class TestMetrics:
    def test_shape_and_headline(self, client):
        body = client.get("/api/v1/metrics").json()
        s = body["summary"]
        assert s["n"] == s["expected"] == 744
        assert s["coverage_pct"] == 100.0
        assert s["shortfall_buffer_mw"] > 0
        assert len(body["by_hour"]) == 24
        assert len(body["by_day"]) == 31
        assert len(body["worst_misses"]) == 10

    def test_earlier_cutoff_changes_result(self, client):
        a = client.get("/api/v1/metrics?cutoff_time=09:50").json()["summary"]["mae_mw"]
        b = client.get("/api/v1/metrics?cutoff_time=09:20").json()["summary"]["mae_mw"]
        assert a != b


def test_accuracy_by_horizon(client):
    body = client.get("/api/v1/accuracy-by-horizon").json()
    assert [p["horizon_hours"] for p in body["points"]] == list(range(1, 49))
    assert body["points"][0]["mae_mw"] < body["points"][-1]["mae_mw"]


@pytest.mark.parametrize(
    ("query", "fragment"),
    [
        ("start=2026-01-20&end=2026-01-10", "must be on or before"),
        ("start=2025-12-01", "within available"),
        ("end=2026-03-01", "within available"),
        ("cutoff_time=25:00", "pattern"),
        ("cutoff_time=9:50", "pattern"),
        ("mode=horizon&horizon_hours=0", "greater than or equal"),
        ("mode=horizon&horizon_hours=49", "less than or equal"),
        ("mode=sideways", "cutoff"),
        ("start=not-a-date", "date"),
    ],
)
def test_invalid_params_return_422(client, query, fragment):
    res = client.get(f"/api/v1/metrics?{query}")
    assert res.status_code == 422
    assert fragment in res.text
