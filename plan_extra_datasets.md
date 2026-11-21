# Extra datasets in GreenOps — progress check and continuation plan

> **Checked:** Saturday 2026-11-21, 13:50 Basel time. Last code change: 13:37 (`frontend/src/dashboardData.ts`).
> **Active release:** `a1aa1fb774fa…` (full build, 28 sources) → Silver `f0203fd3…` → Gold `f529984a…`.
> **Deadlines:** draft submission today 15:00–15:30; final submission Sunday 2026-11-22 08:30.
> **How this was checked:** code review of `src/`, `backend/`, `frontend/src/`, `tests/`, plus the published CSVs of the active release. The test suites were **not rerun** for this check (the review environment could not install DuckDB), and `results.duckdb` was not queried. Test status below is taken from what the test files contain, not from a fresh run.

## 0. Implementation update — Saturday 2026-11-21, 14:35

The plan below was implemented in code the same afternoon. **No new release has been built or activated**: the active release is still `a1aa1fb774fa…`, and the changes take effect after the commands in "To release" run on the Windows machine. A copy of the code before these changes is in `_backup_before_extra_plan_2026-11-21/`.

| Step | State | How it was checked |
|---|---|---|
| Dashboard: one emissions total including Swiss operating CO₂e | Code done | Typecheck and lint pass. Browser test updated, not run |
| 1. Tests | Written | `tests/test_supplemental.py`: 11 tests pass in the review sandbox. `tests/test_pipeline.py`: 4 tests written, **not run** (needs DuckDB and FastAPI) |
| 2. Coverage and gap states in API and dashboard | Code done | Typecheck and lint pass. The endpoint SQL has **not been executed** |
| 3. Silver comparisons | Done | Full Silver build on the real data in the sandbox; all 15 extra tables and 468 comparison rows parse with the published types |
| 4. Bronze manifest and grain labels | Done | Manifest carries bytes, record counts and source paths; snapshot ID unchanged (`f67f1a2d…`) |
| 5. Gold analysis | Done in Python | The Gold calculation was run without DuckDB on the new Silver build: CHF 463,471.49, 128,061.32 kWh, 13,218.68 kg direct CO₂ and both packages are identical to the active release. The DuckDB load and CSV export were **not run** |
| 6. Release | Open | Needs the Windows environment |

What the finished comparisons show: no ledger scope reconciles the provider report within 1% (cloud plus hoster is closest, mean gap 4.3%); Power BI capacity is billed as a fixed capacity-day whatever the refresh minutes; billed CI minutes are about 2.05 × logged run time; agent runs are part of gateway usage and do not explain the invoice excess. Web traffic has three missing days (2026-02-10 to 2026-02-12).

