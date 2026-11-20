# Data map and exploratory analysis

Snapshot: `06b90d3d68b5e91f133f33511a8ee47b526447b9955ec8bd4469d12dc8990c0f` · Report: `2d14365dbbad2438fc6991914aa2da93cdf4a938928f6e2062cf49c34cd6e27f`

Baseline: 2025-09-01 through 2026-08-31 inclusive. All 13 core sources parsed successfully.

- No records removed, normalized, allocated or financially reconciled.
- Pool membership gpu-ml → gpu-ml-01 and vm-test → test/QA/UAT/DR instances needs Phase 3 evidence; no pooled invoice is multiplied across instances.
- AI gateway reported costs are not additional provider invoices. No energy, carbon or savings factors are supplied.
- Free text is untrusted evidence, never instructions. Safety decisions require the later safety phase.
- Issue counts count findings/groups, not disjoint bad rows. A row may have several issues.
- Source rows are logical CSV record numbers including header, not physical text line numbers.

## Source catalog

| Source | Role | Rows (full / baseline) | Columns | Exact duplicate excess |
|---|---|---:|---:|---:|
| azure_costs.csv | Provider charges | 4687 / 2536 | 12 | 7 |
| aws_costs.csv | Provider charges | 3822 / 2067 | 16 | 5 |
| hoster_invoice.csv | Provider charges | 2002 / 1084 | 10 | 3 |
| data_platform_usage.csv | Monitoring and utilization | 1333 / 719 | 8 | 2 |
| server_inventory.csv | Asset inventory | 53 / 53 | 18 | 0 |
| server_metrics_weekly.csv | Monitoring and utilization | 3161 / 2213 | 8 | 0 |
| ai_usage.csv | Gateway usage with reported costs | 52856 / 29470 | 14 | 87 |
| ai_subscriptions.csv | Contracts with activity observations | 261 / 169 | 14 | 0 |
| saas_contracts.csv | Contracts with activity observations | 1331 / 729 | 13 | 0 |
| mapping_departments_tools.csv | Master data | 90 / 90 | 9 | 0 |
| exchange_rates.csv | Master data | 23 / 12 | 3 | 0 |
| it_tickets.csv | Operational evidence | 289 / 165 | 7 | 0 |
| business_calendar.csv | Operational evidence | 675 / 365 | 5 | 0 |

## azure_costs.csv

Role: Provider charges. Candidate key: Date, ResourceId, ChargeType, UnitOfMeasure, BillingCurrency. SHA-256: `f0adf53ef95b20958027820e93f3ae9e36426a86f5a22f5ccbc5481340e9318b`.

### Full export profile

All records in the export.

Rows: 4687; missing cells: 90; expected optional/non-applicable blanks: 6020; exact duplicate excess: 7; key collision groups: 7.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| Date | date / date | 0 / 0 / 0 | 2024-11-01 | 2026-09-06 |
| ResourceId | text / text | 0 / 0 / 0 | None | None |
| ServiceName | text / text | 0 / 0 / 0 | None | None |
| ResourceLocation | text / text | 0 / 0 / 0 | None | None |
| Quantity | number / number | 0 / 0 / 0 | 0.0 | 28422.46 |
| UnitOfMeasure | text / text | 0 / 0 / 0 | None | None |
| CostInBillingCurrency | number / number | 87 / 87 / 0 | -2400.0 | 286.56 |
| BillingCurrency | text / text | 0 / 0 / 0 | None | None |
| ChargeType | text / text | 0 / 0 / 0 | None | None |
| Tags | json / json | 0 / 0 / 0 | None | None |
| AvgCpuPercent | number / number | 3 / 1340 / 0 | 0.0 | 100.0 |
| Notes | text / text | 0 / 4683 / 0 | None | None |

Categories: `{"BillingCurrency": {"CHF": 3355, "EUR": 1332}, "ChargeType": {"Credit": 3, "Usage": 4684}, "UnitOfMeasure": {"GB-day": 669, "GPU-hour": 663, "capacity-day": 668, "node-hour": 1342, "vCPU-hour": 671, "vCore-hour": 674}}`

Amount/credit counts (not cost totals): `[{"currency": "CHF", "charge_type": "Credit", "rows": 3, "missing": 0, "negative_count": 3, "negative_rows": [2111, 3359, 4207]}, {"currency": "CHF", "charge_type": "Usage", "rows": 3352, "missing": 56, "negative_count": 0, "negative_rows": []}, {"currency": "EUR", "charge_type": "Usage", "rows": 1332, "missing": 31, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[{"column": "Tags.project", "proposed": "P-001", "variants": {"P-001": 239, "P001": 39, "p-001": 8}}, {"column": "Tags.project", "proposed": "P-003", "variants": {"P-003": 555, "P003": 60, "p-003": 39}}, {"column": "Tags.project", "proposed": "P-004", "variants": {"P-004": 321, "P004": 42, "p-004": 20}}, {"column": "Tags.project", "proposed": "P-005", "variants": {"P-005": 197, "P005": 26, "p-005": 11}}, {"column": "Tags.project", "proposed": "P-006", "variants": {"P-006": 188, "P006": 13, "p-006": 10}}, {"column": "Tags.project", "proposed": "P-007", "variants": {"P-007": 143, "P007": 16, "p-007": 11}}, {"column": "Tags.project", "proposed": "P-009", "variants": {"P-009": 62, "P009": 9, "p-009": 2}}, {"column": "Tags.project", "proposed": "P-015", "variants": {"P-015": 465, "P015": 40, "p-015": 32}}, {"column": "Tags.project", "proposed": "unknown", "variants": {"": 2139}}]`

Azure JSON diagnostics: `{"empty_objects": 703, "absent_keys": {"department": 703, "tool": 703, "project": 703, "environment": 703}, "blank_values": {"project": 1436, "environment": 600}, "invalid_rows": []}`

Coverage: `{"minimum": "2024-11-01", "maximum": "2026-09-06", "distinct_periods": 675, "cadence": "daily"}`
- /subscriptions/0000/resourcegroups/rg-db/providers/Database/db-fin: observation gap; lifetime/expected activity unverified; internal gaps: 2025-12-03, 2026-02-01, 2026-09-03; baseline absent periods: 2025-12-03, 2026-02-01.
- /subscriptions/0000/resourcegroups/rg-dp/providers/DataPlatform/dp-dev: observation gap; lifetime/expected activity unverified; internal gaps: 2025-03-22, 2025-03-25, 2025-05-30, 2025-07-17, 2025-11-02, 2026-02-12, 2026-08-09; baseline absent periods: 2025-11-02, 2026-02-12, 2026-08-09.
- /subscriptions/0000/resourcegroups/rg-dp/providers/DataPlatform/dp-prod: observation gap; lifetime/expected activity unverified; internal gaps: 2025-03-16, 2025-06-02, 2025-11-12, 2026-08-30; baseline absent periods: 2025-11-12, 2026-08-30.
- /subscriptions/0000/resourcegroups/rg-dp/providers/Storage/dp-storage: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-05, 2025-07-20, 2025-09-04, 2025-10-20, 2026-05-21, 2026-06-18, 2026-08-23; baseline absent periods: 2025-09-04, 2025-10-20, 2026-05-21, 2026-06-18, 2026-08-23.
- /subscriptions/0000/resourcegroups/rg-gpu/providers/GPU-Instances/gpu-ml: observation gap; lifetime/expected activity unverified; internal gaps: 2024-12-04, 2025-01-13, 2025-01-19, 2025-02-06, 2025-05-19, 2025-05-29, 2025-07-14, 2025-08-02, 2025-11-21, 2025-12-31, 2026-04-29, 2026-06-06, 2026-06-20; baseline absent periods: 2025-11-21, 2025-12-31, 2026-04-29, 2026-06-06, 2026-06-20.
- /subscriptions/0000/resourcegroups/rg-pbi/providers/Reporting/pbi-kap: observation gap; lifetime/expected activity unverified; internal gaps: 2025-01-24, 2025-07-28, 2025-07-29, 2025-10-06, 2026-01-25, 2026-04-22, 2026-08-05, 2026-08-27; baseline absent periods: 2025-10-06, 2026-01-25, 2026-04-22, 2026-08-05, 2026-08-27.
- /subscriptions/0000/resourcegroups/rg-vm/providers/Compute/vm-app: observation gap; lifetime/expected activity unverified; internal gaps: 2025-10-05, 2025-12-12, 2026-02-22, 2026-04-02, 2026-04-14, 2026-06-04; baseline absent periods: 2025-10-05, 2025-12-12, 2026-02-22, 2026-04-02, 2026-04-14, 2026-06-04.

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 4687, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.
- Transaction month to FX → exchange_rates.csv: many-to-one; matched 4687, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Monthly EUR/USD CHF-per-unit rates; no conversion performed.

