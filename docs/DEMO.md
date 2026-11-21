# GreenOps Copilot demo

## Presenter transcript

Allow five minutes for the live demo and three minutes for questions. Start
with the [submission build](../README.md#run-the-submission-from-a-fresh-checkout)
already running. The blockquotes are the lines to read aloud.

### 1. Dashboard

**On screen** — Open **Dashboard**. With **Assumptions** set to **Mid** and **Period** set to **All months**, point to the three headline figures, then the **Biggest drivers** and **Monthly footprint** charts.

> GreenOps Copilot starts with the company-wide footprint for September 2025 through August 2026. For this baseline, we estimate about 469,000 Swiss francs in spending, 128,000 kilowatt-hours of electricity, and 18.13 tonnes of carbon dioxide equivalent. Electricity and emissions have partial coverage. Below the totals, we can see the biggest drivers and how the footprint changes month to month.

### 2. Microsoft Copilot utilization and recommendation

**On screen** — Stay on the Dashboard. Confirm **Group by → Tool** and **Metric → Spending**. Click **Microsoft Copilot** under **Biggest drivers**, then scroll to **Utilization analysis**. Point to cost centers **4000**, **4100**, and **4200**. Expand **4000** and open **Source rows**. Click **View recommendation** and show **Reduce unused seats at renewal** with **Spending horizon** set to **Monthly**.

> Clicking Microsoft Copilot filters the trend and utilization analysis to that tool. The utilization table has seven cost-center records. In August, cost center 4000 had 13 unused seats, 4100 had seven, and 4200 had six. The expanded row shows that unused seats also appeared the previous month, and we can see which source rows support the finding.
>
> Those records roll up into one recommendation to reduce persistently unused seats at renewal. Across all seven cost centers, 40 seats went unused in August, representing about 678 Swiss francs that month. The recommendation needs review. Procurement and the product owner should confirm seat demand, minimum commitments, and notice terms before changing the subscription.

### 3. Savings package

**On screen** — Open **Data Explorer → Gold → Detailed overview**. Under
**Savings package**, expand **Conditional package illustration** and keep
**Mid** and **Steady state** selected. Show the target margins and expand the
production rightsizing measure to show the protected Finance dates and its
supporting evidence.

> Our proposed package uses all 15 person-days, or 16,500 francs. It models
> about 58,606 francs and 5.91 tonnes of location-based emissions savings
> per year once the measures take effect. That's 12.49 percent of modeled
> spending and 32.62 percent of modeled emissions, below both challenge
> targets. The production pilot needs Platform and Finance sign-off. The
> two submitted CSVs show the same baseline, measures and assumptions.

### 4. Recommendations and server safety

**On screen** — Open **Recommendations** in the top navigation. Set **Resource type → Servers**, search for `dr-failover`, and expand **Review server downsizing or pauses → dr-failover → Protection evidence 1**. Search for `build-agent-old` next and show **Needs review**.

> Here we can see why a low-utilization server might still need to stay online. The `dr-failover` server is marked Blocked. Ticket T-1094 says it is the emergency fallback and must keep running even if it never sees load. That protection rules out shutting it down or deleting it.
>
> `build-agent-old` needs human review. Its usage is low, but the infrastructure owner still needs to verify dependencies, job history, and restore readiness before considering a pause.

**On screen** — Clear the search, switch **Resource type → Licences**, set **Safety → Eligible**, and search for **Accounting software**. Expand the result.

> An automatic deletion workflow would need an eligible server action. This baseline has zero. This licence renewal is marked Eligible because the renewal date, notice deadline, and seat price are on record. GreenOps provides the proposed action and its supporting evidence.

**Close** — Give the team AI electricity estimate of 0.072 kWh for an
illustrative 300 text-prompt equivalents. Mention that the path to operation
starts with a monthly source refresh, Finance reconciliation and owner sign-off.

### Optional Q&A walkthroughs

#### Analyst Workspace

**On screen** — Open **Analyst Workspace**. Select `cost_facts` and paste this into **Read-only SQL**. Click **Run analysis** and show the results.

```sql
SELECT reporting_department, SUM(cost_chf) AS recorded_spend_chf
FROM cost_facts
GROUP BY reporting_department
ORDER BY recorded_spend_chf DESC NULLS LAST
```

> An analyst can write and run their own read-only SQL against the cleaned Silver data. This query totals recorded spending in Swiss francs by department and shows the departments with the highest spending first.

**On screen** — In **Ask a question**, enter “What was the recorded CHF spend by department?” Click **Draft SQL**, show the generated query in the editor, then click **Run analysis**.

> I can ask the same question in plain English. The workspace chooses a dataset and drafts SQL in the editor, where I can check or edit it before I run it.

**If drafting is unavailable** — Load **Starter investigation → Spending by department** and run it. Say, “The workspace can draft SQL from a question when the AI service is available. This built-in investigation gives us another way to run the department spending analysis.”

#### Data Explorer

**On screen** — Open **Data Explorer**. In **Data Journey**, select `licence_monthly` under **Gold tables** and point to its `contracts` input. Then select `contracts` under **Silver tables** to show `ai_subscriptions.csv` and `saas_contracts.csv` in the lineage view. Click **Inspect table** to open the cleaned Silver records.

> Data Explorer shows where the numbers come from. Gold contains the reporting tables, Silver contains the cleaned records, and Bronze contains the original exports. Here, the Gold licence table draws from Silver contracts. I can follow those contracts back to the AI subscription and SaaS contract files that supplied them. That’s how we can trace a recommendation from the dashboard back to its inputs.

## Bronze exploration demo

1. Run `python -m src.profile --data data --out outputs --docs docs` in the installed Python environment.
2. Run `npm --prefix frontend run build`, then start the combined server with `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001`.
3. Open [Data Explorer](http://127.0.0.1:8001/data-explorer) and choose **Bronze** to see the original exports, what each file contains, and full-export record counts.
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
   Change the group to **Location**. Open the emissions information panel to
   explain the Swiss operating and mixed-EU proxies used in the location-based
   estimate. Open **Coverage by workload** to show a listed gap.
2. Show the `dp-dev` finding and open **View evidence**. Compare time running
   with active time and call out the observation gap. The August AI seat
   findings provide a second example with priced inactivity by product.
3. Show **Utilization analysis**, select a chart driver to narrow the scan, and expand a resource to explain the rule and source rows. Use Gold to compare the automatic and conditional packages.
   Compare steady-state and first-year results. Show the evidence-eligible SaaS
   measures and the additional conditional proposals. Explain why incomplete
   baseline coverage leaves the official target verdict open.
4. Open **Block blanket production shutdown** and show ticket T-1029. The
   Finance closing window and weekend activity are visible in the evidence.
5. Show the two [submitted CSVs](../submission/). They match the baseline and
   conditional package at mid steady state. Close with the operationalization
   note and the team AI electricity scenario below.

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
