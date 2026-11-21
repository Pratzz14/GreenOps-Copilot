# GreenOps Copilot Gold-layer business analysis

Gold gives management a reconciled view of digital spend, estimated energy and location-based emissions, evidence of waste, and savings from a candidate package. The Basel case requires cloud, servers, AI and SaaS coverage for **1 September 2025 through 31 August 2026**, with breakdowns by department and tool. The package is evaluated against **25% annual CHF savings, 40% annual location-based CO₂ reduction and at most CHF 16,500 in implementation cost**, using CHF 1,100 per person-day plus one-time cash expenses. [Case brief](https://github.com/Fa-Bee/sprintd-basel-green-ai-data/blob/30c476fb4932877744643c282e022b5c056f444c/README.md)

## What the current Silver snapshot supports

| Business question | Verified result | Gold requirement |
| --- | --- | --- |
| What was recorded for the baseline year? | **CHF 463,471.49** across 35,667 included records, with 114 missing amounts and zero missing FX rates. A quarter of the recorded subtotal is **CHF 115,867.87**. | Publish recorded CHF with coverage. Recalculate the target once the baseline is validated. |
| Which AI subscriptions have unused seats? | August 2026 Final records show **40** unused Microsoft Copilot seats at **CHF 678.38/month**, **21** ChatGPT Team seats at **CHF 423.99/month**, and **6** Claude Team seats at **CHF 121.14/month**. | Keep monthly seat activity separate from contract-effective savings. Verify notice, renewal and service needs before counting savings. |
| How much did development run versus work? | `dp-dev` recorded **8,616 cluster-hours running** and **747.97 active cluster-hours** across **359 of 365 days**. | Keep observation coverage, cluster-hours, node-hours and billable hours distinct. Apply quarterly training requirements before estimating any reduction. |
| Is on-demand GPU operation quantifiable? | Azure shows **CHF 10,955.77** in recorded `gpu-ml` charges with **nine missing cost rows**. `gpu-ml-01` averaged **9.25%** across 51 complete weekly GPU observations. The billing-to-instance relationship is a candidate. | Confirm the relationship, avoidable charges, startup and standby costs, training windows and location-based factors before crediting CHF or CO₂ savings. |
| Can production be switched off every night and weekend? | `dp-prod` had activity on **103 of 104 weekend days** in the calendar, with one unobserved day. Ticket `T-1029` records finance closing work until about 04:00 on the last three working days of the month. | Withhold blanket shutdown eligibility. Daily data establishes which days had activity. An hourly schedule needs finer evidence and confirmation from the responsible platform and finance owners. |

The figures above come from the published Silver snapshot and describe the synthetic case company. Gold estimates the environmental baseline where it has compatible factors and quantities. The scorecard shows modeled savings against targets and marks the result provisional while coverage and review are open. [Executed Silver checks](gold_silver_checks.sql) · [Assumptions](ASSUMPTIONS.md) · [Case questions](https://github.com/Fa-Bee/sprintd-basel-green-ai-data/blob/30c476fb4932877744643c282e022b5c056f444c/example_questions.md)

## Required Gold tables

`run_id` scopes every table to an immutable snapshot, calculation version and decision date. The proposed schema uses **14 tables**. The two submission CSVs are query outputs. [DuckDB schema](gold_schema.sql)

| Table | One row per | Upstream inputs and business use |
| --- | --- | --- |
| `analysis_run` | Published calculation run | Silver snapshot, case targets, calculation version, baseline dates, decision date, emissions unit basis and coverage. Anchors the overview, scorecard and exports. |
| `subject` | Reportable resource, instance, product, service or unresolved bucket within a run | Silver `assets`, `mapping_departments_tools`, `resource_relationships`, `contracts` and source identifiers. Provides stable scope and responsible role. |
| `cost_monthly` | Month × subject × provider × reporting department × tool × location × cost stream | Silver `cost_facts`, validated ownership and source geography. Stores recorded eligible CHF and coverage counts. Supports reconciliation, trends and spend rankings. |
| `impact_monthly` | Month × subject × provider × reporting department × tool × location × workload boundary × scenario | Silver usage, authoritative billed or observed activity, Gold factors and documented allocation. Stores facility kWh, location-based kg and coverage. Supports carbon and energy rankings. |
| `factor` | Versioned factor or assumption within the run | Sourced grid intensity, energy intensity, PUE, geographic assumptions and shared-cost allocation. Stores definitions, units, dates, and low/mid/high values or text. |
| `licence_monthly` | Final contract key × month | Silver `contracts` and monthly FX. Stores the observed seat snapshot and contract terms for AI and SaaS. |
| `finding` | Evidence-backed waste hypothesis | Silver usage, contracts, billing and asset observations. Stores facts, time window, confidence and verification status for subjects such as `dp-dev`, GPU, SaaS and AI routing. |
| `protection_window` | Target subject × concrete protection instance | Tickets, calendar, inventory and ownership. Stores open-ended or time-bounded restrictions, decision, evidence and role. Supports shutdown overlap checks and escalation. |
| `measure` | Versioned candidate action | Finding, scoped protections, contract terms, alternatives and effort. Stores decision and responsibility, earliest effective date, implementation effort and one-time cash. |
| `measure_scenario` | Measure × assumption scenario × savings horizon | Before/after modeled activity, rates and factors. Stores gross avoided cost, new recurring cost, before/after kWh and before/after location-based emissions. |
| `measure_constraint` | Measure × related measure × constraint type | Shared workloads and operational prerequisites. Records dependencies, mutually exclusive choices and overlapping benefits with a resolution and evidence. |
| `package_result` | Package × scenario × savings horizon | Evaluated baseline and counterfactual, optimizer result and candidate-set scope. Stores the authoritative totals, one-time package cost and assessment maturity. |
| `package_member` | Package result × selected measure | Credited CHF, kWh, emissions and implementation cost evaluated together. Supports package reconciliation and the one-row-per-measure export. |
| `evidence` | Evidence item within a named evidence set | Bronze file and row IDs, Silver transforms, tickets, factor references, formulas and review notes. Each published row points to a reusable evidence set. |

### Calculation and publication rules

- **Financial baseline.** Assign each Silver cost fact to one cost bucket and reconcile to `cost_baseline.csv` at calculation precision. Include eligible provider invoices, gateway charges and Final monthly contracts. Exclude drafts, duplicate rows and unresolved collisions from recorded CHF, while exposing exceptions. Publish missing amounts and missing FX counts alongside the subtotal. Assign dated, in-period `review` rows to known buckets. Keep unresolved dates in run-level evidence. Use `Unallocated` where department cannot be established, and `Unknown` or `Mixed` for geography as supported by the source. Record the direct-attribution rule and keep payment or consumer departments distinct from the chosen reporting department.
- **Attribution and boundaries.** Derive stable subject keys from source system, provider and supported business identifiers. Keep `gpu-ml` separate from `gpu-ml-01` until the relation is verified. Keep `vm-test` at billed-pool grain while member allocation remains unresolved. Use one authoritative activity stream per workload boundary and period. An `impact_monthly` boundary expected to be in scope still gets a coverage row when its estimate is unknown. Record affected records, coverage and fallback rationale in evidence. Aggregate cost and impact separately before comparing them across shared dimensions.
- **Environmental baseline.** Calculate facility kWh from activity × matching intensity with documented IT/facility boundaries. Apply PUE once when the source value covers IT energy. Multiply facility energy by a location-based grid factor and persist the exact factor set for each scenario. Plan for Switzerland, Germany and Ireland, with explicit treatment of mixed or unknown locations and SaaS without a defensible activity proxy. Model vCPU-hours, node-hours, GPU-hours, storage-days, tokens and subscription messages on their own units. Cached input is a subset of input tokens. Document boundary-week treatment, reference period, geography and source dates. Use a single declared emissions basis per run. Hold CO₂-specific export values open if only CO₂e is available, pending a compatible method or case clarification.
- **Observed values and savings.** Use `NULL` for quantities or prices that are unknown. Zero requires evidence or a documented calculation. Inactive seats indicate possible spend at monthly unit prices. Count actual cancellation savings from the effective contract date and count avoided operational energy only when supported by a workload change. `first_year` describes savings realizable in the defined prospective 12 months. `steady_state` describes the annual run rate after implementation. Treat low/mid/high as shared assumptions used consistently for baseline and after-measure totals.
- **Protection and timing.** Use Europe/Zurich for the case schedule and store concrete intervals with offsets. Use half-open intervals and expand recurring windows for the evaluation period. Review named resources in tickets against the structured scope, including `dr-failover` in `T-1094`, and preserve hard restrictions such as `st-backup` retention. Record conflicts and gaps with the responsible reviewer. A zero-row overlap result only means the requested action did not match a published window. Safety eligibility still comes from the evaluated measure and its evidence.
- **Package math.** Net CHF savings are gross avoided cost less new recurring cost. Implementation cost is person-days × CHF 1,100 plus one-time cash. Package evaluation accounts for dependencies, shared effort and duplicate savings claims. Automatic packages contain eligible measures only. Conditional proposals have a separate package ID and their benefits stay outside automatic totals. Check fixed thresholds on unrounded values. A candidate misses a target when its margin is negative. Declare an evaluated candidate set infeasible only after testing its admissible combinations and recording the scope, margins and unresolved factors. Withhold target attainment when cost or carbon coverage is incomplete, estimates are provisional, or a relevant denominator is missing or nonpositive.
- **Publishing.** Validate grain uniqueness, matching run/scenario/horizon keys and matching evidence sets. Reconcile monthly finance to Silver and package totals to the credited ledger. Keep both official CSV headers and order. Populate the required factors and calculation/source text. Leave unsupported bonus fields blank. Scope exports to the same scenario, horizon, package and evidence as the scorecard.

Suggested loading sequence is **recorded spend, seats and observed findings**, then **sourced impact and protection**, then **measure evaluation, package and exports**. Forecasts, market-based allocations and bonus sources can be added after the case requirements are covered.

## Gold query list

The [Gold SQL file](gold_queries.sql) contains 15 read-only DuckDB queries. Each executes against the companion schema once the needed tables are populated.

| ID | Business question or check | Primary tables |
| --- | --- | --- |
| Q01 | What are annual recorded CHF, estimated kWh and location-based emissions, and what is the coverage? | `analysis_run`, `cost_monthly`, `impact_monthly` |
| Q02 | Who drives spending and emissions, and how do the rankings and monthly trends change by provider, department, tool, location or subject? | `cost_monthly`, `impact_monthly` |
| Q03 | How much is recorded or missing by billing stream? | `cost_monthly` |
| Q04 | How many AI/SaaS seats were purchased, active and unused, and what did unused seats cost at monthly unit prices? | `licence_monthly` |
| Q05 | Which contracts with unused or unverified seats have upcoming notice and expiry dates? | `licence_monthly` |
| Q06 | Which waste observations have quantified candidate impacts and how strong is their evidence? | `finding`, `measure`, `measure_scenario` |
| Q07 | What would a scoped action such as GPU on-demand cost and save across scenarios and horizons? | `measure`, `measure_scenario`, `analysis_run` |
| Q08 | Which protections intersect the proposed scope, action and time window? | `protection_window`, `analysis_run` |
| Q09 | Which actions are blocked or need a human decision, and who owns review? | `measure`, `subject` |
| Q10 | What are the before/after totals, margins, remaining budget and all-scenario result? | `package_result`, `analysis_run` |
| Q11 | Are selected measures missing a prerequisite, in conflict, or sharing an avoided workload? | `measure_constraint`, `package_member` |
| Q12 | Which source records, factors and formulas support a result? | `evidence`, `factor` |
| Q13 | Do credited member amounts reconcile to the package, and does automatic membership comply with safety? | `package_result`, `package_member`, `measure` |
| Q14 | Which rows feed the official baseline and assumptions CSV? | `analysis_run`, `cost_monthly`, `impact_monthly`, `factor` |
| Q15 | Which rows feed the official measures CSV for the selected automatic package? | `package_member`, `package_result`, `measure`, `analysis_run`, `evidence`, `factor` |

## Run the queries

Run `python -m src.gold --decision-as-of 2026-11-21` after publishing Silver.
Read `outputs/current_gold.csv` for the active run ID. The run directory
`data/gold/<run_id>/` contains `results.duckdb`, the frozen queries, both CSVs,
and the artifact manifest. The Analyst Workspace continues to query Silver.
Use a read-only DuckDB connection for cross-table Gold SQL.

### Run the checks available today

The [Silver SQL file](gold_silver_checks.sql) contains S01 financial reconciliation, S02 AI seats, S03 development runtime, S04 GPU billing and monitoring, S05 production activity by day type, S06 protection tickets and S07 gateway task/model cost. From the repository root in PowerShell:

```powershell
@'
import csv
from pathlib import Path
import duckdb

with Path('outputs/current_silver.csv').open(encoding='utf-8-sig', newline='') as pointer:
    version = next(csv.DictReader(pointer))['version']
with duckdb.connect() as db:
    silver_dir = Path('data/silver', version).resolve().as_posix()
    db.execute('SET VARIABLE silver_dir = ?', [silver_dir])
    sql = Path('docs/gold_silver_checks.sql').read_text(encoding='utf-8')
    for index, statement in enumerate(db.extract_statements(sql), start=-1):
        result = db.execute(statement)
        if statement.type == duckdb.StatementType.SELECT:
            print(f'\nS{index:02}', ', '.join(column[0] for column in result.description))
            for row in result.fetchall():
                print(*row, sep=' | ')
'@ | .\.venv\Scripts\python.exe -
```

### Run the Gold queries when the tables have data

Open the published `results.duckdb` read-only and run the required statements in
its frozen `queries.sql`. Set only the variables used by the desired query.
The identifiers and time interval below are examples. Use IDs from the
database. The automatic package ID is its run ID.

```sql
SET VARIABLE gold_run_id = 'run-id';
SET VARIABLE gold_scenario = 'mid';
SET VARIABLE gold_horizon = 'steady_state';
SET VARIABLE gold_group_by = 'department';
SET VARIABLE gold_seat_month = DATE '2026-08-01';
SET VARIABLE gold_subject_id = (
  SELECT subject_id FROM gold.subject
  WHERE run_id = getvariable('gold_run_id') AND subject_name = 'dp-prod'
);
SET VARIABLE gold_action = 'shutdown';
SET VARIABLE gold_window_start = TIMESTAMPTZ '2026-11-30 00:00:00+01:00';
SET VARIABLE gold_window_end = TIMESTAMPTZ '2026-11-30 05:00:00+01:00';
SET VARIABLE gold_package_id = 'package-id';
SET VARIABLE gold_evidence_set_id = 'evidence-set-id';
```
