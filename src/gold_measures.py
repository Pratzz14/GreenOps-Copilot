"""Evidence-backed findings, operational protections and candidate estimates."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from src.factors import SCENARIOS
from src.gold_baseline import (
    START, STOP, ZERO, accepted, decimal, dimensions, estimate, key_for, rounded, subtotal,
)

ZONE = ZoneInfo("Europe/Zurich")
HORIZONS = ("first_year", "steady_state")
DAY_RATE = Decimal("1100")
CAP = Decimal("16500")
COST_TARGET = Decimal(".25")
CARBON_TARGET = Decimal(".40")


def one_year_after(day):
    try:
        return day.replace(year=day.year + 1)
    except ValueError:
        return day.replace(year=day.year + 1, day=28)


def training_day(day):
    return day.month in {1, 4, 7, 10} and day.day <= 3


def local_at(day, hour=0):
    return datetime.combine(day, time(hour), ZONE)


def conflicts(rule, action, start, end):
    return (rule["action_scope"] in {action, "all"}
            and (rule.get("starts_at") is None or rule["starts_at"] < end)
            and (rule.get("ends_at") is None or rule["ends_at"] > start))


@dataclass(frozen=True)
class Totals:
    gross: Decimal | None = None
    recurring: Decimal | None = None
    before_energy: Decimal | None = None
    after_energy: Decimal | None = None
    before_co2: Decimal | None = None
    after_co2: Decimal | None = None

    def over_fraction(self, fraction):
        if fraction is None:
            return Totals()
        return Totals(*(rounded(value * fraction) if value is not None else None for value in (
            self.gross, self.recurring, self.before_energy, self.after_energy, self.before_co2, self.after_co2,
        )))


def first_year_fraction(run_start, effective):
    if effective is None:
        return None
    end = one_year_after(run_start)
    return Decimal(max(0, (end - max(run_start, effective)).days)) / (end - run_start).days


def register_protections(data):
    tickets = {row["ticket_id"]: row for row in data.source("it_tickets")
               if row["ticket_id"] and row["event_date"] and date.fromisoformat(row["event_date"]) <= data.decision}
    catalog = {
        "dp-dev": ("Azure", "resource", "Data platform owner"),
        "dp-prod": ("Azure", "resource", "Data platform and Finance owners"),
        "gpu-ml": ("Azure", "resource", "ML platform owner"),
        "gpu-ml-01": ("Azure", "server", "ML platform owner"),
        "vm-test": ("AWS", "resource", "Test platform owner"),
        "dr-failover": ("AWS", "server", "Disaster recovery owner"),
        "st-backup": ("AWS", "resource", "Records and compliance owner"),
        "pbi-07": ("Azure", "report", "Internal Audit"),
    }
    subjects = {name: data.subject(provider, name, family, role=role)
                for name, (provider, family, role) in catalog.items()}

    def protect(name, rule, action, decision, ticket_ids, reason, start=None, end=None):
        rows = [tickets[ticket] for ticket in ticket_ids if ticket in tickets]
        if not rows:
            return
        evidence = data.evidence(("protection", name, rule, start), reason, rows)
        data.add("protection_window", protection_id=f"{rule}:{name}:{start.isoformat() if start else 'standing'}",
                 subject_id=subjects[name], rule_key=rule, action_scope=action, starts_at=start,
                 ends_at=end, decision=decision, responsible_role=catalog[name][2], reason=reason,
                 evidence_set_id=evidence)

    start_year = min(START.year, data.decision.year)
    end_year = one_year_after(data.decision).year
    for year in range(start_year, end_year + 1):
        for month in (1, 4, 7, 10):
            start, stop = local_at(date(year, month, 1)), local_at(date(year, month, 4))
            for name, ticket in (("dp-dev", "T-1053"), ("gpu-ml", "T-1101"), ("gpu-ml-01", "T-1101")):
                protect(name, "quarterly-training", "shutdown", "blocked", [ticket],
                        "Quarterly training needs continuous service on days one through three.", start, stop)
    calendar = defaultdict(dict)
    for row in data.source("business_calendar"):
        if row["event_date"] and row["record_status"] == "accepted":
            day = date.fromisoformat(row["event_date"])
            calendar[day.year, day.month][day] = row
    for (year, month), dates in sorted(calendar.items()):
        start = date(year, month, 1)
        stop = (start + timedelta(days=32)).replace(day=1)
        if len(dates) != (stop - start).days:
            continue
        workdays = sorted(day for day, row in dates.items() if row["workday"] in {"1", "True"})
        for day in workdays[-3:]:
            protect("dp-prod", "finance-close", "shutdown", "blocked", ["T-1029"],
                    "Finance needs the platform through the closing-day overnight window. "
                    "Hold the closing day through 04:00 the following morning.",
                    local_at(day), local_at(day + timedelta(days=1), 4))
    protect("dp-prod", "verify-production-hours", "shutdown", "human_review", ["T-1029"],
            "Finance and platform owners must approve a narrower operating schedule, including future closes.")
    protect("st-backup", "ten-year-retention", "delete", "blocked", ["T-1039", "T-1195"],
            "Backups are subject to ten-year retention and the deletion request was rejected.")
    protect("pbi-07", "audit-report", "shutdown", "blocked", ["T-1167"],
            "Internal Audit requires this report at close. The instruction is to keep it available.")
    protect("dr-failover", "continuity", "all", "blocked", ["T-1094"],
            "The named disaster recovery server must remain running.")
    protect("vm-test", "unresolved-dr-scope", "all", "human_review", ["T-1094"],
            "The billed pool has no verified member allocation. Keep disaster recovery capacity out of any change.")
    protect("vm-test", "release-freeze", "all", "blocked", ["T-1204"],
            "The March 2026 release freeze required continuous availability.",
            local_at(date(2026, 3, 1)), local_at(date(2026, 4, 1)))
    return subjects, tickets


def add_finding(data, id_, subject, category, fact, hypothesis, rows, start=START, stop=STOP,
                confidence="observed"):
    evidence = data.evidence(("finding", id_), fact, rows)
    data.add("finding", finding_id=id_, subject_id=subject, category=category,
             observed_start=start, observed_end_exclusive=stop, observed_fact=fact,
             waste_hypothesis=hypothesis, verification_status="observed", confidence=confidence,
             evidence_set_id=evidence)


def add_measure(data, id_, subject, finding, action, description, change, review, notes, rows,
                estimates=None, factors=(), effort=None, effective=None, notice=None):
    role = data.subjects[subject]["responsible_role"]
    begin = local_at(data.decision)
    end = local_at(one_year_after(data.decision))
    matching = [rule for rule in data.tables["protection_window"] if rule["subject_id"] == subject
                and conflicts(rule, action, begin, end)]
    precedence = ["eligible", "human_review", "blocked"]
    # The action describes the proposed scope. Adjusted schedules require a new review.
    status = max([review, *(rule["decision"] for rule in matching if rule["decision"] in precedence)],
                 key=precedence.index)
    decision_text = " ".join(dict.fromkeys([notes, *(rule["reason"] for rule in matching)]))
    evidence = data.evidence(("measure", id_), decision_text, rows)
    calculation = data.evidence(("estimate", id_),
                                f"{change} {notes}",
                                rows, factors, kind="assumption")
    data.add("measure", measure_id=id_, subject_id=subject, finding_id=finding, description=description,
             proposed_change=change, earliest_effective_date=effective, notice_deadline=notice,
             effort_person_days=effort, one_time_cash_chf=ZERO if effort is not None else None,
             safety_status=status, responsible_role=role, risks_and_exceptions=decision_text,
             evidence_set_id=evidence)
    estimates = estimates or {}
    for scenario in SCENARIOS:
        totals = estimates.get(scenario, Totals())
        for horizon in HORIZONS:
            scoped = totals if horizon == "steady_state" else totals.over_fraction(first_year_fraction(data.decision, effective))
            known = sum(value is not None for value in (
                scoped.gross, scoped.recurring, scoped.before_energy, scoped.after_energy,
                scoped.before_co2, scoped.after_co2,
            ))
            data.add("measure_scenario", measure_id=id_, scenario=scenario, horizon=horizon,
                     gross_avoided_chf=scoped.gross, new_recurring_chf=scoped.recurring,
                     before_energy_kwh=scoped.before_energy, after_energy_kwh=scoped.after_energy,
                     before_location_kg=scoped.before_co2, after_location_kg=scoped.after_co2,
                     estimate_status="unquantified" if known == 0 else "conditional" if status != "eligible"
                     else "estimated" if known == 6 else "partial", evidence_set_id=calculation)


def compute_estimates(data, usage, costs, profiles, factor, reserve_active=False):
    """Reprice only matched eligible variable units and retain all training days."""
    by_day = {row["event_date"]: row for row in costs if accepted(row)}
    result = {}
    for scenario, minimum_hours in zip(SCENARIOS, profiles, strict=True):
        before_units = ZERO
        after_units = ZERO
        savings = []
        for row in usage:
            day = date.fromisoformat(row["event_date"])
            quantity = decimal(row["node_hours"] if reserve_active else row["quantity"])
            if quantity is None:
                continue
            running = decimal(row["runtime_h"]) if reserve_active else quantity
            active = decimal(row["active_use_h"]) if reserve_active else ZERO
            # If active observations are missing, retain all observed running time.
            retained = (running if active is None or training_day(day) else
                        min(running, max(minimum_hours, active + 2 if reserve_active else ZERO)))
            avoided = ZERO if not running else quantity * (running - retained) / running
            before_units += quantity
            after_units += quantity - avoided
            invoice = by_day.get(row["event_date"])
            if invoice and avoided:
                fact = data.finances[invoice["record_id"]]
                billed = decimal(invoice["quantity"])
                if fact["financial_status"] == "included" and billed and billed > 0:
                    savings.append(decimal(fact["cost_chf"]) * min(billed, avoided) / billed)
        energy_before, co2_before = estimate(before_units, factor, "Germany", scenario) if usage else (None, None)
        energy_after, co2_after = estimate(after_units, factor, "Germany", scenario) if usage else (None, None)
        result[scenario] = Totals(subtotal(savings), ZERO if savings else None, energy_before,
                                  energy_after, co2_before, co2_after).over_fraction(Decimal(1))
    return result


def add_licence_measures(data):
    rows = defaultdict(list)
    for row in data.source("contracts"):
        if (accepted(row) and row["source_file"] == "ai_subscriptions.csv"
                and row["reporting_month"] == "2026-08" and row["contract_status"] == "Final"):
            rows[row["provider"], row["product"]].append(row)
    for (provider, product), contracts in sorted(rows.items()):
        subject, *_ = dimensions(data, contracts[0], "ai_subscription")
        data.subject(provider, product, "ai_subscription", role="Procurement and product owner")
        id_ = f"seats-{provider.lower()}"
        valid = [row for row in contracts if row["licences_purchased"] and row["licences_active_30d"]]
        purchased = sum(int(row["licences_purchased"]) for row in valid)
        active = sum(int(row["licences_active_30d"]) for row in valid)
        priced = [
            Decimal(row["licences_purchased"]) - Decimal(row["licences_active_30d"])
            for row in valid
        ]
        amounts = [unused * decimal(row["price_per_seat"]) * decimal(row["fx_rate"])
                   if row["price_per_seat"] and row["fx_rate"] else None
                   for row, unused in zip(valid, priced, strict=True)]
        monthly = subtotal(amounts)
        monthly_text = f"CHF {monthly:,.2f} per month at observed unit prices" if monthly is not None else "no verified unit prices"
        fact = f"{product}: {purchased} purchased, {active} active, {purchased - active} unused in August 2026, {monthly_text}."
        add_finding(data, id_, subject, "licence_utilisation", fact,
                    "Review rightsizing after confirming actual seat needs and renewal conditions.", contracts,
                    date(2026, 8, 1), STOP)
        terms = {(row["contract_end"], row["notice_period_days"]) for row in contracts}
        end_day, notice_days = next(iter(terms)) if len(terms) == 1 else ("", "")
        end = date.fromisoformat(end_day) if end_day else None
        notice = end - timedelta(days=int(notice_days)) if end and notice_days else None
        effective = end + timedelta(days=1) if notice and notice >= data.decision else None
        totals = Totals(gross=monthly * 12 if monthly is not None else None, recurring=ZERO,
                        before_energy=ZERO, after_energy=ZERO, before_co2=ZERO, after_co2=ZERO)
        add_measure(data, f"resize-{id_}", subject, id_, "resize", f"Review unused {product} seats",
                    "Confirm demand and reduce unused seats at the next contract-effective date.",
                    "human_review", "Annual illustration uses August unused seats × monthly CHF price × 12. "
                    "Verify recurring inactivity, seat minimums, renewal and notice before crediting savings. "
                    "Workload is held fixed. Indicative effort is one person-day.",
                    contracts, {scenario: totals for scenario in SCENARIOS}, effort=Decimal(1),
                    effective=effective, notice=notice)


def add_saas_measures(data):
    contracts = defaultdict(list)
    months = {"2026-06", "2026-07", "2026-08"}
    for row in data.source("contracts"):
        if (row["source_file"] == "saas_contracts.csv" and accepted(row)
                and row["contract_status"] == "Final" and row["reporting_month"] in months):
            contracts[row["provider"], row["contract"], row["cost_center"]].append(row)
    for (provider, product, center), rows in sorted(contracts.items()):
        if len(rows) != 3 or {r["reporting_month"] for r in rows} != months:
            continue
        if not all(r["licences_purchased"] and r["licences_active_30d"] for r in rows):
            continue
        unused = min(int(r["licences_purchased"]) - int(r["licences_active_30d"]) for r in rows)
        if unused <= 0:
            continue
        latest = max(rows, key=lambda row: row["reporting_month"])
        price, fx = decimal(latest["price_per_licence"]), decimal(latest["fx_rate"])
        annual = unused * price * fx * 12 if price is not None and fx is not None else None
        subject, *_ = dimensions(data, latest, "saas", data.finances.get(latest["record_id"]))
        data.subject(provider, product, "saas", role="Procurement and product owner")
        identifier = f"saas-seats-{key_for(provider, product, center)}"
        add_finding(data, identifier, subject, "licence_utilisation",
                    f"{unused} persistently unused seats at cost center {center} across June–August 2026.",
                    "Review seat requirements and renewal terms.", rows, date(2026, 6, 1), STOP)
        terms = {(row["contract_end"], row["notice_period_days"]) for row in rows}
        end_day, notice_days = next(iter(terms)) if len(terms) == 1 else ("", "")
        end = date.fromisoformat(end_day) if end_day else None
        notice = end - timedelta(days=int(notice_days)) if end and notice_days else None
        effective = end + timedelta(days=1) if notice and notice >= data.decision else None
        totals = Totals(annual, ZERO, ZERO, ZERO, ZERO, ZERO)
        priced_history = all(data.finances[r["record_id"]]["financial_status"] == "included"
                             and (decimal(r["price_per_licence"]) or ZERO) > ZERO for r in rows)
        eligible = bool(center and effective and priced_history and annual and annual > ZERO)
        add_measure(data, f"resize-{identifier}", subject, identifier, "resize",
                    f"Review {product} seats for {center}", "Reduce persistent unused seats at renewal.",
                    "eligible" if eligible else "human_review",
                    "Minimum unused seats over three months × August CHF price × 12. "
                    "The model assumes renewal at the observed unit price with no minimum above retained seats. "
                    "Workload holds constant. Review actual terms and demand before execution. "
                    "Indicative effort is one person-day.", rows,
                    {scenario: totals for scenario in SCENARIOS}, effort=Decimal(1),
                    effective=effective, notice=notice)


def linked_operational_evidence(data, name, tickets):
    jobs = [dict(row, evidence_detail=f'{row["date"]} · {row["job_name"]} · {row["status"]} · {row["duration_h"]} h')
            for row in data.supplemental.get(("data_platform_jobs.csv", name), [])
            if START.isoformat() <= row.get("date", "") < STOP.isoformat()]
    backups = [dict(row, evidence_detail=f'{name} · {row["backup_tool"]} · '
                    f'retention {row["retention_days"]} days · last restore test {row["last_restore_test"] or "unknown"}')
               for row in data.supplemental.get(("backup_chains.csv", name), [])]
    references = [row for row in tickets.values() if row.get("resource_id") == name
                  or name.casefold() in row.get("resource_mentions", "").split(";")]
    return jobs, backups, references


def add_idle_server_findings(data, tickets):
    start = STOP - timedelta(days=STOP.weekday() + 56)
    observations = defaultdict(list)
    fields = ("cpu_avg_pct", "cpu_max_pct", "ram_avg_pct", "uptime_h", "network_gb")
    for row in data.source("server_metrics_weekly"):
        if (accepted(row) and start.isoformat() <= row["event_date"] and row["week_end"] <= STOP.isoformat()
                and all(row[field] for field in fields)):
            observations[row["server_id"]].append(row)
    for asset in data.source("assets"):
        name = asset["server_id"]
        rows = observations[name]
        if asset["record_status"] != "accepted" or len(rows) < 6:
            continue
        cpu, peak, ram, uptime, traffic = zip(*(tuple(decimal(row[field]) for field in fields) for row in rows))
        count = len(rows)
        if sum(cpu) > 5 * count or max(peak) > 20 or sum(ram) > 40 * count or sum(uptime) < 120 * count:
            continue
        subject = data.subject(asset["provider"], name, "server", asset, "Infrastructure owner")
        identifier = f"server-idle-{key_for(name)}"
        jobs, backups, references = linked_operational_evidence(data, name, tickets)
        checked = [asset, *rows, *jobs, *backups, *references]
        counts = (f"Linked evidence: {len(jobs)} scheduler records, {len(backups)} backup records "
                  f"and {len(references)} tickets. Unlinked evidence leaves coverage open.")
        add_finding(data, identifier, subject, "server_utilisation",
                    f"{count}/8 weeks observed, {sum(cpu)/count:.1f}% average CPU, "
                    f"{max(peak):.1f}% peak CPU, {sum(ram)/count:.1f}% average RAM, "
                    f"{sum(uptime)/count:.1f} h/week uptime, {sum(traffic):.1f} GB transferred. {counts}",
                    "Verify dependencies, scheduled workloads and recovery before changing capacity.",
                    checked, start, STOP)
        add_measure(data, f"review-{identifier}", subject, identifier, "shutdown",
                    f"Review a reversible pause for {name}",
                    "Establish dependencies and protection windows, then plan a monitored pause with rollback.",
                    "human_review", "Weekly observations establish low utilization. Confirm billing attribution, "
                    "dependencies, job history and restore readiness before estimating savings. " + counts,
                    checked)


def add_test_pool_measure(data, subject, tickets):
    jobs, backups, references = linked_operational_evidence(data, "vm-test", tickets)
    protected_days = {row["date"] for row in jobs}
    bills = [row for row in data.source("aws_costs")
             if accepted(row) and row["resource_id"] == "vm-test"
             and row["pricing_unit"] == "vCPU-hour" and row["charge_category"] == "usage"
             and decimal(row["line_item_usage_amount"]) and decimal(row["line_item_usage_amount"]) > ZERO]
    variable = [row for row in bills if row["event_date"] not in protected_days
                and not ("T-1204" in tickets and "2026-03-01" <= row["event_date"] < "2026-04-01")]
    priced = [decimal(data.finances[row["record_id"]]["cost_chf"]) for row in variable
              if data.finances[row["record_id"]]["financial_status"] == "included"
              and decimal(data.finances[row["record_id"]]["cost_chf"]) > ZERO]
    annual = subtotal(priced)
    quantity = subtotal(decimal(row["line_item_usage_amount"]) for row in bills)
    variable_quantity = subtotal(decimal(row["line_item_usage_amount"]) for row in variable)
    estimates = {}
    if quantity is not None and variable_quantity is not None:
        for scenario, fraction in zip(SCENARIOS, map(Decimal, ("0.10", "0.20", "0.30")), strict=True):
            before, before_co2 = estimate(quantity, "vcpu", "Ireland", scenario)
            after, after_co2 = estimate(quantity - fraction * variable_quantity, "vcpu", "Ireland", scenario)
            estimates[scenario] = Totals(annual * fraction if annual is not None else None, ZERO,
                                         before, after, before_co2, after_co2)
    source = [*references, *jobs, *backups, *bills]
    add_finding(data, "test-pool-capacity", subject, "platform_utilisation",
                f"Billed test pool has {len(jobs)} linked scheduler runs in the baseline.",
                "Compare billed capacity with the planned post-release scale-back and keep disaster recovery reserved.",
                [*references, *jobs, *backups])
    add_measure(data, "resize-test-pool", subject, "test-pool-capacity", "resize",
                "Review test pool rightsizing", "Test a staged reduction of verified spare billed pool capacity.",
                "human_review", "Sensitivity applies 10%, 20% or 30% to variable vCPU-hours and recorded usage CHF "
                "outside the release freeze and linked job days. This assumes proportional billing and "
                "no change to protected capacity. Confirm go-live, billable capacity and DR membership before "
                "execution. Three person-days and a 45-day lead time are planning assumptions.",
                source, estimates, ("vcpu", "pue", "grid_ie"), Decimal(3) if estimates else None,
                data.decision + timedelta(days=45) if estimates else None)


def add_ai_routing_measure(data):
    groups = defaultdict(list)
    for row in data.source("ai_usage"):
        if accepted(row) and data.finances[row["record_id"]]["financial_status"] == "included":
            groups[row["task_type"], row["model_class"], row["provider"], row["model"]].append(row)
    if not groups:
        return

    rates = {}
    for key, rows in groups.items():
        complete = [row for row in rows if all(row[k] for k in ("requests", "tokens_in", "tokens_out"))]
        count = sum(decimal(row["requests"]) for row in complete)
        if count >= 100:
            tokens = sum(decimal(row["tokens_in"]) + decimal(row["tokens_out"]) for row in complete)
            chf = sum(decimal(data.finances[row["record_id"]]["cost_chf"]) for row in complete)
            rates[key] = count, tokens / count, chf / count

    matches = []
    for source, (requests, tokens, price) in rates.items():
        for alternative, (_, other_tokens, other_price) in rates.items():
            if (source[:2] == alternative[:2] and other_price < price
                    and tokens * Decimal("0.8") <= other_tokens <= tokens * Decimal("1.2")):
                matches.append((requests * (price - other_price), source, alternative))

    estimates = {}
    notes = "Published cohorts are compared within the same task and model class."
    effort = None
    effective = None
    if matches:
        annual, primary, alternative = min(matches, key=lambda match: (-match[0], match[1], match[2]))
        requests, _, price = rates[primary]
        other_price = rates[alternative][2]
        shares = tuple(map(Decimal, ("0.10", "0.25", "0.50")))
        for scenario, share in zip(SCENARIOS, shares, strict=True):
            estimates[scenario] = Totals(gross=requests * share * price, recurring=requests * share * other_price)
        fact = (f"Across {len(rates)} comparable-size cohorts, {len(matches)} lower-price pairs match the "
                f"task, model class and token-size filter. Best modeled annual CHF saving at a 25% routing "
                f"share is CHF {annual * shares[1]:,.2f}.")
        notes += (f" Compare {primary[2]} · {primary[3]} with {alternative[2]} · {alternative[3]}. "
                  "Each cohort has at least 100 recorded requests, with mean token counts within 20%. "
                  "Savings use the observed CHF/request difference and 10%, 25% or 50% routing. "
                  "Two person-days and a 30-day lead time are pilot assumptions. Validate quality, tariff "
                  "and processing location before execution. Emissions remain unassessed.")
        sources = [*groups[primary], *groups[alternative]]
        effort = Decimal(2)
        effective = data.decision + timedelta(days=30)
    else:
        primary = max(groups, key=lambda key: sum(decimal(data.finances[row["record_id"]]["cost_chf"])
                                                 for row in groups[key]))
        fact = "No lower-price cohort matches the task, model class and token-size filter."
        sources = groups[primary]
    first = sources[0]
    subject, *_ = dimensions(data, first, "ai_gateway", data.finances[first["record_id"]])
    data.subject(first["provider"], first["resource_id"] or "Unallocated", "ai_gateway", role="AI product owner")
    add_finding(data, "ai-routing", subject, "model_cost", fact,
                "Compare modeled savings with pilot effort before changing routing.", sources)
    add_measure(data, "route-ai-workload", subject, "ai-routing", "route", "Review AI model routing",
                "Validate the task-equivalent candidate through a limited quality and latency pilot.",
                "human_review", notes, sources, estimates, effort=effort, effective=effective)


def build_measures(data):
    subjects, tickets = register_protections(data)
    add_licence_measures(data)
    add_idle_server_findings(data, tickets)
    add_saas_measures(data)
    if "T-1230" in tickets:
        add_finding(data, "untrusted-ticket", subjects["dp-prod"], "protection_conflict",
                    "Ticket T-1230 contains instruction-like text and an unverified approval claim.",
                    "Use trusted structured protection rules and observed workload activity.", [tickets["T-1230"]])
    platform = [row for row in data.source("data_platform_usage") if accepted(row)]
    dev = [row for row in platform if row["resource_id"] == "dp-dev"]
    prod = [row for row in platform if row["resource_id"] == "dp-prod"]
    invoices = data.source("azure_costs")
    dev_cost = [row for row in invoices if row["resource_id"] == "dp-dev" and accepted(row)]
    gpu = [row for row in invoices if row["resource_id"] == "gpu-ml" and accepted(row)]
    weekly = [row for row in data.source("server_metrics_weekly") if accepted(row)
              and row["server_id"] == "gpu-ml-01" and row["gpu_avg_pct"]
              and date.fromisoformat(row["week_end"]) <= STOP]
    def lookup(*ids):
        return [tickets[id_] for id_ in ids if id_ in tickets]
    runtime = subtotal(decimal(row["runtime_h"]) for row in dev)
    active = subtotal(decimal(row["active_use_h"]) for row in dev)
    add_finding(data, "development-idle", subjects["dp-dev"], "platform_utilisation",
                f"{runtime} runtime hours and {active} active hours across {len({row['event_date'] for row in dev})} observed days.",
                "Review idle time outside training before testing scheduled pauses.", dev)
    add_measure(data, "schedule-development", subjects["dp-dev"], "development-idle", "schedule",
                "Schedule development cluster pauses",
                "Illustrate 16, 12 or 8 minimum retained hours per observed day plus any greater active time "
                "and startup allowance. Retain all quarterly training hours.",
                "human_review", "Daily data cannot identify contiguous safe time slots. The illustration uses "
                "active time plus two hours, caps avoidable units at matched billed node-hours and includes only "
                "known usage prices. It assumes three person-days and an illustrative 30-day lead time.",
                [*dev, *dev_cost, *lookup("T-1053")],
                compute_estimates(data, dev, dev_cost, (16, 12, 8), "node", reserve_active=True),
                ("node", "pue", "grid_de"), Decimal(3), data.decision + timedelta(days=30))
    points = [decimal(row["gpu_avg_pct"]) for row in weekly]
    average = sum(points, ZERO) / len(points) if points else None
    gpu_fact = (f"Instance gpu-ml-01 averaged {average:.2f}% across {len(points)} complete weekly observations."
                if average is not None else "GPU utilisation needs complete weekly observations.")
    add_finding(data, "gpu-utilisation", subjects["gpu-ml-01"], "server_utilisation", gpu_fact,
                "Confirm the candidate relationship to billed gpu-ml before crediting an on-demand change.", weekly)
    add_measure(data, "gpu-on-demand", subjects["gpu-ml"], "gpu-utilisation", "schedule",
                "Review on-demand GPU scheduling",
                "Illustrate a 16, 12 or 8 GPU-hour daily limit outside the quarterly training window.",
                "human_review", "Billed gpu-ml and monitored gpu-ml-01 remain separate. Confirm attribution, "
                "capacity and standby requirements. Known variable amounts are a partial illustration. "
                "No startup power or new recurring cost is assumed. Indicative effort is three person-days and 30 days lead time.",
                [*gpu, *weekly, *lookup("T-1101")],
                compute_estimates(data, gpu, gpu, (16, 12, 8), "gpu"),
                ("gpu", "pue", "grid_de"), Decimal(3), data.decision + timedelta(days=30))
    weekend = [row for row in prod if date.fromisoformat(row["event_date"]).weekday() >= 5]
    active_days = {row["event_date"] for row in weekend if (decimal(row["active_use_h"]) or ZERO) > 0}
    add_finding(data, "production-weekends", subjects["dp-prod"], "protection_conflict",
                f"Production activity was observed on {len(active_days)} weekend days. Finance uses the platform at month close.",
                "A blanket shutdown would remove required service.",
                [*lookup("T-1029"), *weekend])
    add_measure(data, "shutdown-production", subjects["dp-prod"], "production-weekends", "shutdown",
                "Block blanket production shutdown", "Switch off production nights and weekends.",
                "blocked", "Weekend activity and finance closing contradict a blanket shutdown. "
                "Platform and Finance owners can review a scoped change.", [*lookup("T-1029"), *weekend])
    add_test_pool_measure(data, subjects["vm-test"], tickets)
    add_measure(data, "delete-retained-backup", subjects["st-backup"], None, "delete",
                "Block backup deletion", "Delete the retained backup archive.",
                "blocked", "Legal retention and the rejected deletion request apply.", lookup("T-1039", "T-1195"))
    add_ai_routing_measure(data)
    if dev and gpu:
        reason = "Coordinate any later changes to the two resources that jointly serve quarterly training."
        evidence = data.evidence("coordinate-training", reason, lookup("T-1053", "T-1101"))
        # Until coordinated scheduling is validated, avoid crediting the two changes together.
        data.add("measure_constraint", measure_id="schedule-development", related_measure_id="gpu-on-demand",
                 constraint_type="excludes", resolution_note=reason, evidence_set_id=evidence)
