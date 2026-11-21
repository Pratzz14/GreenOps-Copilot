"""Document the published package and baseline without recalculating their numeric fields."""

import csv
from collections import defaultdict
from decimal import Decimal
from itertools import groupby
from io import StringIO
import re

from src.profile import read_csv


BASELINE_METHODS = {
    "total_cost_baseline_year_chf": (
        "Formula: sum included original-currency line amounts × matched month/currency CHF-per-unit FX, "
        "plus separately modeled missing-amount charges. CHF uses 1. Credits keep their sign. Count each "
        "source charge once. Exact eligible Azure/AWS priced mirrors recover a missing amount inside recorded CHF. "
        "Missing metered costs require positive usage with resource, unit and FX. Imputed CHF = missing quantity × "
        "median of at least 3 positive same-source, resource, month, unit, currency and charge-type original-currency "
        "unit prices × FX. Missing FX, unsupported prices, unresolved duplicates, drafts and review lines receive no "
        "imputed amount. Annual billing does not multiply monthly contract rows. The recorded subtotal is the "
        "observed coverage reference. Lower and upper cost cells are blank because the model publishes no cost range."
    ),
    "total_energy_baseline_year_kwh": (
        "Formula: sum monthly supported activity × scenario IT intensity × PUE for IT-side workloads, plus "
        "facility estimates for tokens and messages. Azure/AWS/hoster metered units include vCPU-hours, vCore-hours, "
        "runner minutes ÷ 60, GPU-hours, node-hours and GB-days when compatible. The data platform's dp-dev and "
        "dp-prod observed node-hours replace corresponding Azure node-hour activity to prevent double counting. "
        "Gateway units = (input + output tokens) ÷ 1,000. Cached input is already included in input. Final "
        "subscription messages are a separate activity stream. Missing or unresolved activity stays unknown. "
        "M365 storage, billed Power BI capacity-days and network GB are planning quantities excluded from the "
        "official energy total. Generic SaaS electricity, unlinked servers and unsupported units have no credit."
    ),
    "total_co2_location_based_baseline_year_kg": (
        "Formula: sum supported facility kWh × the applicable location factor for the same scenario at each "
        "workload boundary. Frankfurt uses Germany consumption CO2, Dublin uses Ireland consumption CO2, Zurich "
        "uses Swiss consumption operating CO2e including imports, and mixed-EU AI text loads use the EEA generation "
        "CO2e proxy. The organizer header says CO2. The mixed calculation is reported as kg CO2e. Unknown locations, "
        "missing activity and unsupported conversions stay outside the subtotal. The Swiss lifecycle series, "
        "market-based certificates and planning-only network/capacity estimates are excluded."
    ),
    "grid_mix_location_based_switzerland": (
        "Operating CO2e, including imports, per kWh consumed. Low/mid/high correspond to 2024, provisional 2025 "
        "and 2022. Treat these as year-based sensitivities. The separate lifecycle range 0.057/0.090/0.135 "
        "kg CO2e/kWh includes upstream emissions and serves as context. A strictly comparable direct-CO2 figure "
        "including imports is unresolved. Apply the operating series once to supported Zurich facility kWh."
    ),
    "grid_mix_location_based_germany": (
        "Mid = 330 g ÷ 1,000 = 0.330 kg CO2/kWh; endpoints = mid × 0.90 or 1.10. Apply once to Frankfurt facility kWh."
    ),
    "grid_mix_location_based_ireland": (
        "Mid = 197.8 g ÷ 1,000 = 0.1978 kg CO2/kWh; endpoints = mid × 0.90 or 1.10. Apply once to Dublin facility kWh."
    ),
    "energy_per_vcpu_hour": (
        "Formula: allocated vCPU-hours × assumed 2/5/10 W per vCPU ÷ 1,000 × PUE. A managed vCore uses the same "
        "proxy. Runner minutes ÷ 60 × assumed 2/4/8 vCPUs × corresponding vCPU rate × PUE."
    ),
    "energy_per_node_hour": (
        "Formula: observed or separately metered node-hours × assumed average node watts (164/350/650) ÷ "
        "1,000 × PUE. Cluster node-hours are the energy quantity. Runtime and active hours determine pause eligibility."
    ),
    "energy_per_gpu_hour": (
        "Formula: billed GPU-hours × assumed IT kW (0.15/0.40/0.70) × PUE. Monitoring utilisation is a safety signal. "
        "The billed GPU and monitored instance require a verified link before operational change."
    ),
    "energy_per_gb_storage_day": (
        "Formula: compatible billed GB-days × disk floor 0.00000648 × overhead multiplier (1/3/10) × PUE. "
        "The disk-only floor uses decimal 20,000 GB. Plain GB transfer cannot be treated as GB-days."
    ),
    "energy_per_1000_tokens": (
        "Mid = 0.24 Wh ÷ 1,000 Wh per kWh × 1,000 ÷ assumed 500 tokens per prompt. Endpoints scale mid by 0.25 "
        "and 5. Apply to input plus output in blocks of 1,000. PUE already included."
    ),
    "energy_per_subscription_message": (
        "Mid = 0.24 Wh ÷ 1,000 Wh per kWh. Endpoints scale mid by 0.25 and 5. Multiply by Final subscription "
        "messages in each observation. PUE already included."
    ),
    "pue": "Facility kWh = IT kWh × PUE (1.09/1.35/1.54). PUE is a facility-to-IT energy ratio.",
    "allocation_rule_shared_costs": (
        "Use source tags and verified ownership, exact unique resource mapping when available, and the observed "
        "contract cost centre. Leave ambiguous ownership Unallocated. Keep pooled charges together. Project hours "
        "and FTE are diagnostic comparisons. Exact high-confidence server relationships support evidence; raw "
        "telemetry and suggested aliases cannot independently allocate invoices."
    ),
}

