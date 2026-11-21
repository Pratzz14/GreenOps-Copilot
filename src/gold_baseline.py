"""Source attribution, baseline estimates and evidence for a Gold run."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from functools import cached_property
from hashlib import sha256
from statistics import median

from src.factors import FACILITY_FACTORS, FACTORS, GRID, SCENARIOS
from src.profile import END, START, read_csv

STOP = END + timedelta(days=1)
ZERO = Decimal(0)
SCALE = Decimal("0.000000000001")
BILLING = {
    "azure_costs": ("quantity", "unit_of_measure", "resource_location"),
    "aws_costs": ("line_item_usage_amount", "pricing_unit", "product_region"),
    "hoster_invoice": ("quantity", "unit", None),
}
UNIT_FACTORS = {
    "vcpu-hour": ("vcpu", Decimal(1)),
    "vcore-hour": ("database_vcore", Decimal(1)),
    "runner-minute": ("build_runner", Decimal(1) / 60),
    "node-hour": ("node", Decimal(1)),
    "gpu-hour": ("gpu", Decimal(1)),
    "gb-day": ("storage", Decimal(1)),
}
STREAMS = {
    "azure_costs.csv": "cloud_invoice",
    "aws_costs.csv": "cloud_invoice",
    "hoster_invoice.csv": "hoster_invoice",
    "ai_usage.csv": "ai_gateway",
    "ai_subscriptions.csv": "ai_subscription",
    "saas_contracts.csv": "saas",
}
KNOWN_REGIONS = {
    "Switzerland (Zurich)": "Switzerland", "Germany (Frankfurt)": "Germany",
    "Ireland (Dublin)": "Ireland", "EU (mixed)": "Mixed",
}


def decimal(value):
    return Decimal(value) if value not in (None, "") else None


def rounded(value):
    return value.quantize(SCALE) if value is not None else None


def subtotal(values):
    known = [value for value in values if value is not None]
    return sum(known, ZERO) if known else None


def in_period(row):
    day = row["event_date"]
    return bool(day and START.isoformat() <= day < STOP.isoformat())


def accepted(row):
    return row["record_status"] == "accepted" and in_period(row)


def month(row):
    return f'{row["reporting_month"]}-01'


def key_for(*values):
    return sha256("\0".join(str(value) for value in values).encode()).hexdigest()[:24]


def region(raw):
    return KNOWN_REGIONS.get(raw, "Mixed" if raw and "mixed" in raw.lower() else "Unknown")


def estimate(quantity, factor, location, scenario):
    if quantity is None or factor is None:
        return None, None
    energy = quantity * FACTORS[factor].value(scenario)
    if factor not in FACILITY_FACTORS:
        energy *= FACTORS["pue"].value(scenario)
    grid = FACTORS[GRID[location]].value(scenario) if location in GRID else None
    return rounded(energy), rounded(energy * grid) if grid is not None else None


class GoldData:
    """Collect rows in dependency order before the transactional database write."""

    def __init__(self, run_id, silver, decision, supplemental=None):
        self.run_id = run_id
        self.silver = silver
        self.decision = decision
        self.supplemental = supplemental or {}
        self.tables = defaultdict(list)
        self.subjects = {}
        self.evidence_ids = set()
        self.source_cache = {}

    def source(self, name):
        if name not in self.source_cache:
            self.source_cache[name] = read_csv(self.silver / f"{name}.csv")[1]
        return self.source_cache[name]

    def add(self, table, **values):
        self.tables[table].append({"run_id": self.run_id, **values})

    def evidence(self, name, detail, rows=(), factors=(), kind="calculation"):
        identifier = key_for(name)
        if identifier in self.evidence_ids:
            raise ValueError(f"Evidence set generated twice: {name}")
        self.evidence_ids.add(identifier)
        self.add("evidence", evidence_set_id=identifier, evidence_no=1, evidence_type=kind,
                 detail=detail)
        number = 2
        for factor in dict.fromkeys(factors):
            self.add("evidence", evidence_set_id=identifier, evidence_no=number,
                     evidence_type="assumption", factor_id=factor, detail=FACTORS[factor].name)
            number += 1
        seen = set()
        for row in rows:
            record = row["record_id"]
            if record in seen:
                continue
            seen.add(record)
            ticket = row.get("ticket_id")
            self.add("evidence", evidence_set_id=identifier, evidence_no=number,
                     evidence_type="ticket" if ticket else "source_record",
                     source_file=row["source_file"], source_row=int(row["source_row"]),
                     source_record_id=record,
                     detail=(row.get("evidence_detail") or
                             (f'{ticket} · {row["title"]} · {row["description"]}' if ticket
                              else f'{row["source_file"]} row {row["source_row"]}')))
            number += 1
        return identifier

    def subject(self, provider, name, family, row=None, role=None):
        identifier = f"{family}:{key_for(provider, name, family)}"
        if identifier not in self.subjects:
            evidence = self.evidence(f"subject:{identifier}", f"{name} · {provider} · {family}",
                                     [row] if row else ())
            result = dict(subject_id=identifier, subject_type=family, subject_name=name,
                          responsible_role=role, evidence_set_id=evidence)
            self.add("subject", **result)
            self.subjects[identifier] = self.tables["subject"][-1]
        elif role and not self.subjects[identifier]["responsible_role"]:
            self.subjects[identifier]["responsible_role"] = role
        return identifier

    @cached_property
    def originals(self):
        return {row["record_id"]: row for table in STREAMS
                for row in self.source(table.removesuffix(".csv"))}

    @cached_property
    def finances(self):
        return {row["record_id"]: row for row in self.source("cost_facts")}


def dimensions(data, source, stream, fact=None):
    fact = fact or {}
    provider = fact.get("provider") or source.get("provider") or "Unknown"
    name = source.get("product") or source.get("contract") or source.get("resource_id") or "Unallocated"
    family = stream if stream in {"ai_subscription", "saas", "ai_gateway"} else "resource"
    subject = data.subject(provider, name, family, source)
    billing = BILLING.get(source["source_file"].removesuffix(".csv"))
    location = region(source.get(billing[2]) if billing else source.get("region"))
    if stream == "hoster_invoice":
        location = "Switzerland"
    if stream in {"ai_subscription", "saas", "ai_gateway"} and location == "Unknown":
        location = "Mixed"
    department = fact.get("reporting_department") or source.get("reporting_department") or "Unallocated"
    mapped_tool = source.get("mapped_tool") if family == "resource" else None
    tool = mapped_tool or fact.get("tool") or source.get("tool") or name
    return subject, provider, department, tool, location


def comparable_usage(data, fact):
    row = data.originals[fact["record_id"]]
    table = fact["source_file"].removesuffix(".csv")
    if table not in BILLING or not fact["resource_id"]:
        return None, None
    quantity_col, unit_col, _ = BILLING[table]
    if (table == "azure_costs" and row["charge_type"] != "Usage"
            or table == "aws_costs" and row["charge_category"] != "usage"):
        return None, None
    quantity = decimal(row[quantity_col])
    if quantity is None or quantity <= 0 or not row[unit_col]:
        return None, None
    return (table, fact["resource_id"], fact["reporting_month"], row[unit_col],
            fact["currency"], fact["charge_type"]), quantity


@dataclass(frozen=True)
class CostEstimate:
    amount_chf: Decimal
    target: dict
    comparables: tuple[dict, ...] = ()


def imputed_costs(data):
    prices = defaultdict(list)
    pending = []
    for fact in data.finances.values():
        if fact["financial_status"] not in {"included", "missing_amount"}:
            continue
        key, quantity = comparable_usage(data, fact)
        if key is None or not fact["fx_rate"]:
            continue
        if fact["financial_status"] == "missing_amount":
            pending.append((fact, key, quantity))
        elif decimal(fact["amount_original"]) > 0:
            prices[key].append((decimal(fact["amount_original"]) / quantity, fact))
    estimates = {}
    for fact, key, quantity in pending:
        match = prices[key]
        if len(match) < 3:
            continue
        rate = median(value for value, _ in match)
        fx = decimal(fact["fx_rate"])
        chf = rounded(quantity * rate * fx)
        sources = ", ".join(str(source["source_row"]) for _, source in match)
        fx_source = "CHF identity" if fact["currency"] == "CHF" else f"FX record {fact['fx_record_id']}"
        detail = (f'{fact["source_file"]} row {fact["source_row"]}: {quantity} {key[3]} × '
                  f'{rate:.8f} {fact["currency"]} median per {key[3]} × {fx} CHF per '
                  f'{fact["currency"]} = CHF {chf}. Same-file price rows: {sources}. {fx_source}.')
        estimates[fact["record_id"]] = CostEstimate(chf, dict(fact, evidence_detail=detail))
    return estimates


def build_cost(data, estimates=None):
    if estimates is None:
        estimates = imputed_costs(data)
    groups = defaultdict(list)
    unresolved_date = []
    for row in data.finances.values():
        status = row["financial_status"]
        if status not in {"included", "missing_amount", "missing_fx", "review", "quarantined"}:
            continue
        if not row["event_date"]:
            unresolved_date.append(row)
        if not in_period(row):
            continue
        stream = STREAMS[row["source_file"]]
        dims = dimensions(data, data.originals[row["record_id"]], stream, row)
        groups[month(row), *dims, stream].append(row)
    for group, rows in sorted(groups.items()):
        report_month, subject, provider, department, tool, location, stream = group
        count = Counter(row["financial_status"] for row in rows)
        amount = subtotal(decimal(row["cost_chf"]) for row in rows if row["financial_status"] == "included")
        recovered = [row for row in rows if row["financial_status"] == "included"
                     and row.get("matched_missing_record_id")]
        imputed = [estimates[row["record_id"]] for row in rows if row["record_id"] in estimates]
        estimated_chf = subtotal(estimate.amount_chf for estimate in imputed)
        evidence = data.evidence(("cost", group), "Sum included Silver CHF at source-record grain. "
                                 f"{len(imputed)} missing charges estimated separately using comparable billing evidence. "
                                 f"Imputed CHF: {estimated_chf}. Missing and review charges remain coverage exceptions.",
                                 [*(estimate.target for estimate in imputed),
                                  *(source for estimate in imputed for source in estimate.comparables), *rows,
                                  *(data.finances[row["matched_missing_record_id"]] for row in recovered)])
        data.add("cost_monthly", report_month=report_month, subject_id=subject, provider=provider,
                 department=department, tool=tool, location=location, cost_stream=stream,
                 recorded_cost_chf=amount, imputed_cost_chf=estimated_chf,
                 recovered_cost_chf=subtotal(decimal(row["cost_chf"]) for row in recovered),
                 included_rows=count["included"],
                 missing_amount_rows=count["missing_amount"], missing_fx_rows=count["missing_fx"],
                 review_rows=count["review"] + count["quarantined"], evidence_set_id=evidence)
    published = data.source("cost_baseline")[0]
    amounts = data.tables["cost_monthly"]
    checks = {"recorded_cost_chf": subtotal(r["recorded_cost_chf"] for r in amounts) or ZERO,
              "included": sum(r["included_rows"] for r in amounts),
              "missing_amount": sum(r["missing_amount_rows"] for r in amounts),
              "missing_fx": sum(r["missing_fx_rows"] for r in amounts)}
    if any(decimal(published[field]) != value for field, value in checks.items()):
        raise ValueError("Gold recorded costs and coverage counts do not reconcile to published Silver")
    coverage = "complete" if published["coverage_status"] == "recorded" else "partial"
    return coverage if checks["included"] else "unknown", unresolved_date


def build_licences(data):
    for row in data.source("contracts"):
        if not accepted(row) or row["contract_status"] != "Final":
            continue
        stream = STREAMS[row["source_file"]]
        subject, provider, department, _, _ = dimensions(data, row, stream, data.finances.get(row["record_id"]))
        price = decimal(row["price_per_seat"] or row["price_per_licence"])
        fx = decimal(row["fx_rate"])
        product = row["product"] or row["contract"]
        evidence = data.evidence(("licence", row["record_id"]),
                                 "Final monthly observation. Unit price multiplied by the Silver monthly CHF FX rate.",
                                 [row])
        data.add("licence_monthly", report_month=month(row), subject_id=subject,
                 contract_key=key_for(stream, provider, product, row["cost_center"]),
                 product_name=product, licence_type=stream, provider=provider, department=department,
                 purchased_seats=row["licences_purchased"] or None,
                 active_seats=row["licences_active_30d"] or None,
                 monthly_price_per_seat_chf=price * fx if price is not None and fx is not None else None,
                 billing_cycle=row["billing"] or None, contract_end=row["contract_end"] or None,
                 notice_period_days=row["notice_period_days"] or None, evidence_set_id=evidence)


def observations(data):
    for table, (quantity_col, unit_col, _) in BILLING.items():
        for row in data.source(table):
            if not in_period(row) or row["record_status"] == "duplicate":
                continue
            unit = row[unit_col].casefold()
            if table == "azure_costs" and row.get("charge_type") != "Usage":
                continue  # Azure credits affect CHF only.
            if table == "azure_costs" and row["resource_id"] in {"dp-dev", "dp-prod"} and unit == "node-hour":
                continue  # Daily platform observations own this workload boundary.
            if table == "aws_costs" and row.get("charge_category") != "usage":
                continue  # Financial-only fees and credits carry no physical activity.
            factor, scale = UNIT_FACTORS.get(unit, (None, Decimal(1)))
            quantity = decimal(row[quantity_col]) if accepted(row) else None
            stream = STREAMS[row["source_file"]]
            dims = dimensions(data, row, stream, data.finances.get(row["record_id"]))
            yield row, dims, f"{table}:{unit or 'unknown'}", factor, quantity * scale if quantity is not None else None
    for row in data.source("data_platform_usage"):
        if not in_period(row) or row["record_status"] == "duplicate":
            continue
        dims = dimensions(data, row, "cloud_invoice", {"provider": "Azure"})
        yield row, dims, "platform:observed-node-hours", "node", decimal(row["node_hours"]) if accepted(row) else None
    for row in data.source("ai_usage"):
        if not in_period(row) or row["record_status"] == "duplicate":
            continue
        dims = dimensions(data, row, "ai_gateway", data.finances.get(row["record_id"]))
        inbound, outbound = decimal(row["tokens_in"]), decimal(row["tokens_out"])
        quantity = (inbound + outbound) / 1000 if accepted(row) and inbound is not None and outbound is not None else None
        yield row, dims, "gateway:tokens", "tokens", quantity
    for row in data.source("contracts"):
        if not in_period(row) or row["contract_status"] != "Final" or row["record_status"] == "duplicate":
            continue
        stream = STREAMS[row["source_file"]]
        dims = dimensions(data, row, stream, data.finances.get(row["record_id"]))
        if stream == "ai_subscription":
            yield row, dims, "subscription:messages", "message", decimal(row["messages_30d"]) if accepted(row) else None
        else:
            yield row, dims, "saas:activity-unknown", None, None


def combine_coverage(values):
    states = set(values)
    if not states or states == {"unknown"}:
        return "unknown"
    return "complete" if states == {"complete"} else "partial"


def build_impact(data):
    groups = defaultdict(list)
    platform_dates = defaultdict(set)
    for row, dims, boundary, factor, quantity in observations(data):
        group = (month(row), *dims, boundary, factor)
        groups[group].append((row, quantity))
        if boundary.startswith("platform:") and quantity is not None:
            platform_dates[month(row), dims[0]].add(row["event_date"])
    for group, records in sorted(groups.items()):
        report_month, subject, provider, department, tool, location, boundary, factor = group
        rows, quantities = zip(*records)
        quantity = subtotal(quantities)
        partial = any(value is None for value in quantities)
        if boundary.startswith("platform:"):
            first_day = date.fromisoformat(report_month)
            next_month = (first_day + timedelta(days=32)).replace(day=1)
            partial |= len(platform_dates[report_month, subject]) < (next_month - first_day).days
        factors = [factor] if factor else []
        if factor and factor not in FACILITY_FACTORS:
            factors.append("pue")
        if location in GRID:
            factors.append(GRID[location])
        explanation = (f"{boundary}: observed activity × {factor} intensity. IT loads multiply by PUE once."
                       if factor else f"{boundary}: the export has no supported activity-to-energy conversion.")
        if partial:
            explanation += " Some qualifying observations are missing or unresolved."
        if location == "Switzerland":
            factors.append("grid_ch_operating")
        if location not in GRID or location == "Switzerland":
            explanation += " A compatible direct-CO2 grid factor is unavailable for this workload."
        evidence = data.evidence(("impact", group), explanation, rows, factors)
        for scenario in SCENARIOS:
            energy, carbon = estimate(quantity, factor, location, scenario)
            data.add("impact_monthly", report_month=report_month, subject_id=subject, provider=provider,
                     department=department, tool=tool, location=location, boundary_id=boundary,
                     scenario=scenario, energy_kwh=energy, location_kg=carbon,
                     swiss_operating_kg_co2e=(rounded(energy * FACTORS["grid_ch_operating"].value(scenario))
                                              if location == "Switzerland" and energy is not None else None),
                     energy_coverage="unknown" if energy is None else "partial" if partial else "complete",
                     carbon_coverage="unknown" if carbon is None else "partial" if partial else "complete",
                     evidence_set_id=evidence)
    impacts = data.tables["impact_monthly"]
    return (combine_coverage(row["energy_coverage"] for row in impacts),
            combine_coverage(row["carbon_coverage"] for row in impacts))
