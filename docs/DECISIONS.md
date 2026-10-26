# Decisions

Each entry records an ambiguity in the brief, what we chose, and why.

## D1. Which delivery days are in scope

The brief says "purchase decisions made in January 2026". Day-ahead decisions are made on D-1 for
delivery day D, so decisions on 1 to 31 January cover **delivery days 2 January to 1 February 2026**.
The range is configurable in the API and UI, but defaults to this.

## D2. What "latest forecast available at decision time" means

The GB day-ahead auction on Nord Pool (N2EX) closes at **09:50 UK time on D-1**
([Nord Pool](https://support.nordpoolgroup.com/support/solutions/articles/8000088463-about-the-day-ahead-gb-auction)).
For each half-hour in D we select the forecast with the latest `publishTime` at or before that moment.
The cutoff time is a parameter because the EPEX GB auction closes earlier, at 09:20. That matters:
at 09:50 the team gets the 09:30 publish; at 09:20 they only have the 07:30 one.

A second **horizon** mode answers an analyst question instead: "how good is a forecast made H hours
ahead?" There the cutoff for target `t` is `t - H`.

Both modes are the same operation: give each target timestamp a cutoff and pick the latest forecast
published at or before it. One function (`selection.py`) implements both, so the no-look-ahead
guarantee is enforced and tested in one place. Every returned point carries its `publish_time`
and `lead_time_hours` so the choice is visible.

Times are handled as timezone-aware UTC internally and converted with `Europe/London` for business
rules. January is GMT, so UK time equals UTC, but the code does not rely on that (tested with a BST date).

## D3. Resolution mismatch

Forecasts are hourly; actuals are half-hourly. We evaluate error only where both exist, which means
on-the-hour actuals (an inner join on `startTime`). We do not interpolate forecasts, because that
invents values the trading team never saw. The alternative, averaging the two half-hours into an
hourly actual, would smooth away the very swings that cause shortfalls. Half of the actuals
(the :30 periods) are shown on the chart but not scored; the API reports `n` so this is visible.

## D4. Error sign convention

`error_mw = forecast_mw - actual_mw`. Positive error means wind came in **below** forecast, so the
utility bought too little and must cover the shortfall at short notice, which is the expensive
direction. The UI calls this "shortfall risk". Negative error means over-procurement.

## D5. Metrics

MAE, RMSE, mean bias, P10/P50/P90 of error, max over- and under-forecast with timestamps, and MAE as
a percentage of mean actual generation. The headline number is the **shortfall buffer**: the P90 of
error, phrased as "procure about X MW above the forecast to cover wind shortfall in 90% of hours".
It is the P90 of **all** errors, not of positive errors only: the latter answers a different
question ("how big is a shortfall when one happens") and would overstate the buffer needed.
If the P90 is negative, no buffer was needed at that confidence and we show zero.

We do **not** use MAPE. Wind output can approach zero, where percentage error explodes and
dominates the average. We have no capacity data (the brief limits us to two datasets), so we
normalise by mean actual generation instead and label it clearly.

Every metric is returned with `n` and coverage, so a number from three data points cannot be
mistaken for a number from three hundred.

## D6. Data quality

- FUELHH revisions: keep the row with the latest `publishTime` per `startTime`.
- WINDFOR: drop rows with `startTime <= publishTime` (restated history, not forecasts). Duplicate
  keys (none observed) resolve deterministically regardless of API order.
- Missing values stay missing: the API returns `null`, charts show gaps. Nothing is zero-filled.
- Ingest logs counts of rows dropped, duplicates removed and missing timestamps.

## D7. Data strategy

January 2026 is historical and does not change, so the API never calls Elexon at request time.
An ingest script fetches once, cleans, and writes a 1.7 MB SQLite file that is committed to the
repo and loaded into memory at startup. SQLite is in the standard library and is easy for a
reviewer to open. We avoided Parquet to keep `pyarrow` out of the serverless bundle.

## D8. Async where it is real

Ingest is I/O bound, so it uses `httpx.AsyncClient` with concurrent weekly chunks, a semaphore and
retries with exponential backoff (5s instead of ~40s for a single call). The API handlers do
CPU-bound pandas work on in-memory data, so they are plain `def` functions that FastAPI runs in its
threadpool. Declaring them `async def` would block the event loop during computation.

## D9. Deployment

Vercel runs the API as one Python function (zero-config FastAPI via `tool.vercel.entrypoint`) and
serves the built React app from its CDN. The same code ships as a single Docker image that serves
both, which runs anywhere a container runs (for example Heroku). Vercel was chosen for the demo
because it gives a free HTTPS URL with no server to manage; Docker keeps us portable.