INFRASTRUCTURE_METHODS = {
    "resize-production-capacity": (
        "For an observed dp-prod day, require active hours ≤ 50% of runtime, accepted same-day positive Azure "
        "node-hour charges and eligible financial status. Exclude scheduler protection days and any day overlapping "
        "Finance close using data_platform_jobs.csv, business_calendar.csv and ticket T-1029. "
        "Avoided node-hours per matched day = min(observed node-hours × 5%/10%/15%, billed node-hours). "
        "Avoided CHF = sum(avoided units × recorded CHF / billed units). Before energy uses matched observed "
        "node-hours and after uses the remaining node-hours. Apply node intensity × PUE and Swiss operating grid "
        "to the same scenario. Pilot within observed low-activity windows with capacity validation and rollback."
    ),
    "resize-test-pool": (
        "Use accepted AWS vm-test usage in billed vCPU-hours. Preserve all linked scheduler days from "
        "data_platform_jobs.csv and the full "
        "March 2026 release freeze. The daily cap is 24 h × 32/24/16 vCPU, giving 768/576/384 vCPU-hours. "
        "Avoided units = max(0, billed units − cap) on each eligible invoice row. CHF = sum(recorded positive "
        "CHF × avoided units / billed units) for eligible charges. Before energy uses the entire billed pool, "
        "and after uses billed units less modeled avoided units. Apply vCPU intensity × PUE and Ireland grid. "
        "Confirm isolated DR capacity, test p95 under load, and restore prior capacity if acceptance fails."
    ),
    "schedule-development": (
        "On each day retain all runtime if observations are missing or it is day 1–3 of a calendar quarter. "
        "Otherwise retained hours = min(runtime, max(scenario floor of 16/12/8 h, active h + 2 h startup allowance)). "
        "Avoided node-hours = observed node-hours × (runtime − retained) / runtime, or zero if runtime is zero. "
        "CHF = sum(accepted same-day variable Azure usage CHF × min(avoided node-hours, billed node-hours) / "
        "billed node-hours) for positive billed units. Apply node factor × PUE and Germany grid to before and "
        "remaining units. Daily readings cannot prove a contiguous pause window. Verify job schedule and restart in a pilot."
    ),
}

