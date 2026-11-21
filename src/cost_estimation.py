"""Use OpenAI to select a pricing basis for charges left open by unit-price imputation."""

import json
import os
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Literal

import httpx
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from src.gold_baseline import BILLING, CostEstimate, comparable_usage, decimal, in_period
from src.ingest import ROOT

SERVICE_COLUMNS = {"azure_costs": "service_name", "aws_costs": "product_servicecode", "hoster_invoice": "service"}
MIN_PEERS = 3
MAX_PEERS = 8


class EstimationError(ValueError):
    """The explicitly requested estimation pass could not complete."""


class PricingBasis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    basis: Literal["fee_chf", "fee_native", "usage_unit_price", "insufficient_evidence"]
    peer_ids: list[StrictInt] = Field(max_length=MAX_PEERS)


def request_basis(charge: dict, peers: list[dict]) -> tuple[PricingBasis, str]:
    env = dotenv_values(ROOT / ".env", interpolate=False)
    key = (os.environ.get("OPENAI_API_KEY") or env.get("OPENAI_API_KEY") or "").strip()
    model = (os.environ.get("OPENAI_COST_MODEL") or env.get("OPENAI_COST_MODEL") or "gpt-4.1-mini").strip()
    if not key:
        raise EstimationError("Set OPENAI_API_KEY in the environment or the project .env for cost estimation.")

    instructions = (
        "Select a pricing basis and comparable peers to estimate one missing charge. You receive only "
        "month offsets relative to the target and categorical alignment with each basis's peer median. "
        "Use only the supplied basis names and peer IDs. Select at least three peers, preferring the basis "
        "with the most close peers and preferring nearby months when choosing between comparable peers. "
        "Close means within 0.5% of the peer median, similar means within 10%, and outlier is further away. "
        "Exclude outliers. Choose insufficient_evidence with an empty list when no basis has enough comparable peers. "
        "The application calculates the amount locally."
    )
    try:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {key}"},
            timeout=httpx.Timeout(30, connect=5),
            json={
                "model": model, "instructions": instructions,
                "input": json.dumps({"charge": charge, "comparable_bills": peers}),
                "store": False, "max_output_tokens": 350,
                "text": {"format": {
                    "type": "json_schema", "name": "missing_cost_estimate", "strict": True,
                    "schema": PricingBasis.model_json_schema(),
                }},
            },
        )
    except httpx.RequestError as error:
        raise EstimationError("Could not reach OpenAI for cost estimation.") from error
    if response.is_error:
        raise EstimationError(f"OpenAI could not estimate missing costs (HTTP {response.status_code}).")
    try:
        body = response.json()
        if body.get("status") == "completed":
            for item in body["output"]:
                if item.get("type") == "message":
                    for part in item["content"]:
                        if part.get("type") == "output_text":
                            return PricingBasis.model_validate_json(part["text"]), body.get("model") or model
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise EstimationError("OpenAI returned an invalid cost estimate.") from error
    raise EstimationError("OpenAI did not complete the cost estimate.")


def billing_key(data, fact):
    table = fact["source_file"].removesuffix(".csv")
    if table not in BILLING or not fact["resource_id"] or not fact["currency"]:
        return None, None
    original = data.originals[fact["record_id"]]
    _, unit_col, region_col = BILLING[table]
    match, quantity = comparable_usage(data, fact)
    if match is None and fact["charge_type"].casefold() != "fee":
        return None, None
    key = (
        table, fact["provider"], fact["resource_id"], fact["currency"], fact["charge_type"],
        original[unit_col], original[SERVICE_COLUMNS[table]], original.get(region_col),
    )
    return key, quantity


def billing_month(row):
    year, month = map(int, row["reporting_month"].split("-"))
    return 12 * year + month


def estimate_missing_costs(data, deterministic):
    history = defaultdict(list)
    pending = []
    for fact in data.finances.values():
        status = fact["financial_status"]
        if (fact["record_status"] != "accepted" or status not in {"included", "outside_baseline", "missing_amount"}
                or not fact["event_date"] or not fact["reporting_month"] or date.fromisoformat(fact["event_date"]) > data.decision):
            continue
        key, quantity = billing_key(data, fact)
        if key is None:
            continue
        if status == "missing_amount":
            if in_period(fact) and fact["record_id"] not in deterministic and decimal(fact["fx_rate"]):
                pending.append((fact, key, quantity))
        elif (decimal(fact["amount_original"]) or 0) > 0 and (decimal(fact["cost_chf"]) or 0) > 0:
            history[key].append((fact, quantity))

    estimates = {}
    for target, key, quantity in pending:
        month = billing_month(target)
        candidates = [pair for pair in history[key] if abs(billing_month(pair[0]) - month) <= 3]
        if quantity is None:
            counts = Counter(row["reporting_month"] for row, _ in candidates)
            candidates = [pair for pair in candidates if counts[pair[0]["reporting_month"]] == 1
                          and pair[0]["reporting_month"] != target["reporting_month"]]
        candidates.sort(key=lambda pair: (abs(billing_month(pair[0]) - month), int(pair[0]["source_row"])))
        candidates = candidates[:MAX_PEERS]
        if len(candidates) < MIN_PEERS:
            continue
        estimate = estimate_charge(target, key[5], quantity, candidates)
        if estimate is not None:
            estimates[target["record_id"]] = estimate
    return estimates


def estimate_charge(target, unit, quantity, candidates):
    fx = Decimal(target["fx_rate"])
    if quantity is None:
        rates = {"fee_chf": [Decimal(row["cost_chf"]) for row, _ in candidates],
                 "fee_native": [Decimal(row["amount_original"]) for row, _ in candidates]}
    else:
        rates = {"usage_unit_price": [Decimal(row["amount_original"]) / units for row, units in candidates]}
    centers = {basis: median(values) for basis, values in rates.items()}
    target_month = billing_month(target)
    peers = [
        {"id": index + 1, "month_offset": billing_month(row) - target_month,
         "alignment": {basis: alignment(values[index], centers[basis]) for basis, values in rates.items()}}
        for index, (row, _) in enumerate(candidates)
    ]
    kind = "metered_usage" if quantity is not None else "recurring_fee"
    choice, model = request_basis({"kind": kind}, peers)
    if choice.basis == "insufficient_evidence":
        return None
    ids = sorted(set(choice.peer_ids))
    if len(ids) < MIN_PEERS or ids[0] < 1 or ids[-1] > len(candidates):
        raise EstimationError("OpenAI selected invalid billing comparables.")
    if choice.basis not in rates:
        raise EstimationError("OpenAI selected a pricing basis incompatible with the missing charge.")
    if any(peers[index - 1]["alignment"][choice.basis] == "outlier" for index in ids):
        raise EstimationError("OpenAI selected an outlier as a billing comparable.")
    rate = median(rates[choice.basis][index - 1] for index in ids)
    if choice.basis == "fee_chf":
        amount = rate
        method = "median CHF fee"
    elif choice.basis == "fee_native":
        amount = rate * fx
        method = "median original-currency fee × target-month FX"
    else:
        amount = rate * quantity * fx
        method = f"median original-currency price per {unit} × target usage × target-month FX"
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    detail = f"OpenAI-assisted estimate ({model}): {method} from {len(ids)} comparable bills = CHF {amount}."
    return CostEstimate(amount, dict(target, evidence_detail=detail), tuple(candidates[index - 1][0] for index in ids))


def alignment(value, center):
    deviation = abs(value - center) / center
    if deviation <= Decimal("0.005"):
        return "close"
    return "similar" if deviation <= Decimal("0.10") else "outlier"
