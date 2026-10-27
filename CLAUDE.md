# Project: UK Wind Forecast Monitor (Gridbricks / REint Full Stack SWE Challenge)

This file is the single source of truth for this project. Read it fully before doing anything.
Follow the phases in order. After each phase: run tests, update `docs/DECISIONS.md` if any decision was made, and make a commit.

---

## 1. Context

**Who this is for:** A take-home challenge for a Full Stack SWE role at Gridbricks (early-stage energy-tech startup).
The evaluators care about: strong React, well-designed async Python APIs, rigour (tests, edge cases),
engineering discipline (git hygiene, CI, docs, observability), and *ownership of ambiguity*.

**The fictional client:** A UK energy utility. Their trading team buys power on the GB **day-ahead market**.
They need to know how much power to procure beyond what wind will produce, so they rely on wind forecasts
made the day before delivery.

**The product must let them:**
1. See the **latest wind generation forecast that was available at decision time**, compared with actual generation.
2. **Quantify forecast error** so they can make purchase decisions that account for it.

**Hard constraints from the brief:**
- Data: only national-level wind data from Elexon BMRS. Nothing else.
  - Actuals: `FUELHH` dataset, filter `fuelType == "WIND"`. Fields: `startTime` (30-min resolution), `generation` (MW).
  - Forecasts: `WINDFOR` dataset. Fields: `startTime`, `publishTime` (when forecast was made), `generation` (MW).
- Scope: data relevant to **purchase decisions made in January 2026**.
- Stack: React frontend, Python backend, Docker, deployed on **Vercel or Heroku**.
- Time budget: **max 16 hours total**. Do not gold-plate. Scope discipline is part of the evaluation.
- AI tool usage must be disclosed in the README.
- Repo must be public with an anonymous random name (e.g. `kjhwr`).

**Deliverables:** deployed app, public repo with README, unlisted YouTube video (max 10 min: 5 min client pitch + 5 min tech lead walkthrough), submission form.

---

## 2. Key domain decisions (resolve ambiguity explicitly; this is what evaluators look for)

Record each of these in `docs/DECISIONS.md` with a one-paragraph rationale.

### D1. Which delivery days are in scope
Day-ahead decisions are made on day D-1 for delivery day D.
Decisions made **Jan 1 to Jan 31, 2026** → delivery days **Jan 2 to Feb 1, 2026** (inclusive).
- Actuals needed: startTime from `2026-01-02T00:00Z` to `2026-02-01T23:30Z`.
- Forecasts needed: publishTime from roughly `2025-12-30T00:00Z` to `2026-02-01T23:59Z` (buffer so fixed-horizon mode works too).
- Make the default range configurable, but default to this.

### D2. What "latest forecast available at decision time" means
GB day-ahead auction (Nord Pool N2EX) gate closure is **09:50 UK time on D-1**. January is GMT, so UK time == UTC, but code must still be timezone-aware (`Europe/London`), never naive.

Two selection modes, both supported by the API:
- **`cutoff` mode (default, the business view):** for each delivery day D, for each target `startTime` in D, pick the forecast with the latest `publishTime <= (D-1 at cutoff_time, Europe/London)`. Default `cutoff_time = 09:50`. User can change it.
- **`horizon` mode (the analyst view):** for each target `startTime` t, pick the forecast with the latest `publishTime <= t - H hours`. User picks H (e.g. 1 to 48). Lets users see how accuracy degrades with lead time.

Always return `publish_time` and `lead_time_hours = startTime - publishTime` with each forecast point so the selection is transparent.

**Invariant (must be tested):** a selected forecast's `publishTime` is never after the cutoff. No look-ahead leakage.

### D3. Resolution mismatch
FUELHH is half-hourly. WINDFOR may be hourly (verify in Phase 1).
Default approach: evaluate error only on timestamps where both exist (inner join on `startTime`). Do not interpolate forecasts silently.
Document the choice and the number of points dropped.

### D4. Error definition and sign convention
`error_mw = forecast_mw - actual_mw`.
- Positive error = **over-forecast** = wind came in lower than expected = the utility under-procured and must buy the shortfall at short notice (expensive). This is the costly direction; highlight it in the UI as "shortfall risk".
- Negative error = under-forecast = over-procured.

