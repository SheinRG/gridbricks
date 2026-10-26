"""HTTP layer only: parse and validate params, call the service, shape the response.

Handlers are plain `def`: the work is CPU-bound pandas on in-memory data, so FastAPI runs
them in its threadpool instead of blocking the event loop (DECISIONS D8).
"""

import logging
from datetime import date, time
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from app import schemas, service
from app.config import get_settings
from app.data_store import DataStore, get_store
from app.selection import Mode

router = APIRouter()
log = logging.getLogger("app.api")

HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


def store_dep() -> DataStore:
    try:
        return get_store()
    except FileNotFoundError as exc:
        raise HTTPException(503, "Data not loaded") from exc


Store = Annotated[DataStore, Depends(store_dep)]


def _check_range(store: DataStore, start: date | None, end: date | None) -> tuple[date, date]:
    settings = get_settings()
    start = start or max(settings.default_start, store.delivery_start)
    end = end or min(settings.default_end, store.delivery_end)
    if start > end:
        raise HTTPException(422, f"start ({start}) must be on or before end ({end})")
    if start < store.delivery_start or end > store.delivery_end:
        raise HTTPException(
            422,
            f"Range must lie within available delivery days "
            f"{store.delivery_start} to {store.delivery_end}",
        )
    return start, end


def common_params(
    store: Store,
    start: Annotated[date | None, Query(description="First UK delivery day")] = None,
    end: Annotated[date | None, Query(description="Last UK delivery day (inclusive)")] = None,
    mode: Annotated[Mode, Query(description="cutoff: trading view; horizon: lead-time view")] = (
        Mode.CUTOFF
    ),
    cutoff_time: Annotated[
        str, Query(pattern=HHMM, description="UK time on D-1 (cutoff mode)")
    ] = "09:50",
    horizon_hours: Annotated[
        int, Query(ge=1, le=48, description="Hours before target (horizon mode)")
    ] = 24,
) -> service.Query:
    start, end = _check_range(store, start, end)
    if mode is Mode.CUTOFF:
        return service.Query(start, end, mode, cutoff_time=time.fromisoformat(cutoff_time))
    return service.Query(start, end, mode, horizon_hours=horizon_hours)


Params = Annotated[service.Query, Depends(common_params)]


def _echo(q: service.Query) -> schemas.ParamsEcho:
    return schemas.ParamsEcho(
        start=q.start,
        end=q.end,
        mode=q.mode,
        cutoff_time=q.cutoff_time.strftime("%H:%M") if q.cutoff_time else None,
        horizon_hours=q.horizon_hours,
    )


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> dicts with NaN/NaT as None, so missing values serialise as null."""
    return df.astype(object).where(df.notna(), None).to_dict("records")


@router.get("/health", response_model=schemas.Health)
def health() -> schemas.Health:
    try:
        store = get_store()
    except FileNotFoundError:
        log.exception("data not loaded")
        return schemas.Health(
            status="degraded",
            data_loaded=False,
            actuals_count=0,
            forecasts_count=0,
            data_range=None,
        )
    return schemas.Health(
        status="ok",
        data_loaded=True,
        actuals_count=len(store.actuals),
        forecasts_count=len(store.forecasts),
        data_range=schemas.DateRange(start=store.delivery_start, end=store.delivery_end),
    )


@router.get("/meta", response_model=schemas.Meta)
def meta(store: Store) -> schemas.Meta:
    s = get_settings()
    return schemas.Meta(
        data_range=schemas.DateRange(start=store.delivery_start, end=store.delivery_end),
        defaults=schemas.Defaults(
            start=max(s.default_start, store.delivery_start),
            end=min(s.default_end, store.delivery_end),
            mode=Mode.CUTOFF,
            cutoff_time=s.default_cutoff_time.strftime("%H:%M"),
            horizon_hours=s.default_horizon_hours,
        ),
        horizon_hours_min=s.min_horizon_hours,
        horizon_hours_max=s.max_horizon_hours,
        timezone=s.market_tz,
        ingested_at=store.meta.get("ingested_at"),
        notes=[
            "Source: Elexon BMRS FUELHH (fuelType WIND) and WINDFOR, national level.",
            "Default cutoff 09:50 UK on D-1 is the Nord Pool (N2EX) day-ahead gate closure.",
            "Forecasts are hourly, actuals half-hourly: only on-the-hour points are scored.",
            "Error = forecast - actual. Positive error means wind fell short of forecast.",
        ],
    )


@router.get("/series", response_model=schemas.SeriesResponse)
def series(q: Params) -> schemas.SeriesResponse:
    df = service.series(q)
    cols = ["start_time", "actual_mw", "forecast_mw", "publish_time", "lead_time_hours", "error_mw"]
    points = _records(df[cols].round({"lead_time_hours": 1}))
    return schemas.SeriesResponse(params=_echo(q), points=points)


@router.get("/metrics", response_model=schemas.MetricsResponse)
def metrics(q: Params) -> schemas.MetricsResponse:
    return schemas.MetricsResponse(params=_echo(q), **service.metrics_report(q))


@router.get("/accuracy-by-horizon", response_model=schemas.HorizonResponse)
def accuracy_by_horizon(
    store: Store, start: date | None = None, end: date | None = None
) -> schemas.HorizonResponse:
    start, end = _check_range(store, start, end)
    return schemas.HorizonResponse(
        params=schemas.DateRange(start=start, end=end),
        points=service.accuracy_by_horizon(start, end),
    )
