import json
from datetime import date
from decimal import Decimal

import httpx

from backend.recommendation_forecast import historical_months, spending_projection
from backend.recommendations import summarize_groups
from backend.recommendation_savings import licence_spend


def test_licence_spending_uses_monthly_seats_and_recurring_annual_floor():
    base = dict(price_per_seat="21", price_per_licence="", fx_rate="0.8076", currency="USD",
                licences_purchased="18", contract_end="2027-02-28", notice_period_days="30",
                source_file="ai_subscriptions.csv", source_row="12")
    history = {
        "2026-06": dict(base, licences_active_30d="12"),
        "2026-07": dict(base, licences_active_30d="12", price_per_seat=""),
        "2026-08": dict(base, licences_active_30d="11"),
    }
    months, annual = licence_spend(history, ["2026-05", "2026-07", "2026-08"], 6, date(2026, 11, 21))
    assert months[0]["amount"] is None
    assert months[1]["reason"] == "Missing valid seat price or CHF exchange rate"
    assert months[2]["amount"] == Decimal("118.7172")
    assert months[2]["unused_seats"] == 7
    assert annual["annual"] == Decimal("1221.0912")
    assert annual["effective_date"] == date(2027, 3, 1)
    assert annual["notice_deadline"] == date(2027, 1, 29)
    assert annual["purchased_seats"] == 18
    assert annual["first_year"] < annual["annual"]
    _, missed = licence_spend(history, [], 6, date(2027, 1, 30))
    assert missed["notice_deadline"] == annual["notice_deadline"]
    assert missed["effective_date"] is None
    assert missed["first_year"] is None


def test_grouped_recommendations_count_distinct_safe_estimates():
    def member(identifier, status, value):
        return {"id": identifier, "safety_status": status, "persistent_unused": 2,
                "estimate": {"measure_id": identifier, "estimates": [{
                    "horizon": "steady_state", "estimate_status": "modeled", "net_chf": value,
                    "savings_kwh": None, "savings_location_kg": None,
                }]}}

    group = {
        ("Tool A", "resize"): [member("a", "eligible", 100), member("a", "eligible", 100),
                               member("b", "human_review", 200), member("c", "blocked", 400),
                               member("d", "eligible", 800)],
        ("Tool B", "resize"): [member("e", "eligible", 1600)],
    }
    overlap = [{"measure_id": "d", "related_measure_id": "e"}]
    first, second = summarize_groups(group, "tool", overlap)
    assert first["safety_counts"] == {"eligible": 3, "human_review": 1, "blocked": 1}
    assert first["savings"]["steady_state"]["net_chf"] == {"eligible": 100, "conditional": 200, "quantified": 2}
    assert first["savings"]["steady_state"]["savings_kwh"]["eligible"] is None
    assert first["omitted_measure_count"] == second["omitted_measure_count"] == 1
    assert second["savings"]["steady_state"]["net_chf"]["eligible"] is None


def test_spending_projection_starts_after_history_and_applies_renewals_by_scope():
    start, stop = date(2025, 9, 1), date(2026, 9, 1)
    history = historical_months(start, stop)

    def licence(effective):
        return {"estimate": None, "safety_status": "eligible",
                "projection_history": dict.fromkeys(history, Decimal("380")),
                "licence_spend": {"annual": Decimal("456"), "effective_date": effective}}

    members = [licence(date(2027, 4, 1)), licence(None)]
    projection = spending_projection(members, 2, history, stop, date(2026, 11, 21))
    assert projection["history"] == [{"month": month, "published_chf": 380} for month in ("2026-06", "2026-07", "2026-08")]
    assert projection["forecast"][0] == {"month": "2026-09", "current_chf": 380, "if_followed_chf": 380}
    assert projection["forecast"][-1] == {"month": "2027-08", "current_chf": 380, "if_followed_chf": 342}
    assert projection["savings_chf"] == 190
    assert projection["covered_scopes"] == 1
    assert spending_projection(members[1:], 1, history, stop, date(2026, 11, 21)) is None


def test_spending_projection_prorates_conditional_runtime_savings():
    history = ["2026-06", "2026-07", "2026-08"]
    member = {"safety_status": "human_review", "projection_history": dict.fromkeys(history, Decimal("250")),
              "estimate": {"earliest_effective_date": date(2026, 12, 21), "estimates": [{
                  "horizon": "steady_state", "net_chf": Decimal("1860"), "estimate_status": "conditional",
              }]}}
    projection = spending_projection([member], 1, history, date(2026, 9, 1), date(2026, 11, 21))
    assert projection["conditional"]
    assert [point["if_followed_chf"] for point in projection["forecast"][:5]] == [250, 250, 250, 195, 95]
    assert projection["savings_chf"] == 1295

