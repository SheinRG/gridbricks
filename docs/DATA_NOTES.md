# Data notes

What we learned about the two Elexon BMRS datasets, verified against live responses on 26 Oct 2026.
Base URL: `https://data.elexon.co.uk/bmrs/api/v1`. No API key needed.

## FUELHH (actual generation by fuel type)

- Endpoint: `GET /datasets/FUELHH/stream?settlementDateFrom=YYYY-MM-DD&settlementDateTo=YYYY-MM-DD&fuelType=WIND`
- Response: a bare JSON list. Fields used: `startTime`, `publishTime`, `generation`, `fuelType`.
  Also present: `settlementDate`, `settlementPeriod`.
- Resolution: 30 minutes. `startTime` is UTC (`Z` suffix). In January, settlement period 1 starts at 00:00Z
  on the settlement date, so `settlementDate`/`settlementPeriod` and `startTime` agree.
  In BST they would differ by an hour, so we filter on `startTime`, never on settlement date.
- `publishTime` is 30 minutes after `startTime` (published when the period closes).
- January 2026 range (2 Jan to 1 Feb): 1,488 rows, which is exactly 31 days x 48. No duplicates, no gaps,
  no negative values. Range 1,695 to 17,805 MW, mean 11,284 MW.
- Range limits: a whole month in one call returns in ~2s.

## WINDFOR (wind generation forecast)

- Endpoint: `GET /datasets/WINDFOR/stream?publishDateTimeFrom=ISO&publishDateTimeTo=ISO`
- Response: a bare JSON list. Fields: `publishTime`, `startTime`, `generation`.
- Resolution: **hourly** (`startTime` always on the hour). Actuals are half-hourly; see DECISIONS D3.
- Publish frequency: **8 per day** at 02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC.
  One extra off-schedule publish at 12:25 was seen in the period. The Elexon glossary still describes
  4 publishes a day; the live data does not match it, so we trust the data.
- Horizon: each publish covers from ~25h **before** `publishTime` to 21:00 on D+2, so up to ~60h ahead.
  The past part restates earlier values and is not a forecast; ingest drops rows with
  `startTime <= publishTime` (4,028 rows in our range).
- Coverage for our use case: for every delivery day 2 Jan to 1 Feb, the latest publish before
  D-1 09:50 is the 09:30 publish, and it covers all 24 hours of D (lead times 14.5h to 37.5h).
- Range limits: a whole month in one call works but takes ~40s. Ingest fetches weekly chunks
  concurrently (4 at a time) and finishes in ~5s.
- No duplicate `(publishTime, startTime)` keys observed. Range 2,292 to 21,353 MW.

## Do the two datasets describe the same wind?

WINDFOR is a forecast for Power Park Modules registered in the Balancing Mechanism (National Grid ESO
submits it). FUELHH `WIND` is metered output of the same BM-registered wind farms. Neither includes
embedded (distribution-connected) wind, so the comparison is like for like.
Sources: [Elexon glossary: Wind Generation Forecast](https://www.elexon.co.uk/bsc/glossary/wind-generation-forecast/),
[CP1381](https://www.elexon.co.uk/change-proposal/cp1381/).

## Processed store

`backend/data/wind_jan2026.sqlite` (~1.7 MB, committed). Tables:

| table | key | columns |
|---|---|---|
| `actuals` | `start_time` | `generation_mw`, `publish_time` |
| `forecasts` | `(publish_time, start_time)` | `generation_mw` |
| `meta` | `key` | `value` (source, ingest time, range) |

Timestamps are stored as ISO 8601 UTC strings. Rebuild with `python backend/scripts/ingest.py`.