INFRASTRUCTURE_DECISIONS = {
    "resize-production-capacity": (
        "Pilot a smaller production setup on quiet days",
        "Production data platform (dp-prod)",
        "In the central estimate, use 10% less computing capacity on qualifying quiet days. "
        "Keep the production service running throughout the pilot.",
        "Data Platform and Finance must approve the trial. Leave month-end close and protected jobs untouched. "
        "Check peak demand and job deadlines, and restore capacity if service worsens.",
    ),
    "resize-test-pool": (
        "Reduce portal testing capacity after go-live",
        "Customer portal test environment (vm-test)",
        "After the portal is accepted, test a 32-virtual-CPU limit. Drop to 24 only if performance tests pass. "
        "The central estimate assumes the 24-CPU limit.",
        "The test platform owner must confirm go-live, test performance and separate disaster recovery capacity. "
        "Keep full capacity for protected jobs and the release freeze. Restore it if acceptance checks fail.",
    ),
    "schedule-development": (
        "Pause the development platform during verified idle hours",
        "Development data platform (dp-dev)",
        "Have the platform team design a pause schedule. The central estimate keeps at least 12 hours per "
        "observed day, with extra time for actual work and startup when needed.",
        "The data platform owner must verify the hourly job schedule and test restart before enabling pauses. "
        "Keep the platform running throughout the first three days of each quarter for training.",
    ),
}

AI_SEATS = (
    "For each qualifying cost centre with three Final June–August observations, retained seats = maximum active seats. "
    "Reclaimable = August purchased − retained. Annual gross CHF = sum(reclaimable × August original-currency "
    "price per seat × August CHF FX × 12). Keep approved and pending demand covered. The workload is held fixed "
    "and the model credits zero avoided electricity and emissions."
)
SAAS_SEATS = (
    "For the same provider, product and cost centre, require one accepted Final record in each of June, July "
    "and August. Reclaimable = min(purchased − active across the three months). Annual gross CHF = reclaimable "
    "× August price per licence × August CHF FX × 12. An eligible renewal requires included positive pricing in "
    "all three months, a cost centre and an open notice deadline. Retained workload stays fixed, so electricity "
    "and emissions savings are zero."
)
RULES = (
    "Dashboard scan: clusters require ≥14 valid distinct dates, ≥70% selected-day coverage and ≤20% active runtime. "
    "Server scan requires ≥3 complete weeks and ≥75% coverage, mean CPU ≤5%, highest weekly peak ≤20%, "
    "mean RAM ≤40% and mean uptime ≥120 h/week. Seat scan flags a positive purchased-minus-active gap in the "
    "latest valid Final month and notes whether it recurs in the prior month. "
    "Recurring recommendation cluster flag: Monday-start complete weeks, at least 5 unique valid dates, >0 runtime and "
    "sum(active h) / sum(runtime h) ≤ 20%. Server flag: unique complete weekly record with avg CPU ≤5%, "
    "peak CPU ≤20%, avg RAM ≤40% and uptime ≥120 h. Both need ≥3 qualifying weeks, ≥50% of observed "
    "weeks qualifying, and a hit in the last four complete weeks. Minimum coverage is 70% for clusters "
    "and 75% for servers. The separate licence flag needs positive unused seats in all last three complete "
    "Final months, grouped by provider, product, cost centre and file. Persistent unused seats use the minimum "
    "monthly gap. Findings screen for review. A measure uses its own pricing, scope and protection checks."
)


def rows(db, sql, values):
    cursor = db.execute(sql, values)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def shown(value):
    return "unknown" if value is None else str(value)


def readable_date(value):
    return f"{value.day} {value:%b %Y}" if value else "To be confirmed"


