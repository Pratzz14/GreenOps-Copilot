# API contract

Prefix: `/api/v1`. Interactive documentation: `/docs`; OpenAPI: `/openapi.json`.
Pydantic models in `backend/schemas.py` own the contract. The React health client
uses generated types in `frontend/src/api/schema.ts`.

`GET /health` returns HTTP 200 before or after source snapshotting:

```json
{
  "status": "ok",
  "api_version": "v1",
  "data_ready": false,
  "snapshot_id": null,
  "core_source_count": null,
  "reason": "No valid source snapshot loaded. Run python -m src.ingest, then restart the API."
}
```

After snapshotting and restarting, `snapshot_id` is the content SHA-256 and
`core_source_count` is 13. `data_ready` remains false: hashing sources is not a
calculated run. Health reports cached startup state, not live disk health.

Unknown API routes return JSON HTTP 404. Malformed identifiers and unsupported
sections or export names return HTTP 422. Unknown measurements are JSON null.

Regenerate frontend types after contract changes:

```powershell
.\.venv\Scripts\python.exe -m backend.export_openapi
npm --prefix frontend run generate:api
```

Vite proxies `/api` to `http://127.0.0.1:8000`; React uses relative `/api/v1`
URLs. FastAPI serves the built frontend at `/` and `/assets/`, after API routes.
Unknown API paths never return frontend HTML. Raw data and outputs are not served.

## Gold runs

Publish Gold against Silver with `python -m src.gold --decision-as-of YYYY-MM-DD`.
Current results bind to the active Silver version. An absent, stale, or damaged
publication returns 503 with `not_ready`. Historical published run IDs remain
readable by ID. Unknown IDs return 404 when Gold has been published.

| Route | Result |
| --- | --- |
| `GET /runs/current` | Run, Silver and factor versions, decision date, baseline and package IDs |
| `GET /runs/{run_id}/overview?scenario=mid` | Recorded and imputed CHF, modeled kWh, and the location-based `reporting_kg_co2e` with `reporting_carbon_coverage`. The overview also exposes direct CO₂ and Swiss operating CO₂e components. |
| `GET /runs/{run_id}/coverage?scenario=mid` | Annual activity, reporting emissions, gap status and factor evidence by workload boundary and location. `planning_kwh` and `planning_kg_co2e` are workload estimates outside the baseline totals. Returns 404 for runs published before gap reasons were stored. |
| `GET /runs/{run_id}/breakdowns?group=department&scenario=mid` | Annual and monthly spend and footprint, with the dashboard's `reporting_kg_co2e`. Groups also include tool, platform, provider, location, and subject. |
| `GET /runs/{run_id}/tables` | The 14 published tables and their row counts for the run |
| `GET /runs/{run_id}/tables/{table}?limit=25&offset=0` | Column schema and a page of rows from a published table, ordered by primary key. Values preserve their exact text representation, missing values are null, and timestamps are UTC. |
| `GET /runs/{run_id}/findings`, `/findings/{finding_id}` | Observations, waste hypotheses, and evidence IDs |
| `GET /runs/{run_id}/measures`, `/safety-decisions`, `/factors` | Measures by scenario and horizon, protection windows, factor sources and ranges |
| `GET /runs/{run_id}/evidence/{evidence_set_id}?limit=20&offset=0` | Paged source rows, ticket text, factor references and calculations. The maximum page size is 100. |
| `GET /packages/{package_id}` | Six scenario/horizon scorecards and the package contribution ledger |
| `GET /packages/{package_id}/exports/{filename}` | `baseline.csv` and `measures.csv` with official headers and project-template order. Use the conditional package ID for its separately labeled draft measures. |
| `GET /submissions/{run_id}/{filename}` | Official selected-package files with unchanged numeric fields and expanded methodology, scenario calculations, and source references. Matches the byte output of `python -m src.exports` for that run. |

The scorecard uses steady-state annual savings for submission and exposes a
separate first-year horizon. Conditional packages and their exports use draft
labels. Provisional results retain missing values. The automatic measures CSV
contains no data rows when no measure qualifies for modeled selection.

## Phase 2 profiling API

Typed contracts are in `backend/quality_models.py`, with the same generated
OpenAPI TypeScript client as the existing API. All routes are read-only:

| Route | Response |
|---|---|
| `GET /api/v1/data-quality?scope=full` | Compact source summaries, report/snapshot IDs, baseline and limitations |
| `GET /api/v1/data-quality/sources/{source_name}?scope=baseline` | One source profile, canonical map and proposed joins; findings loaded separately |
| `GET /api/v1/data-quality/sources/{source_name}/issues?scope=full&offset=0&limit=20&code=missing_value` | Filtered/paginated findings with complete row references and at most three raw examples per finding |

