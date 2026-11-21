"""Catalog and scoped Silver dataset preparation."""
from collections import Counter, defaultdict
from decimal import Decimal

from backend.silver import store
from src.source_specs import EXTRA_SPECS

PREPARED = {
    "server_metrics_with_assets": ("Weekly observations with inventory snapshot context", "Server and observed week",
                                   ["server_metrics_weekly", "assets"]),
    "platform_monthly_usage_cost": ("Platform activity, runtime and Azure charges", "Resource and month",
                                    ["data_platform_usage", "cost_facts"]),
    "ai_usage_with_cost": ("AI consumption and reconciled gateway charges", "AI source record",
                          ["ai_usage", "cost_facts"]),
}
GRAINS = {
    "aws_costs": "AWS billing line", "azure_costs": "Azure billing line",
    "hoster_invoice": "Hoster invoice line", "exchange_rates": "Dated currency rate",
    "business_calendar": "Calendar date", "server_inventory": "Server snapshot record",
    "server_metrics_weekly": "Server and observed week", "data_platform_usage": "Resource and observed date",
    "ai_usage": "AI gateway usage record", "ai_subscriptions": "AI subscription month and version",
    "saas_contracts": "SaaS contract month and version", "it_tickets": "Ticket",
    "mapping_departments_tools": "Documented mapping record", "cost_facts": "Originating charge record",
    "usage_facts": "Originating observation", "assets": "Server snapshot record",
    "contracts": "Originating contract month and version", "ownership": "Documented association",
    "resource_relationships": "Relationship evidence record",
}
GRAINS.update({table: f'{spec.cadence} · {spec.key}' for table, spec in EXTRA_SPECS.items()})
GRAINS['supplemental_comparisons'] = 'Comparison × month × entity × unit'
MONEY = {"cost_chf", "converted_cost_chf", "recorded_cost_chf", "amount_chf"}
PRICES = {"price_per_seat", "price_per_licence", "fx_rate"}
FINANCIAL = MONEY | PRICES | {"amount_original", "amount", "cost_in_billing_currency", "line_item_unblended_cost"}
ASSET_FIELDS = {"asset_record_id": ("record_id", "text"), "asset_environment": ("environment", "text"),
                "asset_owner_department": ("owner_department", "text"), "asset_snapshot_date": ("snapshot_date", "date")}
AI_FIELDS = {"recorded_cost_chf": ("cost_chf", "decimal"),
             "matched_financial_status": ("financial_status", "text")}
PLATFORM_FIELDS = dict(resource_id="text", reporting_month="text", observed_cluster_hours="decimal",
                       active_cluster_hours="decimal", node_hours="decimal", observed_rows="integer",
                       cost_rows="integer", recorded_cost_rows="integer", missing_cost_rows="integer",
                       recorded_cost_chf="decimal")


def unit(name, field):
    if name == "supplemental_comparisons" and field in {"extra_quantity", "core_quantity", "difference"}:
        return "Source-dependent"
    if field == "baseline_storage_gb_days":
        return "GB-days"
    if field == "duration_seconds":
        return "seconds"
    if field in {"refresh_duration_min", "teams_video_minutes", "baseline_teams_video_minutes"}:
        return "minutes"
    if field == "cpu_h":
        return "CPU-hours"
    if field in MONEY:
        return "CHF"
    if field in FINANCIAL:
        return ("CHF per currency" if field == "fx_rate" else "Original currency")
    if field.endswith("_pct") or field in {"avg_cpu_percent", "avg_cpu_utilization"}:
        return "%"
    if field.endswith("_gb"):
        return "GB"
    if field in {"runtime_h", "active_use_h", "observed_cluster_hours", "active_cluster_hours"}:
        return "cluster-hours"
    if field == "node_hours":
        return "node-hours"
    if field.startswith("tokens_") or field == "uncached_input_tokens":
        return "tokens"
    if field in {"quantity", "line_item_usage_amount"}:
        return "Source-dependent"
    if field.startswith(("uptime_h", "runtime_h")):
        return "hours"
    if field in {"requests", "query_count", "messages_30d", "object_requests", "accesses"}:
        return field.removesuffix("_30d").replace("_", " ")
    if field.startswith("licences_"):
        return "seats"
    return None


