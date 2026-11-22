"""Calculate recommendation spending from the published run's Silver snapshot."""

from collections import defaultdict
from datetime import date, timedelta

from src.gold_baseline import GoldData, accepted, decimal, subtotal
from src.gold_measures import compute_estimates, first_year_fraction
from src.recommendations import seat_gap
from src.silver_storage import silver_directory


def licence_spend(history, months, persistent_unused, decision):
    def observation(month):
        row = history.get(month)
        if row is None:
            return {"month": month, "amount": None, "reason": "No qualifying seat records for this month"}
        price = decimal(row["price_per_seat"] or row["price_per_licence"])
        fx = decimal(row["fx_rate"])
        unused = seat_gap(row)
        unit_chf = price * fx if price and fx and price > 0 and fx > 0 else None
        return {"month": month, "amount": unused * unit_chf if unit_chf is not None else None,
                "reason": None if unit_chf is not None else "Missing valid seat price or CHF exchange rate",
                "unused_seats": unused, "seat_price": price, "currency": row["currency"], "fx_rate": fx,
                "unit_chf": unit_chf, "source_file": row["source_file"], "source_row": int(row["source_row"])}

    latest = observation(max(history))
    annual = latest["unit_chf"] * persistent_unused * 12 if latest["unit_chf"] is not None else None
    terms = {(row["contract_end"], row["notice_period_days"]) for row in history.values()}
    effective = deadline = None
    if len(terms) == 1:
        end, notice_days = next(iter(terms))
        if end and notice_days:
            end = date.fromisoformat(end)
            deadline = end - timedelta(days=int(notice_days))
            if deadline >= decision:
                effective = end + timedelta(days=1)
    fraction = first_year_fraction(decision, effective)
    return [observation(month) for month in months], {
        "annual": annual, "first_year": annual * fraction if annual is not None and fraction is not None else None,
        "price_month": latest["month"], "unit_chf": latest["unit_chf"], "effective_date": effective,
        "purchased_seats": int(history[latest["month"]]["licences_purchased"]),
        "notice_deadline": deadline,
        "reason": latest["reason"],
    }


def development_spend(gold, output, months, scenario):
    data = GoldData(gold.run_id, silver_directory(output) / gold.run["silver_version"], gold.run["decision_as_of"])
    by_table = []
    for table in ("data_platform_usage", "azure_costs"):
        periods = defaultdict(list)
        for row in data.source(table):
            if row["resource_id"] == "dp-dev" and accepted(row):
                periods[row["event_date"][:7]].append(row)
        by_table.append(periods)
    usage, costs = by_table
    for month in months:
        if not usage[month]:
            yield {"month": month, "amount": None, "reason": "No runtime evidence for this month"}, None
            continue
        values = compute_estimates(data, usage[month], costs[month], (16, 12, 8), "node", reserve_active=True)
        amount = values[scenario].gross
        retained = {"low": 16, "mid": 12, "high": 8}[scenario]
        sources = []
        for rows in (usage[month], costs[month]):
            if rows:
                sources.append({"file": rows[0]["source_file"],
                                "rows": sorted({int(row["source_row"]) for row in rows})})
        usage_days = {row["event_date"] for row in usage[month]}
        matched = {row["event_date"]: row for row in costs[month] if row["event_date"] in usage_days}
        charges = [data.finances[row["record_id"]] for row in matched.values()
                   if (decimal(row["quantity"]) or 0) > 0]
        billed = subtotal(decimal(charge["cost_chf"]) for charge in charges
                         if charge["financial_status"] == "included")
        yield {"month": month, "amount": amount,
               "reason": None if amount is not None else "No matched variable charges for this month",
               "calculation": f"Reprice avoidable node-hours on matched billing days. Retain at least {retained} hours, "
                              "active time plus startup allowance, and all protected training hours.",
               "sources": sources}, billed


def metric_gaps(member):
    if member["safety_status"] == "blocked":
        return dict.fromkeys(("net_chf", "savings_kwh", "savings_location_kg"), "Blocked by a protection rule")
    if member["category"] == "Licence":
        reason = "No workload reduction modeled"
        return {"net_chf": member["licence_spend"]["reason"],
                "savings_kwh": reason, "savings_location_kg": reason}
    estimate = next((row for row in (member["estimate"] or {}).get("estimates", [])
                     if row["horizon"] == "steady_state"), {})
    return {key: reason for key, reason in {
        "net_chf": "No priced runtime reduction modeled",
        "savings_kwh": "No supported runtime reduction or electricity factor",
        "savings_location_kg": "No supported electricity reduction or location factor",
    }.items() if estimate.get(key) is None}
