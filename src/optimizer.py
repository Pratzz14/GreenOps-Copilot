"""Exact, deterministic selection over admissible Gold measures."""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from itertools import product

from src.factors import SCENARIOS
from src.gold_baseline import ZERO, subtotal
from src.gold_measures import CAP, CARBON_TARGET, COST_TARGET, DAY_RATE, HORIZONS, one_year_after


@dataclass(frozen=True)
class Contribution:
    chf: Decimal
    energy: Decimal
    co2: Decimal
    implementation: Decimal


@dataclass(frozen=True)
class Candidate:
    identifier: str
    status: str
    estimates: dict


def sum_contributions(values):
    result = Contribution(ZERO, ZERO, ZERO, ZERO)
    for value in values:
        result = Contribution(result.chf + value.chf, result.energy + value.energy,
                              result.co2 + value.co2, result.implementation + value.implementation)
    return result


def margins(result, cost, co2):
    return (result.chf - cost * COST_TARGET if cost is not None and cost > 0 else None,
            result.co2 - co2 * CARBON_TARGET if co2 is not None and co2 > 0 else None,
            CAP - result.implementation)


def meets(result, cost, co2):
    return all(value is not None and value >= 0 for value in margins(result, cost, co2))


def admissible(ids, constraints):
    for measure, related, kind in constraints:
        if measure not in ids:
            continue
        if (kind == "requires") != (related in ids):
            return False
    return True


def rank(estimates, baselines, assessable):
    steady = {scenario: estimates[scenario, "steady_state"] for scenario in SCENARIOS}
    passes = {scenario: meets(steady[scenario], baselines[scenario][0], baselines[scenario][2])
              for scenario in SCENARIOS}
    mid = steady["mid"]
    cost, _, co2 = baselines["mid"]
    scores = []
    if cost is not None and cost > 0:
        scores.append(mid.chf / (cost * COST_TARGET) - 1)
    if co2 is not None and co2 > 0:
        scores.append(mid.co2 / (co2 * CARBON_TARGET) - 1)
    return (assessable and all(passes.values()), assessable and passes["mid"],
            min(scores, default=ZERO), mid.co2, mid.chf, -mid.implementation)