**To release** (PowerShell, project root):

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m backend.export_openapi
npm --prefix frontend run generate:api
npm --prefix frontend run typecheck; npm --prefix frontend run lint; npm --prefix frontend run build
.\.venv\Scripts\python.exe -m src.pipeline --decision-as-of 2026-11-21
# restart the API, then:
npm --prefix frontend run test:dashboard; npm --prefix frontend run test:gold; npm --prefix frontend run test:workspace
```

If anything fails, `python -m src.pipeline --activate a1aa1fb774fa9d0ef0a17215dfeb43eaeeb1e04eb39be58d37863b0b727b77a6` returns to the current release; restoring the backup folder returns the code.

Still open from the plan: core-only builds read scheduler and backup evidence from `extra/` directly; no Microsoft 365 service-level energy factor was sourced; the review measures carry activity quantities but no kWh or CHF.

## 1. Where the work stands

**Overall:** Bronze and Silver ingestion of all 15 sources is in place and published. The one-command pipeline exists and has produced an active release. Gold reproduces the pinned baseline exactly and shows Swiss operating CO₂e. What remains is mostly in three areas: the Gold analysis that turns the new sources into estimates and quantified measures, the API/dashboard fields that explain gaps, and tests for the new code.

| Plan section | Status | Short reason |
|---|---|---|
| 1. Bronze | Mostly done | All sources registered, archived, hashed and profiled. Manifest detail and the grain/additivity display are missing. |
| 2. Silver | About two-thirds done | 15 normalized tables and 4 comparisons published. Five planned comparisons/views are missing and three differences are unexplained. |
| 3. Gold | About one-third done | Baseline pinned, Swiss CO₂e done, Gold reads Silver. No M365 estimate, no Power BI ranking, review measures carry no quantities. |
| 4. API and dashboard | About half done | Analyst workspace and Swiss CO₂e done. Gap reasons, activity quantity and unit are stored in Gold but not exposed. |
| 5. Verification and release | About one-third done | Pipeline command works. Only two tests cover the new code; none cover the pipeline. |

### 1.1 Bronze

| Requirement | Status | Evidence |
|---|---|---|
| Registry of 13 core + 13 extra CSV + 2 JSONL + 2 templates | Done | `source_specs.EXTRA_SPECS` / `EXTRA_FILES`, `ingest.TEMPLATES` kept separate |
| Preserve originals, snapshot bytes and hashes | Done | `snapshots/<id>/raw/` holds 30 files, re-hashed after copy and again at release validation |
| Record counts and source paths in the snapshot | Open | `manifest.json` stores only name and SHA-256. Counts live in `data_quality.json`; byte size and source path are stored nowhere |
| Full build with core-only workflow retained | Done | `src.pipeline` (`--core-only`), `ingest`/`profile`/`normalize` accept optional `--extra` |
| Nested JSONL, renamed duration fields, malformed lines | Done | `supplemental.records` flattens `model`/`usage`/`metrics`, maps `duration_s`/`duration_sec`, keeps the line number |
| Missing periods, duplicates, mixed units | Mostly done | Gaps found for M365, Power BI, logs, project hours. `web_traffic` (hourly) is skipped by gap detection although 3 days are absent |
| Every issue traceable to record or line | Done | `source_row` is the CSV record or JSONL line |
| Data Explorer: reporting period and grain, additivity class | Open | `SourceCatalog.tsx` shows only `role · cadence` for extras. No period, no daily-observation / weekly-total / point-in-time label |

### 1.2 Silver

Published row counts: agent runs 37,523 (369 exact duplicates excluded), CI runs 38,565 (374 duplicates excluded, 1,108 with missing metrics flagged), Power BI 39,904, web traffic 16,127, log volume 13,304, jobs 5,810, M365 658, catalogue 500, project hours 489, headcount 154, AI invoices 110, backups 78, provider report 22, projects 15, locations 13.

| Source group | Done | Still open |
|---|---|---|
| Microsoft 365 | MB→GB, 1,859,849 baseline GB-days over 50 weeks, weeks of 2026-03-02/09/16 flagged missing, week of 2026-08-31 prorated to 1 day, video and mail kept separate | Nothing in Silver |
| Power BI | Refresh count, minutes, views per report/day; owner department linked on every row | Comparison with billed Azure capacity `pbi-kap` |
| CI runs and platform jobs | Duplicates excluded, reruns kept, monthly logged vs billed runner minutes for Dublin | Logged time is only 47–50% of billed minutes every month — unexplained. `time_window` is raw text, not classified as flexible / fixed deadline / protection window |
| AI agent runs and invoices | Dedup by run ID, cached ≤ input check, invoice vs gateway by provider, model class and month | Invoices exceed gateway tokens by roughly 3–10% every month — uninvestigated. No agent-level view of retries and workload mix |
| Web, logs, backups, catalogue | Sampling-adjusted web GB matches hoster within ±0.21 GB/month; log GB normalized | Retained log GB-days; backup/catalogue view of storage candidates versus protected data |
| Locations, headcount, projects, hours, provider report | AWS Zurich conflict flagged; project IDs verified against the master | Labeled allocation views. Provider report is compared against the whole ledger (CHF 14–16k/month gap), but the dictionary describes it as a cloud-provider overview — the scope is wrong |
| Gold reads Silver | Done for full builds (`gold.publish` reads scheduler and backup rows from the Silver version) | Core-only builds still read `extra/` directly |

### 1.3 Gold

| Step | Status | Evidence |
|---|---|---|
| Baseline pin | Done | `baseline.csv`: CHF 463,471.49, 128,061 kWh, 13,218.68 kg CO₂ — identical to the pin |
| Swiss operating estimate | Done | `grid_ch_operating` 0.026 / 0.049 / 0.084 kg CO₂e/kWh, computed per impact row; browser test expects 3.96 t CO₂e; official score stays on direct CO₂ |
| 1. M365 storage kWh | Open | Only a finding with a generic disk-benchmark sensitivity. No service-appropriate factor, no billing-overlap check, no coverage row for the missing weeks |
| 2. Power BI ranking | Partial | One review measure for refresh days with zero views. No per-report ranking by refresh effort and views |
| 3. Reconcile before changing totals | Partial | Totals untouched (correct). Storage attribution from logs/backups/catalogue not built |
| 5. Reviewable measures | Partial | Five `human_review` measures exist (report refresh, no-change nightlies, agent retries, flexible jobs, log retention > 90 days) with record counts only — no activity quantity, kWh or CHF, and no backup/catalogue retention measure |

A sizing note that affects priorities: at the existing generic storage factor, M365 storage comes to roughly **13 / 49 / 186 kWh** (low / mid / high) against a 128,061 kWh baseline, about 0.04%. Whatever factor is finally sourced, this item improves coverage, not the totals or the 40% target.

### 1.4 API, dashboard, analyst workflow

| Requirement | Status | Evidence |
|---|---|---|
| New Silver tables in Data Explorer, visual analyst, SQL, AI drafting | Done | `backend/silver.py`, `analysis_data.GRAINS` include extras and `supplemental_comparisons` |
| Swiss operating CO₂e labeled on dashboard | Done | `Dashboard.tsx`, `DashboardCharts.tsx`, `Gold.tsx` |
| Conditional vs credited savings, both official CSVs | Done | Separate conditional package and `conditional-measures.csv`; template headers enforced at build |
| Activity quantity/unit and the three gap states in the API | Open | `activity_quantity`, `activity_unit`, `energy_gap_reason`, `carbon_gap_reason` exist in `gold_schema.sql` and are written by `gold_baseline.py`, but appear in no backend model, route or frontend file |
| Factor source and evidence links on results | Not verified | Evidence sets exist; I did not confirm they are returned on every total and breakdown |

### 1.5 Verification and release

| Requirement | Status | Evidence |
|---|---|---|
| One command Bronze → Silver → Gold with version-chain validation and activation after checks | Done | `python -m src.pipeline --decision-as-of …`; `validate_release` checks Gold→Silver→snapshot→archive hashes |
| Rollback | Done in code, untested | `--activate <release>` and `--activate legacy` |
| Tests for new behaviour | Mostly open | `tests/test_supplemental.py` has two tests (JSONL field variants + malformed line; M365 proration and MB→GB). Nothing for duplicate JSONL records, sampling, conflicting locations, join fan-out, unknown-stays-unknown, or any part of `src/pipeline.py` |
| Per-estimate reconciliation by workload and region | Open | No new estimate has been enabled yet, so there is nothing to reconcile |
| Regressions before cutover | Not confirmed | The release was activated at 13:36; I found no record that backend, frontend and browser suites were run against it |

## 2. Continuation plan

Ordered so that the submission is never at risk. Each step ends with the full pipeline run and the baseline pin check; a step that moves the pinned numbers without an explained activity record, factor and calculation is reverted.

### Step 0 — Confirm the active release before the draft (now, ~20 min)

- [ ] Run `python -m pytest`, `npm --prefix frontend run typecheck`, `lint`, `build`, then `test:dashboard`, `test:gold`, `test:workspace` against the active release.
- [ ] If anything fails and cannot be fixed quickly, `python -m src.pipeline --activate legacy` and submit the draft from the core-only publication.
- [ ] Submit the draft CSVs in the 15:00–15:30 window from whichever release passed.

### Step 1 — Tests for what already exists (P0, ~1.5 h)

Add to `tests/test_supplemental.py` and a new `tests/test_pipeline.py`, using small fixture files:

- [ ] Duplicate JSONL line → second record `duplicate` with `duplicate_of`; same `run_id` with different content → both `review`; CI rerun with the same key stays `accepted`.
- [ ] Missing CI metrics → `missing_run_metrics`, excluded from the runtime comparison, not counted as zero.
- [ ] Web sampling: `gb_out × sample_rate`; `sample_rate < 1` → review and null `expanded_gb`; a UTC hour at 23:00 lands on the next Zurich date and month.
- [ ] Location conflict: a region with accepted billing and `used_by_sme = no` raises `billing_location_conflict`.
- [ ] Fan-out guard: after building comparisons, `sum(core_quantity)` for `provider_spend` equals the cost-baseline subtotal, and extra tables add no rows to `cost_facts`.
- [ ] Pipeline: two identical builds return the same release ID and leave one directory; a build that raises mid-way leaves `current_release.csv` unchanged and no partial release directory; `--activate` of an older release works and a tampered release is refused; the older Gold run stays readable through the API.
- [ ] Baseline pin test: a full build on the real data yields CHF 463,471.49, 128,061.32 kWh and 13,218.68 kg (mid).

### Step 2 — Expose gap reasons and activity in the API and dashboard (P0, ~1.5 h)

- [ ] Add `activity_quantity`, `activity_unit`, `energy_gap_reason`, `carbon_gap_reason`, factor IDs/source URL and `evidence_set_id` to the breakdown models in `backend/gold_models.py` and the queries behind `routes.py`.
- [ ] Map to three user-facing states: **missing activity**, **missing energy factor**, **known kWh with missing grid factor** (`missing_direct_co2_factor`). Null stays null in JSON and blank in CSV.
- [ ] Regenerate `outputs/openapi.json` and `frontend/src/api/schema.ts`; show the state next to each partial subtotal in `DashboardCharts.tsx` and `Gold.tsx`.
- [ ] Test: an impact row with unknown quantity returns `null` energy with reason `missing_activity` through the API, the dashboard e2e and the export.

### Step 3 — Finish the Silver comparisons (P1, ~2 h)

- [ ] **Provider report:** compare against the cloud-provider subset of the ledger (try Azure, AWS, and Azure+AWS; keep the one that reconciles and state it; if none does, label the scope unresolved). Replace the current all-ledger comparison.
- [ ] **Power BI vs capacity:** monthly refresh minutes and views against `pbi-kap` billed quantity and CHF. Publish as a comparison; mark the relationship verified only if the months move together.
- [ ] **CI gap:** split billed-minus-logged by month into missing-metric runs, duplicates and remainder; test whether billed minutes follow `cpu_h` or a per-run minimum. Record the finding in the `interpretation` column.
- [ ] **AI gap:** aggregate agent runs by provider, model class and month (tokens, retries, cached share) as a third column beside invoice and gateway. State whether agent traffic outside the gateway accounts for the 3–10% excess.
- [ ] **Jobs:** add `schedule_class` (flexible / fixed_deadline / protection_window) and `deadline_local` parsed from `time_window`; unparsed text → `review`.
- [ ] **Storage evidence:** `retained_gb_days` for logs (`ingested_gb × retention_days`, labeled as modeled); a backup/catalogue view with `retention_required`, `data_class`, `last_read`, restore-test date, and a `protected` flag.
- [ ] **Allocation views:** cost per FTE and per project hour by department and month, each labeled as an allocation view and kept outside the ledger.
- [ ] Add `web_traffic` to gap detection at daily grain.

### Step 4 — Bronze explorer details (P1, ~45 min)

- [ ] Add `bytes`, `record_count` and `source_path` (relative) per file to the snapshot manifest. This changes the snapshot ID once; rerun the pin test afterwards.
- [ ] Add `period_start`, `period_end`, `grain` and `additivity` (`daily_observation` / `period_total` / `point_in_time` / `master`) to `Spec` and the quality API; render them in `SourceCatalog.tsx` for all 28 sources, with templates still listed as submission formats.

### Step 5 — Gold analysis from the extra sources (P1, ~2.5 h)

Each item sits behind its own switch so it can be reconciled alone against the pin.

- [ ] **Power BI ranking:** per report — refresh count, refresh minutes, views, minutes per view, owner, report type. Regulatory reports and `pbi-07` stay protected. No kWh.
- [ ] **Quantify the five review measures** with activity only: avoidable runner-minutes from no-change nightlies (capped at billed minutes), tokens in retried runs, refresh minutes on zero-view days, flexible job hours, log GB-days above 90 days. Keep them `human_review`; credited savings stay zero.
- [ ] **Retention measure** from backups and catalogue, excluding anything with a retention requirement, restore requirement or protection ticket (`st-backup` stays blocked).
- [ ] **Time shifting:** state on the flexible-jobs measure that no CO₂ saving is claimed without hourly regional grid data.
- [ ] **M365 storage:** add coverage rows (50 of 53 weeks, three missing) with reason `missing_energy_factor`. Add kWh only if a service-level storage factor is found and the overlap with billed storage is checked; otherwise it stays a documented gap. Video and mail stay out unless a matching service-side factor exists.
- [ ] Carry the CHF 16,500 cap, protection windows and overlap constraints into package selection for any measure that later becomes eligible.

### Step 6 — Release (P0, Saturday evening)

- [ ] Run the full pipeline, confirm the pin (or a reconciliation table by workload and region for every deliberate change), run all three test layers, then activate.
- [ ] Update `README.md`, `docs/LIMITATIONS.md`, `docs/ASSUMPTIONS.md` and `docs/API.md` with what the extra sources do and do not support.
- [ ] Freeze. Sunday morning is for submission only.

### If time runs short

Steps 0, 1, 2 and 6 protect the submission and the honesty of the numbers; do those first. Steps 3 and 5 add analytical depth for the jury; within them, the provider-report scope fix, the Power BI ranking and the quantified review measures give the most visible result for the least risk. Step 4 and the M365 kWh factor can be dropped without weakening the submission.

## 3. Open questions for the team

1. Which providers does `provider_monthly_report.csv` cover? The dictionary says "cloud provider"; the label says "Total cost all services".
2. Is there an acceptable source for a Microsoft 365 service-level kWh-per-GB-day factor, or should it stay a documented gap given its ~0.04% size?
3. Should the manifest change in Step 4 (which changes the snapshot ID) happen before or after the final release is cut?
