"""The model selects evidence without receiving amounts or returning a price."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from src import cost_estimation


def test_openai_estimates_unpriced_recurring_fee_from_local_bills(monkeypatch):
    target = dict(
        record_id="missing", record_status="accepted", financial_status="missing_amount",
        source_file="aws_costs.csv", source_row="40", resource_id="internal-id", provider="AWS",
        currency="USD", charge_type="Fee", reporting_month="2025-09", event_date="2025-09-01",
        fx_rate="0.8", amount_original="", cost_chf="",
    )
    history = [
        dict(target, record_id=f"peer{index}", source_row=str(index), reporting_month=month,
             event_date=f"{month}-01", amount_original=price, cost_chf="900.00",
             financial_status="included")
        for index, (month, price) in enumerate(
            [("2025-08", "1115"), ("2025-10", "1126"), ("2025-11", "1135")], 1)
    ]
    facts = {row["record_id"]: row for row in [target, *history]}
    original = dict(charge_category="fee", pricing_unit="Fee", product_region="", product_servicecode="Support")
    data = SimpleNamespace(decision=date(2026, 11, 21), finances=facts, originals=dict.fromkeys(facts, original))
    monkeypatch.setenv("OPENAI_API_KEY", "test-credential")

    def response(url, *, headers, json, timeout):
        assert url == "https://api.openai.com/v1/responses"
        assert json["store"] is False
        import json as parser
        payload = parser.loads(json["input"])
        assert payload == {
            "charge": {"kind": "recurring_fee"},
            "comparable_bills": [
                {"id": 1, "month_offset": -1, "alignment": {"fee_chf": "close", "fee_native": "similar"}},
                {"id": 2, "month_offset": 1, "alignment": {"fee_chf": "close", "fee_native": "close"}},
                {"id": 3, "month_offset": 2, "alignment": {"fee_chf": "close", "fee_native": "similar"}},
            ],
        }
        return httpx.Response(200, json={"status": "completed", "model": "test-model", "output": [
            {"type": "message", "content": [
                {"type": "output_text", "text": '{"basis":"fee_chf","peer_ids":[1,2,3]}'}
            ]},
        ]})

    monkeypatch.setattr(httpx, "post", response)
    assert cost_estimation.estimate_missing_costs(data, {"missing": object()}) == {}
    estimate = cost_estimation.estimate_missing_costs(data, {})["missing"]
    assert estimate.amount_chf == Decimal("900.00")
    assert estimate.comparables == tuple(history)
    assert "OpenAI-assisted estimate (test-model)" in estimate.target["evidence_detail"]

    monkeypatch.setattr(cost_estimation, "request_basis", lambda *_:
                        (cost_estimation.PricingBasis(basis="fee_chf", peer_ids=[1, 2, 4]), "test-model"))
    with pytest.raises(cost_estimation.EstimationError, match="invalid billing comparables"):
        cost_estimation.estimate_missing_costs(data, {})