### D5. Metrics (no external data, so no capacity-normalised metrics)
- MAE, RMSE, mean bias (MW)
- Error percentiles: P10, P50, P90 of `error_mw`
- **Shortfall buffer:** P90 of positive error, phrased as "To cover wind shortfall in 90% of half-hours, procure ~X MW above the forecast."
- Max over-forecast, max under-forecast (with timestamps)
- Normalised MAE as % of mean actual generation (label it clearly)
- **Do not use MAPE.** Wind can be near zero, MAPE explodes. Explain this in DECISIONS.md.
- Breakdowns: by hour of day (UK), by lead-time bucket, by delivery day.
- `n` (sample count) and coverage (% of expected points present) shown alongside every metric.

### D6. Data quality rules
- FUELHH duplicates/revisions for the same `startTime`: keep the row with the latest `publishTime`.
- WINDFOR: may contain multiple rows per (publishTime, startTime); dedupe deterministically.
- Missing points: return `null`, render as gaps in charts. Never fill with zeros.
- Log counts of duplicates removed and gaps found at ingest time.

### D7. Data strategy
January 2026 is historical and immutable. **Do not call Elexon on each user request.**
An ingest script fetches once, cleans, and writes a small committed data file that the API loads into memory at startup.
Store as SQLite (stdlib) or gzipped CSV. **Avoid pyarrow** (bundle size on Vercel).

---

## 3. Elexon API notes (verify in Phase 1, do not trust blindly)

Base URL: `https://data.elexon.co.uk/bmrs/api/v1`
No API key required.

- Actuals: `GET /datasets/FUELHH/stream?settlementDateFrom=YYYY-MM-DD&settlementDateTo=YYYY-MM-DD&fuelType=WIND`
- Forecasts: `GET /datasets/WINDFOR/stream?publishDateTimeFrom=ISO&publishDateTimeTo=ISO`

Docs: https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream and `/WINDFOR/stream`.
Things to confirm in Phase 1 and record in `docs/DATA_NOTES.md`:
- exact parameter names and whether there are max range limits (chunk requests by day or week if so)
- WINDFOR resolution (30 min or 60 min) and forecast horizon (how far ahead each publish covers)
- WINDFOR publish frequency (how many publishes per day)
- timestamp formats and timezone (expect UTC `Z`)
- FUELHH `startTime` vs `settlementDate`/`settlementPeriod` consistency

Use `httpx` with timeouts, retries with backoff (e.g. `tenacity`), and polite chunking.

---

## 4. Tech stack

**Backend**
- Python 3.12, FastAPI, Pydantic v2, pandas, numpy, httpx
- pytest, pytest-cov, ruff (lint + format)
- Standard library `logging` with JSON-ish structured output

**Frontend**
- React 18 + Vite + TypeScript (strict)
- TanStack Query for server state
- ECharts via `echarts-for-react` (built-in zoom/brush; handles thousands of points)
- Tailwind CSS
- Filter state lives in URL query params so any view is shareable/bookmarkable
- Vitest + React Testing Library (a few focused tests, not exhaustive)

**Infra**
- Docker: multi-stage `Dockerfile` (build frontend, serve it plus API from one FastAPI container), plus `docker-compose.yml` for local dev (hot reload)
- GitHub Actions CI: ruff, pytest, frontend typecheck + lint + vitest + build
- Deploy: **Vercel** (React static build + FastAPI as a Python serverless function). Check Vercel's current Python/FastAPI docs for the exact entrypoint and `vercel.json` format before implementing. Bundle size limit applies, so keep Python deps lean. Docker is for local dev and is Heroku-ready as an alternative; explain this trade-off in the README.

---

## 5. Repository structure (target)

