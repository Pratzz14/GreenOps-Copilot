"""Deterministic utilization checks against a published Silver snapshot."""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException

from src.gold_baseline import key_for, region
from src.profile import read_csv
from src.silver_storage import silver_directory


def inspect_utilization(gold, output, months, scenario, group, driver, *, include_estimates=False):
    start, stop = gold.run["baseline_start"], gold.run["baseline_end_exclusive"]
    days = {start + timedelta(days=n) for n in range((stop - start).days)}
    available = {day.isoformat()[:7] for day in days}
    selected = set(months) if months else available
    if not selected <= available:
        raise HTTPException(422, "Select months within the published baseline.")
    days = {day for day in days if day.isoformat()[:7] in selected}
    weeks = {day.isoformat() for day in days if day.weekday() == 0
             and all(day + timedelta(days=n) in days for n in range(7))}
    day_keys = {day.isoformat() for day in days}
    directory = silver_directory(output) / gold.run["silver_version"]

    def load(name):
        records = read_csv(directory / f"{name}.csv")[1]
        return [row for row in records if row["record_status"] == "accepted"]

    dimensions = defaultdict(list)
    cost = ("CASE WHEN recorded_cost_chf IS NOT NULL OR imputed_cost_chf IS NOT NULL "
            "THEN coalesce(recorded_cost_chf, 0) + coalesce(imputed_cost_chf, 0) END"
            if include_estimates else "recorded_cost_chf")
    carbon = ("CASE WHEN location_kg IS NOT NULL OR swiss_operating_kg_co2e IS NOT NULL "
              "THEN coalesce(location_kg, 0) + coalesce(swiss_operating_kg_co2e, 0) END"
              if include_estimates else "location_kg")
    # Group is a validated enum. Keep billing and impact buckets separate.
    for table, value, kind in (
        ("cost_monthly", cost, "cost"),
        ("impact_monthly", "energy_kwh", "energy"),
        ("impact_monthly", carbon, "carbon"),
    ):
        condition = "AND scenario=?" if table == "impact_monthly" else ""
        for row in gold.select(
            f"SELECT subject_id, report_month, department, provider, tool, location, {value} AS amount "
            f"FROM gold.{table} WHERE run_id=? {condition}", *([scenario] if condition else []),
        ):
            dimensions[row["subject_id"]].append((kind, row))

    mappings = {row["resource_id"]: row for row in load("mapping_departments_tools")}
    links = {row["server_id"]: row["resource_id"]
             for row in read_csv(directory / "resource_relationships.csv")[1]
             if row["confidence"] == "high"}
    findings, assessed, insufficient = [], 0, 0

    def record(name, kind, provider, subject_name, family, rows, observation, action, fallback, scope=None):
        nonlocal assessed, insufficient
        subject = f"{family}:{key_for(provider, subject_name, family)}"
        buckets = [pair for pair in dimensions[subject]
                   if pair[1]["report_month"].isoformat()[:7] in selected
                   and (scope is None or pair[1]["department"] == scope)]
        if driver and not (fallback.get(group) == driver or any(row[group] == driver for _, row in buckets)):
            return
        if observation is None:
            insufficient += 1
            return
        assessed += 1
        if not observation:
            return
        values = defaultdict(list)
        for metric, row in buckets:
            if (not driver or row[group] == driver) and row["amount"] is not None:
                values[metric].append(row["amount"])
        findings.append(dict(
            key=f"{kind}:{provider}:{name}", resource=name, category=kind, observation=observation, action=action,
            impact={metric: str(sum(amounts)) for metric, amounts in values.items()},
            evidence={file: sorted({int(row["source_row"]) for row in rows if row["source_file"] == file})
                      for file in sorted({row["source_file"] for row in rows})},
        ))

    clusters = defaultdict(list)
    for row in load("data_platform_usage"):
        clusters[row["resource_id"]].append(row)
    for name, source in clusters.items():
        rows = [r for r in source if r["event_date"] in day_keys and r["runtime_h"] and r["active_use_h"]
                and 0 <= Decimal(r["active_use_h"]) <= Decimal(r["runtime_h"])]
        count = len({r["event_date"] for r in rows})
        runtime = sum(Decimal(r["runtime_h"]) for r in rows)
        active = sum(Decimal(r["active_use_h"]) for r in rows)
        observation = None
        if count >= 14 and count * 10 >= len(days) * 7:
            observation = (f"{active:g} active of {runtime:g} runtime hours ({active/runtime:.1%}). "
                           f"{count}/{len(days)} days observed. Rule: at most 20% active."
                           if runtime and active * 5 <= runtime else "")
        mapping = mappings.get(name, {})
        provider = source[0].get("provider") or "Azure"
        record(name, "Data cluster", provider, name, "resource", rows, observation,
               "Assess resizing or scheduled pauses. Verify hourly demand and protected jobs first.",
               dict(provider=provider, location=region(source[0].get("region")),
                    tool=mapping.get("tool"), department=mapping.get("department")))

    telemetry = defaultdict(list)
    fields = ("cpu_avg_pct", "cpu_max_pct", "ram_avg_pct", "uptime_h")
    for row in load("server_metrics_weekly"):
        if row["event_date"] in weeks and all(row[f] for f in fields):
            telemetry[row["server_id"]].append(row)
    for asset in load("assets"):
        name, provider = asset["server_id"], asset["provider"]
        rows = telemetry[name]
        count = len({row["event_date"] for row in rows})
        observation = None
        if count >= 3 and count * 4 >= len(weeks) * 3:
            cpu, peak, ram, uptime = zip(*(tuple(Decimal(row[f]) for f in fields) for row in rows))
            averages = [sum(series) / len(rows) for series in (cpu, ram, uptime)]
            observation = ""
            if averages[0] <= 5 and max(peak) <= 20 and averages[1] <= 40 and averages[2] >= 120:
                observation = (f"{averages[0]:.1f}% mean CPU, {max(peak):.1f}% peak CPU, "
                               f"{averages[1]:.1f}% mean RAM and {averages[2]:.1f} h/week uptime. "
                               f"{count}/{len(weeks)} weeks observed. Rule: CPU ≤5% mean and ≤20% peak, RAM ≤40%, uptime ≥120 h/week.")
        record(name, "Server", provider, links.get(name, ""), "resource", [asset, *rows], observation,
               "Review downsizing or a reversible pause with the owner. Verify dependencies and protection windows.",
               dict(provider=provider, location=region(asset.get("region")),
                    department=asset.get("reporting_department"), tool=mappings.get(links.get(name), {}).get("tool")))

    contracts = defaultdict(dict)
    for row in load("contracts"):
        if row["contract_status"] == "Final" and row["reporting_month"] in selected:
            name = row["product"] or row["contract"]
            contracts[row["provider"], name, row["cost_center"], row["source_file"]][row["reporting_month"]] = row
    centers = defaultdict(set)
    for (provider, name, center, file), history in contracts.items():
        for row in history.values():
            centers[provider, name, file, row.get("reporting_department") or "Unallocated"].add(center)
    for (provider, name, center, file), history in contracts.items():
        latest = max(history)
        row = history[latest]
        def unused(item):
            if not item or not item["licences_purchased"] or not item["licences_active_30d"]:
                return None
            purchased, active = int(item["licences_purchased"]), int(item["licences_active_30d"])
            return purchased - active if 0 <= active <= purchased else None
        gap = unused(row)
        previous = next((day for day in days if day.isoformat() == f"{latest}-01"), None)
        prior = history.get((previous - timedelta(days=1)).isoformat()[:7]) if previous else None
        recurring = (unused(prior) or 0) > 0
        observation = None if gap is None else ""
        if gap:
            observation = f"{gap} unused seats in {latest} (purchased less active)."
            if recurring:
                observation += " Unused seats also observed in the previous month."
        department = row.get("reporting_department") or "Unallocated"
        family = "ai_subscription" if file == "ai_subscriptions.csv" else "saas"
        # Gold aggregates contracts by department. Do not assign a department-wide
        # total to individual cost centers when more than one center shares it.
        unambiguous = len(centers[provider, name, file, department]) == 1
        record(f"{name} · {center}" if center else name, "Licence", provider, name if unambiguous else "", family,
               [row, prior] if recurring else [row], observation,
               "Review reducing seats at renewal. Confirm minimum commitments and notice terms.",
               dict(provider=provider, location="Mixed", department=department, tool=name), department)
    return {"items": findings, "assessed": assessed, "insufficient": insufficient}