def candidate_choices(candidates, constraints):
    """Collapse interchangeable-cost measures without changing the objective.

    Within an independent group, the top k CHF contributions dominate every
    other selection of k. First-year totals are reported but do not determine
    the selected annual package.
    """
    linked = {identifier for left, right, _ in constraints for identifier in (left, right)}
    groups = defaultdict(list)
    choices = []
    for candidate in candidates:
        annual = [candidate.estimates[scenario, "steady_state"] for scenario in SCENARIOS]
        annual_chf = {value.chf for value in annual}
        implementation = {value.implementation for value in candidate.estimates.values()}
        if (candidate.identifier not in linked and len(annual_chf) == 1 and len(implementation) == 1
                and all(value.co2 == ZERO for value in annual)):
            groups[candidate.status, implementation.pop()].append(candidate)
        else:
            choices.append(((), (candidate,)))
    for (_, cost), group in groups.items():
        ordered = sorted(group, key=lambda c: (-c.estimates["mid", "steady_state"].chf, c.identifier))
        max_count = min(len(ordered), int(CAP // cost)) if cost > 0 else len(ordered)
        choices.append(tuple(tuple(ordered[:count]) for count in range(max_count + 1)))
    return choices


def select(candidates, baselines, constraints, assessable, conditional=False):
    """Stable enumeration. Conditional packages must include a review measure."""
    results = None
    best = None
    allowed = {"eligible", "human_review"} if conditional else {"eligible"}
    choices = candidate_choices((c for c in candidates if c.status in allowed), constraints)
    for selections in product(*choices):
        members = tuple(sorted((c for group in selections for c in group), key=lambda c: c.identifier))
        identifiers = tuple(candidate.identifier for candidate in members)
        if not admissible(frozenset(identifiers), constraints):
            continue
        if conditional and all(candidate.status == "eligible" for candidate in members):
            continue
        estimates = {
            (scenario, horizon): sum_contributions(
                candidate.estimates[scenario, horizon] for candidate in members
            )
            for scenario in SCENARIOS for horizon in HORIZONS
        }
        if any(result.implementation > CAP for result in estimates.values()):
            continue
        score = rank(estimates, baselines, assessable)
        if best is None or score > best[0] or (score == best[0] and identifiers < best[1]):
            best = score, identifiers
            results = members, estimates
    return results


def candidates_for(data):
    scenarios = {}
    for row in data.tables["measure_scenario"]:
        scenarios[row["measure_id"], row["scenario"], row["horizon"]] = row
    for row in data.tables["measure"]:
        if row["safety_status"] == "blocked":
            continue
        effort, cash = row["effort_person_days"], row["one_time_cash_chf"]
        if effort is None or cash is None or effort < 0 or cash < 0:
            continue
        implementation_cost = effort * DAY_RATE + cash
        values = {}
        for scenario in SCENARIOS:
            for horizon in HORIZONS:
                estimate = scenarios[row["measure_id"], scenario, horizon]
                parts = [estimate[key] for key in (
                    "gross_avoided_chf", "new_recurring_chf", "before_energy_kwh", "after_energy_kwh",
                    "before_location_kg", "after_location_kg",
                )]
                status = "estimated" if row["safety_status"] == "eligible" else "conditional"
                if any(value is None for value in parts) or estimate["estimate_status"] != status:
                    continue
                gross, recurring, before_energy, after_energy, before_co2, after_co2 = parts
                values[scenario, horizon] = Contribution(
                    gross - recurring, before_energy - after_energy, before_co2 - after_co2, implementation_cost,
                )
        if len(values) == len(SCENARIOS) * len(HORIZONS):
            yield Candidate(row["measure_id"], row["safety_status"], values)


def persist_package(data, selected, baselines, assessable, kind, candidate_count, eligible_count):
    members, estimates = selected
    package_id = data.run_id if kind == "automatic" else f"{data.run_id}-conditional"
    primary = estimates["mid", "steady_state"]
    cost, _, co2 = baselines["mid"]
    if assessable and kind == "automatic":
        evaluation = "evaluated"
        selection = "feasible" if meets(primary, cost, co2) else "infeasible"
    else:
        evaluation = selection = "provisional"
    note = (f"Evaluated {candidate_count} fully quantified candidates within the stated scope. "
            f"{eligible_count} qualified for automatic selection.")
    if not assessable:
        note += " Baseline coverage or units prevent a target verdict."
    if kind == "conditional":
        note += " This illustration requires human review and carries no credit in the automatic package."
    elif not members:
        note += " No candidate contributes to the automatic package."
    evidence = data.evidence(("package", kind), note)
    for (scenario, horizon), result in estimates.items():
        baseline_cost, baseline_energy, baseline_co2 = baselines[scenario]
        data.add("package_result", package_id=package_id, scenario=scenario, horizon=horizon,
                 package_kind=kind, evaluation_status=evaluation, selection_status=selection,
                 candidate_set_note=note, evaluation_start=data.decision if horizon == "first_year" else None,
                 evaluation_end_exclusive=one_year_after(data.decision) if horizon == "first_year" else None,
                 baseline_cost_chf=baseline_cost, baseline_energy_kwh=baseline_energy,
                 baseline_location_kg=baseline_co2, net_savings_chf=result.chf,
                 savings_energy_kwh=result.energy, savings_location_kg=result.co2,
                 implementation_chf=result.implementation, evidence_set_id=evidence)
        for candidate in members:
            value = candidate.estimates[scenario, horizon]
            calculations = next(row for row in data.tables["measure_scenario"]
                                if (row["measure_id"], row["scenario"], row["horizon"])
                                == (candidate.identifier, scenario, horizon))
            data.add("package_member", package_id=package_id, scenario=scenario, horizon=horizon,
                     measure_id=candidate.identifier, credited_cost_chf=value.chf,
                     credited_energy_kwh=value.energy, credited_location_kg=value.co2,
                     credited_implementation_chf=value.implementation,
                     allocation_note=("Conditional only" if kind == "conditional" else
                                      "Full non-overlapping contribution"),
                     evidence_set_id=calculations["evidence_set_id"])


def build_packages(data, cost_coverage, carbon_coverage):
    baseline_cost = subtotal(row["recorded_cost_chf"] for row in data.tables["cost_monthly"])
    baselines = {}
    for scenario in SCENARIOS:
        impact = [row for row in data.tables["impact_monthly"] if row["scenario"] == scenario]
        baselines[scenario] = (baseline_cost, subtotal(row["energy_kwh"] for row in impact),
                               subtotal(row["location_kg"] for row in impact))
    assessable = cost_coverage == carbon_coverage == "complete" and all(
        cost is not None and cost > 0 and co2 is not None and co2 > 0
        for cost, _, co2 in baselines.values()
    )
    constraints = [(row["measure_id"], row["related_measure_id"], row["constraint_type"])
                   for row in data.tables["measure_constraint"]]
    candidates = list(candidates_for(data))
    eligible = [candidate for candidate in candidates if candidate.status == "eligible"]
    automatic = select(eligible, baselines, constraints, assessable)
    persist_package(data, automatic, baselines, assessable, "automatic", len(eligible), len(eligible))
    conditional = select(candidates, baselines, constraints, assessable=False, conditional=True)
    if conditional:
        persist_package(data, conditional, baselines, assessable, "conditional", len(candidates), len(eligible))
