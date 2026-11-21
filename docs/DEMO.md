# Bronze exploration demo

1. Run `python -m src.profile --data data --out outputs --docs docs` in the installed Python environment.
2. Run `npm --prefix frontend run build`, then start the combined server with `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001`.
3. Open [Data Explorer](http://127.0.0.1:8001/data-explorer). Bronze opens first with the 13 original exports, what each file contains, and full-export record counts.
4. Under **Exploration completed**, compare **Full exports** with **Baseline period**. The summary and drill-downs follow the selected period. The source catalog always shows full-export counts.
5. Expand **Completeness**, **Duplicate candidates**, **Date coverage**, or **Quality findings** to see the corresponding charts.
6. Expand **Source analysis**, select `data_platform_usage.csv` under **Source**, then choose **Coverage and proposed joins** under **Analysis**. Expand `dp-dev` to inspect six missing baseline dates. Missing observations do not establish downtime. **Filter and compare source profiles** offers source search, filters and sorting.
7. Choose **Issues and evidence**, filter to exact duplicate candidates, and expand a finding to see examples and logical row references.
8. Choose **Fields and distributions** and select `active_use_h`. For an example with units and currencies, select `azure_costs.csv` and compare its quantity and cost distributions.
9. Select `ai_subscriptions.csv` to inspect Draft/Final frequencies and coexistence groups. Choose **Canonical mapping** to see proposed source fields, rules and fallbacks.
10. Expand **Provenance & analysis limits** to see the selected report and snapshot identities. Switch to **Silver** and **Gold** to see each layer’s purpose and status, then return to **Bronze** to resume your exploration.

The installed application runs offline without external assets or services.
Refresh sources via CLI and restart the API to load a new report. Run
`npm --prefix frontend run test:eda` for the desktop and mobile regression.
The test uses port 8001 by default. Set `EDA_URL` to target a different server.

## Silver Analyst Workspace demo

1. Publish Silver with `python -m src.normalize` followed by
   `python -m src.reconciliation` and restart the combined app.
2. Open **Analyst Workspace**, choose **Spending by department**, and click
   **Run analysis**. Expand **Quality, coverage and query provenance** to see
   the version, applied scope and missing-cost coverage.
3. Open **Chart** and choose `reporting_department` and `recorded_cost_chf`.
   Export the CSV and JSON metadata together to retain the result context.
4. Try **Platform activity versus runtime**, **Final AI seat utilization**,
   **AI costs by task and model**, and **Server utilization with asset context**.
   Start each investigation with an explicit run.
5. Switch to **Visual** and choose a dataset. Select output fields including
   `record_id`, add a typed filter, and run. Use **View lineage** on a source
   row, or group the query and inspect its provenance. Choose **Open in SQL**
   to edit the generated query.
6. Expand **Saved analyses**, name the definition and save. Reload, reopen the
   definition and rerun. If Silver has changed after a refresh, review and
   confirm the rebase before rerunning.

Run `npm --prefix frontend run test:workspace` against the combined local server.
Set `EDA_URL` if the port differs from 8001.

## Gold layer demo

Publish Silver, then run `python -m src.gold --decision-as-of 2026-11-21`. Start
the combined local app and open the **Gold** tab in **Data Explorer**. Expand
any table to show its schema and records, then open **Detailed overview**.

1. Show the annual baseline, coverage, and spend and emissions by department.
   Change the group to **Location**. Explain the separately reported Swiss
   operating CO₂e estimate and the scorecard's direct CO₂ basis.
2. Show the `dp-dev` finding and open **View evidence**. Compare time running
   with active time and call out the observation gap. The August AI seat
   findings provide a second example with priced inactivity by product.
3. Show **Utilization analysis**, select a chart driver to narrow the scan, and expand a resource to explain the rule and source rows. Use Gold to compare the automatic and conditional packages.
   Compare steady-state and first-year results. Show the evidence-eligible SaaS
   measures and the additional conditional proposals. Explain why incomplete
   baseline coverage leaves the official target verdict open.
4. Open **Block blanket production shutdown** and show ticket T-1029. The
   Finance closing window and weekend activity are visible in the evidence.
5. Download the two draft CSVs. They use the same baseline and package as the
   mid steady-state scorecard. Download the separately labeled conditional
   measures CSV to review the illustrative package. Close with the
   operationalization note and the team AI electricity scenario below.

## Operationalization

Start with a monthly source refresh owned by IT and Finance. Reconcile provider
charges with Finance, review disputed mappings with service owners, and pin
the factor version alongside every published run. Alert on missing sources,
stale versions, new coverage gaps, and changes in the selected package.
Publish immutable snapshots through the local build commands. For production,
use authenticated source connectors, durable storage, restricted access, and
an audit trail for operational changes. The prototype provides recommendations
and evidence. Infrastructure owners execute and verify changes separately.

## Team AI electricity estimate

**Illustrative sprint scenario: 0.07 kWh of text-inference electricity
(midpoint 0.072 kWh, sensitivity range 0.006–0.60 kWh).** No team usage meter
or request log was available. The scenarios are planning assumptions.

| Scenario | Assumed text-prompt equivalents | kWh per equivalent | Estimated kWh |
| --- | ---: | ---: | ---: |
| Low | 100 | 0.00006 | 0.006 |
| Mid | 300 | 0.00024 | 0.072 |
| High | 500 | 0.0012 | 0.60 |

Multiply the two input columns. The midpoint intensity is anchored to Google's
reported 0.24 Wh median Gemini Apps text prompt. The low and high intensities
are sensitivity assumptions for using that benchmark as a proxy. The scenario
covers hosted text inference and excludes tool execution, image workloads,
laptops and local services. Keep it separate from the case company's footprint.
[Google measurement study](https://arxiv.org/abs/2508.15734)