def unit_key(name, field, columns):
    if name == "supplemental_comparisons" and field in {"extra_quantity", "core_quantity", "difference"}:
        return "unit"
    if (name, field) in {("m365_usage", "storage"), ("log_volume", "log_gb")}:
        return "storage_unit" if name == "m365_usage" else "unit"
    if field in FINANCIAL - MONEY:
        return next((key for key in ("original_currency", "currency") if key in columns), None)
    if field in {"quantity", "line_item_usage_amount"}:
        return next((key for key in ("unit", "unit_of_measure", "pricing_unit") if key in columns), None)
    if name == "usage_facts" and field in {"runtime_h", "node_hours", "requests", "query_count"}:
        return "source_file"
    return None


def unique(rows, *keys):
    identities = [tuple(row[key] for key in keys) for row in rows]
    if any(None in key for key in identities) or len(set(identities)) != len(identities):
        raise ValueError(f"Expected unique non-null {' / '.join(keys)} keys")


def availability(silver, name):
    try:
        if name == "server_metrics_with_assets":
            unique((r for r in silver.rows["assets"] if r["record_status"] == "accepted"), "server_id")
            unique((r for r in silver.rows["server_metrics_weekly"] if r["record_status"] == "accepted"),
                   "server_id", "event_date")
        elif name == "ai_usage_with_cost":
            unique(origin_costs(silver, "ai_usage"), "record_id")
        elif name == "platform_monthly_usage_cost":
            unique(origin_costs(silver, "azure_costs"), "record_id")
    except ValueError as error:
        return str(error)
    return None


def schema(silver, name):
    if name == "platform_monthly_usage_cost":
        return PLATFORM_FIELDS
    if name in PREPARED:
        base = PREPARED[name][2][0]
        fields = ASSET_FIELDS if base == "server_metrics_weekly" else AI_FIELDS
        return silver.columns[base] | {key: kind for key, (_, kind) in fields.items()}
    return silver.columns[name]


def scoped(silver, rows, filters):
    for raw in rows:
        origin = silver.records.get(raw.get("record_id"), raw)
        status = origin.get("record_status", "accepted")
        if filters.disposition not in ("all", status):
            continue
        if filters.period == "baseline" and "baseline_overlap" in origin:
            missing_date = not origin.get("event_date") and origin.get("financial_status") in {
                "missing_amount", "missing_fx", "review", "quarantined",
            }
            if not (origin["baseline_overlap"] or origin.get("baseline_context") or missing_date):
                continue
        row = dict(raw)
        if filters.financial == "eligible" and "baseline_eligible" in row and not row["baseline_eligible"]:
            for field in FINANCIAL & row.keys():
                row[field] = None
        yield row


def origin_costs(silver, table):
    return [row for row in silver.rows["cost_facts"] if row["source_file"] == f"{table}.csv"]