def decision_fields(row, mid):
    identifier = row["measure_id"]
    if identifier in INFRASTRUCTURE_DECISIONS:
        title, scope, action, approval = INFRASTRUCTURE_DECISIONS[identifier]
    else:
        seats = re.match(r"(?:Remove|Reclaim) (\d+) (?:persistently unused )?seats\b", row["change"])
        if not seats or not identifier.startswith(("resize-saas-seats-", "resize-seats-")):
            return
        count = seats[1]
        scope = row["resource_or_source"]
        title = f"Remove {count} unused {scope} seats at renewal"
        centre_marker = " at renewal for cost centre "
        if centre_marker in row["description"]:
            scope = f"{scope} (cost centre {row['description'].rsplit(centre_marker, 1)[1]})"
        action = f"Use June–August seat usage to confirm demand, then renew with {count} fewer paid seats."
        approval = ("Procurement and the product owner must confirm demand, minimum seat commitments, "
                    "price and notice terms. Keep approved and pending requests covered.")
        if identifier == "resize-seats-anthropic" and "annual billing" in row["change"]:
            title = f"Remove {count} Claude seats and switch the rest to annual billing"
            action += " Ask for an annual quote for the remaining Claude Team Standard seats."
            approval += " Approve annual prepayment before accepting the quote."
    timing = f"Modeled start: {readable_date(mid['earliest_effective_date'])}."
    if mid["notice_deadline"]:
        timing += f" Give notice by {readable_date(mid['notice_deadline'])}."
    row.update(description=title, resource_or_source=scope, change=f"{action} {timing}",
               risks_and_exceptions=approval)


def baseline_details(db, run, base):
    factors = rows(db, """SELECT * FROM gold.factor WHERE run_id = ?
                         ORDER BY factor_id""", [run])
    climate = {item["factor_id"]: item for item in factors}
    spending = rows(db, """
        SELECT cost_stream, sum(recorded_cost_chf) AS recorded, sum(imputed_cost_chf) AS imputed,
               sum(included_rows) AS included, sum(missing_amount_rows) AS missing_amount,
               sum(missing_fx_rows) AS missing_fx, sum(review_rows) AS review
        FROM gold.cost_monthly WHERE run_id = ? GROUP BY cost_stream ORDER BY cost_stream
    """, [run])
    impact = rows(db, """
        SELECT location, sum(energy_kwh) AS kwh, sum(location_kg) AS kg,
               count(*) FILTER (WHERE energy_kwh IS NULL) AS unknown_energy,
               count(*) FILTER (WHERE location_kg IS NULL) AS unknown_carbon
        FROM gold.impact_monthly WHERE run_id = ? AND scenario = 'mid'
        GROUP BY location ORDER BY location
    """, [run])
    sources = {
        "total_cost_baseline_year_chf": "azure_costs.csv, aws_costs.csv, hoster_invoice.csv, ai_usage.csv, "
            "ai_subscriptions.csv, saas_contracts.csv, exchange_rates.csv; Silver cost_facts and cost_baseline",
        "total_energy_baseline_year_kwh": "azure_costs.csv, aws_costs.csv, hoster_invoice.csv, data_platform_usage.csv, "
            "ai_usage.csv, ai_subscriptions.csv; Gold impact_monthly and factor",
        "total_co2_location_based_baseline_year_kg": "Gold impact_monthly and factor; location fields on invoice, "
            "platform and AI sources; Swiss VSE, German UBA, Irish SEAI and EEA",
        "allocation_rule_shared_costs": "mapping_departments_tools.csv, invoice tags, contract cost centres, "
            "server_inventory.csv; Silver ownership and resource_relationships",
    }
    for row in base:
        name = row["parameter"]
        if row["must_or_bonus"] == "Bonus":
            continue
        details = [row["calculation_or_assumption"], BASELINE_METHODS.get(name, "")]
        if name == "total_cost_baseline_year_chf":
            details.append("Reconciliation by cost stream: " + "; ".join(
                f"{item['cost_stream']} recorded CHF {shown(item['recorded'])}, imputed CHF "
                f"{item['imputed'] if item['imputed'] is not None else 'none credited'}, "
                f"{item['included']} included, {item['missing_amount']} originally "
                f"missing amount, {item['missing_fx']} missing FX, {item['review']} review/quarantined"
                for item in spending
            ) + ". Missing-amount counts include rows subsequently imputed in Gold.")
        if name in ("total_energy_baseline_year_kwh", "total_co2_location_based_baseline_year_kg"):
            details.append("Mid by reported location: " + "; ".join(
                f"{item['location']}: {shown(item['kwh'])} kWh, {shown(item['kg'])} kg CO2e "
                f"({item['unknown_energy']} energy and {item['unknown_carbon']} emissions buckets unquantified)"
                for item in impact
            ) + ". Bucket counts describe monthly reporting groups and cannot be interpreted as source records.")
        if name == "total_co2_location_based_baseline_year_kg":
            proxy = climate.get("grid_eu_planning")
            if proxy:
                values = "/".join(shown(proxy[f"value_{case}"]) for case in ("low", "mid", "high"))
                details.append(f"Mixed-EU grid low/mid/high = {values} kg CO2e/kWh. {proxy['definition_and_rationale']}")
                sources[name] += "; " + proxy["source_reference"]
        if name == "allocation_rule_shared_costs":
            details.extend([RULES, "The detailed methodology and all 28 input roles are documented in docs/ASSUMPTIONS.md."])
        row["calculation_or_assumption"] = "\n".join(filter(None, details))
        if name in sources:
            row["source"] = " | ".join(filter(None, (row["source"], sources[name])))