Issue categories: `{"blank_tag": 2, "business_key_collision": 7, "coverage_gap": 1, "exact_duplicate_candidate": 7, "missing_tag": 4, "missing_value": 2, "project_id_variant": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Records dated within the baseline; drafts and duplicate candidates retained.

Rows: 2536; missing cells: 58; expected optional/non-applicable blanks: 3255; exact duplicate excess: 7; key collision groups: 7.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| Date | date / date | 0 / 0 / 0 | 2025-09-01 | 2026-08-31 |
| ResourceId | text / text | 0 / 0 / 0 | None | None |
| ServiceName | text / text | 0 / 0 / 0 | None | None |
| ResourceLocation | text / text | 0 / 0 / 0 | None | None |
| Quantity | number / number | 0 / 0 / 0 | 0.0 | 28204.24 |
| UnitOfMeasure | text / text | 0 / 0 / 0 | None | None |
| CostInBillingCurrency | number / number | 56 / 56 / 0 | -2400.0 | 286.56 |
| BillingCurrency | text / text | 0 / 0 / 0 | None | None |
| ChargeType | text / text | 0 / 0 / 0 | None | None |
| Tags | json / json | 0 / 0 / 0 | None | None |
| AvgCpuPercent | number / number | 2 / 724 / 0 | 0.0 | 100.0 |
| Notes | text / text | 0 / 2533 / 0 | None | None |

Categories: `{"BillingCurrency": {"CHF": 1812, "EUR": 724}, "ChargeType": {"Credit": 2, "Usage": 2534}, "UnitOfMeasure": {"GB-day": 361, "GPU-hour": 361, "capacity-day": 361, "node-hour": 728, "vCPU-hour": 360, "vCore-hour": 365}}`

Amount/credit counts (not cost totals): `[{"currency": "CHF", "charge_type": "Credit", "rows": 2, "missing": 0, "negative_count": 2, "negative_rows": [3359, 4207]}, {"currency": "CHF", "charge_type": "Usage", "rows": 1810, "missing": 37, "negative_count": 0, "negative_rows": []}, {"currency": "EUR", "charge_type": "Usage", "rows": 724, "missing": 19, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[{"column": "Tags.project", "proposed": "P-001", "variants": {"P-001": 131, "P001": 19, "p-001": 6}}, {"column": "Tags.project", "proposed": "P-003", "variants": {"P-003": 316, "P003": 29, "p-003": 22}}, {"column": "Tags.project", "proposed": "P-004", "variants": {"P-004": 172, "P004": 27, "p-004": 9}}, {"column": "Tags.project", "proposed": "P-005", "variants": {"P-005": 111, "P005": 10, "p-005": 8}}, {"column": "Tags.project", "proposed": "P-006", "variants": {"P-006": 103, "P006": 7, "p-006": 6}}, {"column": "Tags.project", "proposed": "P-007", "variants": {"P-007": 75, "P007": 9, "p-007": 6}}, {"column": "Tags.project", "proposed": "P-009", "variants": {"P-009": 32, "P009": 5, "p-009": 1}}, {"column": "Tags.project", "proposed": "P-015", "variants": {"P-015": 233, "P015": 23, "p-015": 22}}, {"column": "Tags.project", "proposed": "unknown", "variants": {"": 1154}}]`

Azure JSON diagnostics: `{"empty_objects": 379, "absent_keys": {"department": 379, "tool": 379, "project": 379, "environment": 379}, "blank_values": {"project": 775, "environment": 314}, "invalid_rows": []}`

Coverage: `{"minimum": "2025-09-01", "maximum": "2026-08-31", "distinct_periods": 365, "cadence": "daily"}`
- /subscriptions/0000/resourcegroups/rg-db/providers/Database/db-fin: observation gap; lifetime/expected activity unverified; internal gaps: 2025-12-03, 2026-02-01; baseline absent periods: 2025-12-03, 2026-02-01.
- /subscriptions/0000/resourcegroups/rg-dp/providers/DataPlatform/dp-dev: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-02, 2026-02-12, 2026-08-09; baseline absent periods: 2025-11-02, 2026-02-12, 2026-08-09.
- /subscriptions/0000/resourcegroups/rg-dp/providers/DataPlatform/dp-prod: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-12, 2026-08-30; baseline absent periods: 2025-11-12, 2026-08-30.
- /subscriptions/0000/resourcegroups/rg-dp/providers/Storage/dp-storage: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-04, 2025-10-20, 2026-05-21, 2026-06-18, 2026-08-23; baseline absent periods: 2025-09-04, 2025-10-20, 2026-05-21, 2026-06-18, 2026-08-23.
- /subscriptions/0000/resourcegroups/rg-gpu/providers/GPU-Instances/gpu-ml: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-21, 2025-12-31, 2026-04-29, 2026-06-06, 2026-06-20; baseline absent periods: 2025-11-21, 2025-12-31, 2026-04-29, 2026-06-06, 2026-06-20.
- /subscriptions/0000/resourcegroups/rg-pbi/providers/Reporting/pbi-kap: observation gap; lifetime/expected activity unverified; internal gaps: 2025-10-06, 2026-01-25, 2026-04-22, 2026-08-05, 2026-08-27; baseline absent periods: 2025-10-06, 2026-01-25, 2026-04-22, 2026-08-05, 2026-08-27.
- /subscriptions/0000/resourcegroups/rg-vm/providers/Compute/vm-app: observation gap; lifetime/expected activity unverified; internal gaps: 2025-10-05, 2025-12-12, 2026-02-22, 2026-04-02, 2026-04-14, 2026-06-04; baseline absent periods: 2025-10-05, 2025-12-12, 2026-02-22, 2026-04-02, 2026-04-14, 2026-06-04.

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 2536, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.
- Transaction month to FX → exchange_rates.csv: many-to-one; matched 2536, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Monthly EUR/USD CHF-per-unit rates; no conversion performed.

Issue categories: `{"blank_tag": 2, "business_key_collision": 7, "coverage_gap": 1, "exact_duplicate_candidate": 7, "missing_tag": 4, "missing_value": 2, "project_id_variant": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | azure_costs.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | Date | Parse documented date format; retain raw value. |
| resource_id | ResourceId | Azure path / AWS ARN suffix candidate; otherwise direct. Instance IDs are not pooled billing IDs. |
| provider | constant Azure | Direct source value; no transformation in Phase 2. |
| cost_center | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| department | Tags.department | Direct source value; no transformation in Phase 2. |
| tool | Tags.tool | Direct source value; no transformation in Phase 2. |
| region | ResourceLocation | Direct source value; no transformation in Phase 2. |
| quantity | Quantity | Direct source value; no transformation in Phase 2. |
| unit | UnitOfMeasure | Direct source value; no transformation in Phase 2. |
| amount_original | CostInBillingCurrency | Direct source value; no transformation in Phase 2. |
| currency | BillingCurrency | Direct source value; no transformation in Phase 2. |
| fx_rate | exchange_rates.csv | Phase 3: CHF=1; EUR/USD monthly CHF per foreign unit; missing rate → null. |
| cost_chf | derived in Phase 3 | Reported CHF for gateway/hoster; other currencies require monthly FX. No financial totals in Phase 2. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## aws_costs.csv

Role: Provider charges. Candidate key: line_item_usage_start_date, line_item_resource_id, line_item_line_item_type, pricing_unit, line_item_currency_code. SHA-256: `8eaf5d155cd8091ab208a1a385a4e52f166f2ad5f215362dd6ce2925129de39d`.

### Full export profile

All records in the export.

Rows: 3822; missing cells: 4008; expected optional/non-applicable blanks: 8989; exact duplicate excess: 5; key collision groups: 5.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| line_item_usage_start_date | timestamp / timestamp | 0 / 0 / 0 | 2024-11-01 | 2026-09-06 |
| line_item_resource_id | text / text | 0 / 0 / 0 | None | None |
| product_servicecode | text / text | 0 / 0 / 0 | None | None |
| product_region | text / text | 0 / 0 / 0 | None | None |
| line_item_usage_amount | number / number | 0 / 0 / 0 | 1.0 | 76970.47 |
| pricing_unit | text / text | 0 / 0 / 0 | None | None |
| line_item_unblended_cost | number / number | 87 / 87 / 0 | 0.243363 | 1164.294955 |
| line_item_currency_code | text / text | 0 / 0 / 0 | None | None |
| line_item_line_item_type | text / text | 0 / 0 / 0 | None | None |
| resource_tags_user_department | text / text | 959 / 959 / 0 | None | None |
| resource_tags_user_tool | text / text | 598 / 598 / 0 | None | None |
| resource_tags_user_project | text / text | 1357 / 1357 / 0 | None | None |
| resource_tags_user_environment | text / text | 552 / 552 / 0 | None | None |
| avg_cpu_utilization | number / number | 455 / 3149 / 0 | 1.1 | 82.9 |
| object_requests | number / number | 0 / 2489 / 0 | 0.0 | 5.0 |
| line_item_description | text / text | 0 / 3806 / 0 | None | None |

Categories: `{"line_item_currency_code": {"USD": 3822}, "line_item_line_item_type": {"Fee": 23, "Usage": 3799}, "pricing_unit": {"GB": 669, "GB-day": 1333, "month": 23, "runner-minute": 669, "vCPU-hour": 1128}}`

Amount/credit counts (not cost totals): `[{"currency": "USD", "charge_type": "Fee", "rows": 23, "missing": 1, "negative_count": 0, "negative_rows": []}, {"currency": "USD", "charge_type": "Usage", "rows": 3799, "missing": 86, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[{"column": "resource_tags_user_project", "proposed": "P-001", "variants": {"P-001": 467, "P001": 42, "p-001": 32}}, {"column": "resource_tags_user_project", "proposed": "P-002", "variants": {"P-002": 437, "P002": 46, "p-002": 30}}, {"column": "resource_tags_user_project", "proposed": "P-003", "variants": {"P-003": 66, "P003": 9, "p-003": 5}}, {"column": "resource_tags_user_project", "proposed": "P-004", "variants": {"P-004": 255, "P004": 25, "p-004": 12}}, {"column": "resource_tags_user_project", "proposed": "P-014", "variants": {"P-014": 138, "P014": 10, "p-014": 8}}, {"column": "resource_tags_user_project", "proposed": "P-015", "variants": {"P-015": 746, "P015": 91, "p-015": 46}}, {"column": "resource_tags_user_project", "proposed": "unknown", "variants": {"": 1357}}]`

Coverage: `{"minimum": "2024-11-01", "maximum": "2026-09-06", "distinct_periods": 675, "cadence": "daily"}`
- arn:aws:build-service:eu:0000:cicd: observation gap; lifetime/expected activity unverified; internal gaps: 2024-12-05, 2025-05-17, 2026-01-01, 2026-01-06, 2026-01-31, 2026-03-04, 2026-07-18; baseline absent periods: 2026-01-01, 2026-01-06, 2026-01-31, 2026-03-04, 2026-07-18.
- arn:aws:compute:eu:0000:sandbox: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-02, 2024-11-03, 2024-11-09, 2024-11-10, 2024-11-16, 2024-11-17, 2024-11-23, 2024-11-24, 2024-11-30, 2024-12-01, 2024-12-07, 2024-12-08, 2024-12-11, 2024-12-13, 2024-12-14, 2024-12-15, 2024-12-21, 2024-12-22, 2024-12-25, 2024-12-26, 2024-12-28, 2024-12-29, 2025-01-01, 2025-01-04, 2025-01-05, 2025-01-11, 2025-01-12, 2025-01-18, 2025-01-19, 2025-01-25, 2025-01-26, 2025-02-01, 2025-02-02, 2025-02-08, 2025-02-09, 2025-02-15, 2025-02-16, 2025-02-22, 2025-02-23, 2025-03-01, 2025-03-02, 2025-03-08, 2025-03-09, 2025-03-15, 2025-03-16, 2025-03-22, 2025-03-23, 2025-03-29, 2025-03-30, 2025-04-05, 2025-04-06, 2025-04-12, 2025-04-13, 2025-04-18, 2025-04-19, 2025-04-20, 2025-04-21, 2025-04-26, 2025-04-27, 2025-05-01, 2025-05-03, 2025-05-04, 2025-05-10, 2025-05-11, 2025-05-17, 2025-05-18, 2025-05-24, 2025-05-25, 2025-05-29, 2025-05-31, 2025-06-01, 2025-06-07, 2025-06-08, 2025-06-09, 2025-06-14, 2025-06-15, 2025-06-21, 2025-06-22, 2025-06-28, 2025-06-29, 2025-07-05, 2025-07-06, 2025-07-12, 2025-07-13, 2025-07-19, 2025-07-20, 2025-07-22, 2025-07-26, 2025-07-27, 2025-08-01, 2025-08-02, 2025-08-03, 2025-08-09, 2025-08-10, 2025-08-16, 2025-08-17, 2025-08-23, 2025-08-24, 2025-08-30, 2025-08-31, 2025-09-06, 2025-09-07, 2025-09-13, 2025-09-14, 2025-09-20, 2025-09-21, 2025-09-27, 2025-09-28, 2025-10-04, 2025-10-05, 2025-10-11, 2025-10-12, 2025-10-18, 2025-10-19, 2025-10-25, 2025-10-26, 2025-11-01, 2025-11-02, 2025-11-08, 2025-11-09, 2025-11-15, 2025-11-16, 2025-11-22, 2025-11-23, 2025-11-29, 2025-11-30, 2025-12-06, 2025-12-07, 2025-12-10, 2025-12-13, 2025-12-14, 2025-12-20, 2025-12-21, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2026-01-01, 2026-01-03, 2026-01-04, 2026-01-10, 2026-01-11, 2026-01-17, 2026-01-18, 2026-01-24, 2026-01-25, 2026-01-31, 2026-02-01, 2026-02-07, 2026-02-08, 2026-02-14, 2026-02-15, 2026-02-21, 2026-02-22, 2026-02-28, 2026-03-01, 2026-03-07, 2026-03-08, 2026-03-10, 2026-03-14, 2026-03-15, 2026-03-21, 2026-03-22, 2026-03-28, 2026-03-29, 2026-04-03, 2026-04-04, 2026-04-05, 2026-04-06, 2026-04-11, 2026-04-12, 2026-04-18, 2026-04-19, 2026-04-25, 2026-04-26, 2026-04-27, 2026-04-29, 2026-05-01, 2026-05-02, 2026-05-03, 2026-05-04, 2026-05-09, 2026-05-10, 2026-05-14, 2026-05-16, 2026-05-17, 2026-05-23, 2026-05-24, 2026-05-25, 2026-05-30, 2026-05-31, 2026-06-06, 2026-06-07, 2026-06-13, 2026-06-14, 2026-06-20, 2026-06-21, 2026-06-27, 2026-06-28, 2026-07-04, 2026-07-05, 2026-07-07, 2026-07-11, 2026-07-12, 2026-07-18, 2026-07-19, 2026-07-25, 2026-07-26, 2026-08-01, 2026-08-02, 2026-08-07, 2026-08-08, 2026-08-09, 2026-08-15, 2026-08-16, 2026-08-22, 2026-08-23, 2026-08-29, 2026-08-30; baseline absent periods: 2025-09-06, 2025-09-07, 2025-09-13, 2025-09-14, 2025-09-20, 2025-09-21, 2025-09-27, 2025-09-28, 2025-10-04, 2025-10-05, 2025-10-11, 2025-10-12, 2025-10-18, 2025-10-19, 2025-10-25, 2025-10-26, 2025-11-01, 2025-11-02, 2025-11-08, 2025-11-09, 2025-11-15, 2025-11-16, 2025-11-22, 2025-11-23, 2025-11-29, 2025-11-30, 2025-12-06, 2025-12-07, 2025-12-10, 2025-12-13, 2025-12-14, 2025-12-20, 2025-12-21, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2026-01-01, 2026-01-03, 2026-01-04, 2026-01-10, 2026-01-11, 2026-01-17, 2026-01-18, 2026-01-24, 2026-01-25, 2026-01-31, 2026-02-01, 2026-02-07, 2026-02-08, 2026-02-14, 2026-02-15, 2026-02-21, 2026-02-22, 2026-02-28, 2026-03-01, 2026-03-07, 2026-03-08, 2026-03-10, 2026-03-14, 2026-03-15, 2026-03-21, 2026-03-22, 2026-03-28, 2026-03-29, 2026-04-03, 2026-04-04, 2026-04-05, 2026-04-06, 2026-04-11, 2026-04-12, 2026-04-18, 2026-04-19, 2026-04-25, 2026-04-26, 2026-04-27, 2026-04-29, 2026-05-01, 2026-05-02, 2026-05-03, 2026-05-04, 2026-05-09, 2026-05-10, 2026-05-14, 2026-05-16, 2026-05-17, 2026-05-23, 2026-05-24, 2026-05-25, 2026-05-30, 2026-05-31, 2026-06-06, 2026-06-07, 2026-06-13, 2026-06-14, 2026-06-20, 2026-06-21, 2026-06-27, 2026-06-28, 2026-07-04, 2026-07-05, 2026-07-07, 2026-07-11, 2026-07-12, 2026-07-18, 2026-07-19, 2026-07-25, 2026-07-26, 2026-08-01, 2026-08-02, 2026-08-07, 2026-08-08, 2026-08-09, 2026-08-15, 2026-08-16, 2026-08-22, 2026-08-23, 2026-08-29, 2026-08-30.
- arn:aws:compute:eu:0000:vm-test: observation gap; lifetime/expected activity unverified; internal gaps: 2025-05-16, 2025-07-20, 2025-12-23; baseline absent periods: 2025-12-23.
- arn:aws:network:eu:0000:net-egress: observation gap; lifetime/expected activity unverified; internal gaps: 2024-12-06, 2025-07-15, 2025-10-18, 2025-11-09, 2025-12-03, 2026-01-04; baseline absent periods: 2025-10-18, 2025-11-09, 2025-12-03, 2026-01-04.
- arn:aws:storage:eu:0000:st-archive: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-17, 2025-03-13, 2025-03-22, 2025-09-12, 2025-10-05, 2025-11-02, 2025-12-26, 2025-12-29, 2026-01-01, 2026-01-04, 2026-03-21, 2026-07-29, 2026-08-10, 2026-08-16; baseline absent periods: 2025-09-12, 2025-10-05, 2025-11-02, 2025-12-26, 2025-12-29, 2026-01-01, 2026-01-04, 2026-03-21, 2026-07-29, 2026-08-10, 2026-08-16.
- arn:aws:storage:eu:0000:st-backup: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-04, 2024-11-24, 2025-01-30, 2025-04-13, 2025-06-01; baseline absent periods: none.
- arn:aws:support:eu:0000:support: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-02, 2024-11-03, 2024-11-04, 2024-11-05, 2024-11-06, 2024-11-07, 2024-11-08, 2024-11-09, 2024-11-10, 2024-11-11, 2024-11-12, 2024-11-13, 2024-11-14, 2024-11-15, 2024-11-16, 2024-11-17, 2024-11-18, 2024-11-19, 2024-11-20, 2024-11-21, 2024-11-22, 2024-11-23, 2024-11-24, 2024-11-25, 2024-11-26, 2024-11-27, 2024-11-28, 2024-11-29, 2024-11-30, 2024-12-02, 2024-12-03, 2024-12-04, 2024-12-05, 2024-12-06, 2024-12-07, 2024-12-08, 2024-12-09, 2024-12-10, 2024-12-11, 2024-12-12, 2024-12-13, 2024-12-14, 2024-12-15, 2024-12-16, 2024-12-17, 2024-12-18, 2024-12-19, 2024-12-20, 2024-12-21, 2024-12-22, 2024-12-23, 2024-12-24, 2024-12-25, 2024-12-26, 2024-12-27, 2024-12-28, 2024-12-29, 2024-12-30, 2024-12-31, 2025-01-02, 2025-01-03, 2025-01-04, 2025-01-05, 2025-01-06, 2025-01-07, 2025-01-08, 2025-01-09, 2025-01-10, 2025-01-11, 2025-01-12, 2025-01-13, 2025-01-14, 2025-01-15, 2025-01-16, 2025-01-17, 2025-01-18, 2025-01-19, 2025-01-20, 2025-01-21, 2025-01-22, 2025-01-23, 2025-01-24, 2025-01-25, 2025-01-26, 2025-01-27, 2025-01-28, 2025-01-29, 2025-01-30, 2025-01-31, 2025-02-02, 2025-02-03, 2025-02-04, 2025-02-05, 2025-02-06, 2025-02-07, 2025-02-08, 2025-02-09, 2025-02-10, 2025-02-11, 2025-02-12, 2025-02-13, 2025-02-14, 2025-02-15, 2025-02-16, 2025-02-17, 2025-02-18, 2025-02-19, 2025-02-20, 2025-02-21, 2025-02-22, 2025-02-23, 2025-02-24, 2025-02-25, 2025-02-26, 2025-02-27, 2025-02-28, 2025-03-02, 2025-03-03, 2025-03-04, 2025-03-05, 2025-03-06, 2025-03-07, 2025-03-08, 2025-03-09, 2025-03-10, 2025-03-11, 2025-03-12, 2025-03-13, 2025-03-14, 2025-03-15, 2025-03-16, 2025-03-17, 2025-03-18, 2025-03-19, 2025-03-20, 2025-03-21, 2025-03-22, 2025-03-23, 2025-03-24, 2025-03-25, 2025-03-26, 2025-03-27, 2025-03-28, 2025-03-29, 2025-03-30, 2025-03-31, 2025-04-02, 2025-04-03, 2025-04-04, 2025-04-05, 2025-04-06, 2025-04-07, 2025-04-08, 2025-04-09, 2025-04-10, 2025-04-11, 2025-04-12, 2025-04-13, 2025-04-14, 2025-04-15, 2025-04-16, 2025-04-17, 2025-04-18, 2025-04-19, 2025-04-20, 2025-04-21, 2025-04-22, 2025-04-23, 2025-04-24, 2025-04-25, 2025-04-26, 2025-04-27, 2025-04-28, 2025-04-29, 2025-04-30, 2025-05-02, 2025-05-03, 2025-05-04, 2025-05-05, 2025-05-06, 2025-05-07, 2025-05-08, 2025-05-09, 2025-05-10, 2025-05-11, 2025-05-12, 2025-05-13, 2025-05-14, 2025-05-15, 2025-05-16, 2025-05-17, 2025-05-18, 2025-05-19, 2025-05-20, 2025-05-21, 2025-05-22, 2025-05-23, 2025-05-24, 2025-05-25, 2025-05-26, 2025-05-27, 2025-05-28, 2025-05-29, 2025-05-30, 2025-05-31, 2025-06-02, 2025-06-03, 2025-06-04, 2025-06-05, 2025-06-06, 2025-06-07, 2025-06-08, 2025-06-09, 2025-06-10, 2025-06-11, 2025-06-12, 2025-06-13, 2025-06-14, 2025-06-15, 2025-06-16, 2025-06-17, 2025-06-18, 2025-06-19, 2025-06-20, 2025-06-21, 2025-06-22, 2025-06-23, 2025-06-24, 2025-06-25, 2025-06-26, 2025-06-27, 2025-06-28, 2025-06-29, 2025-06-30, 2025-07-02, 2025-07-03, 2025-07-04, 2025-07-05, 2025-07-06, 2025-07-07, 2025-07-08, 2025-07-09, 2025-07-10, 2025-07-11, 2025-07-12, 2025-07-13, 2025-07-14, 2025-07-15, 2025-07-16, 2025-07-17, 2025-07-18, 2025-07-19, 2025-07-20, 2025-07-21, 2025-07-22, 2025-07-23, 2025-07-24, 2025-07-25, 2025-07-26, 2025-07-27, 2025-07-28, 2025-07-29, 2025-07-30, 2025-07-31, 2025-08-02, 2025-08-03, 2025-08-04, 2025-08-05, 2025-08-06, 2025-08-07, 2025-08-08, 2025-08-09, 2025-08-10, 2025-08-11, 2025-08-12, 2025-08-13, 2025-08-14, 2025-08-15, 2025-08-16, 2025-08-17, 2025-08-18, 2025-08-19, 2025-08-20, 2025-08-21, 2025-08-22, 2025-08-23, 2025-08-24, 2025-08-25, 2025-08-26, 2025-08-27, 2025-08-28, 2025-08-29, 2025-08-30, 2025-08-31, 2025-09-02, 2025-09-03, 2025-09-04, 2025-09-05, 2025-09-06, 2025-09-07, 2025-09-08, 2025-09-09, 2025-09-10, 2025-09-11, 2025-09-12, 2025-09-13, 2025-09-14, 2025-09-15, 2025-09-16, 2025-09-17, 2025-09-18, 2025-09-19, 2025-09-20, 2025-09-21, 2025-09-22, 2025-09-23, 2025-09-24, 2025-09-25, 2025-09-26, 2025-09-27, 2025-09-28, 2025-09-29, 2025-09-30, 2025-10-02, 2025-10-03, 2025-10-04, 2025-10-05, 2025-10-06, 2025-10-07, 2025-10-08, 2025-10-09, 2025-10-10, 2025-10-11, 2025-10-12, 2025-10-13, 2025-10-14, 2025-10-15, 2025-10-16, 2025-10-17, 2025-10-18, 2025-10-19, 2025-10-20, 2025-10-21, 2025-10-22, 2025-10-23, 2025-10-24, 2025-10-25, 2025-10-26, 2025-10-27, 2025-10-28, 2025-10-29, 2025-10-30, 2025-10-31, 2025-11-02, 2025-11-03, 2025-11-04, 2025-11-05, 2025-11-06, 2025-11-07, 2025-11-08, 2025-11-09, 2025-11-10, 2025-11-11, 2025-11-12, 2025-11-13, 2025-11-14, 2025-11-15, 2025-11-16, 2025-11-17, 2025-11-18, 2025-11-19, 2025-11-20, 2025-11-21, 2025-11-22, 2025-11-23, 2025-11-24, 2025-11-25, 2025-11-26, 2025-11-27, 2025-11-28, 2025-11-29, 2025-11-30, 2025-12-02, 2025-12-03, 2025-12-04, 2025-12-05, 2025-12-06, 2025-12-07, 2025-12-08, 2025-12-09, 2025-12-10, 2025-12-11, 2025-12-12, 2025-12-13, 2025-12-14, 2025-12-15, 2025-12-16, 2025-12-17, 2025-12-18, 2025-12-19, 2025-12-20, 2025-12-21, 2025-12-22, 2025-12-23, 2025-12-24, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2025-12-29, 2025-12-30, 2025-12-31, 2026-01-02, 2026-01-03, 2026-01-04, 2026-01-05, 2026-01-06, 2026-01-07, 2026-01-08, 2026-01-09, 2026-01-10, 2026-01-11, 2026-01-12, 2026-01-13, 2026-01-14, 2026-01-15, 2026-01-16, 2026-01-17, 2026-01-18, 2026-01-19, 2026-01-20, 2026-01-21, 2026-01-22, 2026-01-23, 2026-01-24, 2026-01-25, 2026-01-26, 2026-01-27, 2026-01-28, 2026-01-29, 2026-01-30, 2026-01-31, 2026-02-02, 2026-02-03, 2026-02-04, 2026-02-05, 2026-02-06, 2026-02-07, 2026-02-08, 2026-02-09, 2026-02-10, 2026-02-11, 2026-02-12, 2026-02-13, 2026-02-14, 2026-02-15, 2026-02-16, 2026-02-17, 2026-02-18, 2026-02-19, 2026-02-20, 2026-02-21, 2026-02-22, 2026-02-23, 2026-02-24, 2026-02-25, 2026-02-26, 2026-02-27, 2026-02-28, 2026-03-02, 2026-03-03, 2026-03-04, 2026-03-05, 2026-03-06, 2026-03-07, 2026-03-08, 2026-03-09, 2026-03-10, 2026-03-11, 2026-03-12, 2026-03-13, 2026-03-14, 2026-03-15, 2026-03-16, 2026-03-17, 2026-03-18, 2026-03-19, 2026-03-20, 2026-03-21, 2026-03-22, 2026-03-23, 2026-03-24, 2026-03-25, 2026-03-26, 2026-03-27, 2026-03-28, 2026-03-29, 2026-03-30, 2026-03-31, 2026-04-02, 2026-04-03, 2026-04-04, 2026-04-05, 2026-04-06, 2026-04-07, 2026-04-08, 2026-04-09, 2026-04-10, 2026-04-11, 2026-04-12, 2026-04-13, 2026-04-14, 2026-04-15, 2026-04-16, 2026-04-17, 2026-04-18, 2026-04-19, 2026-04-20, 2026-04-21, 2026-04-22, 2026-04-23, 2026-04-24, 2026-04-25, 2026-04-26, 2026-04-27, 2026-04-28, 2026-04-29, 2026-04-30, 2026-05-02, 2026-05-03, 2026-05-04, 2026-05-05, 2026-05-06, 2026-05-07, 2026-05-08, 2026-05-09, 2026-05-10, 2026-05-11, 2026-05-12, 2026-05-13, 2026-05-14, 2026-05-15, 2026-05-16, 2026-05-17, 2026-05-18, 2026-05-19, 2026-05-20, 2026-05-21, 2026-05-22, 2026-05-23, 2026-05-24, 2026-05-25, 2026-05-26, 2026-05-27, 2026-05-28, 2026-05-29, 2026-05-30, 2026-05-31, 2026-06-02, 2026-06-03, 2026-06-04, 2026-06-05, 2026-06-06, 2026-06-07, 2026-06-08, 2026-06-09, 2026-06-10, 2026-06-11, 2026-06-12, 2026-06-13, 2026-06-14, 2026-06-15, 2026-06-16, 2026-06-17, 2026-06-18, 2026-06-19, 2026-06-20, 2026-06-21, 2026-06-22, 2026-06-23, 2026-06-24, 2026-06-25, 2026-06-26, 2026-06-27, 2026-06-28, 2026-06-29, 2026-06-30, 2026-07-02, 2026-07-03, 2026-07-04, 2026-07-05, 2026-07-06, 2026-07-07, 2026-07-08, 2026-07-09, 2026-07-10, 2026-07-11, 2026-07-12, 2026-07-13, 2026-07-14, 2026-07-15, 2026-07-16, 2026-07-17, 2026-07-18, 2026-07-19, 2026-07-20, 2026-07-21, 2026-07-22, 2026-07-23, 2026-07-24, 2026-07-25, 2026-07-26, 2026-07-27, 2026-07-28, 2026-07-29, 2026-07-30, 2026-07-31, 2026-08-02, 2026-08-03, 2026-08-04, 2026-08-05, 2026-08-06, 2026-08-07, 2026-08-08, 2026-08-09, 2026-08-10, 2026-08-11, 2026-08-12, 2026-08-13, 2026-08-14, 2026-08-15, 2026-08-16, 2026-08-17, 2026-08-18, 2026-08-19, 2026-08-20, 2026-08-21, 2026-08-22, 2026-08-23, 2026-08-24, 2026-08-25, 2026-08-26, 2026-08-27, 2026-08-28, 2026-08-29, 2026-08-30, 2026-08-31; baseline absent periods: 2025-09-02, 2025-09-03, 2025-09-04, 2025-09-05, 2025-09-06, 2025-09-07, 2025-09-08, 2025-09-09, 2025-09-10, 2025-09-11, 2025-09-12, 2025-09-13, 2025-09-14, 2025-09-15, 2025-09-16, 2025-09-17, 2025-09-18, 2025-09-19, 2025-09-20, 2025-09-21, 2025-09-22, 2025-09-23, 2025-09-24, 2025-09-25, 2025-09-26, 2025-09-27, 2025-09-28, 2025-09-29, 2025-09-30, 2025-10-02, 2025-10-03, 2025-10-04, 2025-10-05, 2025-10-06, 2025-10-07, 2025-10-08, 2025-10-09, 2025-10-10, 2025-10-11, 2025-10-12, 2025-10-13, 2025-10-14, 2025-10-15, 2025-10-16, 2025-10-17, 2025-10-18, 2025-10-19, 2025-10-20, 2025-10-21, 2025-10-22, 2025-10-23, 2025-10-24, 2025-10-25, 2025-10-26, 2025-10-27, 2025-10-28, 2025-10-29, 2025-10-30, 2025-10-31, 2025-11-02, 2025-11-03, 2025-11-04, 2025-11-05, 2025-11-06, 2025-11-07, 2025-11-08, 2025-11-09, 2025-11-10, 2025-11-11, 2025-11-12, 2025-11-13, 2025-11-14, 2025-11-15, 2025-11-16, 2025-11-17, 2025-11-18, 2025-11-19, 2025-11-20, 2025-11-21, 2025-11-22, 2025-11-23, 2025-11-24, 2025-11-25, 2025-11-26, 2025-11-27, 2025-11-28, 2025-11-29, 2025-11-30, 2025-12-02, 2025-12-03, 2025-12-04, 2025-12-05, 2025-12-06, 2025-12-07, 2025-12-08, 2025-12-09, 2025-12-10, 2025-12-11, 2025-12-12, 2025-12-13, 2025-12-14, 2025-12-15, 2025-12-16, 2025-12-17, 2025-12-18, 2025-12-19, 2025-12-20, 2025-12-21, 2025-12-22, 2025-12-23, 2025-12-24, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2025-12-29, 2025-12-30, 2025-12-31, 2026-01-02, 2026-01-03, 2026-01-04, 2026-01-05, 2026-01-06, 2026-01-07, 2026-01-08, 2026-01-09, 2026-01-10, 2026-01-11, 2026-01-12, 2026-01-13, 2026-01-14, 2026-01-15, 2026-01-16, 2026-01-17, 2026-01-18, 2026-01-19, 2026-01-20, 2026-01-21, 2026-01-22, 2026-01-23, 2026-01-24, 2026-01-25, 2026-01-26, 2026-01-27, 2026-01-28, 2026-01-29, 2026-01-30, 2026-01-31, 2026-02-02, 2026-02-03, 2026-02-04, 2026-02-05, 2026-02-06, 2026-02-07, 2026-02-08, 2026-02-09, 2026-02-10, 2026-02-11, 2026-02-12, 2026-02-13, 2026-02-14, 2026-02-15, 2026-02-16, 2026-02-17, 2026-02-18, 2026-02-19, 2026-02-20, 2026-02-21, 2026-02-22, 2026-02-23, 2026-02-24, 2026-02-25, 2026-02-26, 2026-02-27, 2026-02-28, 2026-03-02, 2026-03-03, 2026-03-04, 2026-03-05, 2026-03-06, 2026-03-07, 2026-03-08, 2026-03-09, 2026-03-10, 2026-03-11, 2026-03-12, 2026-03-13, 2026-03-14, 2026-03-15, 2026-03-16, 2026-03-17, 2026-03-18, 2026-03-19, 2026-03-20, 2026-03-21, 2026-03-22, 2026-03-23, 2026-03-24, 2026-03-25, 2026-03-26, 2026-03-27, 2026-03-28, 2026-03-29, 2026-03-30, 2026-03-31, 2026-04-02, 2026-04-03, 2026-04-04, 2026-04-05, 2026-04-06, 2026-04-07, 2026-04-08, 2026-04-09, 2026-04-10, 2026-04-11, 2026-04-12, 2026-04-13, 2026-04-14, 2026-04-15, 2026-04-16, 2026-04-17, 2026-04-18, 2026-04-19, 2026-04-20, 2026-04-21, 2026-04-22, 2026-04-23, 2026-04-24, 2026-04-25, 2026-04-26, 2026-04-27, 2026-04-28, 2026-04-29, 2026-04-30, 2026-05-02, 2026-05-03, 2026-05-04, 2026-05-05, 2026-05-06, 2026-05-07, 2026-05-08, 2026-05-09, 2026-05-10, 2026-05-11, 2026-05-12, 2026-05-13, 2026-05-14, 2026-05-15, 2026-05-16, 2026-05-17, 2026-05-18, 2026-05-19, 2026-05-20, 2026-05-21, 2026-05-22, 2026-05-23, 2026-05-24, 2026-05-25, 2026-05-26, 2026-05-27, 2026-05-28, 2026-05-29, 2026-05-30, 2026-05-31, 2026-06-02, 2026-06-03, 2026-06-04, 2026-06-05, 2026-06-06, 2026-06-07, 2026-06-08, 2026-06-09, 2026-06-10, 2026-06-11, 2026-06-12, 2026-06-13, 2026-06-14, 2026-06-15, 2026-06-16, 2026-06-17, 2026-06-18, 2026-06-19, 2026-06-20, 2026-06-21, 2026-06-22, 2026-06-23, 2026-06-24, 2026-06-25, 2026-06-26, 2026-06-27, 2026-06-28, 2026-06-29, 2026-06-30, 2026-07-02, 2026-07-03, 2026-07-04, 2026-07-05, 2026-07-06, 2026-07-07, 2026-07-08, 2026-07-09, 2026-07-10, 2026-07-11, 2026-07-12, 2026-07-13, 2026-07-14, 2026-07-15, 2026-07-16, 2026-07-17, 2026-07-18, 2026-07-19, 2026-07-20, 2026-07-21, 2026-07-22, 2026-07-23, 2026-07-24, 2026-07-25, 2026-07-26, 2026-07-27, 2026-07-28, 2026-07-29, 2026-07-30, 2026-07-31, 2026-08-02, 2026-08-03, 2026-08-04, 2026-08-05, 2026-08-06, 2026-08-07, 2026-08-08, 2026-08-09, 2026-08-10, 2026-08-11, 2026-08-12, 2026-08-13, 2026-08-14, 2026-08-15, 2026-08-16, 2026-08-17, 2026-08-18, 2026-08-19, 2026-08-20, 2026-08-21, 2026-08-22, 2026-08-23, 2026-08-24, 2026-08-25, 2026-08-26, 2026-08-27, 2026-08-28, 2026-08-29, 2026-08-30, 2026-08-31.

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 3822, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.
- Transaction month to FX → exchange_rates.csv: many-to-one; matched 3822, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Monthly EUR/USD CHF-per-unit rates; no conversion performed.

Issue categories: `{"business_key_collision": 5, "coverage_gap": 1, "exact_duplicate_candidate": 5, "missing_department_mapping": 1, "missing_value": 6, "project_id_variant": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Records dated within the baseline; drafts and duplicate candidates retained.

Rows: 2067; missing cells: 2152; expected optional/non-applicable blanks: 4859; exact duplicate excess: 5; key collision groups: 5.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| line_item_usage_start_date | timestamp / timestamp | 0 / 0 / 0 | 2025-09-01 | 2026-08-31 |
| line_item_resource_id | text / text | 0 / 0 / 0 | None | None |
| product_servicecode | text / text | 0 / 0 / 0 | None | None |
| product_region | text / text | 0 / 0 / 0 | None | None |
| line_item_usage_amount | number / number | 0 / 0 / 0 | 1.0 | 76523.28 |
| pricing_unit | text / text | 0 / 0 / 0 | None | None |
| line_item_unblended_cost | number / number | 42 / 42 / 0 | 0.262763 | 1164.294955 |
| line_item_currency_code | text / text | 0 / 0 / 0 | None | None |
| line_item_line_item_type | text / text | 0 / 0 / 0 | None | None |
| resource_tags_user_department | text / text | 514 / 514 / 0 | None | None |
| resource_tags_user_tool | text / text | 313 / 313 / 0 | None | None |
| resource_tags_user_project | text / text | 732 / 732 / 0 | None | None |
| resource_tags_user_environment | text / text | 304 / 304 / 0 | None | None |
| avg_cpu_utilization | number / number | 247 / 1702 / 0 | 1.1 | 82.9 |
| object_requests | number / number | 0 / 1346 / 0 | 0.0 | 5.0 |
| line_item_description | text / text | 0 / 2058 / 0 | None | None |

Categories: `{"line_item_currency_code": {"USD": 2067}, "line_item_line_item_type": {"Fee": 12, "Usage": 2055}, "pricing_unit": {"GB": 361, "GB-day": 721, "month": 12, "runner-minute": 361, "vCPU-hour": 612}}`

Amount/credit counts (not cost totals): `[{"currency": "USD", "charge_type": "Fee", "rows": 12, "missing": 1, "negative_count": 0, "negative_rows": []}, {"currency": "USD", "charge_type": "Usage", "rows": 2055, "missing": 41, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[{"column": "resource_tags_user_project", "proposed": "P-001", "variants": {"P-001": 254, "P001": 23, "p-001": 17}}, {"column": "resource_tags_user_project", "proposed": "P-002", "variants": {"P-002": 236, "P002": 27, "p-002": 19}}, {"column": "resource_tags_user_project", "proposed": "P-003", "variants": {"P-003": 39, "P003": 6, "p-003": 4}}, {"column": "resource_tags_user_project", "proposed": "P-004", "variants": {"P-004": 136, "P004": 13, "p-004": 7}}, {"column": "resource_tags_user_project", "proposed": "P-014", "variants": {"P-014": 65, "P014": 6, "p-014": 6}}, {"column": "resource_tags_user_project", "proposed": "P-015", "variants": {"P-015": 407, "P015": 44, "p-015": 26}}, {"column": "resource_tags_user_project", "proposed": "unknown", "variants": {"": 732}}]`

Coverage: `{"minimum": "2025-09-01", "maximum": "2026-08-31", "distinct_periods": 365, "cadence": "daily"}`
- arn:aws:build-service:eu:0000:cicd: observation gap; lifetime/expected activity unverified; internal gaps: 2026-01-01, 2026-01-06, 2026-01-31, 2026-03-04, 2026-07-18; baseline absent periods: 2026-01-01, 2026-01-06, 2026-01-31, 2026-03-04, 2026-07-18.
- arn:aws:compute:eu:0000:sandbox: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-06, 2025-09-07, 2025-09-13, 2025-09-14, 2025-09-20, 2025-09-21, 2025-09-27, 2025-09-28, 2025-10-04, 2025-10-05, 2025-10-11, 2025-10-12, 2025-10-18, 2025-10-19, 2025-10-25, 2025-10-26, 2025-11-01, 2025-11-02, 2025-11-08, 2025-11-09, 2025-11-15, 2025-11-16, 2025-11-22, 2025-11-23, 2025-11-29, 2025-11-30, 2025-12-06, 2025-12-07, 2025-12-10, 2025-12-13, 2025-12-14, 2025-12-20, 2025-12-21, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2026-01-01, 2026-01-03, 2026-01-04, 2026-01-10, 2026-01-11, 2026-01-17, 2026-01-18, 2026-01-24, 2026-01-25, 2026-01-31, 2026-02-01, 2026-02-07, 2026-02-08, 2026-02-14, 2026-02-15, 2026-02-21, 2026-02-22, 2026-02-28, 2026-03-01, 2026-03-07, 2026-03-08, 2026-03-10, 2026-03-14, 2026-03-15, 2026-03-21, 2026-03-22, 2026-03-28, 2026-03-29, 2026-04-03, 2026-04-04, 2026-04-05, 2026-04-06, 2026-04-11, 2026-04-12, 2026-04-18, 2026-04-19, 2026-04-25, 2026-04-26, 2026-04-27, 2026-04-29, 2026-05-01, 2026-05-02, 2026-05-03, 2026-05-04, 2026-05-09, 2026-05-10, 2026-05-14, 2026-05-16, 2026-05-17, 2026-05-23, 2026-05-24, 2026-05-25, 2026-05-30, 2026-05-31, 2026-06-06, 2026-06-07, 2026-06-13, 2026-06-14, 2026-06-20, 2026-06-21, 2026-06-27, 2026-06-28, 2026-07-04, 2026-07-05, 2026-07-07, 2026-07-11, 2026-07-12, 2026-07-18, 2026-07-19, 2026-07-25, 2026-07-26, 2026-08-01, 2026-08-02, 2026-08-07, 2026-08-08, 2026-08-09, 2026-08-15, 2026-08-16, 2026-08-22, 2026-08-23, 2026-08-29, 2026-08-30; baseline absent periods: 2025-09-06, 2025-09-07, 2025-09-13, 2025-09-14, 2025-09-20, 2025-09-21, 2025-09-27, 2025-09-28, 2025-10-04, 2025-10-05, 2025-10-11, 2025-10-12, 2025-10-18, 2025-10-19, 2025-10-25, 2025-10-26, 2025-11-01, 2025-11-02, 2025-11-08, 2025-11-09, 2025-11-15, 2025-11-16, 2025-11-22, 2025-11-23, 2025-11-29, 2025-11-30, 2025-12-06, 2025-12-07, 2025-12-10, 2025-12-13, 2025-12-14, 2025-12-20, 2025-12-21, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2026-01-01, 2026-01-03, 2026-01-04, 2026-01-10, 2026-01-11, 2026-01-17, 2026-01-18, 2026-01-24, 2026-01-25, 2026-01-31, 2026-02-01, 2026-02-07, 2026-02-08, 2026-02-14, 2026-02-15, 2026-02-21, 2026-02-22, 2026-02-28, 2026-03-01, 2026-03-07, 2026-03-08, 2026-03-10, 2026-03-14, 2026-03-15, 2026-03-21, 2026-03-22, 2026-03-28, 2026-03-29, 2026-04-03, 2026-04-04, 2026-04-05, 2026-04-06, 2026-04-11, 2026-04-12, 2026-04-18, 2026-04-19, 2026-04-25, 2026-04-26, 2026-04-27, 2026-04-29, 2026-05-01, 2026-05-02, 2026-05-03, 2026-05-04, 2026-05-09, 2026-05-10, 2026-05-14, 2026-05-16, 2026-05-17, 2026-05-23, 2026-05-24, 2026-05-25, 2026-05-30, 2026-05-31, 2026-06-06, 2026-06-07, 2026-06-13, 2026-06-14, 2026-06-20, 2026-06-21, 2026-06-27, 2026-06-28, 2026-07-04, 2026-07-05, 2026-07-07, 2026-07-11, 2026-07-12, 2026-07-18, 2026-07-19, 2026-07-25, 2026-07-26, 2026-08-01, 2026-08-02, 2026-08-07, 2026-08-08, 2026-08-09, 2026-08-15, 2026-08-16, 2026-08-22, 2026-08-23, 2026-08-29, 2026-08-30.
- arn:aws:compute:eu:0000:vm-test: observation gap; lifetime/expected activity unverified; internal gaps: 2025-12-23; baseline absent periods: 2025-12-23.
- arn:aws:network:eu:0000:net-egress: observation gap; lifetime/expected activity unverified; internal gaps: 2025-10-18, 2025-11-09, 2025-12-03, 2026-01-04; baseline absent periods: 2025-10-18, 2025-11-09, 2025-12-03, 2026-01-04.
- arn:aws:storage:eu:0000:st-archive: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-12, 2025-10-05, 2025-11-02, 2025-12-26, 2025-12-29, 2026-01-01, 2026-01-04, 2026-03-21, 2026-07-29, 2026-08-10, 2026-08-16; baseline absent periods: 2025-09-12, 2025-10-05, 2025-11-02, 2025-12-26, 2025-12-29, 2026-01-01, 2026-01-04, 2026-03-21, 2026-07-29, 2026-08-10, 2026-08-16.
- arn:aws:support:eu:0000:support: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-02, 2025-09-03, 2025-09-04, 2025-09-05, 2025-09-06, 2025-09-07, 2025-09-08, 2025-09-09, 2025-09-10, 2025-09-11, 2025-09-12, 2025-09-13, 2025-09-14, 2025-09-15, 2025-09-16, 2025-09-17, 2025-09-18, 2025-09-19, 2025-09-20, 2025-09-21, 2025-09-22, 2025-09-23, 2025-09-24, 2025-09-25, 2025-09-26, 2025-09-27, 2025-09-28, 2025-09-29, 2025-09-30, 2025-10-02, 2025-10-03, 2025-10-04, 2025-10-05, 2025-10-06, 2025-10-07, 2025-10-08, 2025-10-09, 2025-10-10, 2025-10-11, 2025-10-12, 2025-10-13, 2025-10-14, 2025-10-15, 2025-10-16, 2025-10-17, 2025-10-18, 2025-10-19, 2025-10-20, 2025-10-21, 2025-10-22, 2025-10-23, 2025-10-24, 2025-10-25, 2025-10-26, 2025-10-27, 2025-10-28, 2025-10-29, 2025-10-30, 2025-10-31, 2025-11-02, 2025-11-03, 2025-11-04, 2025-11-05, 2025-11-06, 2025-11-07, 2025-11-08, 2025-11-09, 2025-11-10, 2025-11-11, 2025-11-12, 2025-11-13, 2025-11-14, 2025-11-15, 2025-11-16, 2025-11-17, 2025-11-18, 2025-11-19, 2025-11-20, 2025-11-21, 2025-11-22, 2025-11-23, 2025-11-24, 2025-11-25, 2025-11-26, 2025-11-27, 2025-11-28, 2025-11-29, 2025-11-30, 2025-12-02, 2025-12-03, 2025-12-04, 2025-12-05, 2025-12-06, 2025-12-07, 2025-12-08, 2025-12-09, 2025-12-10, 2025-12-11, 2025-12-12, 2025-12-13, 2025-12-14, 2025-12-15, 2025-12-16, 2025-12-17, 2025-12-18, 2025-12-19, 2025-12-20, 2025-12-21, 2025-12-22, 2025-12-23, 2025-12-24, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2025-12-29, 2025-12-30, 2025-12-31, 2026-01-02, 2026-01-03, 2026-01-04, 2026-01-05, 2026-01-06, 2026-01-07, 2026-01-08, 2026-01-09, 2026-01-10, 2026-01-11, 2026-01-12, 2026-01-13, 2026-01-14, 2026-01-15, 2026-01-16, 2026-01-17, 2026-01-18, 2026-01-19, 2026-01-20, 2026-01-21, 2026-01-22, 2026-01-23, 2026-01-24, 2026-01-25, 2026-01-26, 2026-01-27, 2026-01-28, 2026-01-29, 2026-01-30, 2026-01-31, 2026-02-02, 2026-02-03, 2026-02-04, 2026-02-05, 2026-02-06, 2026-02-07, 2026-02-08, 2026-02-09, 2026-02-10, 2026-02-11, 2026-02-12, 2026-02-13, 2026-02-14, 2026-02-15, 2026-02-16, 2026-02-17, 2026-02-18, 2026-02-19, 2026-02-20, 2026-02-21, 2026-02-22, 2026-02-23, 2026-02-24, 2026-02-25, 2026-02-26, 2026-02-27, 2026-02-28, 2026-03-02, 2026-03-03, 2026-03-04, 2026-03-05, 2026-03-06, 2026-03-07, 2026-03-08, 2026-03-09, 2026-03-10, 2026-03-11, 2026-03-12, 2026-03-13, 2026-03-14, 2026-03-15, 2026-03-16, 2026-03-17, 2026-03-18, 2026-03-19, 2026-03-20, 2026-03-21, 2026-03-22, 2026-03-23, 2026-03-24, 2026-03-25, 2026-03-26, 2026-03-27, 2026-03-28, 2026-03-29, 2026-03-30, 2026-03-31, 2026-04-02, 2026-04-03, 2026-04-04, 2026-04-05, 2026-04-06, 2026-04-07, 2026-04-08, 2026-04-09, 2026-04-10, 2026-04-11, 2026-04-12, 2026-04-13, 2026-04-14, 2026-04-15, 2026-04-16, 2026-04-17, 2026-04-18, 2026-04-19, 2026-04-20, 2026-04-21, 2026-04-22, 2026-04-23, 2026-04-24, 2026-04-25, 2026-04-26, 2026-04-27, 2026-04-28, 2026-04-29, 2026-04-30, 2026-05-02, 2026-05-03, 2026-05-04, 2026-05-05, 2026-05-06, 2026-05-07, 2026-05-08, 2026-05-09, 2026-05-10, 2026-05-11, 2026-05-12, 2026-05-13, 2026-05-14, 2026-05-15, 2026-05-16, 2026-05-17, 2026-05-18, 2026-05-19, 2026-05-20, 2026-05-21, 2026-05-22, 2026-05-23, 2026-05-24, 2026-05-25, 2026-05-26, 2026-05-27, 2026-05-28, 2026-05-29, 2026-05-30, 2026-05-31, 2026-06-02, 2026-06-03, 2026-06-04, 2026-06-05, 2026-06-06, 2026-06-07, 2026-06-08, 2026-06-09, 2026-06-10, 2026-06-11, 2026-06-12, 2026-06-13, 2026-06-14, 2026-06-15, 2026-06-16, 2026-06-17, 2026-06-18, 2026-06-19, 2026-06-20, 2026-06-21, 2026-06-22, 2026-06-23, 2026-06-24, 2026-06-25, 2026-06-26, 2026-06-27, 2026-06-28, 2026-06-29, 2026-06-30, 2026-07-02, 2026-07-03, 2026-07-04, 2026-07-05, 2026-07-06, 2026-07-07, 2026-07-08, 2026-07-09, 2026-07-10, 2026-07-11, 2026-07-12, 2026-07-13, 2026-07-14, 2026-07-15, 2026-07-16, 2026-07-17, 2026-07-18, 2026-07-19, 2026-07-20, 2026-07-21, 2026-07-22, 2026-07-23, 2026-07-24, 2026-07-25, 2026-07-26, 2026-07-27, 2026-07-28, 2026-07-29, 2026-07-30, 2026-07-31; baseline absent periods: 2025-09-02, 2025-09-03, 2025-09-04, 2025-09-05, 2025-09-06, 2025-09-07, 2025-09-08, 2025-09-09, 2025-09-10, 2025-09-11, 2025-09-12, 2025-09-13, 2025-09-14, 2025-09-15, 2025-09-16, 2025-09-17, 2025-09-18, 2025-09-19, 2025-09-20, 2025-09-21, 2025-09-22, 2025-09-23, 2025-09-24, 2025-09-25, 2025-09-26, 2025-09-27, 2025-09-28, 2025-09-29, 2025-09-30, 2025-10-02, 2025-10-03, 2025-10-04, 2025-10-05, 2025-10-06, 2025-10-07, 2025-10-08, 2025-10-09, 2025-10-10, 2025-10-11, 2025-10-12, 2025-10-13, 2025-10-14, 2025-10-15, 2025-10-16, 2025-10-17, 2025-10-18, 2025-10-19, 2025-10-20, 2025-10-21, 2025-10-22, 2025-10-23, 2025-10-24, 2025-10-25, 2025-10-26, 2025-10-27, 2025-10-28, 2025-10-29, 2025-10-30, 2025-10-31, 2025-11-02, 2025-11-03, 2025-11-04, 2025-11-05, 2025-11-06, 2025-11-07, 2025-11-08, 2025-11-09, 2025-11-10, 2025-11-11, 2025-11-12, 2025-11-13, 2025-11-14, 2025-11-15, 2025-11-16, 2025-11-17, 2025-11-18, 2025-11-19, 2025-11-20, 2025-11-21, 2025-11-22, 2025-11-23, 2025-11-24, 2025-11-25, 2025-11-26, 2025-11-27, 2025-11-28, 2025-11-29, 2025-11-30, 2025-12-02, 2025-12-03, 2025-12-04, 2025-12-05, 2025-12-06, 2025-12-07, 2025-12-08, 2025-12-09, 2025-12-10, 2025-12-11, 2025-12-12, 2025-12-13, 2025-12-14, 2025-12-15, 2025-12-16, 2025-12-17, 2025-12-18, 2025-12-19, 2025-12-20, 2025-12-21, 2025-12-22, 2025-12-23, 2025-12-24, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2025-12-29, 2025-12-30, 2025-12-31, 2026-01-02, 2026-01-03, 2026-01-04, 2026-01-05, 2026-01-06, 2026-01-07, 2026-01-08, 2026-01-09, 2026-01-10, 2026-01-11, 2026-01-12, 2026-01-13, 2026-01-14, 2026-01-15, 2026-01-16, 2026-01-17, 2026-01-18, 2026-01-19, 2026-01-20, 2026-01-21, 2026-01-22, 2026-01-23, 2026-01-24, 2026-01-25, 2026-01-26, 2026-01-27, 2026-01-28, 2026-01-29, 2026-01-30, 2026-01-31, 2026-02-02, 2026-02-03, 2026-02-04, 2026-02-05, 2026-02-06, 2026-02-07, 2026-02-08, 2026-02-09, 2026-02-10, 2026-02-11, 2026-02-12, 2026-02-13, 2026-02-14, 2026-02-15, 2026-02-16, 2026-02-17, 2026-02-18, 2026-02-19, 2026-02-20, 2026-02-21, 2026-02-22, 2026-02-23, 2026-02-24, 2026-02-25, 2026-02-26, 2026-02-27, 2026-02-28, 2026-03-02, 2026-03-03, 2026-03-04, 2026-03-05, 2026-03-06, 2026-03-07, 2026-03-08, 2026-03-09, 2026-03-10, 2026-03-11, 2026-03-12, 2026-03-13, 2026-03-14, 2026-03-15, 2026-03-16, 2026-03-17, 2026-03-18, 2026-03-19, 2026-03-20, 2026-03-21, 2026-03-22, 2026-03-23, 2026-03-24, 2026-03-25, 2026-03-26, 2026-03-27, 2026-03-28, 2026-03-29, 2026-03-30, 2026-03-31, 2026-04-02, 2026-04-03, 2026-04-04, 2026-04-05, 2026-04-06, 2026-04-07, 2026-04-08, 2026-04-09, 2026-04-10, 2026-04-11, 2026-04-12, 2026-04-13, 2026-04-14, 2026-04-15, 2026-04-16, 2026-04-17, 2026-04-18, 2026-04-19, 2026-04-20, 2026-04-21, 2026-04-22, 2026-04-23, 2026-04-24, 2026-04-25, 2026-04-26, 2026-04-27, 2026-04-28, 2026-04-29, 2026-04-30, 2026-05-02, 2026-05-03, 2026-05-04, 2026-05-05, 2026-05-06, 2026-05-07, 2026-05-08, 2026-05-09, 2026-05-10, 2026-05-11, 2026-05-12, 2026-05-13, 2026-05-14, 2026-05-15, 2026-05-16, 2026-05-17, 2026-05-18, 2026-05-19, 2026-05-20, 2026-05-21, 2026-05-22, 2026-05-23, 2026-05-24, 2026-05-25, 2026-05-26, 2026-05-27, 2026-05-28, 2026-05-29, 2026-05-30, 2026-05-31, 2026-06-02, 2026-06-03, 2026-06-04, 2026-06-05, 2026-06-06, 2026-06-07, 2026-06-08, 2026-06-09, 2026-06-10, 2026-06-11, 2026-06-12, 2026-06-13, 2026-06-14, 2026-06-15, 2026-06-16, 2026-06-17, 2026-06-18, 2026-06-19, 2026-06-20, 2026-06-21, 2026-06-22, 2026-06-23, 2026-06-24, 2026-06-25, 2026-06-26, 2026-06-27, 2026-06-28, 2026-06-29, 2026-06-30, 2026-07-02, 2026-07-03, 2026-07-04, 2026-07-05, 2026-07-06, 2026-07-07, 2026-07-08, 2026-07-09, 2026-07-10, 2026-07-11, 2026-07-12, 2026-07-13, 2026-07-14, 2026-07-15, 2026-07-16, 2026-07-17, 2026-07-18, 2026-07-19, 2026-07-20, 2026-07-21, 2026-07-22, 2026-07-23, 2026-07-24, 2026-07-25, 2026-07-26, 2026-07-27, 2026-07-28, 2026-07-29, 2026-07-30, 2026-07-31, 2026-08-02, 2026-08-03, 2026-08-04, 2026-08-05, 2026-08-06, 2026-08-07, 2026-08-08, 2026-08-09, 2026-08-10, 2026-08-11, 2026-08-12, 2026-08-13, 2026-08-14, 2026-08-15, 2026-08-16, 2026-08-17, 2026-08-18, 2026-08-19, 2026-08-20, 2026-08-21, 2026-08-22, 2026-08-23, 2026-08-24, 2026-08-25, 2026-08-26, 2026-08-27, 2026-08-28, 2026-08-29, 2026-08-30, 2026-08-31.

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 2067, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.
- Transaction month to FX → exchange_rates.csv: many-to-one; matched 2067, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Monthly EUR/USD CHF-per-unit rates; no conversion performed.

Issue categories: `{"business_key_collision": 5, "coverage_gap": 1, "exact_duplicate_candidate": 5, "missing_department_mapping": 1, "missing_value": 6, "project_id_variant": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | aws_costs.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | line_item_usage_start_date | Parse documented timestamp format; retain raw value. |
| resource_id | line_item_resource_id | Azure path / AWS ARN suffix candidate; otherwise direct. Instance IDs are not pooled billing IDs. |
| provider | constant AWS | Direct source value; no transformation in Phase 2. |
| cost_center | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| department | resource_tags_user_department | Direct source value; no transformation in Phase 2. |
| tool | resource_tags_user_tool | Direct source value; no transformation in Phase 2. |
| region | product_region | Direct source value; no transformation in Phase 2. |
| quantity | line_item_usage_amount | Direct source value; no transformation in Phase 2. |
| unit | pricing_unit | Direct source value; no transformation in Phase 2. |
| amount_original | line_item_unblended_cost | Direct source value; no transformation in Phase 2. |
| currency | line_item_currency_code | Direct source value; no transformation in Phase 2. |
| fx_rate | exchange_rates.csv | Phase 3: CHF=1; EUR/USD monthly CHF per foreign unit; missing rate → null. |
| cost_chf | derived in Phase 3 | Reported CHF for gateway/hoster; other currencies require monthly FX. No financial totals in Phase 2. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## hoster_invoice.csv

Role: Provider charges. Candidate key: Date, Item, Service, Unit, CostCenter. SHA-256: `a530e0571f45a2a51362743fe8d765a3343d342b62436f88ff8b0b8e498642d1`.

### Full export profile

All records in the export.

Rows: 2002; missing cells: 940; expected optional/non-applicable blanks: 3332; exact duplicate excess: 3; key collision groups: 3.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| Date | swiss_date / swiss_date | 0 / 0 / 0 | 2024-11-01 | 2026-09-06 |
| Item | text / text | 0 / 0 / 0 | None | None |
| Service | text / text | 0 / 0 / 0 | None | None |
| Quantity | number / number | 0 / 0 / 0 | 17.35 | 64040.17 |
| Unit | text / text | 0 / 0 / 0 | None | None |
| Amount_CHF | number / number | 35 / 35 / 0 | 1.28 | 44.96 |
| CostCenter | text / text | 189 / 189 / 0 | None | None |
| ProjectNumber | text / text | 716 / 716 / 0 | None | None |
| Accesses | number / number | 0 / 1331 / 0 | 35.0 | 6282.0 |
| Remark | text / text | 0 / 2001 / 0 | None | None |

Categories: `{"Unit": {"GB": 667, "GB-day": 1335}}`

Amount/credit counts (not cost totals): `[{"currency": "CHF", "charge_type": "reported", "rows": 2002, "missing": 35, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[{"column": "ProjectNumber", "proposed": "P-001", "variants": {"P-001": 317, "P001": 42, "p-001": 20}}, {"column": "ProjectNumber", "proposed": "P-002", "variants": {"P-002": 239, "P002": 32, "p-002": 20}}, {"column": "ProjectNumber", "proposed": "P-003", "variants": {"P-003": 149, "P003": 14, "p-003": 6}}, {"column": "ProjectNumber", "proposed": "P-005", "variants": {"P-005": 101, "P005": 14, "p-005": 8}}, {"column": "ProjectNumber", "proposed": "P-006", "variants": {"P-006": 79, "P006": 6, "p-006": 7}}, {"column": "ProjectNumber", "proposed": "P-007", "variants": {"P-007": 63, "P007": 10, "p-007": 8}}, {"column": "ProjectNumber", "proposed": "P-008", "variants": {"P-008": 63, "P008": 9, "p-008": 4}}, {"column": "ProjectNumber", "proposed": "P-010", "variants": {"P-010": 62, "P010": 12, "p-010": 1}}, {"column": "ProjectNumber", "proposed": "unknown", "variants": {"": 716}}]`

Coverage: `{"minimum": "2024-11-01", "maximum": "2026-09-06", "distinct_periods": 675, "cadence": "daily"}`
- Logging and monitoring: observation gap; lifetime/expected activity unverified; internal gaps: 2024-12-23, 2025-01-14, 2025-03-05, 2025-04-10, 2025-06-25, 2025-07-27, 2025-11-09, 2025-12-10, 2026-02-18, 2026-05-21, 2026-06-02, 2026-06-05; baseline absent periods: 2025-11-09, 2025-12-10, 2026-02-18, 2026-05-21, 2026-06-02, 2026-06-05.
- Project file storage: observation gap; lifetime/expected activity unverified; internal gaps: 2025-02-12, 2025-07-29, 2026-01-17, 2026-08-09; baseline absent periods: 2026-01-17, 2026-08-09.
- Web hosting and CDN: observation gap; lifetime/expected activity unverified; internal gaps: 2025-02-11, 2025-04-07, 2025-04-09, 2025-11-14, 2026-05-30, 2026-06-04, 2026-06-06, 2026-06-09, 2026-07-31; baseline absent periods: 2025-11-14, 2026-05-30, 2026-06-04, 2026-06-06, 2026-06-09, 2026-07-31.

#### Proposed joins

- Hoster label to tool → mapping_departments_tools.csv: many-to-one; matched 2002, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Use only unique label matches; Item is not a resource identifier.
- Cost center to department → mapping_departments_tools.csv: many-to-one; matched 1813, unmatched 0, blank 189, ambiguous 0, ownership conflicts 0. Distinct department associations only. Blank departments stay unknown, never default to IT.

Issue categories: `{"business_key_collision": 3, "coverage_gap": 1, "exact_duplicate_candidate": 3, "missing_identifier": 1, "missing_join_key": 1, "missing_value": 3, "project_id_variant": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Records dated within the baseline; drafts and duplicate candidates retained.

Rows: 1084; missing cells: 495; expected optional/non-applicable blanks: 1803; exact duplicate excess: 3; key collision groups: 3.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| Date | swiss_date / swiss_date | 0 / 0 / 0 | 2025-09-01 | 2026-08-31 |
| Item | text / text | 0 / 0 / 0 | None | None |
| Service | text / text | 0 / 0 / 0 | None | None |
| Quantity | number / number | 0 / 0 / 0 | 21.68 | 64040.17 |
| Unit | text / text | 0 / 0 / 0 | None | None |
| Amount_CHF | number / number | 16 / 16 / 0 | 1.58 | 44.96 |
| CostCenter | text / text | 98 / 98 / 0 | None | None |
| ProjectNumber | text / text | 381 / 381 / 0 | None | None |
| Accesses | number / number | 0 / 720 / 0 | 45.0 | 6282.0 |
| Remark | text / text | 0 / 1083 / 0 | None | None |

Categories: `{"Unit": {"GB": 360, "GB-day": 724}}`

Amount/credit counts (not cost totals): `[{"currency": "CHF", "charge_type": "reported", "rows": 1084, "missing": 16, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[{"column": "ProjectNumber", "proposed": "P-001", "variants": {"P-001": 169, "P001": 24, "p-001": 10}}, {"column": "ProjectNumber", "proposed": "P-002", "variants": {"P-002": 135, "P002": 18, "p-002": 11}}, {"column": "ProjectNumber", "proposed": "P-003", "variants": {"P-003": 77, "P003": 5, "p-003": 4}}, {"column": "ProjectNumber", "proposed": "P-005", "variants": {"P-005": 59, "P005": 9, "p-005": 8}}, {"column": "ProjectNumber", "proposed": "P-006", "variants": {"P-006": 47, "P006": 2, "p-006": 4}}, {"column": "ProjectNumber", "proposed": "P-007", "variants": {"P-007": 35, "P007": 5, "p-007": 3}}, {"column": "ProjectNumber", "proposed": "P-008", "variants": {"P-008": 35, "P008": 3, "p-008": 1}}, {"column": "ProjectNumber", "proposed": "P-010", "variants": {"P-010": 35, "P010": 4}}, {"column": "ProjectNumber", "proposed": "unknown", "variants": {"": 381}}]`

Coverage: `{"minimum": "2025-09-01", "maximum": "2026-08-31", "distinct_periods": 365, "cadence": "daily"}`
- Logging and monitoring: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-09, 2025-12-10, 2026-02-18, 2026-05-21, 2026-06-02, 2026-06-05; baseline absent periods: 2025-11-09, 2025-12-10, 2026-02-18, 2026-05-21, 2026-06-02, 2026-06-05.
- Project file storage: observation gap; lifetime/expected activity unverified; internal gaps: 2026-01-17, 2026-08-09; baseline absent periods: 2026-01-17, 2026-08-09.
- Web hosting and CDN: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-14, 2026-05-30, 2026-06-04, 2026-06-06, 2026-06-09, 2026-07-31; baseline absent periods: 2025-11-14, 2026-05-30, 2026-06-04, 2026-06-06, 2026-06-09, 2026-07-31.

#### Proposed joins

- Hoster label to tool → mapping_departments_tools.csv: many-to-one; matched 1084, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Use only unique label matches; Item is not a resource identifier.
- Cost center to department → mapping_departments_tools.csv: many-to-one; matched 986, unmatched 0, blank 98, ambiguous 0, ownership conflicts 0. Distinct department associations only. Blank departments stay unknown, never default to IT.

Issue categories: `{"business_key_collision": 3, "coverage_gap": 1, "exact_duplicate_candidate": 3, "missing_identifier": 1, "missing_join_key": 1, "missing_value": 3, "project_id_variant": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | hoster_invoice.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | Date | Parse documented swiss_date format; retain raw value. |
| resource_id | Item → mapping.tool | Proposed label lookup only if unique; otherwise unknown. |
| provider | constant Swiss hoster | Direct source value; no transformation in Phase 2. |
| cost_center | CostCenter | Direct source value; no transformation in Phase 2. |
| department | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| tool | Item | Direct source value; no transformation in Phase 2. |
| region | unknown | Not recorded or not applicable in this source; preserve null. |
| quantity | Quantity | Direct source value; no transformation in Phase 2. |
| unit | Unit | Direct source value; no transformation in Phase 2. |
| amount_original | Amount_CHF | Direct source value; no transformation in Phase 2. |
| currency | CHF | Direct source value; no transformation in Phase 2. |
| fx_rate | exchange_rates.csv | Phase 3: CHF=1; EUR/USD monthly CHF per foreign unit; missing rate → null. |
| cost_chf | Amount_CHF | Reported CHF for gateway/hoster; other currencies require monthly FX. No financial totals in Phase 2. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## data_platform_usage.csv

Role: Monitoring and utilization. Candidate key: date, resource_id, cluster. SHA-256: `b2e9eba3fc6b6ae5dc6af958cbfd88efc90a7a3a762b13c37a7bb40cc13c6092`.

### Full export profile

All records in the export.

Rows: 1333; missing cells: 0; expected optional/non-applicable blanks: 0; exact duplicate excess: 2; key collision groups: 2.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| date | date / date | 0 / 0 / 0 | 2024-11-01 | 2026-09-06 |
| resource_id | text / text | 0 / 0 / 0 | None | None |
| cluster | text / text | 0 / 0 / 0 | None | None |
| region | text / text | 0 / 0 / 0 | None | None |
| node_count | number / number | 0 / 0 / 0 | 8.0 | 20.0 |
| runtime_h | number / number | 0 / 0 / 0 | 24.0 | 24.0 |
| active_use_h | number / number | 0 / 0 / 0 | 0.0 | 24.0 |
| query_count | number / number | 0 / 0 / 0 | 0.0 | 7339.0 |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2024-11-01", "maximum": "2026-09-06", "distinct_periods": 675, "cadence": "daily"}`
- dp-dev: observation gap; lifetime/expected activity unverified; internal gaps: 2024-12-09, 2025-02-12, 2025-04-12, 2025-10-24, 2025-11-12, 2025-12-01, 2026-02-12, 2026-04-30, 2026-06-23, 2026-09-05; baseline absent periods: 2025-10-24, 2025-11-12, 2025-12-01, 2026-02-12, 2026-04-30, 2026-06-23.
- dp-prod: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-10, 2025-01-14, 2025-09-19, 2026-01-13, 2026-02-17, 2026-04-18, 2026-06-01, 2026-06-02, 2026-06-25; baseline absent periods: 2025-09-19, 2026-01-13, 2026-02-17, 2026-04-18, 2026-06-01, 2026-06-02, 2026-06-25.

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 1333, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.

Issue categories: `{"business_key_collision": 2, "coverage_gap": 1, "exact_duplicate_candidate": 2}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Records dated within the baseline; drafts and duplicate candidates retained.

Rows: 719; missing cells: 0; expected optional/non-applicable blanks: 0; exact duplicate excess: 2; key collision groups: 2.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| date | date / date | 0 / 0 / 0 | 2025-09-01 | 2026-08-31 |
| resource_id | text / text | 0 / 0 / 0 | None | None |
| cluster | text / text | 0 / 0 / 0 | None | None |
| region | text / text | 0 / 0 / 0 | None | None |
| node_count | number / number | 0 / 0 / 0 | 8.0 | 20.0 |
| runtime_h | number / number | 0 / 0 / 0 | 24.0 | 24.0 |
| active_use_h | number / number | 0 / 0 / 0 | 0.0 | 24.0 |
| query_count | number / number | 0 / 0 / 0 | 0.0 | 7339.0 |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2025-09-01", "maximum": "2026-08-31", "distinct_periods": 365, "cadence": "daily"}`
- dp-dev: observation gap; lifetime/expected activity unverified; internal gaps: 2025-10-24, 2025-11-12, 2025-12-01, 2026-02-12, 2026-04-30, 2026-06-23; baseline absent periods: 2025-10-24, 2025-11-12, 2025-12-01, 2026-02-12, 2026-04-30, 2026-06-23.
- dp-prod: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-19, 2026-01-13, 2026-02-17, 2026-04-18, 2026-06-01, 2026-06-02, 2026-06-25; baseline absent periods: 2025-09-19, 2026-01-13, 2026-02-17, 2026-04-18, 2026-06-01, 2026-06-02, 2026-06-25.

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 719, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.

Issue categories: `{"business_key_collision": 2, "coverage_gap": 1, "exact_duplicate_candidate": 2}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | data_platform_usage.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | date | Parse documented date format; retain raw value. |
| resource_id | resource_id | Azure path / AWS ARN suffix candidate; otherwise direct. Instance IDs are not pooled billing IDs. |
| provider | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_center | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| department | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| tool | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| region | region | Direct source value; no transformation in Phase 2. |
| quantity | unknown | Not recorded or not applicable in this source; preserve null. |
| unit | unknown | Not recorded or not applicable in this source; preserve null. |
| amount_original | unknown | Not recorded or not applicable in this source; preserve null. |
| currency | unknown | Not recorded or not applicable in this source; preserve null. |
| fx_rate | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_chf | unknown | Not recorded or not applicable in this source; preserve null. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## server_inventory.csv

Role: Asset inventory. Candidate key: server_id. SHA-256: `2c81d215df79c356c2c5ca7a4a5e8686125cae3cb871d4f97c1aaba2bdbdef2c`.

### Full export profile

Snapshot/master context, not historical baseline measurements.

Rows: 53; missing cells: 78; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| server_id | text / text | 0 / 0 / 0 | None | None |
| provider | text / text | 0 / 0 / 0 | None | None |
| region | text / text | 0 / 0 / 0 | None | None |
| vcpu | number / number | 0 / 0 / 0 | 0.5 | 8.0 |
| ram_gb | number / number | 0 / 0 / 0 | 1.0 | 56.0 |
| type | text / text | 0 / 0 / 0 | None | None |
| owner_cost_center | text / text | 10 / 10 / 0 | None | None |
| created | date / date | 0 / 0 / 0 | 2023-05-10 | 2026-02-02 |
| last_login | date / date | 0 / 0 / 0 | 2024-12-20 | 2026-09-05 |
| cpu_utilisation_30d_pct | number / number | 10 / 10 / 0 | 0.1 | 44.8 |
| ram_utilisation_30d_pct | number / number | 0 / 0 / 0 | 5.9 | 69.1 |
| runtime_h_30d | number / number | 0 / 0 / 0 | 22.0 | 720.0 |
| tags | text / text | 17 / 17 / 0 | None | None |
| operating_system | text / text | 0 / 0 / 0 | None | None |
| patch_level | text / text | 0 / 0 / 0 | None | None |
| project_id | text / text | 20 / 20 / 0 | None | None |
| environment | text / text | 0 / 0 / 0 | None | None |
| criticality | text / text | 21 / 21 / 0 | None | None |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[{"column": "project_id", "proposed": "P-001", "variants": {"P-001": 9, "P001": 1}}, {"column": "project_id", "proposed": "P-002", "variants": {"P-002": 3}}, {"column": "project_id", "proposed": "P-004", "variants": {"P-004": 9, "P004": 1}}, {"column": "project_id", "proposed": "P-008", "variants": {"P-008": 1}}, {"column": "project_id", "proposed": "P-014", "variants": {"P-014": 7, "P014": 1}}, {"column": "project_id", "proposed": "P-015", "variants": {"P-015": 1}}, {"column": "project_id", "proposed": "unknown", "variants": {"": 20}}]`

Coverage: `null`

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 0, unmatched 53, blank 0, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.
- Cost center to department → mapping_departments_tools.csv: many-to-one; matched 43, unmatched 0, blank 10, ambiguous 0, ownership conflicts 0. Distinct department associations only. Blank departments stay unknown, never default to IT.

Issue categories: `{"missing_join_key": 1, "missing_value": 5, "project_id_variant": 1, "unmatched_join": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Snapshot/master context, not historical baseline measurements.

Rows: 53; missing cells: 78; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| server_id | text / text | 0 / 0 / 0 | None | None |
| provider | text / text | 0 / 0 / 0 | None | None |
| region | text / text | 0 / 0 / 0 | None | None |
| vcpu | number / number | 0 / 0 / 0 | 0.5 | 8.0 |
| ram_gb | number / number | 0 / 0 / 0 | 1.0 | 56.0 |
| type | text / text | 0 / 0 / 0 | None | None |
| owner_cost_center | text / text | 10 / 10 / 0 | None | None |
| created | date / date | 0 / 0 / 0 | 2023-05-10 | 2026-02-02 |
| last_login | date / date | 0 / 0 / 0 | 2024-12-20 | 2026-09-05 |
| cpu_utilisation_30d_pct | number / number | 10 / 10 / 0 | 0.1 | 44.8 |
| ram_utilisation_30d_pct | number / number | 0 / 0 / 0 | 5.9 | 69.1 |
| runtime_h_30d | number / number | 0 / 0 / 0 | 22.0 | 720.0 |
| tags | text / text | 17 / 17 / 0 | None | None |
| operating_system | text / text | 0 / 0 / 0 | None | None |
| patch_level | text / text | 0 / 0 / 0 | None | None |
| project_id | text / text | 20 / 20 / 0 | None | None |
| environment | text / text | 0 / 0 / 0 | None | None |
| criticality | text / text | 21 / 21 / 0 | None | None |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[{"column": "project_id", "proposed": "P-001", "variants": {"P-001": 9, "P001": 1}}, {"column": "project_id", "proposed": "P-002", "variants": {"P-002": 3}}, {"column": "project_id", "proposed": "P-004", "variants": {"P-004": 9, "P004": 1}}, {"column": "project_id", "proposed": "P-008", "variants": {"P-008": 1}}, {"column": "project_id", "proposed": "P-014", "variants": {"P-014": 7, "P014": 1}}, {"column": "project_id", "proposed": "P-015", "variants": {"P-015": 1}}, {"column": "project_id", "proposed": "unknown", "variants": {"": 20}}]`

Coverage: `null`

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 0, unmatched 53, blank 0, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.
- Cost center to department → mapping_departments_tools.csv: many-to-one; matched 43, unmatched 0, blank 10, ambiguous 0, ownership conflicts 0. Distinct department associations only. Blank departments stay unknown, never default to IT.

Issue categories: `{"missing_join_key": 1, "missing_value": 5, "project_id_variant": 1, "unmatched_join": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | server_inventory.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | unknown | Not recorded or not applicable in this source; preserve null. |
| resource_id | server_id | Azure path / AWS ARN suffix candidate; otherwise direct. Instance IDs are not pooled billing IDs. |
| provider | provider | Direct source value; no transformation in Phase 2. |
| cost_center | owner_cost_center | Direct source value; no transformation in Phase 2. |
| department | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| tool | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| region | region | Direct source value; no transformation in Phase 2. |
| quantity | unknown | Not recorded or not applicable in this source; preserve null. |
| unit | unknown | Not recorded or not applicable in this source; preserve null. |
| amount_original | unknown | Not recorded or not applicable in this source; preserve null. |
| currency | unknown | Not recorded or not applicable in this source; preserve null. |
| fx_rate | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_chf | unknown | Not recorded or not applicable in this source; preserve null. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## server_metrics_weekly.csv

Role: Monitoring and utilization. Candidate key: week_start, server_id. SHA-256: `77f2dd2f514347138d1a06e2d4c77356ef34ffd14552d3f94d4c07361b676299`.

### Full export profile

Weekly intervals overlapping the period; no proration.

Rows: 3161; missing cells: 0; expected optional/non-applicable blanks: 3079; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| week_start | date / date | 0 / 0 / 0 | 2024-10-28 | 2026-08-31 |
| server_id | text / text | 0 / 0 / 0 | None | None |
| cpu_avg_pct | number / number | 0 / 0 / 0 | 0.1 | 79.7 |
| cpu_max_pct | number / number | 0 / 0 / 0 | 0.1 | 100.0 |
| ram_avg_pct | number / number | 0 / 0 / 0 | 5.3 | 75.8 |
| network_gb | number / number | 0 / 0 / 0 | 0.03 | 154.12 |
| uptime_h | number / number | 0 / 0 / 0 | 0.0 | 168.0 |
| gpu_avg_pct | number / number | 0 / 3079 / 0 | 1.2 | 43.8 |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2024-10-28", "maximum": "2026-08-31", "distinct_periods": 97, "cadence": "weekly"}`
- app-01: observation gap; lifetime/expected activity unverified; internal gaps: 2025-06-23, 2025-08-11, 2025-09-22, 2025-09-29, 2025-12-22, 2026-05-04; baseline absent periods: 2025-09-22, 2025-09-29, 2025-12-22, 2026-05-04.
- app-02: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-04, 2025-01-20, 2026-07-06; baseline absent periods: 2026-07-06.
- app-03: observation gap; lifetime/expected activity unverified; internal gaps: 2024-12-09, 2025-04-14, 2025-04-21; baseline absent periods: none.
- app-04: observation gap; lifetime/expected activity unverified; internal gaps: 2025-01-27, 2025-05-19, 2026-06-15; baseline absent periods: 2026-06-15.
- app-05: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-16; baseline absent periods: 2026-02-16.
- app-06: observation gap; lifetime/expected activity unverified; internal gaps: 2026-05-18, 2026-08-17; baseline absent periods: 2026-05-18, 2026-08-17.
- app-07: observation gap; lifetime/expected activity unverified; internal gaps: 2025-06-23, 2025-09-29, 2026-07-13; baseline absent periods: 2025-09-29, 2026-07-13.
- app-08: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-22, 2025-11-03; baseline absent periods: 2025-09-22, 2025-11-03.
- app-09: observation gap; lifetime/expected activity unverified; internal gaps: 2025-04-14, 2025-05-05, 2025-07-07, 2025-07-28, 2026-02-02; baseline absent periods: 2026-02-02.
- app-10: observation gap; lifetime/expected activity unverified; internal gaps: 2025-05-19, 2025-08-04; baseline absent periods: none.
- app-11: observation gap; lifetime/expected activity unverified; internal gaps: 2026-04-13; baseline absent periods: 2026-04-13.
- app-12: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-04, 2025-07-07, 2026-03-02, 2026-06-01; baseline absent periods: 2026-03-02, 2026-06-01.
- build-agent-old: observation gap; lifetime/expected activity unverified; internal gaps: 2024-12-23, 2025-06-16, 2026-06-29; baseline absent periods: 2026-06-29.
- gpu-ml-01: observation gap; lifetime/expected activity unverified; internal gaps: 2025-06-09, 2025-12-22; baseline absent periods: 2025-12-22.
- poc-ki-2024: observation gap; lifetime/expected activity unverified; internal gaps: 2025-06-23, 2026-01-12, 2026-02-09, 2026-07-27; baseline absent periods: 2026-01-12, 2026-02-09, 2026-07-27.
- qa-regression-01: observation gap; lifetime/expected activity unverified; internal gaps: 2025-06-09, 2026-02-02; baseline absent periods: 2026-02-02.
- qa-regression-02: observation gap; lifetime/expected activity unverified; internal gaps: 2026-06-08; baseline absent periods: 2026-06-08.
- sbx-alex-01: observation gap; lifetime/expected activity unverified; internal gaps: 2026-04-06; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-04-06.
- sbx-alex-07: observation gap; lifetime/expected activity unverified; internal gaps: 2026-07-13; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-07-13.
- sbx-alex-13: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-alex-19: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-bea-02: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-bea-08: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-bea-14: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-bea-20: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-chris-03: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-16, 2026-08-10; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-16, 2026-08-10.
- sbx-chris-09: observation gap; lifetime/expected activity unverified; internal gaps: 2026-05-25; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-05-25.
- sbx-chris-15: observation gap; lifetime/expected activity unverified; internal gaps: 2026-03-16, 2026-05-11; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-03-16, 2026-05-11.
- sbx-chris-21: observation gap; lifetime/expected activity unverified; internal gaps: 2026-04-13; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-04-13.
- sbx-dana-04: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-dana-10: observation gap; lifetime/expected activity unverified; internal gaps: 2026-08-17; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-08-17.
- sbx-dana-16: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-23, 2026-08-24; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-02, 2026-02-23, 2026-08-24.
- sbx-dana-22: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-eli-05: observation gap; lifetime/expected activity unverified; internal gaps: 2026-04-27; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-04-27.
- sbx-eli-11: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-09, 2026-08-24; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-09, 2026-08-24.
- sbx-eli-17: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-eli-23: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-fay-06: observation gap; lifetime/expected activity unverified; internal gaps: 2026-04-06, 2026-06-29, 2026-07-06; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-04-06, 2026-06-29, 2026-07-06.
- sbx-fay-12: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-16, 2026-06-22; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-16, 2026-06-22.
- sbx-fay-18: observation gap; lifetime/expected activity unverified; internal gaps: 2026-03-23, 2026-04-20; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-03-23, 2026-04-20.
- sbx-fay-24: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-09, 2026-02-23, 2026-04-20, 2026-06-08, 2026-06-29; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-09, 2026-02-23, 2026-04-20, 2026-06-08, 2026-06-29.
- test-01: observation gap; lifetime/expected activity unverified; internal gaps: 2025-04-07, 2025-04-14, 2026-02-16; baseline absent periods: 2026-02-16.
- test-02: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-10; baseline absent periods: 2025-11-10.
- test-03: observation gap; lifetime/expected activity unverified; internal gaps: 2025-05-19, 2025-07-28, 2026-06-15; baseline absent periods: 2026-06-15.
- test-04: observation gap; lifetime/expected activity unverified; internal gaps: 2025-12-29, 2026-01-05, 2026-04-27; baseline absent periods: 2025-12-29, 2026-01-05, 2026-04-27.
- test-05: observation gap; lifetime/expected activity unverified; internal gaps: 2025-06-09, 2025-09-15, 2025-11-03; baseline absent periods: 2025-09-15, 2025-11-03.
- test-06: observation gap; lifetime/expected activity unverified; internal gaps: 2026-03-30; baseline absent periods: 2026-03-30.
- test-07: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-24, 2026-04-27, 2026-06-08; baseline absent periods: 2025-11-24, 2026-04-27, 2026-06-08.
- test-08: observation gap; lifetime/expected activity unverified; internal gaps: 2025-07-21, 2026-05-18, 2026-07-27, 2026-08-03; baseline absent periods: 2026-05-18, 2026-07-27, 2026-08-03.
- uat-portal: observation gap; lifetime/expected activity unverified; internal gaps: 2025-04-07, 2025-06-30; baseline absent periods: none.
- uat-shop: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-17, 2026-07-13; baseline absent periods: 2025-11-17, 2026-07-13.

#### Proposed joins

- Resource / asset mapping → server_inventory.csv: many-to-one; matched 3161, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.

Issue categories: `{"coverage_gap": 1, "weekly_boundary_overlap": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Weekly intervals overlapping the period; no proration.

Rows: 2213; missing cells: 0; expected optional/non-applicable blanks: 2161; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| week_start | date / date | 0 / 0 / 0 | 2025-09-01 | 2026-08-31 |
| server_id | text / text | 0 / 0 / 0 | None | None |
| cpu_avg_pct | number / number | 0 / 0 / 0 | 0.1 | 79.7 |
| cpu_max_pct | number / number | 0 / 0 / 0 | 0.1 | 100.0 |
| ram_avg_pct | number / number | 0 / 0 / 0 | 5.3 | 75.8 |
| network_gb | number / number | 0 / 0 / 0 | 0.04 | 154.12 |
| uptime_h | number / number | 0 / 0 / 0 | 0.0 | 168.0 |
| gpu_avg_pct | number / number | 0 / 2161 / 0 | 4.8 | 43.8 |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2025-09-01", "maximum": "2026-08-31", "distinct_periods": 53, "cadence": "weekly"}`
- app-01: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-22, 2025-09-29, 2025-12-22, 2026-05-04; baseline absent periods: 2025-09-22, 2025-09-29, 2025-12-22, 2026-05-04.
- app-02: observation gap; lifetime/expected activity unverified; internal gaps: 2026-07-06; baseline absent periods: 2026-07-06.
- app-04: observation gap; lifetime/expected activity unverified; internal gaps: 2026-06-15; baseline absent periods: 2026-06-15.
- app-05: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-16; baseline absent periods: 2026-02-16.
- app-06: observation gap; lifetime/expected activity unverified; internal gaps: 2026-05-18, 2026-08-17; baseline absent periods: 2026-05-18, 2026-08-17.
- app-07: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-29, 2026-07-13; baseline absent periods: 2025-09-29, 2026-07-13.
- app-08: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-22, 2025-11-03; baseline absent periods: 2025-09-22, 2025-11-03.
- app-09: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-02; baseline absent periods: 2026-02-02.
- app-11: observation gap; lifetime/expected activity unverified; internal gaps: 2026-04-13; baseline absent periods: 2026-04-13.
- app-12: observation gap; lifetime/expected activity unverified; internal gaps: 2026-03-02, 2026-06-01; baseline absent periods: 2026-03-02, 2026-06-01.
- build-agent-old: observation gap; lifetime/expected activity unverified; internal gaps: 2026-06-29; baseline absent periods: 2026-06-29.
- gpu-ml-01: observation gap; lifetime/expected activity unverified; internal gaps: 2025-12-22; baseline absent periods: 2025-12-22.
- poc-ki-2024: observation gap; lifetime/expected activity unverified; internal gaps: 2026-01-12, 2026-02-09, 2026-07-27; baseline absent periods: 2026-01-12, 2026-02-09, 2026-07-27.
- qa-regression-01: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-02; baseline absent periods: 2026-02-02.
- qa-regression-02: observation gap; lifetime/expected activity unverified; internal gaps: 2026-06-08; baseline absent periods: 2026-06-08.
- sbx-alex-01: observation gap; lifetime/expected activity unverified; internal gaps: 2026-04-06; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-04-06.
- sbx-alex-07: observation gap; lifetime/expected activity unverified; internal gaps: 2026-07-13; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-07-13.
- sbx-alex-13: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-alex-19: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-bea-02: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-bea-08: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-bea-14: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-bea-20: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-chris-03: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-16, 2026-08-10; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-16, 2026-08-10.
- sbx-chris-09: observation gap; lifetime/expected activity unverified; internal gaps: 2026-05-25; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-05-25.
- sbx-chris-15: observation gap; lifetime/expected activity unverified; internal gaps: 2026-03-16, 2026-05-11; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-03-16, 2026-05-11.
- sbx-chris-21: observation gap; lifetime/expected activity unverified; internal gaps: 2026-04-13; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-04-13.
- sbx-dana-04: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-dana-10: observation gap; lifetime/expected activity unverified; internal gaps: 2026-08-17; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-08-17.
- sbx-dana-16: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-23, 2026-08-24; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-02, 2026-02-23, 2026-08-24.
- sbx-dana-22: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-eli-05: observation gap; lifetime/expected activity unverified; internal gaps: 2026-04-27; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-04-27.
- sbx-eli-11: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-09, 2026-08-24; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-09, 2026-08-24.
- sbx-eli-17: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-eli-23: observation gap; lifetime/expected activity unverified; internal gaps: none; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26.
- sbx-fay-06: observation gap; lifetime/expected activity unverified; internal gaps: 2026-04-06, 2026-06-29, 2026-07-06; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-04-06, 2026-06-29, 2026-07-06.
- sbx-fay-12: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-16, 2026-06-22; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-16, 2026-06-22.
- sbx-fay-18: observation gap; lifetime/expected activity unverified; internal gaps: 2026-03-23, 2026-04-20; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-03-23, 2026-04-20.
- sbx-fay-24: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-09, 2026-02-23, 2026-04-20, 2026-06-08, 2026-06-29; baseline absent periods: 2025-09-01, 2025-09-08, 2025-09-15, 2025-09-22, 2025-09-29, 2025-10-06, 2025-10-13, 2025-10-20, 2025-10-27, 2025-11-03, 2025-11-10, 2025-11-17, 2025-11-24, 2025-12-01, 2025-12-08, 2025-12-15, 2025-12-22, 2025-12-29, 2026-01-05, 2026-01-12, 2026-01-19, 2026-01-26, 2026-02-09, 2026-02-23, 2026-04-20, 2026-06-08, 2026-06-29.
- test-01: observation gap; lifetime/expected activity unverified; internal gaps: 2026-02-16; baseline absent periods: 2026-02-16.
- test-02: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-10; baseline absent periods: 2025-11-10.
- test-03: observation gap; lifetime/expected activity unverified; internal gaps: 2026-06-15; baseline absent periods: 2026-06-15.
- test-04: observation gap; lifetime/expected activity unverified; internal gaps: 2025-12-29, 2026-01-05, 2026-04-27; baseline absent periods: 2025-12-29, 2026-01-05, 2026-04-27.
- test-05: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-15, 2025-11-03; baseline absent periods: 2025-09-15, 2025-11-03.
- test-06: observation gap; lifetime/expected activity unverified; internal gaps: 2026-03-30; baseline absent periods: 2026-03-30.
- test-07: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-24, 2026-04-27, 2026-06-08; baseline absent periods: 2025-11-24, 2026-04-27, 2026-06-08.
- test-08: observation gap; lifetime/expected activity unverified; internal gaps: 2026-05-18, 2026-07-27, 2026-08-03; baseline absent periods: 2026-05-18, 2026-07-27, 2026-08-03.
- uat-shop: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-17, 2026-07-13; baseline absent periods: 2025-11-17, 2026-07-13.

#### Proposed joins

- Resource / asset mapping → server_inventory.csv: many-to-one; matched 2213, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.

Issue categories: `{"coverage_gap": 1, "weekly_boundary_overlap": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | server_metrics_weekly.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | week_start | Parse documented date format; retain raw value. |
| resource_id | server_id | Azure path / AWS ARN suffix candidate; otherwise direct. Instance IDs are not pooled billing IDs. |
| provider | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_center | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| department | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| tool | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| region | unknown | Not recorded or not applicable in this source; preserve null. |
| quantity | unknown | Not recorded or not applicable in this source; preserve null. |
| unit | unknown | Not recorded or not applicable in this source; preserve null. |
| amount_original | unknown | Not recorded or not applicable in this source; preserve null. |
| currency | unknown | Not recorded or not applicable in this source; preserve null. |
| fx_rate | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_chf | unknown | Not recorded or not applicable in this source; preserve null. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## ai_usage.csv

Role: Gateway usage with reported costs. Candidate key: date, resource_id, tool, department, task_type, provider, model_class, model, project_id. SHA-256: `9504ac11928543bdda384d338966fad32ad7c09b97a54e667a9f22ee60762011`.

### Full export profile

All records in the export.

Rows: 52856; missing cells: 22559; expected optional/non-applicable blanks: 0; exact duplicate excess: 87; key collision groups: 87.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| date | date / date | 0 / 0 / 0 | 2024-11-01 | 2026-09-06 |
| resource_id | text / text | 0 / 0 / 0 | None | None |
| tool | text / text | 0 / 0 / 0 | None | None |
| department | text / text | 0 / 0 / 0 | None | None |
| task_type | text / text | 0 / 0 / 0 | None | None |
| model_class | text / text | 0 / 0 / 0 | None | None |
| provider | text / text | 0 / 0 / 0 | None | None |
| model | text / text | 0 / 0 / 0 | None | None |
| requests | number / number | 0 / 0 / 0 | 1.0 | 338567.0 |
| tokens_in | number / number | 0 / 0 / 0 | 220.0 | 437866578.0 |
| tokens_in_cache | number / number | 0 / 0 / 0 | 0.0 | 6881245.0 |
| tokens_out | number / number | 1575 / 1575 / 0 | 181.0 | 11815961.0 |
| cost_chf | number / number | 0 / 0 / 0 | 0.0009 | 1153.3706 |
| project_id | text / text | 20984 / 20984 / 0 | None | None |

Categories: `{}`

Amount/credit counts (not cost totals): `[{"currency": "CHF", "charge_type": "reported", "rows": 52856, "missing": 0, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[{"column": "project_id", "proposed": "P-001", "variants": {"P-001": 690, "P001": 81, "p-001": 37}}, {"column": "project_id", "proposed": "P-005", "variants": {"P-005": 218, "P005": 14, "p-005": 9}}, {"column": "project_id", "proposed": "P-006", "variants": {"P-006": 48, "P006": 5, "p-006": 2}}, {"column": "project_id", "proposed": "P-007", "variants": {"P-007": 78, "P007": 8, "p-007": 3}}, {"column": "project_id", "proposed": "P-011", "variants": {"P-011": 342, "P011": 33, "p-011": 22}}, {"column": "project_id", "proposed": "P-013", "variants": {"P-013": 7691, "P013": 866, "p-013": 438}}, {"column": "project_id", "proposed": "P-014", "variants": {"P-014": 7188, "P014": 875, "p-014": 436}}, {"column": "project_id", "proposed": "P-015", "variants": {"P-015": 10868, "P015": 1293, "p-015": 627}}, {"column": "project_id", "proposed": "unknown", "variants": {"": 20984}}]`

Coverage: `{"minimum": "2024-11-01", "maximum": "2026-09-06", "distinct_periods": 675, "cadence": "daily"}`
- ai-agent: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-04, 2024-11-16, 2024-11-30, 2024-12-01, 2024-12-25, 2025-01-06, 2025-01-12, 2025-01-18, 2025-01-19, 2025-02-02, 2025-02-09, 2025-02-23, 2025-03-01, 2025-03-15, 2025-03-30, 2025-04-26, 2025-04-27, 2025-04-29, 2025-05-01, 2025-05-03, 2025-05-10, 2025-05-12, 2025-05-17, 2025-05-23, 2025-05-24, 2025-05-29, 2025-05-31, 2025-06-28, 2025-06-29, 2025-07-19, 2025-07-27, 2025-08-02, 2025-08-30, 2025-09-29, 2025-11-01, 2025-11-08, 2025-11-09, 2025-11-15, 2025-11-27, 2025-12-25, 2025-12-28, 2026-01-01, 2026-01-10, 2026-02-07, 2026-03-17, 2026-06-15, 2026-06-19, 2026-06-20; baseline absent periods: 2025-09-29, 2025-11-01, 2025-11-08, 2025-11-09, 2025-11-15, 2025-11-27, 2025-12-25, 2025-12-28, 2026-01-01, 2026-01-10, 2026-02-07, 2026-03-17, 2026-06-15, 2026-06-19, 2026-06-20.
- ai-agent2: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-03, 2024-11-09, 2024-11-10, 2024-11-16, 2024-11-17, 2024-11-23, 2024-11-24, 2024-11-30, 2024-12-01, 2024-12-07, 2024-12-08, 2024-12-14, 2024-12-15, 2024-12-21, 2024-12-22, 2024-12-26, 2024-12-28, 2024-12-29, 2025-01-01, 2025-01-04, 2025-01-05, 2025-01-09, 2025-01-11, 2025-01-12, 2025-01-19, 2025-01-25, 2025-01-26, 2025-02-01, 2025-02-08, 2025-02-09, 2025-02-16, 2025-02-22, 2025-02-23, 2025-03-01, 2025-03-02, 2025-03-08, 2025-03-09, 2025-03-15, 2025-03-22, 2025-03-23, 2025-03-29, 2025-03-30, 2025-04-05, 2025-04-06, 2025-04-12, 2025-04-13, 2025-04-18, 2025-04-19, 2025-04-21, 2025-04-26, 2025-04-27, 2025-04-30, 2025-05-01, 2025-05-03, 2025-05-04, 2025-05-10, 2025-05-11, 2025-05-17, 2025-05-25, 2025-05-29, 2025-06-01, 2025-06-07, 2025-06-09, 2025-06-12, 2025-06-14, 2025-06-15, 2025-06-22, 2025-06-28, 2025-06-29, 2025-07-05, 2025-07-06, 2025-07-12, 2025-07-13, 2025-07-18, 2025-07-19, 2025-07-20, 2025-07-26, 2025-07-27, 2025-08-01, 2025-08-03, 2025-08-09, 2025-08-10, 2025-08-14, 2025-08-16, 2025-08-17, 2025-08-22, 2025-08-23, 2025-08-30, 2025-08-31, 2025-09-07, 2025-09-14, 2025-09-20, 2025-09-21, 2025-09-27, 2025-09-28, 2025-10-04, 2025-10-11, 2025-10-12, 2025-10-18, 2025-10-19, 2025-10-23, 2025-10-25, 2025-10-26, 2025-11-01, 2025-11-02, 2025-11-08, 2025-11-15, 2025-11-16, 2025-11-20, 2025-11-22, 2025-11-23, 2025-12-06, 2025-12-07, 2025-12-13, 2025-12-14, 2025-12-21, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2026-01-01, 2026-01-03, 2026-01-04, 2026-01-10, 2026-01-17, 2026-01-18, 2026-01-24, 2026-02-01, 2026-02-07, 2026-02-08, 2026-02-15, 2026-02-21, 2026-02-22, 2026-02-28, 2026-03-01, 2026-03-07, 2026-03-08, 2026-03-14, 2026-03-21, 2026-03-28, 2026-03-29, 2026-04-05, 2026-04-06, 2026-04-25, 2026-05-02, 2026-05-10, 2026-05-17, 2026-05-24, 2026-05-30, 2026-05-31, 2026-06-13, 2026-06-27, 2026-06-29, 2026-07-04, 2026-07-05, 2026-07-11, 2026-07-18, 2026-07-25, 2026-07-26, 2026-08-01, 2026-08-08; baseline absent periods: 2025-09-07, 2025-09-14, 2025-09-20, 2025-09-21, 2025-09-27, 2025-09-28, 2025-10-04, 2025-10-11, 2025-10-12, 2025-10-18, 2025-10-19, 2025-10-23, 2025-10-25, 2025-10-26, 2025-11-01, 2025-11-02, 2025-11-08, 2025-11-15, 2025-11-16, 2025-11-20, 2025-11-22, 2025-11-23, 2025-12-06, 2025-12-07, 2025-12-13, 2025-12-14, 2025-12-21, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2026-01-01, 2026-01-03, 2026-01-04, 2026-01-10, 2026-01-17, 2026-01-18, 2026-01-24, 2026-02-01, 2026-02-07, 2026-02-08, 2026-02-15, 2026-02-21, 2026-02-22, 2026-02-28, 2026-03-01, 2026-03-07, 2026-03-08, 2026-03-14, 2026-03-21, 2026-03-28, 2026-03-29, 2026-04-05, 2026-04-06, 2026-04-25, 2026-05-02, 2026-05-10, 2026-05-17, 2026-05-24, 2026-05-30, 2026-05-31, 2026-06-13, 2026-06-27, 2026-06-29, 2026-07-04, 2026-07-05, 2026-07-11, 2026-07-18, 2026-07-25, 2026-07-26, 2026-08-01, 2026-08-08.
- ai-marketing: observation gap; lifetime/expected activity unverified; internal gaps: 2024-11-11, 2024-11-21, 2024-12-17, 2025-06-18, 2025-07-15, 2025-11-02, 2025-12-24, 2026-01-15, 2026-08-19; baseline absent periods: 2025-11-02, 2025-12-24, 2026-01-15, 2026-08-19.
- ai-quote: observation gap; lifetime/expected activity unverified; internal gaps: 2025-04-17, 2025-04-20, 2025-07-18, 2025-07-26, 2026-01-28, 2026-03-10, 2026-07-08; baseline absent periods: 2026-01-28, 2026-03-10, 2026-07-08.
- ai-report: observation gap; lifetime/expected activity unverified; internal gaps: 2024-12-01, 2024-12-31, 2025-04-03, 2025-04-30, 2025-05-16, 2025-07-04, 2025-07-17, 2025-08-10, 2025-09-17, 2026-01-20, 2026-03-04, 2026-05-07; baseline absent periods: 2025-09-17, 2026-01-20, 2026-03-04, 2026-05-07.

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 52856, unmatched 0, blank 0, ambiguous 0, ownership conflicts 48436. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.

Issue categories: `{"business_key_collision": 87, "coverage_gap": 1, "exact_duplicate_candidate": 87, "missing_identifier": 1, "missing_value": 2, "ownership_conflict": 1, "project_id_variant": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Records dated within the baseline; drafts and duplicate candidates retained.

Rows: 29470; missing cells: 12585; expected optional/non-applicable blanks: 0; exact duplicate excess: 87; key collision groups: 87.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| date | date / date | 0 / 0 / 0 | 2025-09-01 | 2026-08-31 |
| resource_id | text / text | 0 / 0 / 0 | None | None |
| tool | text / text | 0 / 0 / 0 | None | None |
| department | text / text | 0 / 0 / 0 | None | None |
| task_type | text / text | 0 / 0 / 0 | None | None |
| model_class | text / text | 0 / 0 / 0 | None | None |
| provider | text / text | 0 / 0 / 0 | None | None |
| model | text / text | 0 / 0 / 0 | None | None |
| requests | number / number | 0 / 0 / 0 | 1.0 | 338567.0 |
| tokens_in | number / number | 0 / 0 / 0 | 220.0 | 437866578.0 |
| tokens_in_cache | number / number | 0 / 0 / 0 | 0.0 | 6881245.0 |
| tokens_out | number / number | 876 / 876 / 0 | 186.0 | 11815961.0 |
| cost_chf | number / number | 0 / 0 / 0 | 0.0009 | 1153.3706 |
| project_id | text / text | 11709 / 11709 / 0 | None | None |

Categories: `{}`

Amount/credit counts (not cost totals): `[{"currency": "CHF", "charge_type": "reported", "rows": 29470, "missing": 0, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[{"column": "project_id", "proposed": "P-001", "variants": {"P-001": 376, "P001": 43, "p-001": 20}}, {"column": "project_id", "proposed": "P-005", "variants": {"P-005": 138, "P005": 6, "p-005": 5}}, {"column": "project_id", "proposed": "P-006", "variants": {"P-006": 25, "P006": 3, "p-006": 2}}, {"column": "project_id", "proposed": "P-007", "variants": {"P-007": 38, "P007": 7, "p-007": 2}}, {"column": "project_id", "proposed": "P-011", "variants": {"P-011": 192, "P011": 22, "p-011": 10}}, {"column": "project_id", "proposed": "P-013", "variants": {"P-013": 4274, "P013": 486, "p-013": 263}}, {"column": "project_id", "proposed": "P-014", "variants": {"P-014": 3962, "P014": 483, "p-014": 223}}, {"column": "project_id", "proposed": "P-015", "variants": {"P-015": 6119, "P015": 719, "p-015": 343}}, {"column": "project_id", "proposed": "unknown", "variants": {"": 11709}}]`

Coverage: `{"minimum": "2025-09-01", "maximum": "2026-08-31", "distinct_periods": 365, "cadence": "daily"}`
- ai-agent: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-29, 2025-11-01, 2025-11-08, 2025-11-09, 2025-11-15, 2025-11-27, 2025-12-25, 2025-12-28, 2026-01-01, 2026-01-10, 2026-02-07, 2026-03-17, 2026-06-15, 2026-06-19, 2026-06-20; baseline absent periods: 2025-09-29, 2025-11-01, 2025-11-08, 2025-11-09, 2025-11-15, 2025-11-27, 2025-12-25, 2025-12-28, 2026-01-01, 2026-01-10, 2026-02-07, 2026-03-17, 2026-06-15, 2026-06-19, 2026-06-20.
- ai-agent2: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-07, 2025-09-14, 2025-09-20, 2025-09-21, 2025-09-27, 2025-09-28, 2025-10-04, 2025-10-11, 2025-10-12, 2025-10-18, 2025-10-19, 2025-10-23, 2025-10-25, 2025-10-26, 2025-11-01, 2025-11-02, 2025-11-08, 2025-11-15, 2025-11-16, 2025-11-20, 2025-11-22, 2025-11-23, 2025-12-06, 2025-12-07, 2025-12-13, 2025-12-14, 2025-12-21, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2026-01-01, 2026-01-03, 2026-01-04, 2026-01-10, 2026-01-17, 2026-01-18, 2026-01-24, 2026-02-01, 2026-02-07, 2026-02-08, 2026-02-15, 2026-02-21, 2026-02-22, 2026-02-28, 2026-03-01, 2026-03-07, 2026-03-08, 2026-03-14, 2026-03-21, 2026-03-28, 2026-03-29, 2026-04-05, 2026-04-06, 2026-04-25, 2026-05-02, 2026-05-10, 2026-05-17, 2026-05-24, 2026-05-30, 2026-05-31, 2026-06-13, 2026-06-27, 2026-06-29, 2026-07-04, 2026-07-05, 2026-07-11, 2026-07-18, 2026-07-25, 2026-07-26, 2026-08-01, 2026-08-08; baseline absent periods: 2025-09-07, 2025-09-14, 2025-09-20, 2025-09-21, 2025-09-27, 2025-09-28, 2025-10-04, 2025-10-11, 2025-10-12, 2025-10-18, 2025-10-19, 2025-10-23, 2025-10-25, 2025-10-26, 2025-11-01, 2025-11-02, 2025-11-08, 2025-11-15, 2025-11-16, 2025-11-20, 2025-11-22, 2025-11-23, 2025-12-06, 2025-12-07, 2025-12-13, 2025-12-14, 2025-12-21, 2025-12-25, 2025-12-26, 2025-12-27, 2025-12-28, 2026-01-01, 2026-01-03, 2026-01-04, 2026-01-10, 2026-01-17, 2026-01-18, 2026-01-24, 2026-02-01, 2026-02-07, 2026-02-08, 2026-02-15, 2026-02-21, 2026-02-22, 2026-02-28, 2026-03-01, 2026-03-07, 2026-03-08, 2026-03-14, 2026-03-21, 2026-03-28, 2026-03-29, 2026-04-05, 2026-04-06, 2026-04-25, 2026-05-02, 2026-05-10, 2026-05-17, 2026-05-24, 2026-05-30, 2026-05-31, 2026-06-13, 2026-06-27, 2026-06-29, 2026-07-04, 2026-07-05, 2026-07-11, 2026-07-18, 2026-07-25, 2026-07-26, 2026-08-01, 2026-08-08.
- ai-marketing: observation gap; lifetime/expected activity unverified; internal gaps: 2025-11-02, 2025-12-24, 2026-01-15, 2026-08-19; baseline absent periods: 2025-11-02, 2025-12-24, 2026-01-15, 2026-08-19.
- ai-quote: observation gap; lifetime/expected activity unverified; internal gaps: 2026-01-28, 2026-03-10, 2026-07-08; baseline absent periods: 2026-01-28, 2026-03-10, 2026-07-08.
- ai-report: observation gap; lifetime/expected activity unverified; internal gaps: 2025-09-17, 2026-01-20, 2026-03-04, 2026-05-07; baseline absent periods: 2025-09-17, 2026-01-20, 2026-03-04, 2026-05-07.

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 29470, unmatched 0, blank 0, ambiguous 0, ownership conflicts 27030. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.

Issue categories: `{"business_key_collision": 87, "coverage_gap": 1, "exact_duplicate_candidate": 87, "missing_identifier": 1, "missing_value": 2, "ownership_conflict": 1, "project_id_variant": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | ai_usage.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | date | Parse documented date format; retain raw value. |
| resource_id | resource_id | Azure path / AWS ARN suffix candidate; otherwise direct. Instance IDs are not pooled billing IDs. |
| provider | provider | Direct source value; no transformation in Phase 2. |
| cost_center | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| department | department | Direct source value; no transformation in Phase 2. |
| tool | tool | Direct source value; no transformation in Phase 2. |
| region | unknown | Not recorded or not applicable in this source; preserve null. |
| quantity | unknown | Not recorded or not applicable in this source; preserve null. |
| unit | unknown | Not recorded or not applicable in this source; preserve null. |
| amount_original | cost_chf | Direct source value; no transformation in Phase 2. |
| currency | CHF | Direct source value; no transformation in Phase 2. |
| fx_rate | exchange_rates.csv | Phase 3: CHF=1; EUR/USD monthly CHF per foreign unit; missing rate → null. |
| cost_chf | cost_chf | Reported CHF for gateway/hoster; other currencies require monthly FX. No financial totals in Phase 2. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## ai_subscriptions.csv

Role: Contracts with activity observations. Candidate key: month, product, provider, cost_center, contract_status. SHA-256: `e97515c02392c8aa99927fd2c36d59b7dd47106b70f7cedb48a29b3eff6f4f9f`.

### Full export profile

All records in the export.

Rows: 261; missing cells: 0; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| month | date / date | 0 / 0 / 0 | 2024-11-01 | 2026-08-01 |
| product | text / text | 0 / 0 / 0 | None | None |
| provider | text / text | 0 / 0 / 0 | None | None |
| cost_center | text / text | 0 / 0 / 0 | None | None |
| licences_purchased | number / number | 0 / 0 / 0 | 4.0 | 36.0 |
| licences_active_30d | number / number | 0 / 0 / 0 | 0.0 | 25.0 |
| messages_30d | number / number | 0 / 0 / 0 | 0.0 | 8417.0 |
| price_per_seat | number / number | 0 / 0 / 0 | 21.0 | 30.0 |
| currency | text / text | 0 / 0 / 0 | None | None |
| amount | number / number | 0 / 0 / 0 | 97.38 | 1080.0 |
| contract_status | text / text | 0 / 0 / 0 | None | None |
| contract_end | date / date | 0 / 0 / 0 | 2026-11-30 | 2027-02-28 |
| notice_period_days | number / number | 0 / 0 / 0 | 30.0 | 30.0 |
| billing | text / text | 0 / 0 / 0 | None | None |

Categories: `{"billing": {"monthly": 261}, "contract_status": {"Draft": 24, "Final": 237}, "currency": {"USD": 261}}`

Amount/credit counts (not cost totals): `[{"currency": "USD", "charge_type": "Draft", "rows": 24, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "USD", "charge_type": "Final", "rows": 237, "missing": 0, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2024-11-01", "maximum": "2026-08-01", "distinct_periods": 22, "cadence": "monthly"}`

#### Proposed joins

- Cost center to department → mapping_departments_tools.csv: many-to-one; matched 261, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Distinct department associations only. Blank departments stay unknown, never default to IT.
- Transaction month to FX → exchange_rates.csv: many-to-one; matched 261, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Monthly EUR/USD CHF-per-unit rates; no conversion performed.

Issue categories: `{"draft_final_coexistence": 24}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Records dated within the baseline; drafts and duplicate candidates retained.

Rows: 169; missing cells: 0; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| month | date / date | 0 / 0 / 0 | 2025-09-01 | 2026-08-01 |
| product | text / text | 0 / 0 / 0 | None | None |
| provider | text / text | 0 / 0 / 0 | None | None |
| cost_center | text / text | 0 / 0 / 0 | None | None |
| licences_purchased | number / number | 0 / 0 / 0 | 4.0 | 36.0 |
| licences_active_30d | number / number | 0 / 0 / 0 | 0.0 | 24.0 |
| messages_30d | number / number | 0 / 0 / 0 | 0.0 | 8417.0 |
| price_per_seat | number / number | 0 / 0 / 0 | 21.0 | 30.0 |
| currency | text / text | 0 / 0 / 0 | None | None |
| amount | number / number | 0 / 0 / 0 | 100.0 | 1080.0 |
| contract_status | text / text | 0 / 0 / 0 | None | None |
| contract_end | date / date | 0 / 0 / 0 | 2026-11-30 | 2027-02-28 |
| notice_period_days | number / number | 0 / 0 / 0 | 30.0 | 30.0 |
| billing | text / text | 0 / 0 / 0 | None | None |

Categories: `{"billing": {"monthly": 169}, "contract_status": {"Draft": 13, "Final": 156}, "currency": {"USD": 169}}`

Amount/credit counts (not cost totals): `[{"currency": "USD", "charge_type": "Draft", "rows": 13, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "USD", "charge_type": "Final", "rows": 156, "missing": 0, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2025-09-01", "maximum": "2026-08-01", "distinct_periods": 12, "cadence": "monthly"}`

#### Proposed joins

- Cost center to department → mapping_departments_tools.csv: many-to-one; matched 169, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Distinct department associations only. Blank departments stay unknown, never default to IT.
- Transaction month to FX → exchange_rates.csv: many-to-one; matched 169, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Monthly EUR/USD CHF-per-unit rates; no conversion performed.

Issue categories: `{"draft_final_coexistence": 13}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | ai_subscriptions.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | month | Parse documented date format; retain raw value. |
| resource_id | unknown | Not recorded or not applicable in this source; preserve null. |
| provider | provider | Direct source value; no transformation in Phase 2. |
| cost_center | cost_center | Direct source value; no transformation in Phase 2. |
| department | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| tool | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| region | unknown | Not recorded or not applicable in this source; preserve null. |
| quantity | unknown | Not recorded or not applicable in this source; preserve null. |
| unit | unknown | Not recorded or not applicable in this source; preserve null. |
| amount_original | amount | Direct source value; no transformation in Phase 2. |
| currency | currency | Direct source value; no transformation in Phase 2. |
| fx_rate | exchange_rates.csv | Phase 3: CHF=1; EUR/USD monthly CHF per foreign unit; missing rate → null. |
| cost_chf | derived in Phase 3 | Reported CHF for gateway/hoster; other currencies require monthly FX. No financial totals in Phase 2. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## saas_contracts.csv

Role: Contracts with activity observations. Candidate key: month, contract, provider, cost_center, contract_status. SHA-256: `acb5f4d7b8e347b19d68f7181e0967b718e39cabd8e7e7d00df0b22d10c0d9d4`.

### Full export profile

All records in the export.

Rows: 1331; missing cells: 0; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| month | date / date | 0 / 0 / 0 | 2024-11-01 | 2026-08-01 |
| contract | text / text | 0 / 0 / 0 | None | None |
| provider | text / text | 0 / 0 / 0 | None | None |
| cost_center | text / text | 0 / 0 / 0 | None | None |
| licences_purchased | number / number | 0 / 0 / 0 | 5.0 | 43.0 |
| licences_active_30d | number / number | 0 / 0 / 0 | 1.0 | 39.0 |
| price_per_licence | number / number | 0 / 0 / 0 | 4.0 | 55.0 |
| currency | text / text | 0 / 0 / 0 | None | None |
| amount | number / number | 0 / 0 / 0 | 20.0 | 958.01 |
| contract_status | text / text | 0 / 0 / 0 | None | None |
| contract_end | date / date | 0 / 0 / 0 | 2026-10-31 | 2027-09-30 |
| notice_period_days | number / number | 0 / 0 / 0 | 30.0 | 90.0 |
| billing | text / text | 0 / 0 / 0 | None | None |

Categories: `{"billing": {"annual": 848, "monthly": 483}, "contract_status": {"Draft": 121, "Final": 1210}, "currency": {"CHF": 366, "EUR": 287, "USD": 678}}`

Amount/credit counts (not cost totals): `[{"currency": "CHF", "charge_type": "Draft", "rows": 36, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "CHF", "charge_type": "Final", "rows": 330, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "EUR", "charge_type": "Draft", "rows": 23, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "EUR", "charge_type": "Final", "rows": 264, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "USD", "charge_type": "Draft", "rows": 62, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "USD", "charge_type": "Final", "rows": 616, "missing": 0, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2024-11-01", "maximum": "2026-08-01", "distinct_periods": 22, "cadence": "monthly"}`

#### Proposed joins

- Cost center to department → mapping_departments_tools.csv: many-to-one; matched 1331, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Distinct department associations only. Blank departments stay unknown, never default to IT.
- Transaction month to FX → exchange_rates.csv: many-to-one; matched 1331, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Monthly EUR/USD CHF-per-unit rates; no conversion performed.

Issue categories: `{"draft_final_coexistence": 121}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Records dated within the baseline; drafts and duplicate candidates retained.

Rows: 729; missing cells: 0; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| month | date / date | 0 / 0 / 0 | 2025-09-01 | 2026-08-01 |
| contract | text / text | 0 / 0 / 0 | None | None |
| provider | text / text | 0 / 0 / 0 | None | None |
| cost_center | text / text | 0 / 0 / 0 | None | None |
| licences_purchased | number / number | 0 / 0 / 0 | 5.0 | 43.0 |
| licences_active_30d | number / number | 0 / 0 / 0 | 1.0 | 39.0 |
| price_per_licence | number / number | 0 / 0 / 0 | 4.0 | 55.0 |
| currency | text / text | 0 / 0 / 0 | None | None |
| amount | number / number | 0 / 0 / 0 | 20.0 | 958.01 |
| contract_status | text / text | 0 / 0 / 0 | None | None |
| contract_end | date / date | 0 / 0 / 0 | 2026-10-31 | 2027-09-30 |
| notice_period_days | number / number | 0 / 0 / 0 | 30.0 | 90.0 |
| billing | text / text | 0 / 0 / 0 | None | None |

Categories: `{"billing": {"annual": 468, "monthly": 261}, "contract_status": {"Draft": 69, "Final": 660}, "currency": {"CHF": 201, "EUR": 156, "USD": 372}}`

Amount/credit counts (not cost totals): `[{"currency": "CHF", "charge_type": "Draft", "rows": 21, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "CHF", "charge_type": "Final", "rows": 180, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "EUR", "charge_type": "Draft", "rows": 12, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "EUR", "charge_type": "Final", "rows": 144, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "USD", "charge_type": "Draft", "rows": 36, "missing": 0, "negative_count": 0, "negative_rows": []}, {"currency": "USD", "charge_type": "Final", "rows": 336, "missing": 0, "negative_count": 0, "negative_rows": []}]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2025-09-01", "maximum": "2026-08-01", "distinct_periods": 12, "cadence": "monthly"}`

#### Proposed joins

- Cost center to department → mapping_departments_tools.csv: many-to-one; matched 729, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Distinct department associations only. Blank departments stay unknown, never default to IT.
- Transaction month to FX → exchange_rates.csv: many-to-one; matched 729, unmatched 0, blank 0, ambiguous 0, ownership conflicts 0. Monthly EUR/USD CHF-per-unit rates; no conversion performed.

Issue categories: `{"draft_final_coexistence": 69}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | saas_contracts.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | month | Parse documented date format; retain raw value. |
| resource_id | unknown | Not recorded or not applicable in this source; preserve null. |
| provider | provider | Direct source value; no transformation in Phase 2. |
| cost_center | cost_center | Direct source value; no transformation in Phase 2. |
| department | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| tool | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| region | unknown | Not recorded or not applicable in this source; preserve null. |
| quantity | unknown | Not recorded or not applicable in this source; preserve null. |
| unit | unknown | Not recorded or not applicable in this source; preserve null. |
| amount_original | amount | Direct source value; no transformation in Phase 2. |
| currency | currency | Direct source value; no transformation in Phase 2. |
| fx_rate | exchange_rates.csv | Phase 3: CHF=1; EUR/USD monthly CHF per foreign unit; missing rate → null. |
| cost_chf | derived in Phase 3 | Reported CHF for gateway/hoster; other currencies require monthly FX. No financial totals in Phase 2. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## mapping_departments_tools.csv

Role: Master data. Candidate key: resource_id. SHA-256: `d12ba1c00fa43ff0f6e0f2128c6fc5f613ce84cca197f0fc4820566bb2e437e1`.

### Full export profile

Snapshot/master context, not historical baseline measurements.

Rows: 90; missing cells: 185; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| resource_id | text / text | 0 / 0 / 0 | None | None |
| tool | text / text | 0 / 0 / 0 | None | None |
| department | text / text | 1 / 1 / 0 | None | None |
| cost_center | text / text | 0 / 0 / 0 | None | None |
| responsible_role | text / text | 0 / 0 / 0 | None | None |
| environment | text / text | 14 / 14 / 0 | None | None |
| criticality | text / text | 30 / 30 / 0 | None | None |
| default_project | text / text | 69 / 69 / 0 | None | None |
| rechargeable | text / text | 71 / 71 / 0 | None | None |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[{"column": "default_project", "proposed": "P-001", "variants": {"P-001": 2, "p-001": 1}}, {"column": "default_project", "proposed": "P-002", "variants": {"P-002": 1, "p-002": 1}}, {"column": "default_project", "proposed": "P-003", "variants": {"P-003": 3}}, {"column": "default_project", "proposed": "P-004", "variants": {"P-004": 2}}, {"column": "default_project", "proposed": "P-005", "variants": {"P-005": 2}}, {"column": "default_project", "proposed": "P-013", "variants": {"P-013": 1}}, {"column": "default_project", "proposed": "P-015", "variants": {"P-015": 6, "P015": 1, "p-015": 1}}, {"column": "default_project", "proposed": "unknown", "variants": {"": 69}}]`

Coverage: `null`

#### Proposed joins

- Cost center to department → mapping_departments_tools.csv: many-to-one; matched 89, unmatched 1, blank 0, ambiguous 0, ownership conflicts 0. Distinct department associations only. Blank departments stay unknown, never default to IT.

Issue categories: `{"missing_value": 5, "project_id_variant": 1, "unmatched_join": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Snapshot/master context, not historical baseline measurements.

Rows: 90; missing cells: 185; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| resource_id | text / text | 0 / 0 / 0 | None | None |
| tool | text / text | 0 / 0 / 0 | None | None |
| department | text / text | 1 / 1 / 0 | None | None |
| cost_center | text / text | 0 / 0 / 0 | None | None |
| responsible_role | text / text | 0 / 0 / 0 | None | None |
| environment | text / text | 14 / 14 / 0 | None | None |
| criticality | text / text | 30 / 30 / 0 | None | None |
| default_project | text / text | 69 / 69 / 0 | None | None |
| rechargeable | text / text | 71 / 71 / 0 | None | None |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[{"column": "default_project", "proposed": "P-001", "variants": {"P-001": 2, "p-001": 1}}, {"column": "default_project", "proposed": "P-002", "variants": {"P-002": 1, "p-002": 1}}, {"column": "default_project", "proposed": "P-003", "variants": {"P-003": 3}}, {"column": "default_project", "proposed": "P-004", "variants": {"P-004": 2}}, {"column": "default_project", "proposed": "P-005", "variants": {"P-005": 2}}, {"column": "default_project", "proposed": "P-013", "variants": {"P-013": 1}}, {"column": "default_project", "proposed": "P-015", "variants": {"P-015": 6, "P015": 1, "p-015": 1}}, {"column": "default_project", "proposed": "unknown", "variants": {"": 69}}]`

Coverage: `null`

#### Proposed joins

- Cost center to department → mapping_departments_tools.csv: many-to-one; matched 89, unmatched 1, blank 0, ambiguous 0, ownership conflicts 0. Distinct department associations only. Blank departments stay unknown, never default to IT.

Issue categories: `{"missing_value": 5, "project_id_variant": 1, "unmatched_join": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | mapping_departments_tools.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | unknown | Not recorded or not applicable in this source; preserve null. |
| resource_id | resource_id | Azure path / AWS ARN suffix candidate; otherwise direct. Instance IDs are not pooled billing IDs. |
| provider | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_center | cost_center | Direct source value; no transformation in Phase 2. |
| department | department | Direct source value; no transformation in Phase 2. |
| tool | tool | Direct source value; no transformation in Phase 2. |
| region | unknown | Not recorded or not applicable in this source; preserve null. |
| quantity | unknown | Not recorded or not applicable in this source; preserve null. |
| unit | unknown | Not recorded or not applicable in this source; preserve null. |
| amount_original | unknown | Not recorded or not applicable in this source; preserve null. |
| currency | unknown | Not recorded or not applicable in this source; preserve null. |
| fx_rate | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_chf | unknown | Not recorded or not applicable in this source; preserve null. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## exchange_rates.csv

Role: Master data. Candidate key: month. SHA-256: `2a7689131f4c8ab12ee59c4f0d388e5711020729b547ae51dba78b66d764a291`.

### Full export profile

All records in the export.

Rows: 23; missing cells: 0; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| month | date / date | 0 / 0 / 0 | 2024-11-01 | 2026-09-01 |
| eur_chf | number / number | 0 / 0 / 0 | 0.9094 | 0.9548 |
| usd_chf | number / number | 0 / 0 / 0 | 0.773 | 0.9092 |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2024-11-01", "maximum": "2026-09-01", "distinct_periods": 23, "cadence": "monthly"}`

#### Proposed joins


Issue categories: `{}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Records dated within the baseline; drafts and duplicate candidates retained.

Rows: 12; missing cells: 0; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| month | date / date | 0 / 0 / 0 | 2025-09-01 | 2026-08-01 |
| eur_chf | number / number | 0 / 0 / 0 | 0.9094 | 0.9362 |
| usd_chf | number / number | 0 / 0 / 0 | 0.773 | 0.8107 |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2025-09-01", "maximum": "2026-08-01", "distinct_periods": 12, "cadence": "monthly"}`

#### Proposed joins


Issue categories: `{}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | exchange_rates.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | month | Parse documented date format; retain raw value. |
| resource_id | unknown | Not recorded or not applicable in this source; preserve null. |
| provider | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_center | unknown | Not recorded or not applicable in this source; preserve null. |
| department | unknown | Not recorded or not applicable in this source; preserve null. |
| tool | unknown | Not recorded or not applicable in this source; preserve null. |
| region | unknown | Not recorded or not applicable in this source; preserve null. |
| quantity | unknown | Not recorded or not applicable in this source; preserve null. |
| unit | unknown | Not recorded or not applicable in this source; preserve null. |
| amount_original | unknown | Not recorded or not applicable in this source; preserve null. |
| currency | unknown | Not recorded or not applicable in this source; preserve null. |
| fx_rate | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_chf | unknown | Not recorded or not applicable in this source; preserve null. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## it_tickets.csv

Role: Operational evidence. Candidate key: ticket_id. SHA-256: `cb8197c8739e091a656f03595d2da2b9f3f7e0dc39de116867ca9bc04073110e`.

### Full export profile

All records in the export.

Rows: 289; missing cells: 220; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| ticket_id | text / text | 0 / 0 / 0 | None | None |
| date | date / date | 0 / 0 / 0 | 2024-11-02 | 2026-09-01 |
| type | text / text | 0 / 0 / 0 | None | None |
| resource_id | text / text | 220 / 220 / 0 | None | None |
| title | text / text | 0 / 0 / 0 | None | None |
| description | text / text | 0 / 0 / 0 | None | None |
| status | text / text | 0 / 0 / 0 | None | None |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2024-11-02", "maximum": "2026-09-01", "distinct_periods": 231, "cadence": "events"}`

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 69, unmatched 0, blank 220, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.

Issue categories: `{"missing_join_key": 1, "missing_value": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Records dated within the baseline; drafts and duplicate candidates retained.

Rows: 165; missing cells: 125; expected optional/non-applicable blanks: 0; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| ticket_id | text / text | 0 / 0 / 0 | None | None |
| date | date / date | 0 / 0 / 0 | 2025-09-04 | 2026-08-30 |
| type | text / text | 0 / 0 / 0 | None | None |
| resource_id | text / text | 125 / 125 / 0 | None | None |
| title | text / text | 0 / 0 / 0 | None | None |
| description | text / text | 0 / 0 / 0 | None | None |
| status | text / text | 0 / 0 / 0 | None | None |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2025-09-04", "maximum": "2026-08-30", "distinct_periods": 126, "cadence": "events"}`

#### Proposed joins

- Resource / asset mapping → mapping_departments_tools.csv: many-to-one; matched 40, unmatched 0, blank 125, ambiguous 0, ownership conflicts 0. Suffix extraction is proposed only. Inventory instances are not automatically members of billable pools.

Issue categories: `{"missing_join_key": 1, "missing_value": 1}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | it_tickets.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | date | Parse documented date format; retain raw value. |
| resource_id | resource_id | Azure path / AWS ARN suffix candidate; otherwise direct. Instance IDs are not pooled billing IDs. |
| provider | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_center | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| department | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| tool | mapping_departments_tools.csv | Proposed verified resource/ownership lookup; conflicting or missing ownership stays unknown (Phase 3: Unallocated). |
| region | unknown | Not recorded or not applicable in this source; preserve null. |
| quantity | unknown | Not recorded or not applicable in this source; preserve null. |
| unit | unknown | Not recorded or not applicable in this source; preserve null. |
| amount_original | unknown | Not recorded or not applicable in this source; preserve null. |
| currency | unknown | Not recorded or not applicable in this source; preserve null. |
| fx_rate | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_chf | unknown | Not recorded or not applicable in this source; preserve null. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## business_calendar.csv

Role: Operational evidence. Candidate key: date. SHA-256: `29cc16057e21f0a5c79237ca3c70976884be1fa3825800fac4ffdb3bd6a118de`.

### Full export profile

All records in the export.

Rows: 675; missing cells: 0; expected optional/non-applicable blanks: 1248; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| date | date / date | 0 / 0 / 0 | 2024-11-01 | 2026-09-06 |
| weekday | text / text | 0 / 0 / 0 | None | None |
| workday | binary / binary | 0 / 0 / 0 | 0.0 | 1.0 |
| public_holiday | text / text | 0 / 657 / 0 | None | None |
| company_holidays | text / text | 0 / 591 / 0 | None | None |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2024-11-01", "maximum": "2026-09-06", "distinct_periods": 675, "cadence": "daily"}`

#### Proposed joins


Issue categories: `{}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Baseline export profile

Records dated within the baseline; drafts and duplicate candidates retained.

Rows: 365; missing cells: 0; expected optional/non-applicable blanks: 679; exact duplicate excess: 0; key collision groups: 0.

| Field | Expected / observed type | Missing / blank / invalid | Min | Max |
|---|---|---:|---|---|
| date | date / date | 0 / 0 / 0 | 2025-09-01 | 2026-08-31 |
| weekday | text / text | 0 / 0 / 0 | None | None |
| workday | binary / binary | 0 / 0 / 0 | 0.0 | 1.0 |
| public_holiday | text / text | 0 / 356 / 0 | None | None |
| company_holidays | text / text | 0 / 323 / 0 | None | None |

Categories: `{}`

Amount/credit counts (not cost totals): `[]`

Project spelling candidates: `[]`

Coverage: `{"minimum": "2025-09-01", "maximum": "2026-08-31", "distinct_periods": 365, "cadence": "daily"}`

#### Proposed joins


Issue categories: `{}`. Complete row references and bounded raw evidence are in `outputs/data_quality.json`.

### Canonical field mapping (proposed, not executed)

| Canonical field | Source | Rule / fallback |
|---|---|---|
| source_file | provenance | business_calendar.csv |
| source_row | provenance | 1-based logical CSV record, header is record 1; not physical line number. |
| event_date | date | Parse documented date format; retain raw value. |
| resource_id | unknown | Not recorded or not applicable in this source; preserve null. |
| provider | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_center | unknown | Not recorded or not applicable in this source; preserve null. |
| department | unknown | Not recorded or not applicable in this source; preserve null. |
| tool | unknown | Not recorded or not applicable in this source; preserve null. |
| region | unknown | Not recorded or not applicable in this source; preserve null. |
| quantity | unknown | Not recorded or not applicable in this source; preserve null. |
| unit | unknown | Not recorded or not applicable in this source; preserve null. |
| amount_original | unknown | Not recorded or not applicable in this source; preserve null. |
| currency | unknown | Not recorded or not applicable in this source; preserve null. |
| fx_rate | unknown | Not recorded or not applicable in this source; preserve null. |
| cost_chf | unknown | Not recorded or not applicable in this source; preserve null. |
| quality_flags | profiling issues | Attach source-row issues without deleting records. |

## Official templates

### template_baseline_and_assumptions.csv

Read-only official template; example measure rows are not proposed savings.

Headers (exact order): `parameter, must_or_bonus, value_low, value_mid, value_high, unit, source, calculation_or_assumption`

- total_cost_baseline_year_chf (CHF per year): unknown; factors/estimates or Phase 3+ calculation required
- total_energy_baseline_year_kwh (kWh per year): unknown; factors/estimates or Phase 3+ calculation required
- total_co2_location_based_baseline_year_kg (kg CO2 per year): unknown; factors/estimates or Phase 3+ calculation required
- total_co2_market_based_baseline_year_kg (kg CO2 per year): unknown; factors/estimates or Phase 3+ calculation required
- grid_mix_location_based_switzerland (kg CO2 per kWh): unknown; factors/estimates or Phase 3+ calculation required
- grid_mix_location_based_germany (kg CO2 per kWh): unknown; factors/estimates or Phase 3+ calculation required
- grid_mix_location_based_ireland (kg CO2 per kWh): unknown; factors/estimates or Phase 3+ calculation required
- grid_mix_market_based (kg CO2 per kWh): unknown; factors/estimates or Phase 3+ calculation required
- energy_per_vcpu_hour (kWh): unknown; factors/estimates or Phase 3+ calculation required
- energy_per_node_hour (kWh): unknown; factors/estimates or Phase 3+ calculation required
- energy_per_gpu_hour (kWh): unknown; factors/estimates or Phase 3+ calculation required
- energy_per_gb_storage_day (kWh): unknown; factors/estimates or Phase 3+ calculation required
- energy_per_1000_tokens (kWh): unknown; factors/estimates or Phase 3+ calculation required
- energy_per_subscription_message (kWh): unknown; factors/estimates or Phase 3+ calculation required
- pue (ratio): unknown; factors/estimates or Phase 3+ calculation required
- growth_per_year (percent): unknown; factors/estimates or Phase 3+ calculation required
- allocation_rule_shared_costs (text): unknown; factors/estimates or Phase 3+ calculation required

### template_measures_package.csv

Read-only official template; example measure rows are not proposed savings.

Headers (exact order): `measure_id, description, resource_or_source, change, effort_person_days, savings_cost_chf_per_year, savings_energy_kwh_per_year, savings_co2_kg_location_based, savings_co2_kg_market_based, risks_and_exceptions, assumptions_and_sources`


## Source relationships and next phases

Monitoring, assets and operational evidence are distinct from financial facts. Contract metadata (end, notice, billing) is not an event date. Inventory was exported as of 2026-09-06; 30-day values must not stand in for the entire baseline.

Energy/emissions factors, shared allocation, signed monthly FX conversion, Final-only financial selection, semantic deduplication and pooled asset relationships belong to Phase 3 and later. Unknown numeric fields remain null; ownership remains unknown until verified (Phase 3 display: Unallocated).