def prepare(silver, name, filters):
    if name not in PREPARED:
        rows = list(scoped(silver, silver.rows[name], filters))
        coverage = Counter(r["financial_status"] for r in rows if r.get("financial_status"))
        return rows, dict(coverage)
    base, right = PREPARED[name][2]
    left_rows = list(scoped(silver, silver.rows[base], filters))
    if right == "assets":
        assets = list(scoped(silver, silver.rows[right], filters))
        unique(assets, "server_id")
        index = {row["server_id"]: row for row in assets}
        rows = [row | {key: index.get(row["server_id"], {}).get(field)
                       for key, (field, _) in ASSET_FIELDS.items()} for row in left_rows]
        return rows, {"observations": len(rows), "matched_assets": sum(bool(r["asset_record_id"]) for r in rows)}
    costs = list(scoped(silver, origin_costs(silver, "ai_usage" if base == "ai_usage" else "azure_costs"), filters))
    coverage = dict(Counter(row["financial_status"] for row in costs))
    if base == "ai_usage":
        unique(costs, "record_id")
        index = {row["record_id"]: row for row in costs}
        rows = [row | {key: index.get(row["record_id"], {}).get(field)
                       for key, (field, _) in AI_FIELDS.items()} for row in left_rows]
        return rows, coverage | {"unmatched_usage": sum(r["matched_financial_status"] is None for r in rows)}
    usage_groups, cost_groups = defaultdict(list), defaultdict(list)
    key_fields = ("resource_id", "reporting_month")
    for row in left_rows:
        usage_groups[tuple(row[key] for key in key_fields)].append(row)
    # Include cost-only months for platform resources. Never allocate costs across clusters.
    resources = {row["resource_id"] for row in silver.rows[base] if row["resource_id"]}
    for row in costs:
        if row["resource_id"] in resources and row["reporting_month"]:
            cost_groups[tuple(row[key] for key in key_fields)].append(row)
    rows = []
    matched_costs = []
    for key in sorted(usage_groups.keys() | cost_groups.keys(), key=lambda k: tuple(v or "" for v in k)):
        usage, charges = usage_groups[key], cost_groups[key]
        matched_costs.extend(charges)
        result = dict(zip(key_fields, key, strict=True))
        for output, field, population in (
            ("observed_cluster_hours", "runtime_h", usage), ("active_cluster_hours", "active_use_h", usage),
            ("node_hours", "node_hours", usage), ("recorded_cost_chf", "cost_chf", charges),
        ):
            values = [Decimal(row[field]) for row in population if row[field] is not None]
            result[output] = sum(values, Decimal(0)) if values else None
        result.update(observed_rows=len(usage), cost_rows=len(charges),
                      recorded_cost_rows=sum(r["cost_chf"] is not None for r in charges),
                      missing_cost_rows=sum(r["financial_status"] in {"missing_amount", "missing_fx"} for r in charges))
        rows.append(result)
    unique(rows, *key_fields)
    return rows, dict(Counter(row["financial_status"] for row in matched_costs)) | {
        "months_without_usage": sum(not row["observed_rows"] for row in rows),
        "months_without_cost_records": sum(not row["cost_rows"] for row in rows),
    }


def catalog(request):
    silver = store(request)
    entries = []
    originals = {entry.table: entry for entry in silver.overview.tables}
    for name in (*originals, *PREPARED):
        source = originals.get(name)
        purpose, grain, inputs = PREPARED.get(name, (source.purpose if source else "", GRAINS.get(name, ""), [name]))
        columns = schema(silver, name)
        limits = list(source.limitations) if source else []
        if name not in silver.source_tables:
            limits.append("Connected representation. Its records can overlap Silver source tables.")
        if name in {"ai_usage", "ai_usage_with_cost", "usage_facts", "cost_facts"}:
            limits.append("Consumer department and owner department describe different roles. Cached tokens are included in input tokens.")
        if name in {"contracts", "ai_subscriptions", "saas_contracts", "cost_facts"}:
            limits.append("Contract amounts are monthly. Use Final records for seat utilization.")
        if name in {"server_inventory", "assets", "server_metrics_with_assets"}:
            limits.append("Inventory attributes describe the observed snapshot. Snapshot measurements have no annual total.")
        if name.startswith("server_metrics"):
            limits.append("Weekly values describe complete weeks. Baseline boundary overlap is flagged.")
        if name == "resource_relationships":
            limits.append("Candidate GPU matches and unresolved test pools provide no verified allocation.")
        if name == "platform_monthly_usage_cost":
            limits.append("Hours and node-hours measure different quantities. Cost coverage is shown separately.")
        if name.startswith("server_metrics"):
            date_context = "Complete weeks intersecting the selected period; see baseline_boundary_week."
        elif name in {"assets", "server_inventory"}:
            date_context = "Inventory snapshot context; see snapshot_date and the 30-day observation window."
        elif "reporting_month" in columns:
            date_context = "Baseline scope uses source observation dates; reporting_month identifies the reporting month."
        else:
            date_context = "No time-series grain. Linked records follow their originating dates where available."
        entries.append(dict(date_context=date_context, name=name, purpose=purpose, grain=grain, inputs=inputs,
                            kind="prepared" if name in PREPARED else "source" if name in silver.source_tables else "connected",
                            unavailable=availability(silver, name), limitations=limits,
                            fields=[dict(name=field, type=kind, unit=unit(name, field),
                                         unit_key=unit_key(name, field, columns)) for field, kind in columns.items()]))
    return silver, entries
