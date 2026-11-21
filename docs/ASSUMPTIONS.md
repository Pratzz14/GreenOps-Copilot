# Submission methodology and source audit

The baseline covers **1 September 2025 through 31 August 2026 inclusive**.
The decision date is **21 November 2026**. The model uses Europe/Zurich for
operational protection windows. The [baseline CSV](../submission/template_baseline_and_assumptions.csv)
reports the annual modeled footprint. The [measures CSV](../submission/template_measures_package.csv)
contains the nine members of the package selected for submission. Each member
has case-record references, effort, approval and timing assumptions, before and
after impacts, and all six combinations of scenario and horizon. The
organizer's original column names and row structure are preserved.

The exhibits below are for Gold run
`23d0f19319d52c5c4587001f657c9305de9b48092258a40493da72d4d9fcb3ad`.
Use the run ID and the evidence IDs in the exports to find specific
`gold.evidence` records or query `/api/v1/runs/{run_id}/evidence/{evidence_set_id}`.
CSV row references are logical records with the header at row 1. JSONL source
row references identify the original line number. Bronze bytes and source
hashes are preserved. Silver normalizes source fields, retains record lineage
and reconciles spending. Gold calculates the modeled footprint and proposals.
[Dataset provenance and SHA-256](DATA_SNAPSHOT.md) · [Source columns and units](../data/data_dictionary.md) · [API](API.md)

## Case inputs and where they enter the calculation

