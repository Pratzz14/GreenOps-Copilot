"""Regression checks for Gold publication and decision integrity."""

import csv
import io
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D

import duckdb
import pytest
from fastapi.testclient import TestClient

from backend.gold import GoldRead
from backend.gold_models import GoldProtection
from backend.main import create_app
from src.factors import SCENARIOS
from src.gold import DATABASE, SCHEMA, TABLES, TEMPLATES, current_run, publish, query, resolve_run, statement_sql
from src.gold_baseline import estimate
from src.gold_measures import CAP, HORIZONS, conflicts, first_year_fraction, local_at, training_day
from src.optimizer import Candidate, Contribution, meets, select
from src.profile import read_csv
from src.silver_storage import atomic_csv
from test_silver import build_small  # noqa: F401 — reuse the standard Silver fixture


def candidate(identifier, status, chf, carbon, cost):
    amounts = Contribution(D(chf), D(1), D(carbon), D(cost))
    return Candidate(identifier, status, {(s, h): amounts for s in SCENARIOS for h in HORIZONS})


def test_exact_thresholds_and_deterministic_constraints():
    baseline = {s: (D(100), D(100), D(100)) for s in SCENARIOS}
    exact = candidate("exact", "eligible", 25, 40, CAP)
    assert meets(exact.estimates["mid", "steady_state"], D(100), D(100))
    assert not meets(Contribution(D("24.9999999999"), D(0), D(40), CAP), D(100), D(100))
    assert not meets(Contribution(D(25), D(0), D("39.9999999999"), CAP), D(100), D(100))
    assert not meets(Contribution(D(25), D(0), D(40), CAP + D(".01")), D(100), D(100))
    overlapping = candidate("alternative", "eligible", 25, 40, CAP)
    for options in ([exact, overlapping], [overlapping, exact]):
        selected, _ = select(options, baseline, [("exact", "alternative", "excludes")], True)
        assert [row.identifier for row in selected] == ["alternative"]
    assert select([exact], baseline, [("exact", "prerequisite", "requires")], True)[0] == ()
    review = candidate("review", "human_review", 40, 50, 100)
    assert select([exact, review], baseline, [], False, conditional=True)[0] == (review,)


def test_budget_search_keeps_lower_ranked_independent_seat_measures():
    baseline = {s: (D(1000), D(100), D(100)) for s in SCENARIOS}
    development = candidate("development", "human_review", 20, 40, 3300)
    gpu = candidate("gpu", "human_review", 20, 30, 3300)
    licences = [candidate(f"seat-{price:02}", "eligible", price, 0, 1100) for price in range(1, 43)]
    selected, estimates = select([*licences, gpu, development], baseline,
                                 [("development", "gpu", "excludes")], False, conditional=True)
    assert {row.identifier for row in selected} == {"development", *(f"seat-{price}" for price in range(31, 43))}
    assert estimates["mid", "steady_state"].implementation == CAP
    assert estimates["mid", "steady_state"].chf == 20 + sum(range(31, 43))


def test_environmental_units_and_protection_boundaries():
    assert estimate(D(1000), "tokens", "Germany", "mid") == (D(".48"), D(".1584"))
    assert estimate(D(10), "node", "Germany", "mid") == (D("4.725"), D("1.55925"))
    assert estimate(D(10), "node", "Switzerland", "mid") == (D("4.725"), D(".231525"))
    assert estimate(D(10), None, "Germany", "mid") == (None, None)
    assert training_day(date(2027, 1, 3)) and not training_day(date(2027, 1, 4))
    begins = local_at(date(2027, 1, 1))
    ends = local_at(date(2027, 1, 4))
    rule = {"action_scope": "shutdown", "starts_at": begins, "ends_at": ends}
    assert conflicts(rule, "shutdown", begins, ends)
    assert not conflicts(rule, "shutdown", ends, ends + timedelta(hours=1))
    assert not conflicts(rule, "read", begins, ends)
    assert first_year_fraction(date(2026, 11, 21), date(2027, 11, 21)) == 0
    assert first_year_fraction(date(2026, 11, 21), date(2026, 11, 21)) == 1
    assert first_year_fraction(date(2026, 11, 21), date(2027, 5, 21)) == D(184) / 365
    assert first_year_fraction(date(2026, 11, 21), None) is None


def test_protection_timestamps_keep_zurich_offset_in_api():
    with duckdb.connect() as db:
        db.execute(SCHEMA.read_text(encoding="utf-8"))
        db.execute("""
            INSERT INTO gold.analysis_run VALUES (
                'run', 'snapshot', 'silver', 'calculation', DATE '2025-09-01', DATE '2026-09-01',
                DATE '2026-11-21', 'Europe/Zurich', 'CO2', 'partial', 'partial', 'partial',
                .25, .40, 16500, 1100, 'evidence'
            );
            INSERT INTO gold.subject (run_id, subject_id, subject_type, subject_name, evidence_set_id)
                VALUES ('run', 'prod', 'resource', 'dp-prod', 'evidence');
            INSERT INTO gold.protection_window VALUES (
                'run', 'protection', 'prod', 'finance-close', 'shutdown',
                TIMESTAMPTZ '2026-11-27 00:00:00+01', TIMESTAMPTZ '2026-11-28 04:00:00+01',
                'blocked', 'Finance', 'Month end', 'evidence'
            )
        """)
        result = GoldRead(db, (), {"run_id": "run"}, {}, None)
        rule = GoldProtection.model_validate(result.protections()[0])
        assert rule.starts_at.astimezone(timezone.utc) == datetime(2026, 11, 26, 23, tzinfo=timezone.utc)
        assert rule.ends_at.astimezone(timezone.utc) == datetime(2026, 11, 28, 3, tzinfo=timezone.utc)


