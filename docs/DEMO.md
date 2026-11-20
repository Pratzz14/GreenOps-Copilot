# Phase 2 EDA demo

1. Run `python -m src.profile --data data --out outputs --docs docs` in the installed Python environment.
2. Run `npm --prefix frontend run build`, then start the combined server with `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001`.
3. Open [the EDA dashboard](http://127.0.0.1:8001). The full export contains 70,583 records from 13 sources; identical raw rows are retained as candidates.
4. Compare **Full exports** with **Baseline period**. Inspect completeness, duplicate and coverage charts. Snapshot/master context and overlapping weeks are explicitly labeled.
5. Filter the catalog to **data_platform**, select `data_platform_usage.csv`, then **Coverage & joins**. Expand `dp-dev` to inspect six missing baseline dates. Missing observations do not prove the cluster was off.
6. Open **Issues & evidence**, filter to exact duplicate candidates, and expand their row references. No deletion has occurred.
7. Open **Fields & distributions**, choose `active_use_h`, and inspect the observed distribution. These are observations, not savings estimates.
8. Select `ai_subscriptions.csv`. Inspect Draft/Final frequencies and their coexistence groups; no financial baseline is computed here.
9. Open **Canonical map** to see all 16 planned cost fields with direct, derived or unknown mappings. Inspect join ambiguity before attempting aggregation.
10. Expand **Provenance & analysis limits**. Reports are reproducible from the frozen source inputs. `GET /api/v1/runs/current` remains 503 until Phase 3+.

The installed application runs offline without external assets or services.
Refresh sources via CLI and restart the API to load a new report. Use
`EDA_URL=http://127.0.0.1:8001` (PowerShell: `$env:EDA_URL = "..."`) with
`npm --prefix frontend run test:eda` for desktop/mobile and failure/retry QA.
Port 8000 is the normal development backend; 8001 is used for the Phase 2
review because the older server occupies 8000. Vite's existing development
proxy still targets 8000; use the combined 8001 app for this review.