Sample data ALTYCA, sprintd Basel 2026. Usage and volume observations are
synthetic. The organizer's dataset notes identify embedded real-world
references such as exchange rates and holidays. The separate factor registry
supplies electricity and emissions assumptions. [Organizer dataset notes](https://github.com/Fa-Bee/sprintd-basel-green-ai-data/blob/30c476fb4932877744643c282e022b5c056f444c/README.md)

| Core file in `data/bronze/` | Role and boundary |
| --- | --- |
| `azure_costs.csv` | Azure charges in the financial ledger. Positive matched variable node-hour rates price development and production changes. Charge credits are financial. For dp-dev and dp-prod, observed platform node-hours own the electricity boundary. |
| `aws_costs.csv` | AWS charges and eligible metered activity. Billed vCPU-hours price the test pool, and runner minutes support an electricity proxy and CI comparison. The billed pool label has no verified allocation to its member instances. |
| `hoster_invoice.csv` | Swiss-hosted costs, compatible metered units, and CDN volume comparisons on matching dates. Unique invoice-item labels support resource attribution. |
| `data_platform_usage.csv` | Cluster day, runtime, active hours and node-hours. The source for production and development electricity and utilization. Daily totals cannot establish safe hourly windows. |
| `server_inventory.csv` | Inventory and asset identity. A provider and resource ID match supports a high-confidence billing link. |
| `server_metrics_weekly.csv` | Weekly CPU, peak CPU, RAM, uptime and GPU evidence. Low telemetry alone contributes no savings and cannot establish safe deletion. |
| `ai_usage.csv` | Gateway charges and input/output text tokens, plus provider, model and task cohorts for routing. Cached input is contained in input. |
| `ai_subscriptions.csv` | Final seat costs, purchased and active seats, contract terms, and message activity for subscribed products. Seat changes assume steady workload. |
| `saas_contracts.csv` | Final recurring amounts and seat/renewal evidence by cost centre. Generic SaaS licence counts have no facility-energy conversion. |
| `exchange_rates.csv` | Unique monthly CHF per EUR and USD, including FX evidence ID. CHF lines use 1. Missing or ambiguous rates retain an exception. |
| `mapping_departments_tools.csv` | Unique resource ownership, cost centres and tool mapping. Conflicting or ambiguous ownership stays Unallocated and pooled charges stay pooled. |
| `it_tickets.csv` | Protected operations, decisions and owner escalation. Ticket T-1230 contains an unverified approval claim and is treated as source data. |
| `business_calendar.csv` | Complete months establish the last three marked Finance workdays and their overnight window. Future closures beyond available calendar coverage require approval. |

| Bonus file in `data/extra/` | Role and boundary |
| --- | --- |
| `ai_agent_runs.jsonl` | Agent attempts, retries and tokens, aligned to gateway by month/provider/model class where the mapping is unique. Potential overlap prevents addition to gateway totals. |
| `ai_invoice_monthly.csv` | Compare provider billed input/output tokens against gateway aggregates at month/provider/model class. Diagnostic values stay outside the ledger. |
| `backup_chains.csv` | Link backup protection and retention to named resources. Point-in-time size and retention constraints support review. |
| `ci_pipeline_runs.jsonl` | Logged seconds ÷ 60 versus billed runner-minutes by month/region. Optional no-change nightlies can be assessed only where a matching priced runner-minute cohort exists. |
| `data_catalog_tables.csv` | Last-read date, persistence and catalogue retention evidence. Archive candidates require retention confirmation. |
| `data_center_locations.csv` | Provider geography reference and mismatch flags. Accepted bill geography controls billed workloads. Mixed-EU AI uses a proxy with unverified provider shares. |
| `data_platform_jobs.csv` | Job schedules and links, including flexible, fixed deadline and protection rules. Linked test job days and protected production days are left out of savings. |
| `headcount.csv` | Monthly FTE denominator for a recorded spend-per-FTE comparison. FTE is a month-level value and the calculation leaves financial allocations unchanged. |
| `log_volume.csv` | Ingested GB, retention settings and GB-day planning. Review policy before changing retention. |
| `m365_usage.csv` | Weekly storage GB × overlapping baseline days gives GB-days. A hardware storage proxy is planning-only because hosting, service overhead and billing overlap are unresolved. |
| `powerbi_usage.csv` | Daily refresh count, minutes, views, and quiet reports for review. Refresh minutes and fixed billed capacity-days represent different units. |
| `project_hours_monthly.csv` | Booked project hours by department and month. Diagnostic spend per booked hour leaves ledger attribution intact. |
| `projects.csv` | Validates canonical project IDs against the master. |
| `provider_monthly_report.csv` | Compare monthly reported cost against six ledger scopes. The closest cloud-plus-hoster comparison stays unresolved at about a 4% gap. |
| `web_traffic.csv` | Sampled hourly traffic expanded by sampling rate for comparison with billed CDN GB on matching dates. It carries no additive baseline impact. |

The separate Bronze template CSVs define the organizer's schema. Source
quality checks cover duplicate grain, missing and changed units, record date
coverage and unresolved financial or ownership joins. Silver automatically
collapses supported aggregate mirrors with retained lineage and holds ambiguous
gateway or hoster repeats for review. Normalize only documented currency,
time and unit conventions. Formula fields, locale and evidence IDs are
preserved in the export. [Silver normalization](../src/normalize.py) ·
[Validation rules](../src/silver_rules.py) · [Silver reconciliation](../src/reconciliation.py)

## Baseline equations and controls

**Recorded CHF** = sum of each accepted, in-window, eligible original currency
charge × its month and currency CHF FX. Final contract versions contribute at
the grain provided, so monthly contract charges stay monthly even for annual
billing. Credit signs are preserved. For a priced Azure/AWS aggregate mirror,
Silver counts the included priced record once. Gold reconciles its included
counts and amounts against Silver.

**Imputed CHF** = missing metered quantity × median valid comparable
original-currency price per unit × target monthly FX. At least three positive
included peers must agree on source table, resource, month, billing unit,
currency and charge type. Review rows, missing FX, and unmatched price
populations stay outside the estimate. The submission uses deterministic
imputation. The optional OpenAI-assisted fallback in the application is
separate and contributes no value to this run. The cost template reports the
recorded subtotal and imputation separately and leaves low/high blank because
there is no fitted cost interval.

| Cost stream | Recorded CHF | Imputed CHF | Included rows | Originally missing amount | Review or quarantined |
| --- | ---: | ---: | ---: | ---: | ---: |
| Azure and AWS cloud invoices | 255,635.44 | 5,386.28 | 4,493 | 98 | 0 |
| Swiss hoster | 18,596.19 | 356.22 | 1,062 | 16 | 6 |
| AI gateway | 39,314.21 | — | 29,296 | 0 | 174 |
| AI subscriptions | 35,767.78 | — | 156 | 0 | 0 |
| SaaS contracts | 114,157.87 | — | 660 | 0 | 0 |
| **Total** | **463,471.49** | **5,742.50** | **35,667** | **114** | **180** |

Counts cover dated Gold reporting buckets and exclude out-of-window rows.
There were zero missing-FX rows in those buckets. Originally missing amounts
include amounts Gold later imputed. Rounding above is for display. Gold's
reported mid cost is **CHF 469,213.99**.

**Facility kWh** = supported activity × the matched scenario intensity × PUE
when the intensity is IT-only. Use gateway (input + output) ÷ 1,000 blocks
and Final subscription messages directly with their facility-side factors,
with no extra PUE. Calculate workload-month energy before summing. For the
platform, accepted observed node-hours replace matching Azure node-hour
energy activity. The invoice still supplies financial costs and eligible
rates. Missing source days or uncertain units reduce coverage. Capacity-days,
plain network GB and M365 storage are tracked separately as planning-only
estimates. Providers can verify metered electricity and operating profiles.

**Location-based kg CO₂e** = sum of supported workload-month facility kWh ×
applicable scenario grid factor. Germany and Ireland are direct CO₂ references.
The Swiss estimate uses operating CO₂e including imports. Mixed-EU text AI
uses generation CO₂e. As a result, the organizer's CO₂ column carries modeled
CO₂e with the mixed scope disclosed. No market-based series or growth forecast
was calculated. Their optional numeric fields remain empty.

| Matched location | Mid facility kWh | Mid location-based kg CO₂e |
| --- | ---: | ---: |
| Germany / Frankfurt | 37,234.08 | 12,287.25 |
| Ireland / Dublin | 4,708.97 | 931.43 |
| Switzerland / Zurich | 80,800.64 | 3,959.23 |
| Mixed EU, qualifying AI | 5,317.62 | 949.06 |
| **Modeled subtotal** | **128,061.32** | **18,126.97** |

The energy cases are **46,725.28 / 128,061.32 / 291,080.64 kWh**. The
corresponding emissions cases are **5,334.39 / 18,126.97 / 50,940.22 kg CO₂e**.
These are paired planning scenarios. A low-case saving and a high-case
baseline describe different assumptions and cannot be combined. Unknown
impact records stay unknown. Explicit zero trading effects in a licence
measure reflect the unchanged-workload assumption.

## External factors and scenario interpretation

All factor values below are the exact published model inputs. They are
documented estimates or benchmark-anchored assumptions. The listed sources
describe the benchmark or underlying data boundary. The current report or site
may have newer values. [Versioned factor registry](../src/factors.py)

| Factor | Unit | Low / mid / high | Derivation, scope and source |
| --- | --- | --- | --- |
| German consumption grid | kg CO₂/kWh | 0.297 / 0.330 / 0.363 | March 2026 UBA publication, 2025 provisional domestic consumption with electricity trade balance. Mid 330 g/kWh ÷ 1,000, endpoints ±10%. [UBA report](https://www.umweltbundesamt.de/system/files/medien/11850/publikationen/2026-03/16_2026_CC.pdf) |
| Irish consumption grid | kg CO₂/kWh | 0.17802 / 0.1978 / 0.21758 | SEAI 2025 provisional factor in the published run, 197.8 g/kWh ÷ 1,000, endpoints ±10%. Domestic losses are in scope and emissions outside Ireland are excluded in the source. [SEAI electricity conversion factors](https://www.seai.ie/data-and-insights/seai-statistics/conversion-factors) |
| Swiss operating consumption grid | kg CO₂e/kWh | 0.026 / 0.049 / 0.084 | Domestic and imported operating components for 2024, provisional 2025, and 2022, respectively. [VSE results, slide 2](https://www.strom.ch/system/files/media/documents/20260115-ds-teneur-en-co2-du-mix-electrique-suisse.pdf) |
| Swiss lifecycle context | kg CO₂e/kWh | 0.057 / 0.090 / 0.135 | Same scenario years, including upstream emissions. Context only. Direct CO₂ including imports is unresolved. [VSE results, slide 2](https://www.strom.ch/system/files/media/documents/20260115-ds-teneur-en-co2-du-mix-electrique-suisse.pdf) |
| Mixed EU AI generation | kg CO₂e/kWh | 0.16062687 / 0.1784743 / 0.19632173 | EEA 2025 estimated EU generation intensity in the run, endpoints ±10%. Provider-specific routes and country shares are unknown. [EEA intensity series](https://www.eea.europa.eu/en/analysis/indicators/greenhouse-gas-emission-intensity-of-1) |
| vCPU and vCore | IT kWh/allocated hour | 0.002 / 0.005 / 0.010 | Assume 2/5/10 W per allocated vCPU or vCore, then divide by 1,000. Hardware, packing and SKU are unknown. [SPECpower Dell benchmark](https://www.spec.org/power_ssj2008/results/res2025q1/power_ssj2008-20250310-01503.html) |
| Platform node | IT kWh/node-hour | 0.164 / 0.350 / 0.650 | Assume 164/350/650 W per node. Idle and partial-load points anchor the power scale, while actual cluster hardware is unknown. [SPECpower Dell benchmark](https://www.spec.org/power_ssj2008/results/res2025q1/power_ssj2008-20250310-01503.html) |
| Build runner | IT kWh/runner-hour | 0.004 / 0.020 / 0.080 | Assume 2/4/8 vCPUs × corresponding vCPU factor. Billed minutes ÷ 60. [SPECpower Dell benchmark](https://www.spec.org/power_ssj2008/results/res2025q1/power_ssj2008-20250310-01503.html) |
| GPU including host allocation | IT kWh/GPU-hour | 0.15 / 0.40 / 0.70 | Unknown average accelerator load and host share. Board power bounds inform the assumptions. [NVIDIA H100 data sheet](https://resources.nvidia.com/en-us-gpu-resources/h100-datasheet-24306?download=1) |
| Persistent storage | IT kWh/GB-day | 0.00000648 / 0.00001944 / 0.0000648 | 5.4 W × 24 h ÷ 20,000 GB ÷ 1,000, then × 1/3/10 for replicas, utilization and storage overhead. [Seagate Exos X20 data sheet](https://www.seagate.com/content/dam/seagate/migrated-assets/www-content/datasheets/pdfs/exos-x20-channel-DS2080-2111US-en_CA.pdf) |
| Gateway text token blocks | facility kWh/1,000 tokens | 0.00012 / 0.00048 / 0.0024 | 0.24 Wh per Gemini text prompt ÷ 1,000 × 1,000/500 assumed tokens. Endpoints use 0.25× and 5× for model and length variation. [Google measurement study](https://arxiv.org/abs/2508.15734) |
| AI subscription message | facility kWh/message | 0.00006 / 0.00024 / 0.0012 | Treat a message as a text prompt and convert 0.24 Wh to kWh. Endpoints use 0.25× and 5×. [Google measurement study](https://arxiv.org/abs/2508.15734) |
| PUE | facility/IT energy ratio | 1.09 / 1.35 / 1.54 | Google fleet and industry reference points anchor low/high. Mid is a planning assumption. Apply once to IT-only factors. [Google data center efficiency](https://www.datacenters.google/efficiency/) |
| Power BI planning capacity | assumed vCores | 4 / 8 / 16 | Capacity-days × 24 × scenario vCores × vCore intensity × PUE. Illustrative only. [Microsoft Fabric capacity documentation](https://learn.microsoft.com/en-us/fabric/enterprise/licenses#capacity) |
| Network transmission planning | kWh/GB | 0.0065 / 0.0065 / 0.0065 | UK fixed-network attribution proxy for billed GB, excluded from the baseline. Hosting and possible overlap are unresolved. [Ofcom network study](https://www.ofcom.org.uk/siteassets/resources/documents/research-and-data/technology-research/2022/carbon-emissions-of-streaming-and-digital-terrestrial-television-3.pdf) |

## Utilization rules, recurrence and operational approval

The dashboard highlights evidence in the selected period. The recurring
recommendation screen checks persistence on the full baseline. Gold measures
bind action-specific evidence, pricing, constraints and responsibility.

| Resource | Dashboard scan | Recurring recommendation rule |
| --- | --- | --- |
| Data cluster | ≥14 distinct valid days and ≥70% of selected days. Flag when total active ÷ total runtime ≤20% with positive runtime. | A complete Monday-start week needs ≥5 distinct valid days, positive runtime and ≤20% active/runtime. Require ≥70% observed-week coverage. |
| Server | ≥3 complete observed weeks and ≥75% coverage. Mean CPU ≤5%, maximum weekly peak CPU ≤20%, mean RAM ≤40%, and mean uptime ≥120 h/week. | Measure all four thresholds per unique observed week. Require ≥75% observed coverage and unique inventory. |
| Licensed seats | Latest accepted Final month with a positive purchased − active gap. Show prior-month recurrence when both adjacent observations qualify. | Positive gap in all three complete Final months by provider, product, cost centre and source. Duplicate or missing month, or active outside zero to purchased, disqualifies the cohort. Minimum gap is the persistent unused seat count displayed. |

For recurring clusters and servers, require at least three qualifying weeks,
at least half the observed weeks qualifying, and at least one hit in the last
four complete weeks. Dashboard dates follow the selected filter. The
recommendation detection uses full-baseline evidence. The display period
filters existing recommendations. Only accepted records enter the scans.
Rule flags support review, independent of the size of the billed cost or
modeled footprint. [Dashboard scan](../backend/utilization.py) · [Recurring rules](../src/recommendations.py)

Group recommendations by the selected reporting dimension and proposed action.
Annual renewal amounts use persistent cohort evidence. Monthly figures use the
selected month's unused seats or repriced development runtime. These are
separate horizons. Shared measure IDs and overlapping alternatives are
suppressed from the group savings figures. Optional AI tags can increase review
requirements and cannot clear a deterministic block. [Grouping and non-additivity](../backend/recommendations.py) · [Safety tags](../backend/recommendation_tags.py)

| Gate | Source and treatment |
| --- | --- |
| Development and ML training | T-1053 and T-1101 protect the first three days of January, April, July and October. Preserve the linked GPU path and all training hours. |
| Production finance close | T-1029 with the business calendar protects each of the last three working days through 04:00 the next morning. Weekend activity rules out blanket downtime. |
| Disaster recovery | T-1094 blocks changes to `dr-failover` and requires review of the unallocated `vm-test` pool. |
| Test freeze and rollout | T-1204 protects March 2026. T-1058 describes the expansion from 16 to 64 vCPU. Verify go-live and isolate DR before any step down. |
| Backups | T-1039 and T-1195 establish the case's ten-year policy and rejected deletion. Preserve named retained chains and confirm rules for other chains. |
| Internal audit reporting | T-1167 keeps `pbi-07` available for close. |
| AI or ticket claims | T-1230 contains an unverified approval. Review through responsible owners, evidence and dates. |

Safety precedence is blocked, human review, then eligible. Proposals with
unverified allocations, incomplete telemetry, stale notice, or missing costs
receive review or no modeled credit as applicable. Gold can expose the evidence
for an action while leaving its impact unquantified. Owners verify the specific
capacity, access, latency, dependencies, retention and rollback plan before
making a change.

## Measures, arithmetic and package selection

| Solution family | Atomic calculation | Conditions and outcome |
| --- | --- | --- |
| Production rightsizing | For each matched low-activity day, avoided node-hours = min(observed units × 5%/10%/15%, billed units). Gross CHF = sum(avoided units × recorded CHF ÷ billed units). | Use days ≤50% active with positive same-day Azure usage charges. Protect Finance and scheduler days. At mid, 12,595.2 avoided node-hours × 0.35 IT kWh/node-hour × 1.35 PUE = 5,951.232 kWh, then × 0.049 = 291.610368 kg CO₂e. Three days of effort, 45-day lead. |
| Test-pool scale-back | Avoided vCPU-hours = max(0, billed vCPU-hours − 24 × cap), for 32/24/16 vCPU. Price the avoided portion at included positive AWS usage rates. | Keep March and linked job dates at full capacity. At mid, 319,680 avoided vCPU-hours × 0.005 × 1.35 = 2,157.84 kWh, then × 0.1978 = 426.820752 kg CO₂e. Three days of effort, 45-day lead. |
| Development schedule | Remaining runtime = min(runtime, max(16/12/8 h, active + 2 h)) outside training. Avoided node-hours = observed node-hours × fraction of runtime removed. CHF depends on eligible same-day matched bills and is capped by billed units. | Missing active observation or protected training keeps the full runtime. At mid, 33,312 avoided node-hours × 0.35 × 1.35 = 15,739.92 kWh, then × 0.330 = 5,194.1736 kg CO₂e. Three days of effort, 30-day lead. |
| SaaS seat rightsizing | For each centre, take the minimum monthly purchased − active gap. Multiply by August price × August FX × 12. | One Final eligible record for each month June–August, positive history, confirm contractual floor, end date − notice days, and effective day after term end. Four SaaS cohorts in the package. One day each, zero energy and emissions savings. |
| AI seats and Claude pricing | For each centre, reclaim August purchased − highest active seats across June–August. Multiply by August price × August FX × 12. Claude retained Standard seats add USD 5 per seat/month × August FX × 12 under the assumed annual offer. | Keep approved and pending demand. Verify renewal and quote, and approve prepayment. Microsoft Copilot and Claude in the package. One day each, zero electricity and emissions savings. [Claude pricing](https://claude.com/pricing) |

Gold also evaluates alternatives and findings beyond the nine submitted rows.
The Zurich development pilot moves routine operation with a 20%/10%/0% premium
on retained variable spend while Frankfurt training remains. It includes five
person-days and CHF 500 cash, takes 60 days, needs a like-for-like quote and
cannot be combined with standalone pauses or on-demand GPU savings. The GPU
scheduling hypothesis tests 16/12/8 h outside training with unresolved meter
attribution. The routing model compares cohorts with at least 100 requests
within the same task and model class and mean token lengths within 20%.
Its 10%/25%/50% shares are pilot sensitivities and quality needs testing.
CI can model optional no-change nightlies only where billed comparable
runner-minutes and accepted usage support it. Flexible jobs, recurring agent
attempts, quiet refreshes, stale catalogue tables, logs and backup retention
may warrant review. Activity observations alone do not establish savings.
[All proposal implementations](../src/gold_measures.py)

For each scenario, net CHF = gross avoided CHF − new recurring CHF. Avoided
electricity = before facility kWh − after facility kWh. Avoided emissions =
before location kg − after location kg. First-year contributions multiply
steady-state effects by max(0, days remaining after the later of effective or
decision date) ÷ days in the first 12 months. This assumes uniform savings from
the effective day and does not model seasonality. Implementation = person-days
× CHF 1,100 + one-time cash. The cap is CHF 16,500. Apply it once against all
distinct package members.

Gold ranks admissible packages without overlap and enforces dependencies.
Forty fully quantified measures qualified for automatic selection and 49 were
available for the conditional comparison. Each candidate needs complete
CHF, energy and emissions components for all six displayed cases.
For this provisional case it maximizes the weaker attainment ratio against
25% cost reduction and 40% emissions reduction at mid steady state, breaking
ties by higher emissions savings, higher CHF savings and lower
implementation cost in package optimization. Export chooses the better-rated
published package under the cap and prefers the automatic package on an
exact attainment tie. Additional ordering is in the code. Coverage is too
incomplete for a definitive target verdict. The automatic package conservatively
models CHF 18,073.22 annual savings, zero credited emissions savings, at the
same implementation cap. The submitted package includes human-review actions.
[Optimizer](../src/optimizer.py) · [Export selection](../src/exports.py)

| Submitted package | Assumptions | Net CHF | Avoided kWh | Avoided kg CO₂e |
| --- | --- | ---: | ---: | ---: |
| Steady state | Low | 46,493.20 | 5,653.18 | 1,307.58 |
| Steady state | Mid | 58,605.60 | 23,848.99 | 5,912.60 |
| Steady state | High | 70,718.00 | 69,279.80 | 19,013.11 |
| First 12 months | Low | 39,221.50 | 5,119.36 | 1,194.83 |
| First 12 months | Mid | 50,083.29 | 21,555.55 | 5,397.11 |
| First 12 months | High | 60,945.08 | 62,565.59 | 17,332.28 |

The mid savings equal 12.49% of modeled cost and 32.62% of modeled
location-based emissions, both below target. Full implementation is
15 person-days with zero one-time cash assumed for these nine measures.
[Target gaps and feasibility](FEASIBILITY.md)

## Regenerate and inspect

Run `python -m src.exports` from the installed project after publishing Gold.
The command prints the content-versioned export directory. The official
submission API serves the same enriched files. The immutable Gold database
remains the reference for numeric results and source evidence. The optional
notes report explicit assumptions, context and unknowns in the two
organizer text columns, so the template's numeric fields remain parseable.