`scope` accepts only `full` or `baseline`. Limit is 1–200; offset is nonnegative.
Invalid parameters return 422; unknown core source names return 404. Missing,
corrupt, checksum-invalid or snapshot-mismatched reports return 503 `not_ready`.
Report identity is included in all successful responses to prevent mixing
versions in the frontend cache. Full raw tables are never sent to the browser.

At startup the service checks schema, report checksum, all 15 input hashes
against the selected immutable manifest, exactly 13 source names and complete
canonical mappings. Ordinary GETs use memory and do not reopen CSVs or run ETL.
Source updates take effect only after regenerating the snapshot/report and
restarting the service. `/health.data_ready` remains false and calculation
routes remain 503 until later phases produce a calculated run.

## Silver exploration

All successful responses carry the loaded Silver version. Send the overview's
`version` with subsequent calls for consistency. A stale version returns 409,
invalid filters return 422, unknown catalog tables or record IDs return 404,
and absent or invalid artifacts return 503.

| GET path (under `/api/v1/silver`) | Filters and data |
| --- | --- |
| `/` (use `/api/v1/silver` without a trailing slash) | Build status, snapshot, catalog, audit counts and financial coverage |
| `/tables/{table}/rows` | `scope=full\|baseline`, `status=accepted\|review\|duplicate\|quarantined\|all`, offset and limit |
| `/tables/{table}/profile` | Source table, scope, column completeness, observations, distributions and Bronze comparisons |
| `/records/{record_id}` | Cleaned record plus Bronze reference, transformation history, evidence and issues |
| `/issues` | Optional source table and issue code, offset and limit |
| `/reconciliation` | Dimension (total, source_file, provider, reporting_month, reporting_department, currency), offset and limit |

Money and decimal measurements are JSON strings, preserving CSV precision.
Null numeric cells are JSON null. The records API uses the logical Bronze
record number (the header is record 1). The startup loader validates and reads
the published version once. Requests perform no transformations.

## Silver analysis

All analyst endpoints are under `/api/v1/analysis`. See the generated OpenAPI for
the request and response schemas.

| Method and path | Response or effect |
|---|---|
| GET `/catalog` | Current Silver version, baseline dates, default scope, datasets, fields, join availability and starters |
| POST `/preview` | Validated SQL for a visual definition, without executing it |
| POST `/draft` | Optional OpenAI draft and automatic Silver dataset selection, without executing it |
| POST `/query` | Executes a versioned definition and returns result metadata plus the first 100 rows |
| GET `/results/{id}?offset=0&limit=100` | Page from the cached result. Page size 1–1,000 |
| GET `/results/{id}/csv` | CSV attachment of the cached rows, with empty CSV fields for nulls |
| GET `/results/{id}/metadata` | JSON attachment with SQL, version, scope, types, units, coverage and limits |
| GET or POST `/saved` | List or create local definitions |
| PUT or DELETE `/saved/{id}` | Update or delete one local definition |

Every preview and query requires a dataset and Silver version. The definition
also contains the mode, scope, visual configuration or SQL, and chart settings.
Missing Silver returns 503, a stale version returns 409, invalid definitions and
unavailable joins return 422, an active query returns 429, and a timed-out query
returns 408. A missing or expired result returns 404.

SQL allows one SELECT with non-recursive CTEs and subqueries over the selected
dataset. The API checks the parsed statement and runs it in an isolated DuckDB
process with one active query, two engine threads, a 256 MB engine memory limit,
and a five-second execution budget after dataset loading. The worker is
discarded after each run. External access and extension autoloading are disabled.

The API materializes at most 10,000 rows and caches ten completed results for 15
minutes. Charts use at most 1,000 returned rows. Decimal result values are
serialized as exact decimal strings when DuckDB returns DECIMAL. DuckDB AVG
and division can return floating-point values, as shown by their result types.
SQL expressions with undetermined units are marked **Unverified**. For financial
reconciliation, use DECIMAL subtotals with explicit CHF fields and the default
eligibility scope. The coverage object describes the scoped dataset before
query-specific filters. Aggregate coverage within a query can be computed from
financial disposition fields.

Analyses and exports are exploratory. The query process operates on a
manifest-validated view of the startup Silver version and writes no layer data.

The catalog exposes `ai_configured` as a boolean. `/draft` accepts a Silver
version, scope, and question. It sends available dataset schemas and scope
with the question to OpenAI, then checks the chosen dataset and SQL against the local read-only
rules and field names. The response carries a draft and explanation, or null
SQL when the question cannot be answered from the current dataset.
