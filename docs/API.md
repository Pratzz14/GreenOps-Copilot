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

Planned run, finding, measure, safety, factor, package and export routes are
registered as HTTP 503 stubs until calculation phases are implemented:

```json
{
  "detail": {
    "code": "not_ready",
    "message": "Calculated run unavailable. Source snapshotting does not calculate a baseline or package."
  }
}
```

Unknown API routes return JSON HTTP 404. Malformed identifiers and unsupported
sections/export names return HTTP 422. Valid-looking IDs receive 503 while
there is no run store; existence checks will follow with calculated runs.
Template examples are never exposed as completed submission downloads.

Initial `RunIdentity`, `Measurement` and `Overview` contracts define run/package
identity, data/factor versions, scenario, horizon, period, units, estimate status
and quality flags. Unknown measurements are JSON null; NaN/infinity are rejected.
Detailed finding/package contracts remain pending. These are schema definitions,
not fabricated result fixtures.

Regenerate frontend types after contract changes:

```powershell
.\.venv\Scripts\python.exe -m backend.export_openapi
npm --prefix frontend run generate:api
```

Vite proxies `/api` to `http://127.0.0.1:8000`; React uses relative `/api/v1`
URLs. FastAPI serves the built frontend at `/` and `/assets/`, after API routes.
Unknown API paths never return frontend HTML. Raw data and outputs are not served.

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