def ranges(numbers):
    groups = groupby(enumerate(sorted(set(numbers))), key=lambda pair: pair[1] - pair[0])
    spans = []
    for _, values in groups:
        sequence = [value for _, value in values]
        spans.append(str(sequence[0]) if len(sequence) == 1 else f"{sequence[0]}–{sequence[-1]}")
    return ", ".join(spans)


def evidence_notes(evidence, contracts):
    files, seats = defaultdict(list), []
    for item in evidence:
        key = (item["source_file"], item["source_row"])
        if key[0] and key[1] is not None:
            files[key[0]].append(key[1])
        if key in contracts:
            row = contracts[key]
            price = row["price_per_seat"] or row["price_per_licence"]
            seats.append((row["cost_center"], row["reporting_month"], key,
                          f"{row['licences_purchased']} purchased / {row['licences_active_30d']} active, "
                          f"{row['currency']} {price} per seat, FX {row['fx_rate']} CHF per unit"))
    source_rows = "Case source rows (logical CSV rows, header is row 1): " + "; ".join(
        f"{name} ({len(set(numbers))} records): {ranges(numbers)}" for name, numbers in sorted(files.items())
    )
    detail = [source_rows]
    if seats:
        detail.append("Seat evidence by cost centre and month: " + "; ".join(
            f"{center or 'unallocated'} {month}: {values} ({name} row {number})"
            for center, month, (name, number), values in sorted(set(seats))
        ))
    return detail


