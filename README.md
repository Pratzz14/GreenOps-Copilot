# GreenOps Copilot

Traceable GreenOps decisions for the sprintd Basel Green AI & Data case.
Stack: deterministic Python engine, FastAPI, React + TypeScript + Vite.

The local app opens the Gold Dashboard when a validated run is published.
Data Explorer includes profiles for the 13 core sources, cleaned Silver data,
and the Gold calculation tables. See **Build and verify Gold** for the pipeline.

## Hackathon submission

Submit the prototype and both filled CSVs from [submission/](submission/).

- [Baseline and assumptions CSV](submission/template_baseline_and_assumptions.csv)
- [Measures package CSV](submission/template_measures_package.csv)

The September 2025 through August 2026 baseline and the selected
9-measure portfolio come from the same Gold run. At steady state, the
portfolio models CHF 58,606 in annual savings (12.49%), 23,849 kWh of annual
electricity savings, and 5,913 kg CO₂e of annual location-based emissions
savings (32.62%). Estimated implementation costs CHF 16,500
(15 person-days). The modeled savings fall short of the 25% cost and 40%
emissions targets. The package is provisional because coverage is partial,
some emissions use proxies, and some measures require owner approval.

The selected package includes scaling back the customer portal's test pool
after acceptance, reclaiming AI and SaaS seats at renewal, and pausing the
development cluster around quarterly training. The Gold measures catalogue
also includes a Zurich development pilot that keeps Frankfurt GPU training
intact. Its savings still depend on a like-for-like Zurich quote and cutover
validation.