```
/
├── CLAUDE.md                  # this file
├── README.md
├── docker-compose.yml
├── Dockerfile                 # multi-stage production image
├── vercel.json
├── requirements.txt           # root, for Vercel (mirrors backend deps)
├── api/
│   └── index.py               # Vercel entrypoint, imports FastAPI app
├── backend/
│   ├── app/
│   │   ├── main.py            # app factory, middleware, router mount
│   │   ├── config.py          # settings (pydantic-settings), defaults
│   │   ├── logging.py
│   │   ├── api/
│   │   │   └── v1.py          # route handlers only, thin
│   │   ├── schemas.py         # Pydantic response models
│   │   ├── data_store.py      # loads processed data once, in-memory
│   │   ├── selection.py       # forecast selection logic (cutoff / horizon)
│   │   └── metrics.py         # pure functions, fully unit tested
│   ├── scripts/
│   │   └── ingest.py          # fetch from Elexon, clean, write data file
│   ├── data/
│   │   └── wind_jan2026.sqlite  # committed processed data
│   ├── tests/
│   │   ├── test_selection.py
│   │   ├── test_metrics.py
│   │   ├── test_ingest_cleaning.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── pyproject.toml         # ruff + pytest config
├── frontend/
│   ├── src/
│   │   ├── api/               # typed client + TanStack Query hooks
│   │   ├── components/        # charts, KPI tiles, controls, tables
│   │   ├── hooks/             # useUrlState, etc.
│   │   ├── lib/               # formatting, time helpers
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts         # dev proxy /api -> backend
├── docs/
│   ├── ARCHITECTURE.md        # diagram + request flow
│   ├── DECISIONS.md           # D1..Dn with rationale
│   └── DATA_NOTES.md          # what we learned about the datasets
└── .github/workflows/ci.yml
```

---

## 6. API design (versioned, typed, stable)

All endpoints under `/api/v1`. All times ISO 8601 UTC in responses. All responses are Pydantic models.

Common query params (validated):
- `start`, `end`: delivery date range (dates), default = D1 range, must lie within available data
- `mode`: `cutoff` | `horizon` (default `cutoff`)
- `cutoff_time`: `HH:MM` UK local, default `09:50` (only for `cutoff` mode)
- `horizon_hours`: int 1..48, default 24 (only for `horizon` mode)

Endpoints:
- `GET /health` → `{status, data_loaded, actuals_count, forecasts_count, data_range}`
- `GET /meta` → available ranges, defaults, dataset notes (drives UI defaults)
- `GET /series` → `{points: [{start_time, actual_mw, forecast_mw, publish_time, lead_time_hours, error_mw}], params_echo}`
- `GET /metrics` → `{summary: {...D5 metrics..., n, coverage}, by_hour: [...], by_lead_bucket: [...], by_day: [...], worst_misses: [...]}`
- `GET /accuracy-by-horizon` → MAE / RMSE / P90 for H = 1..48 hours (precompute or cache; powers the "how accuracy decays" chart)

Rules:
- Invalid params → 422 with clear message (e.g. start after end, out-of-range dates).
- Cache computed results per param set (`functools.lru_cache` on a hashable key).
- Middleware: request id, request timing logged, `X-Response-Time` header.
- CORS only as needed for local dev.

---

## 7. Frontend design

Single-page dashboard. Clean, professional, energy/trading feel. Not a CRUD form.

Layout (top to bottom):
1. **Header:** product name, one-line description, date-range picker, mode toggle (Trading cutoff / Fixed horizon), cutoff time input or horizon slider.
2. **KPI row:** MAE, RMSE, Bias, P90 shortfall buffer, coverage. Each with a tooltip explaining it in plain English.
3. **Main chart:** actual vs selected forecast over time, error shaded between lines, zoom/brush, tooltip showing publish time and lead time.
4. **Two-up row:** error distribution histogram (with P10/P50/P90 markers) | error by hour of day (bar).
5. **Accuracy vs horizon chart:** MAE and P90 vs lead time 1..48h. Mark the current selection.
6. **Worst misses table:** top 10 by absolute error, sortable.
7. **Methodology panel (collapsible):** the assumptions from section 2 in plain language.

UX rules:
- Loading skeletons, empty states, and error states for every query.
- Debounce slider input; keep previous data visible while refetching (`placeholderData: keepPreviousData`).
- Memoize chart options; avoid re-rendering charts on unrelated state changes.
- Display times in UK time with timezone label.
- Units always shown (MW).
- Responsive down to laptop width; mobile is a nice-to-have.

---

## 8. Build phases (with time budget, total ≈ 16h)

