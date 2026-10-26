"""Response models. All times are UTC ISO 8601; all power values are MW, rounded to 0.1."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.selection import Mode


class DateRange(BaseModel):
    start: date
    end: date


class Health(BaseModel):
    status: str
    data_loaded: bool
    actuals_count: int
    forecasts_count: int
    data_range: DateRange | None


class Defaults(BaseModel):
    start: date
    end: date
    mode: Mode
    cutoff_time: str = Field(examples=["09:50"])
    horizon_hours: int


class Meta(BaseModel):
    data_range: DateRange = Field(description="Delivery days available (UK dates)")
    defaults: Defaults
    horizon_hours_min: int
    horizon_hours_max: int
    timezone: str
    ingested_at: str | None
    notes: list[str]


class ParamsEcho(BaseModel):
    start: date
    end: date
    mode: Mode
    cutoff_time: str | None
    horizon_hours: int | None


class SeriesPoint(BaseModel):
    start_time: datetime
    actual_mw: float | None
    forecast_mw: float | None
    publish_time: datetime | None = Field(description="When the selected forecast was published")
    lead_time_hours: float | None = Field(description="start_time - publish_time")
    error_mw: float | None = Field(description="forecast - actual; positive = shortfall risk")


class SeriesResponse(BaseModel):
    params: ParamsEcho
    points: list[SeriesPoint]


class ErrorStats(BaseModel):
    n: int
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    p90_mw: float | None


class Extreme(BaseModel):
    start_time: datetime
    error_mw: float
    forecast_mw: float
    actual_mw: float


class Summary(ErrorStats):
    expected: int = Field(description="Points that could have been scored (hourly targets)")
    coverage_pct: float | None
    p10_mw: float | None
    p50_mw: float | None
    shortfall_buffer_mw: float | None = Field(
        description="Extra MW above forecast that covered the shortfall in 90% of hours"
    )
    mean_actual_mw: float | None
    nmae_pct: float | None = Field(description="MAE as % of mean actual generation")
    max_over_forecast: Extreme | None
    max_under_forecast: Extreme | None


class HourStats(ErrorStats):
    hour: int = Field(description="Hour of day, UK local time")


class LeadBucketStats(ErrorStats):
    label: str
    lead_min_h: int
    lead_max_h: int


class DayStats(ErrorStats):
    date: date


class Miss(BaseModel):
    start_time: datetime
    actual_mw: float
    forecast_mw: float
    error_mw: float
    publish_time: datetime
    lead_time_hours: float


class MetricsResponse(BaseModel):
    params: ParamsEcho
    summary: Summary
    by_hour: list[HourStats]
    by_lead_bucket: list[LeadBucketStats]
    by_day: list[DayStats]
    worst_misses: list[Miss]


class HorizonPoint(ErrorStats):
    horizon_hours: int
    coverage_pct: float | None
    mean_lead_hours: float | None


class HorizonResponse(BaseModel):
    params: DateRange
    points: list[HorizonPoint]
