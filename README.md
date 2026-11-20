# GreenOps Copilot

Traceable GreenOps decisions for the sprintd Basel Green AI & Data case.
Stack: deterministic Python engine, FastAPI, React + TypeScript + Vite.

The local setup is runnable. The main page is the Phase 2 exploratory analysis
dashboard: 13 source profiles, quality charts, baseline/full-export views,
measurement distributions by original unit/currency and source evidence. Calculated baselines, findings, measures and exports belong
to later phases and currently return explicit `not_ready` responses.

## Supported environment

Verified on Windows with **Python 3.14.6**, **Node 22.14.0**, **npm 10.9.2**.
Version hints are in `.python-version` and `.nvmrc`. Python dependencies,
including transitive dependencies, are pinned in `requirements.txt`. npm uses
exact direct versions and `frontend/package-lock.json`. No API keys are needed.

## Install

From the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix frontend ci
```

Installation requires internet. The installed app and built frontend run locally
without external services, remote assets or fonts.

## Prepare sources

```powershell
.\.venv\Scripts\python.exe -m src.ingest --data data --out outputs
```

`python -m src` is an alias for this initial pipeline entry point. It hashes
exactly 13 core CSVs and two templates into an immutable
`outputs/snapshots/<snapshot_id>/manifest.json`, then updates
`outputs/current_snapshot.json`. Identical inputs reuse the same snapshot ID.
This stage does not calculate a baseline or make results ready. Restart the
backend after refreshing the snapshot. Ordinary GETs do not run ingestion.

## Profile and explore the sources

```powershell
.\.venv\Scripts\python.exe -m src.profile --data data --out outputs --docs docs
```

The profiler validates the dictionary schema, preserves UTF-8/BOM CSV strings
and quoted free text, and writes `outputs/data_quality.json` plus
`docs/DATA_MAP.md`. It reuses the immutable snapshot format. Rerunning unchanged
inputs produces identical reports; no source rows are edited, dropped or joined.

The dashboard shows completeness, duplicate candidates, event-date coverage,
quality categories, numeric distributions and monthly record counts. Select a
source in **Source catalog**, then use **Fields & distributions**, **Issues &
evidence**, **Coverage & joins**, or **Canonical map**. **Baseline period**
selects September 2025–August 2026 observations; snapshot/master sources remain
context and boundary-overlapping weeks are labeled without proration.

The API validates the saved report against its snapshot at startup. After
regenerating the report, restart the backend. A missing, corrupt or mismatched
report produces a retryable error, never fabricated data. Profiling does not
make calculated financial results ready.

## Run the app

For development, use two PowerShell terminals:

```powershell
# Terminal 1
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2; host, port and /api proxy are configured in vite.config.ts
npm --prefix frontend run dev
```

Open [the development app](http://localhost:5173).

For the combined local demo, build first, then start a single backend process:

```powershell
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open [the combined app](http://127.0.0.1:8000),
[health](http://127.0.0.1:8000/api/v1/health), or
[API documentation](http://127.0.0.1:8000/docs).
Build before launching the backend so its static routes are registered.
Stop a server with Ctrl+C; use only one backend process on port 8000.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run build
```

Tests use `outputs/pytest/` to avoid Windows temporary-path length limits.
Some Windows sandboxes block asyncio's local socket pair: run API tests and
servers in a terminal with loopback access if startup stalls.

Regenerate frontend types after API contract changes:

```powershell
.\.venv\Scripts\python.exe -m backend.export_openapi
npm --prefix frontend run generate:api
```

## Project layout and data

```text
data/                            13 core CSVs + 2 official templates
src/                             Snapshot + read-only profiling CLI; source contracts
backend/                         FastAPI, contracts and cached metadata
frontend/src/api/                Client and generated OpenAPI types
frontend/src/components/         Future shared UI components
frontend/src/features/           Future findings, package, safety and export UI
tests/                           Profiling, snapshot, API and static-serving checks
docs/                            Snapshot, data map, assumptions, API and demo
outputs/                         Generated artifacts (ignored by Git)
sprintd-basel-green-ai-data/      Original docs, upstream Git metadata, extra/
```

P0 CSVs were **moved**, not copied, into `data/`. Treat them as read-only.
Bonus files remain untouched in `sprintd-basel-green-ai-data/extra/`.
See [source hashes](docs/DATA_SNAPSHOT.md), [API contract](docs/API.md),
[demo guide](docs/DEMO.md), and [current limitations](docs/LIMITATIONS.md).

Attribution: **Sample data ALTYCA, sprintd Basel 2026**.
Official reporting baseline: **2025-09-01 through 2026-08-31 inclusive**.

## EDA browser regression

With the combined server running, execute:

```powershell
$env:EDA_URL = "http://127.0.0.1:8000"
npm --prefix frontend run test:eda
```

The check uses the installed Playwright Chromium, compares visible totals with
the API, exercises drill-downs, filters, baseline switching and error/retry,
and checks desktop/mobile layout and console health. Screenshots go to the
Windows temporary directory under `greenops-phase2-qa/`. If Chromium is absent,
install the browser once with `npm --prefix frontend exec -- playwright install chromium`.

For the active Phase 2 review session, the combined EDA server uses
[port 8001](http://127.0.0.1:8001) because the older server already occupies
8000. Use `--port 8001` and set `EDA_URL` accordingly when reproducing that session.