def test_published_run_queries_exports_and_stale_pointer(build_small):
    _, out, silver_version, _ = build_small
    day = date(2026, 11, 21)
    run_id = publish(out, day)
    directory, metadata = resolve_run(out, run_id)
    before = (directory / "manifest.json").read_bytes()
    assert publish(out, day) == run_id
    assert (directory / "manifest.json").read_bytes() == before
    assert metadata["silver_version"] == silver_version

    with duckdb.connect(str(directory / DATABASE), read_only=True) as db:
        queries = statement_sql(db, (directory / "queries.sql").read_text(encoding="utf-8"))
        evidence_id = db.execute("SELECT evidence_set_id FROM gold.analysis_run").fetchone()[0]
        subject_id = db.execute("SELECT subject_id FROM gold.subject WHERE subject_name='dp-prod'").fetchone()[0]
        scope = dict(run_id=run_id, scenario="mid", group_by="department", seat_month=date(2026, 8, 1),
                     package_id=run_id, horizon="steady_state", subject_id=subject_id, action="shutdown",
                     evidence_set_id=evidence_id,
                     window_start=datetime(2026, 8, 1, tzinfo=timezone.utc),
                     window_end=datetime(2026, 9, 1, tzinfo=timezone.utc))
        results = {index: query(db, queries, index, **scope) for index in range(1, 16)}
        assert results[11] == []
        assert len(results[13]) == 6 and len(results[14]) == 17
        assert all(row["target_status"] == "unassessed" and row["meets_all_three_scenarios"] is None
                   for row in results[10])
        assert db.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='gold'").fetchone()[0] == 14

    with TestClient(create_app(out, out)) as client:
        base = f"/api/v1/runs/{run_id}"
        assert client.get("/api/v1/runs/current").json()["run_id"] == run_id
        for suffix in ("/overview", "/breakdowns?group=tool", "/findings", "/measures", "/safety-decisions", "/factors"):
            assert client.get(base + suffix).status_code == 200
        catalog = client.get(base + "/tables").json()
        assert catalog["run_id"] == run_id
        assert {entry["name"] for entry in catalog["tables"]} == set(TABLES)
        for entry in catalog["tables"]:
            page = client.get(base + f"/tables/{entry['name']}?limit=1").json()
            assert page["row_count"] == entry["row_count"]
            assert any(column["name"] == "run_id" and column["primary_key"] for column in page["columns"])
            assert len(page["items"]) == min(1, entry["row_count"])
            assert page["run_id"] == run_id
        factor_page = client.get(base + "/tables/factor?limit=100").json()
        german = next(row for row in factor_page["items"] if row["factor_id"] == "grid_de")
        swiss = next(row for row in factor_page["items"] if row["factor_id"] == "grid_ch")
        assert german["value_mid"] == "0.330000000000"
        assert swiss["value_mid"] is None
        assert client.get(base + "/tables/factor?offset=1&limit=1").json()["items"] == factor_page["items"][1:2]
        assert client.get(base + "/tables/factor?limit=101").status_code == 422
        assert client.get(base + "/tables/unknown").status_code == 404
        assert client.get(base + f"/evidence/{evidence_id}?limit=2").json()["total"] >= 1
        package = client.get(f"/api/v1/packages/{run_id}").json()
        assert len(package["scores"]) == 6 and package["members"] == []
        for filename, official in TEMPLATES.items():
            response = client.get(f"/api/v1/packages/{run_id}/exports/{filename}")
            assert response.status_code == 200
            header, *_ = list(csv.reader(response.content.decode("utf-8-sig").splitlines()))
            assert header == read_csv(official)[0]
            assert "draft-" in response.headers["content-disposition"]
            submission = client.get(f"/api/v1/submissions/{run_id}/{filename}")
            assert submission.status_code == 200
            assert submission.content.startswith(b"\xef\xbb\xbf")
            assert official.name in submission.headers["content-disposition"]
            if filename == "baseline.csv":
                exported = list(csv.DictReader(io.StringIO(submission.content.decode("utf-8-sig"))))
                assert "Reconciliation by cost stream" in exported[0]["calculation_or_assumption"]
        assert client.get("/api/v1/runs/unknown/overview").status_code == 404
        assert client.get(base + "/evidence/unknown").status_code == 404
        atomic_csv(out / "current_silver.csv", [{"version": "a" * 64}])
        with pytest.raises(OSError):
            publish(out, day)
        assert current_run(out) == run_id
        assert client.get("/api/v1/runs/current").status_code == 503
        assert client.get(base + "/overview").status_code == 200
        (directory / "baseline.csv").write_text("corrupt", encoding="utf-8")
        assert client.get(base + "/overview").status_code == 503