def measure_details(db, run, package, base, silver):
    if not base:
        return
    contract_file = silver / "contracts.csv"
    contracts = {(row["source_file"], int(row["source_row"])): row
                 for row in read_csv(contract_file)[1]} if contract_file.is_file() else {}
    scenarios = defaultdict(list)
    for entry in rows(db, """
        SELECT pm.*, ms.* EXCLUDE (run_id, measure_id, scenario, horizon, evidence_set_id),
               m.notice_deadline, m.earliest_effective_date, m.safety_status, m.one_time_cash_chf,
               m.evidence_set_id AS decision_evidence, r.day_rate_chf, r.decision_as_of
        FROM gold.package_member pm
        JOIN gold.measure_scenario ms USING (run_id, measure_id, scenario, horizon)
        JOIN gold.measure m USING (run_id, measure_id)
        JOIN gold.analysis_run r USING (run_id)
        WHERE pm.run_id = ? AND pm.package_id = ?
        ORDER BY measure_id, CASE horizon WHEN 'steady_state' THEN 0 ELSE 1 END,
                 CASE scenario WHEN 'low' THEN 0 WHEN 'mid' THEN 1 ELSE 2 END
    """, [run, package]):
        scenarios[entry["measure_id"]].append(entry)
    evidence_by_set = defaultdict(list)
    for item in rows(db, """
        SELECT e.*, f.source_reference, f.value_low, f.value_mid, f.value_high, f.unit
        FROM gold.evidence e LEFT JOIN gold.factor f USING (run_id, factor_id)
        WHERE e.run_id = ? AND e.evidence_set_id IN (
          SELECT DISTINCT evidence_set_id FROM gold.package_member WHERE run_id = ? AND package_id = ?
        ) ORDER BY evidence_set_id, evidence_no
    """, [run, run, package]):
        evidence_by_set[item["evidence_set_id"]].append(item)
    for row in base:
        id_ = row["measure_id"]
        cases = scenarios[id_]
        mid = next(item for item in cases if item["horizon"] == "steady_state" and item["scenario"] == "mid")
        first_year = next(item for item in cases if item["horizon"] == "first_year" and item["scenario"] == "mid")
        evidence = evidence_by_set[mid["evidence_set_id"]]
        annual_billing = "annual billing" in row["change"]
        original_scope = row["resource_or_source"]
        original_risks = row["risks_and_exceptions"]
        decision_fields(row, mid)
        effort = Decimal(row["effort_person_days"]).normalize()
        detail = [
            f"Once in place: CHF {mid['credited_cost_chf']:,.2f} per year. "
            f"First 12 months after the decision: CHF {first_year['credited_cost_chf']:,.2f}, allowing for lead time.",
            f"Implementation budget: CHF {mid['credited_implementation_chf']:,.2f} "
            f"for {effort:f} person-days, including CHF {mid['one_time_cash_chf']:,.2f} in one-time cash.",
            "Calculation and evidence",
            f"Run {run}. Package {package}. Numeric columns use the central assumptions for a full year in operation. "
            f"Decision date {mid['decision_as_of']}. Gold resource {original_scope}. Rule status: {mid['safety_status']}.",
            f"Implementation = {row['effort_person_days']} person-days × CHF {mid['day_rate_chf']} + "
            f"CHF {mid['one_time_cash_chf']} one-time cash = CHF {mid['credited_implementation_chf']}.",
        ]
        if id_ in INFRASTRUCTURE_METHODS:
            detail.append(INFRASTRUCTURE_METHODS[id_])
        elif id_.startswith("resize-saas-seats-"):
            detail.append(SAAS_SEATS)
        elif id_.startswith("resize-seats-"):
            detail.append(AI_SEATS)
            if id_ == "resize-seats-anthropic" and annual_billing:
                detail.append("Add retained Claude Team Standard seats × (USD 25 monthly − USD 20 annual equivalent) "
                              "× August FX × 12. Confirm annual quote and prepayment. https://claude.com/pricing")
        detail += [item["detail"] for item in evidence if item["evidence_type"] == "assumption" and not item["factor_id"]]
        detail.append(f"Original review conditions: {original_risks}")
        detail.append("Credits: gross avoided CHF − new recurring CHF; before kWh − after kWh; before kg CO2e − "
                      "after kg CO2e. First 12 months prorate by calendar days from effective start to the decision "
                      "anniversary divided by total days in that horizon. Implementation is incurred once.")
        for item in cases:
            detail.append(
                f"{item['horizon']} {item['scenario']}: CHF {shown(item['gross_avoided_chf'])} gross − "
                f"{shown(item['new_recurring_chf'])} recurring = {shown(item['credited_cost_chf'])} net; "
                f"kWh {shown(item['before_energy_kwh'])} → {shown(item['after_energy_kwh'])} = "
                f"{shown(item['credited_energy_kwh'])} avoided; kg CO2e {shown(item['before_location_kg'])} → "
                f"{shown(item['after_location_kg'])} = {shown(item['credited_location_kg'])} avoided."
            )
        for item in evidence:
            if item["factor_id"]:
                values = "/".join(shown(item[f"value_{case}"]) for case in ("low", "mid", "high"))
                detail.append(f"{item['detail']} ({item['factor_id']}): {values} {item['unit']} low/mid/high. "
                              f"{item['source_reference']}")
        detail.extend(evidence_notes(evidence, contracts))
        detail.extend(item["detail"] for item in evidence if item["evidence_type"] == "ticket")
        detail.append(f"Contribution evidence {mid['evidence_set_id']}; decision evidence {mid['decision_evidence']}.")
        row["assumptions_and_sources"] = "\n".join(detail)
    base.sort(key=lambda row: (-Decimal(row["savings_cost_chf_per_year"]), row["measure_id"]))


def detailed_csv(db, run, package, artifact, *, baseline, silver):
    columns, contents = read_csv(artifact)
    if baseline:
        baseline_details(db, run, contents)
    else:
        measure_details(db, run, package, contents, silver)
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(contents)
    return output.getvalue().encode("utf-8-sig")