Case data attribution: Sample data ALTYCA, sprintd Basel 2026.
[Organizer requirements](https://github.com/Fa-Bee/sprintd-basel-green-ai-data#submission-baseline-assumptions-and-package-of-measures)

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
data/bronze/                     13 core CSVs + 2 official templates
data/silver/                     Generated versioned CSV tables and reports
data/gold/                       Reserved for Gold CSVs
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

P0 CSVs were **moved**, not copied, into `data/bronze/`. Treat them as read-only.
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

## Build with the extra datasets

Run the full pipeline from the project root:

```powershell
.\.venv\Scripts\python.exe -m src.pipeline --decision-as-of 2026-11-21
```

The full build archives the raw inputs, profiles 28 sources, publishes the
normalized CSVs and reconciled Silver facts, and builds Gold against that exact
Silver version. Restart the API to load the selected release. The existing
individual commands below still support the core-only workflow. Use
`--core-only` for a core-only pipeline release or `--activate <release-id>`
to select an earlier validated release. Use `--activate legacy` to return to
the pre-pipeline publication if its Bronze, Silver and Gold versions agree.

In Silver Analyst Workspace, open **supplemental_comparisons** to compare
invoice and gateway tokens, agent and gateway token volumes by model class,
logged and billed CI time, sampled and billed web traffic, Power BI refresh
minutes against billed capacity-days, and the provider report against six
candidate ledger scopes. It also holds two allocation views, recorded CHF per
FTE and per booked project hour. Each row is aggregated to month and entity
before it is joined, names its `basis`, and stays outside the financial ledger.
Only `same_unit` rows carry a difference.

Job runs carry a `schedule_class` (flexible, fixed deadline, protection window
or by arrangement). Logs carry modeled `retained_gb_days`. Backup chains and
catalogue tables carry protection reasons and review-candidate flags, where an
unknown retention requirement stays unknown.

Gold measures use the extra logs as evidence for review. Microsoft 365
storage GB-days and Power BI refresh activity are available for analysis.
Their baseline electricity estimates require matching service intensity or
capacity evidence, so Microsoft 365 storage appears in the baseline as
activity with a missing energy factor. The dashboard shows one emissions
total: direct CO₂ for Germany and Ireland plus Swiss operating CO₂e. Its
information panel gives both parts. The submission CSVs and the 40% target
stay on direct CO₂. Open **Coverage by workload** on the dashboard, or call
`GET /api/v1/runs/{run_id}/coverage`, to see each workload's activity,
factor sources and whether activity, an energy factor or a direct-CO₂ grid
factor is missing.

Run the release tests with `python -m pytest tests/test_supplemental.py
tests/test_pipeline.py`. Set `GREENOPS_FULL_PIPELINE=1` to also rebuild the
complete case data and check the pinned baseline (several minutes).

## Build and reconcile Silver

Run these commands after profiling Bronze, then restart the API.

```powershell
.\.venv\Scripts\python.exe -m src.normalize --data data --out outputs
.\.venv\Scripts\python.exe -m src.reconciliation --out outputs
```

Normalization stages CSVs for the exact source snapshot and transformation
code. Reconciliation checks grouped sums and publishes the immutable
`data/silver/<version>/` directory and `outputs/current_silver.csv` pointer.
The top-level `cost_baseline.csv`, `reconciliation_report.csv` and
`unresolved_issues.csv` are convenience copies. The API checks the versioned
manifest and content hashes at startup and serves the loaded version until
restart. It compares the input identity with the Bronze snapshot when present.

Open **Silver** for the cleaned tables, full export and baseline views,
applicability and distribution profiles, same-population comparisons, record
lineage, financial reconciliation and unresolved issues. Decimal amounts are
stored at calculation precision. The financial subtotal includes recorded
eligible provider and gateway charges and Final contracts within 2025-09-01
through 2026-08-31. Missing costs and rates stay blank and financial coverage is
reported separately from build readiness. Contract months remain monthly for
annual billing cycles. Usage observations carry no additional cost. The GPU
alias remains a candidate and the test pool has no instance allocations.
Publish Gold after Silver reconciliation to see the case baseline, findings,
measures, and submission exports.

Run Silver browser regression against the built app with
`node frontend/e2e/silver.cjs` and set `EDA_URL` if the server uses a different
local port.

## Silver Analyst Workspace

Open **Analyst Workspace** at `/analysis` to build visual queries or write a
read-only DuckDB SELECT over one Silver dataset. Open **Data Explorer** at
`/data-explorer` to inspect the underlying data layers.

- The catalog contains 19 Silver tables and three fixed joins. Connected tables
  can repeat records from cleaned sources. Use `cost_facts` for reconciliation.
- Visual supports typed filters, multiple grouping dimensions, aggregate and
  row-level arithmetic metrics, and explicit sorting and limits. **Open in SQL**
  copies the generated query into an editable buffer.
- The baseline, accepted disposition and eligible cost amounts are the defaults.
  Ineligible monetary values are masked, and missing costs remain null. Coverage
  describes the scoped dataset before query-specific filters.
- Save definitions locally in `outputs/saved_analyses.json`. Opening one requires
  an explicit rerun. A changed Silver version requires a confirmed rebase.
- Download exploratory CSV and JSON metadata from the same cached result.
  Run the browser regression with `npm --prefix frontend run test:workspace`.

See [the API contract](docs/API.md#silver-analysis) and [demo walkthrough](docs/DEMO.md#silver-analyst-workspace-demo).

### Draft SQL with OpenAI

Describe the analysis you want in the question box. AI chooses a Silver dataset and the relevant fields.
Review the draft in the editable SQL pane and run it when ready. The request
sends the question, available schemas, and scope to OpenAI without Silver rows.

Add the key to the ignored `.env` file in the project root.

```dotenv
OPENAI_API_KEY=your_key_here
```

Reload the workspace after saving the file to enable **Draft SQL**. A backend environment variable
overrides the file. Set `OPENAI_ANALYSIS_MODEL` to override the default
`gpt-4.1-mini`. The direct SQL editor and Visual builder are available without
an API key.

## Build and verify Gold

After publishing Silver, build the Gold run for the case decision date.

```powershell
.\.venv\Scripts\python.exe -m src.gold --decision-as-of 2026-11-21
```

The command validates the current Silver snapshot, loads 14 Gold tables into
DuckDB, reconciles package contributions, and checks both official CSV layouts.
Identical inputs reuse the same immutable run. Each run is in
`data/gold/<run_id>/` and `outputs/current_gold.csv` selects the active run.
Build again after publishing a new Silver version.

Pass `--estimate-missing-costs` to use OpenAI for charges the local unit-price
imputation leaves open. Set `OPENAI_API_KEY` in the environment or project
`.env`. The model receives relative month offsets and price-consistency
categories. Gold calculates the amount locally and records the chosen method
and comparison bills in its evidence. Set `OPENAI_COST_MODEL` to override the
default `gpt-4.1-mini`.

The app opens **Dashboard** at `/dashboard`. The report shows the company-wide
baseline, linked footprint charts, the savings package, and decisions that
require human review. Choose a ranking row to focus the monthly trend. The
chart filters leave the baseline and package at company-wide scope.
Run `npm --prefix frontend run test:dashboard` against the combined local app.

Recommendations use recurring baseline observations and share the dashboard filters.
Run `.\.venv\Scripts\python.exe -m backend.recommendations` to add OpenAI review
tags to the current published run, or pass `--tag-recommendations` when publishing
Gold. The batch uses the existing `OPENAI_API_KEY`. Dashboard reads use the
saved tags and rule-based decisions.

Open **Gold** in **Data Explorer** to see the baseline and browse all 14
published tables. Expand a table to inspect its schema and records. Open
**Detailed overview** for spending breakdowns, findings, safety decisions, and
the savings package. The scorecard defaults to the mid
steady-state scenario used in the exports. Switch to **First 12 months** to
see the effect of lead times and effective dates. The submission exports use the assessed portfolio's mid steady-state estimates.
The scorecard stays provisional while coverage and owner approvals are open.
Download the files from Dashboard or Gold, or run
`python -m src.exports` to generate both official filenames together under
`outputs/submission/<run_id>/` for the active release.

Run `npm --prefix frontend run test:gold` against the combined local app.
Set `EDA_URL` for a port other than 8001. [Demo](docs/DEMO.md#gold-layer-demo) ·
[Gold contract](docs/GOLD_LAYER.md) · [Coverage limitations](docs/LIMITATIONS.md).