from backend.recommendation_tags import ReviewTag, cache_path, cached_tag, enrich, evidence_version, final_status, read_tags, verify_tag
from src.recommendations import recurring, seat_gap, server_weeks, unique_periods


def test_recurrence_needs_repeated_recent_observations_with_coverage():
    weeks = {f"week-{index:02}" for index in range(12)}
    observed = dict.fromkeys(weeks)
    qualifying = dict.fromkeys(sorted(weeks)[6:])
    assert recurring(observed, qualifying, weeks, 75)
    assert not recurring(observed, dict.fromkeys(sorted(weeks)[:6]), weeks, 75)
    assert not recurring(observed, {"week-11": None}, weeks, 75)
    assert not recurring(dict.fromkeys(sorted(weeks)[6:]), qualifying, weeks, 75)


def test_duplicate_period_cannot_supply_evidence():
    row = dict(event_date="2026-08-03", cpu_avg_pct="5", cpu_max_pct="20",
               ram_avg_pct="40", uptime_h="120")
    assert server_weeks([row], {row["event_date"]}) == (
        {row["event_date"]: [row]}, {row["event_date"]: [row]},
    )
    assert server_weeks([row, row], {row["event_date"]}) == ({}, {})
    assert unique_periods([row, row, dict(row, event_date="2026-08-10")], "event_date").keys() == {"2026-08-10"}
    assert seat_gap({"licences_purchased": "10", "licences_active_30d": "0"}) == 10
    assert seat_gap({"licences_purchased": "10", "licences_active_30d": "11"}) == 0


def test_ai_tags_can_add_review_but_cannot_clear_protections():
    item = dict(id="one", category="Licence", rule_status="eligible", observed=3, qualifying=3,
                persistent_unused=2, protection_evidence_ids=[],
                estimate={"notice_deadline": None, "estimates": [{"horizon": "steady_state", "net_chf": 40,
                                          "savings_kwh": None, "savings_location_kg": None}]})
    review = ReviewTag(decision="human_review", reason="estimate_coverage", evidence_id="one.estimate")
    eligible = ReviewTag(decision="eligible", reason="rule_eligibility", evidence_id="one.rule")
    assert verify_tag(item, review)
    assert verify_tag(item, eligible)
    assert not verify_tag(item, review.model_copy(update={"evidence_id": "another.estimate"}))
    assert not verify_tag(dict(item, rule_status="blocked"), eligible)
    assert final_status("eligible", review) == "human_review"
    assert final_status("blocked", eligible) == "blocked"
    assert final_status("human_review", eligible) == "human_review"
    assert final_status("eligible", None) == "eligible"


def test_ai_batch_persists_validated_tags_and_reuses_them(tmp_path, monkeypatch):
    item = dict(id="seat", category="Licence", rule_status="eligible", observed=3, qualifying=3,
                persistent_unused=2, protection_evidence_ids=[], evidence=[], next_check="Verify notice.",
                decision_as_of=date(2026, 11, 21),
                estimate={"notice_deadline": date(2026, 11, 25), "estimates": []})
    monkeypatch.setattr("backend.recommendation_tags.settings", lambda: ("test-key", "test-model"))
    calls = []
    legacy_tag = {"decision": "human_review", "reason": "contract", "evidence_id": "seat.notice"}
    path = cache_path(tmp_path, "run")
    path.parent.mkdir()
    path.write_text(json.dumps({"seat": {"version": evidence_version(item), "tag": legacy_tag}}), encoding="utf-8")
    assert cached_tag(item, read_tags(tmp_path, "run")).explanation is None
    explanation = "Two seats were persistently unused, and the notice deadline is four days away."

    def respond(url, **options):
        calls.append(url)
        facts = json.loads(options["json"]["input"])[0]
        assert facts["seat.notice"] == {"notice_days_remaining": 4}
        data = {"tags": [{**legacy_tag, "explanation": explanation}]}
        return httpx.Response(200, request=httpx.Request("POST", url), json={
            "output": [{"content": [{"type": "output_text", "text": json.dumps(data)}]}],
        })

    monkeypatch.setattr("backend.recommendation_tags.httpx.post", respond)
    assert enrich(tmp_path, "run", [item]) == 1
    saved = read_tags(tmp_path, "run")
    assert cached_tag(item, saved).explanation == explanation
    assert final_status(item["rule_status"], cached_tag(item, saved)) == "human_review"
    assert cached_tag(dict(item, evidence=[{"file": "contracts.csv", "row": 5}]), saved) is None
    assert enrich(tmp_path, "run", [item]) == 0
    assert len(calls) == 1
