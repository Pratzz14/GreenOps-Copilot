"""Read recommendations and enrich a published run on demand."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

from fastapi import HTTPException

from backend.gold import open_published_gold
from backend.recommendation_forecast import historical_months, spending_projection
from backend.recommendation_savings import development_spend, licence_spend, metric_gaps
from backend.recommendation_tags import cached_tag, enrich, final_status, read_tags
from src.gold import current_run
from src.gold_baseline import key_for
from src.platforms import subject_platform, subject_platforms
from src.recommendations import catalog


def list_recommendations(gold, output, months, scenario, group, driver, *, grouped=False, projection_months=()):
    start, stop = gold.run["baseline_start"], gold.run["baseline_end_exclusive"]
    if any(len(month) != 7 or month[4] != "-" or not (month[:4] + month[5:]).isdigit()
           or not 1 <= int(month[5:]) <= 12 or not start.isoformat()[:7] <= month <= stop.isoformat()[:7]
           or month + "-01" >= stop.isoformat() for month in months or ()):
        raise HTTPException(422, "Select months within the published baseline.")
    saved = read_tags(output, gold.run_id)
    selected = set(months or ())
    last_month = (stop - timedelta(days=1)).isoformat()[:7]
    development = None
    drivers = defaultdict(set)
    if driver and group in {"provider", "department", "tool", "location"}:
        for table in ("cost_monthly", "impact_monthly"):
            for row in gold.select(f"""
                SELECT DISTINCT subject_id, report_month FROM gold.{table} WHERE run_id=? AND {group}=?
            """, driver):
                drivers[row["subject_id"]].add(row["report_month"].isoformat()[:7])
    for item in catalog(gold, output):
        qualifying_months = set(item["months"])
        display_months = qualifying_months & selected if months else qualifying_months
        if not display_months:
            continue
        scope = (item["resource"] if group == "subject" else item["attribution"].get(group)) or "Unallocated"
        if driver and scope != driver and (grouped or not display_months & drivers[item["billing_subject"]]):
            continue
        tag = cached_tag(item, saved)
        item["ai_tag"] = tag
        item["safety_status"] = final_status(item["rule_status"], tag)
        if item["estimate"]:
            item["estimate"] = dict(item["estimate"], estimates=[
                row for row in item["estimate"]["estimates"] if row["scenario"] == scenario
            ])
        member = {key: value for key, value in item.items()
                  if key not in {"evidence", "attribution", "billing_subject", "decision_as_of", "action", "seat_history"}}
        if grouped:
            periods = sorted(selected) if selected else sorted(display_months | {last_month})
            pricing_periods = sorted(set(periods).union(projection_months))
            breakdown, annual = [], None
            projection_history = {}
            if item["seat_history"]:
                observations, annual = licence_spend(item["seat_history"], pricing_periods, item["persistent_unused"], gold.run["decision_as_of"])
                breakdown = [period for period in observations if period["month"] in periods]
                for period in observations:
                    if period["month"] in projection_months and period.get("unit_chf") is not None:
                        seats = item["seat_history"][period["month"]]["licences_purchased"]
                        projection_history[period["month"]] = int(seats) * period["unit_chf"]
            elif item["estimate"] and item["estimate"]["measure_id"] == "schedule-development":
                if development is None:
                    development = list(development_spend(gold, output, pricing_periods, scenario))
                breakdown = [period for period, _ in development if period["month"] in periods]
                projection_history = {period["month"]: billed for period, billed in development}
            else:
                reason = ("Blocked by a protection rule" if item["safety_status"] == "blocked"
                          else "No priced runtime reduction modeled" if item["billing_subject"]
                          else "No verified billing link")
                breakdown = [{"month": month, "amount": None, "reason": reason} for month in periods]
            member.update(monthly_spend=breakdown, licence_spend=annual, projection_history=projection_history)
            member["metric_gaps"] = metric_gaps(member)
        yield (scope, item["action"], member) if grouped else member


def group_recommendations(gold, output, months, scenario, group, driver):
    groups = defaultdict(list)
    start, stop = gold.run["baseline_start"], gold.run["baseline_end_exclusive"]
    history = historical_months(start, stop)
    for scope, action, member in list_recommendations(gold, output, months, scenario, group, driver,
                                                      grouped=True, projection_months=history):
        groups[scope, action].append(member)
    display_month = max(months) if months else (gold.run["baseline_end_exclusive"] - timedelta(days=1)).isoformat()[:7]
    return summarize_groups(groups, group, gold.select("""
        SELECT measure_id, related_measure_id FROM gold.measure_constraint
        WHERE run_id=? AND constraint_type IN ('overlaps', 'excludes')
    """), display_month, projection_period=(history, stop.replace(day=1), gold.run["decision_as_of"]))


def metric_total(values):
    return {**{status: sum(values[status]) if values[status] else None for status in ("eligible", "conditional")},
            "quantified": sum(map(len, values.values()))}


def estimate_id(member):
    estimate = member["estimate"]
    if estimate:
        return estimate["measure_id"]
    return member["id"] if member.get("licence_spend") else None


def summarize_groups(groups, dimension, constraints, display_month="", *, projection_period=None):
    available = {member["estimate"]["measure_id"] for members in groups.values() for member in members
                 if member["estimate"] and member["safety_status"] != "blocked"}
    conflicts = set()
    for row in constraints:
        pair = {row["measure_id"], row["related_measure_id"]}
        if pair <= available:
            conflicts.update(pair)
    measure_groups = defaultdict(set)
    for scope_action, members in groups.items():
        for member in members:
            if member["estimate"] and member["safety_status"] != "blocked":
                measure_groups[member["estimate"]["measure_id"]].add(scope_action)
    conflicts.update(measure for measure, scopes in measure_groups.items() if len(scopes) > 1)

    for (scope, action), members in sorted(groups.items()):
        counts = Counter(member["safety_status"] for member in members)
        seats = [item["persistent_unused"] for item in members if item["persistent_unused"] is not None]
        measures = {}
        for member in sorted(members, key=lambda item: item["id"]):
            measure_id = estimate_id(member)
            if not measure_id or member["safety_status"] == "blocked":
                continue
            previous = measures.get(measure_id)
            if not previous or member["safety_status"] == "human_review":
                measures[measure_id] = member
        savings = {}
        monthly = {period["month"]: defaultdict(list) for member in members for period in member.get("monthly_spend", [])}
        for measure_id, member in measures.items():
            if measure_id in conflicts:
                continue
            status = "eligible" if member["safety_status"] == "eligible" else "conditional"
            for period in member.get("monthly_spend", []):
                if period["amount"] is not None:
                    monthly[period["month"]][status].append(period["amount"])
        for horizon in ("steady_state", "first_year"):
            metrics = {key: defaultdict(list) for key in ("net_chf", "savings_kwh", "savings_location_kg")}
            for measure_id, member in measures.items():
                if measure_id in conflicts:
                    continue
                if licence := member.get("licence_spend"):
                    amount = licence["annual" if horizon == "steady_state" else "first_year"]
                    if amount is not None:
                        status = "eligible" if member["safety_status"] == "eligible" else "conditional"
                        metrics["net_chf"][status].append(amount)
                    continue
                for estimate in member["estimate"]["estimates"]:
                    if estimate["horizon"] != horizon:
                        continue
                    status = ("eligible" if member["safety_status"] == "eligible"
                              and estimate["estimate_status"] != "conditional" else "conditional")
                    for key, values in metrics.items():
                        if estimate[key] is not None:
                            values[status].append(estimate[key])
            savings[horizon] = {key: metric_total(values) for key, values in metrics.items()}
        projection = spending_projection(
            (member for measure_id, member in measures.items() if measure_id not in conflicts),
            len(members), *projection_period,
        ) if projection_period else None
        public_members = [{key: value for key, value in member.items() if key != "projection_history"} for member in members]
        yield {"id": key_for(dimension, scope, action), "scope": scope, "action": action, "members": public_members,
               "persistent_unused": sum(seats) if seats else None,
               "cost_center_count": len({member.get("cost_center") for member in members} - {None}),
               "safety_counts": dict(counts), "savings": savings,
               "monthly_spend": {month: metric_total(values) for month, values in sorted(monthly.items())},
               "display_month": display_month,
               "omitted_measure_count": len(measures.keys() & conflicts), "spending_projection": projection}


def platform_breakdowns(gold, output, scenario):
    platforms = subject_platforms(gold, output)
    totals = defaultdict(list)
    for row in gold.breakdowns(scenario, "subject"):
        totals[row["report_month"], subject_platform(row["driver"], platforms)].append(row)
    nullable = ("recorded_cost_chf", "imputed_cost_chf", "recovered_cost_chf",
                "estimated_kwh", "estimated_location_kg", "swiss_operating_kg_co2e", "reporting_kg_co2e",
                "planning_kwh", "planning_kg_co2e")
    counts = ("unresolved_cost_rows", "incomplete_energy_buckets", "incomplete_carbon_buckets")
    for (month, platform), rows in totals.items():
        metrics = {key: [row[key] for row in rows if row.get(key) is not None] for key in nullable}
        yield {"report_month": month, "driver": platform, "spend_rank": None, "emissions_rank": None,
               "planning_energy_boundaries": sorted({boundary for row in rows
                                                      for boundary in row.get("planning_energy_boundaries", [])}),
               "needs_energy_factor": any(row.get("needs_energy_factor") for row in rows),
               **{key: sum(values) if values else None for key, values in metrics.items()},
               **{key: sum(row[key] or 0 for row in rows) for key in counts}}


def tag_run(output, run_id):
    with open_published_gold(output, run_id) as gold:
        items = list(catalog(gold, output))
    return enrich(output, run_id, items)


def main():
    from src.pipeline import active_output

    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    output = active_output(args.out)
    print(f"Saved {tag_run(output, current_run(output))} recommendation tags.")


if __name__ == "__main__":
    main()