### Phase 0: Scaffold (1h)
- Repo layout per section 5, `.gitignore`, ruff/pytest config, Vite React TS app, Tailwind, docker-compose with backend + frontend hot reload.
- Minimal `/api/v1/health` and a frontend that calls it.
- CI workflow running lint + tests + build (can be mostly empty tests at this point).
- **Done when:** `docker compose up` shows the frontend talking to the backend, CI is green.

### Phase 1: Data exploration and ingest (2.5h)
- Hit both Elexon endpoints with small ranges, inspect raw JSON, fill in `docs/DATA_NOTES.md` (section 3 checklist).
- Write `scripts/ingest.py`: chunked fetch, retries, parse, timezone-aware, dedupe per D6, write processed data file. Idempotent and re-runnable.
- Log summary: rows fetched, duplicates removed, gaps, min/max timestamps.
- Unit test the cleaning functions with small hand-made fixtures (no network in tests).
- **Done when:** processed data file is committed and DATA_NOTES.md is filled.

### Phase 2: Core logic (2.5h)
- `selection.py`: cutoff mode and horizon mode, vectorised with pandas (`merge_asof` on publishTime per target, or groupby + filter). Must be correct before fast.
- `metrics.py`: pure functions for every metric in D5 plus breakdowns.
- Tests (this is where rigour shows):
  - no forecast selected with publishTime after cutoff (property-style test over many params)
  - picks the *latest* eligible forecast when several exist
  - target with no eligible forecast → null, not dropped silently
  - DST-safe cutoff computation (test a date in BST even though January is GMT)
  - resolution mismatch join behaviour
  - metrics on known small arrays (hand-computed expected values), empty input, all-null input
- **Done when:** coverage on `selection.py` and `metrics.py` is high and all edge cases pass.

### Phase 3: API (1.5h)
- Implement endpoints from section 6 with Pydantic models, validation, caching, middleware, logging.
- `test_api.py` using FastAPI `TestClient`: happy paths, 422s, param echo.
- **Done when:** OpenAPI docs at `/docs` look clean and all tests pass.

### Phase 4: Frontend (4h)
- Typed API client + hooks, URL state hook.
- Build components from section 7 in order of importance: controls → KPI row → main chart → histogram + by-hour → horizon chart → worst misses → methodology.
- A few Vitest tests: URL state parsing, number formatting, one component render with mocked data.
- **Done when:** a non-technical person can answer "how much extra should I buy to be safe?" from the screen.

### Phase 5: Production packaging and deploy (1.5h)
- Multi-stage Dockerfile: build frontend, copy into backend image, FastAPI serves static files + API. Verify `docker build && docker run` works.
- Vercel deploy: static frontend + Python function for API, processed data file bundled. Verify all endpoints work on the deployed URL.
- Smoke-test the deployed URL in an incognito window.
- **Done when:** public URL works end to end.

### Phase 6: Docs and polish (1h)
- README (see section 9), ARCHITECTURE.md with a Mermaid diagram, DECISIONS.md complete.
- Remove dead code, check lint, final CI green.

### Phase 7: Video (2h, done by the human, Claude can help script)
See section 10.

---

## 9. README requirements

Must include:
- One-paragraph product summary and screenshot/GIF
- **Live demo link** (Vercel)
- **How to run:** `docker compose up` (dev), `docker build/run` (prod image), and without Docker
- **How to re-ingest data:** `python backend/scripts/ingest.py`
- **Directory and file guide** (required by the brief)
- Key assumptions (short list linking to DECISIONS.md)
- Testing and CI overview
- Limitations and what I would do next (e.g. probabilistic forecasts, cost-weighted error using price data, alerting, live data pipeline)
- **AI tools used:** state explicitly that Claude Code was used, and for what
- Writing style: plain, clear, no hype. **Do not use em dashes or en dashes** in README or docs.

---

## 10. Video outline (max 10 min)

**Part 1: Client pitch (≤ 5 min).** Audience: utility trading team. Business language, no code.
1. The problem: day-ahead purchase decided at 09:50 the day before; wind forecast error turns into expensive short-notice buying.
2. Live demo: pick a day, show the forecast they actually had at gate closure vs what happened.
3. The headline number: "Over January, to cover wind shortfall 90% of the time you needed ~X MW above forecast."
4. When forecasts are worst (hours of day, longer lead times, specific days).
5. What a full rollout would add.

**Part 2: Tech lead walkthrough (≤ 5 min).**
1. Architecture diagram: ingest → processed store → FastAPI (selection + metrics) → React dashboard.
2. Key decisions D1 to D7 and why (especially no look-ahead leakage and the cutoff definition).
3. Code tour: `selection.py`, `metrics.py`, tests, API schemas, frontend data flow.
4. Practices: CI, tests, commit history, logging, Docker, deploy trade-offs.
5. Limitations and next steps.

---

## 11. Working rules for Claude Code

- Work phase by phase. Do not start a phase until the previous one meets its "Done when".
- Small, focused commits using Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `ci:`). Never one giant commit.
- Write tests alongside logic, not at the end.
- Keep route handlers thin; business logic lives in pure, testable modules.
- No network calls in tests. Use fixtures.
- Never use naive datetimes. UTC internally, Europe/London for business rules and display.
- When something in the data contradicts this plan, stop, record it in DATA_NOTES.md, update DECISIONS.md, then adapt.
- Respect the 16h budget. If a feature is not in sections 6 to 7, ask before building it.
- If unsure about a library's current API (Vercel config, ECharts props, Elexon params), check the docs rather than guessing.
- Keep dependencies minimal and pinned.

---

## 12. Open items to confirm

- [x] WINDFOR resolution, horizon, publish frequency (Phase 1): hourly, 8 publishes/day, ~59h ahead. See DATA_NOTES.md.
- [x] Elexon stream endpoint range limits (Phase 1): a full month works in one call but WINDFOR takes ~40s, so chunk weekly.
- [ ] Vercel deploy verified on the live URL (bundle limit is now 500 MB, pandas + numpy fit comfortably)
- [ ] Submission deadline: not stated in the brief or the email; ask the recruiter on Wellfound

---

## 13. Agreed revisions (these override earlier sections where they conflict)

1. **Deploy early.** A hello-world Vercel deploy (static frontend + `/api/v1/health`) is part of Phase 0, so platform risk surfaces at hour 1, not hour 14.
2. **Async where it is real.** Route handlers are plain `def` (CPU-bound pandas work runs in FastAPI's threadpool; `async def` would block the event loop). Ingest uses `httpx.AsyncClient` with concurrent weekly chunks, a semaphore and retries.
3. **One selection function.** Both modes reduce to "per target `startTime`, a cutoff timestamp; pick the latest forecast with `publishTime <= cutoff`". Cutoff mode: cutoff = D-1 at `cutoff_time` Europe/London. Horizon mode: cutoff = t - H. One `merge_asof`, one leakage invariant, one test suite.
4. **Cut list if time is short (in order):** per-day breakdown, sortable worst-misses table (plain top 10 is fine), frontend hot reload in compose, frontend tests beyond 2 or 3. Protect: main chart, KPI row with shortfall buffer, accuracy-vs-horizon chart.
5. **Phase 1 verifications:** auction gate-closure source for the 09:50 default, WINDFOR horizon covers all of D from the D-1 cutoff, FUELHH WIND and WINDFOR describe the same (transmission-metered) wind.
6. **Optional, only if time allows:** "procure-to" line = forecast minus P90 shortfall buffer, explicitly labelled as an in-sample backtest.
7. The challenge brief `.docx` is not committed (it is the client's document); it is gitignored.
8. **Deviations made during the build** (all recorded in docs/DECISIONS.md or the README):
   - Vercel deploys as two services (`vercel.json` `services`: Vite `frontend`, FastAPI `backend`), because the importer requires it for this repo layout. No `api/index.py` or root `requirements.txt`; the backend's deps come from `backend/pyproject.toml`, and CI checks it matches `backend/requirements.txt`.
   - Shortfall buffer = P90 of **all** errors (what "cover 90% of hours" means), not P90 of positive errors only (D5).
   - React 19 (what the Vite template installs) instead of 18. Worst-misses table is a plain top 10, no dark mode (cut list).
