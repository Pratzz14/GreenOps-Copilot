"""Silver analyst workspace acceptance checks against independent Silver calculations."""
from collections import defaultdict
from decimal import Decimal
from time import monotonic

import pytest
from fastapi.testclient import TestClient

from backend.analysis import Runtime, Scope, STARTERS, TTL
from backend.analysis_data import availability, prepare
from backend.analysis_engine import Visual, compile_visual, validate_sql
from backend.main import create_app
from src.ingest import ROOT
from src.normalize import build
from src.reconciliation import publish


@pytest.fixture(scope="module")
def workspace(tmp_path_factory):
    out = tmp_path_factory.mktemp("analyst")
    # Reuse the normal publishing entry point in a disposable workspace.
    import shutil
    shutil.copytree(ROOT / "data" / "bronze", out / "data" / "bronze")
    from src.ingest import snapshot
    snapshot(out / "data", out)
    build(out / "data", out)
    publish(out)
    dist = out / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<main>GreenOps</main>", encoding="utf-8")
    with TestClient(create_app(out, dist)) as client:
        yield client, out


@pytest.mark.parametrize("sql", [
    "SELECT * FROM cost_facts JOIN assets ON true", "SELECT * FROM cost_facts, cost_facts b",
    "SELECT * FROM cost_facts; SELECT * FROM cost_facts", "DROP TABLE cost_facts",
    "SELECT * FROM read_csv('sample.csv')", "SELECT * FROM duckdb_tables()",
    "SELECT * FROM information_schema.tables", "SELECT * FROM missing",
    "WITH RECURSIVE a AS (SELECT * FROM cost_facts) SELECT * FROM a",
    "WITH a AS (SELECT * FROM cost_facts) SELECT getenv('example') FROM a",
    "SELECT * FROM cost_facts UNION ALL SELECT * FROM cost_facts",
])
def test_sql_scope_restrictions(sql):
    with pytest.raises(ValueError):
        validate_sql(sql, "cost_facts")


def test_visual_month_units_and_protected_division():
    columns = {"event_date": "date", "cost_chf": "decimal", "amount_original": "decimal",
               "currency": "text", "licences_active_30d": "decimal", "licences_purchased": "decimal"}
    definition = Visual.model_validate({
        "groups": [{"field": "event_date", "month": True}],
        "metrics": [{"op": "sum", "field": "amount_original", "name": "recorded"}],
    })
    with pytest.raises(ValueError, match="currency"):
        compile_visual("cost_facts", columns, definition)
    definition = Visual.model_validate(definition.model_dump() | {"filters": [
        {"field": "currency", "op": "eq", "values": ["CHF"]}
    ]})
    sql = compile_visual("cost_facts", columns, definition)
    assert "DATE_TRUNC" in sql and "'CHF'" in sql
    validate_sql(sql, "cost_facts")
    calc = Visual.model_validate({"metrics": [{"op": "calculate", "name": "active_share",
                                             "left": "licences_active_30d", "right": "licences_purchased"}]})
    assert "NULLIF" in compile_visual("cost_facts", columns, calc)


def test_analysis_routes_starters_and_exports(workspace):
    client, _ = workspace
    assert client.get("/", follow_redirects=False).headers["location"] == "/dashboard"
    for path in ("/dashboard", "/data-explorer", "/analysis", "/recommendations"):
        assert client.get(path).status_code == 200
    assert client.get("/api/v1/analysis/missing").json()["detail"]["code"] == "not_found"
    catalog = client.get("/api/v1/analysis/catalog").json()
    assert len(catalog["datasets"]) == 22
    assert all(not entry["unavailable"] for entry in catalog["datasets"])
    version = catalog["version"]
    silver = client.app.state.silver
    runs = {}
    for name, dataset, sql in STARTERS:
        response = client.post("/api/v1/analysis/query", json=dict(version=version, dataset=dataset, mode="sql", sql=sql))
        assert response.status_code == 200, (name, response.text)
        runs[dataset] = response.json()
    costs = runs["cost_facts"]
    actual = sum(Decimal(row[1]) for row in costs["rows"] if row[1] is not None)
    assert actual == Decimal(silver.overview.recorded_cost_chf)
    baseline = silver.rows["cost_baseline"][0]
    assert sum(row[3] for row in costs["rows"]) == int(baseline["missing_amount"]) + int(baseline["missing_fx"])
    seats = defaultdict(lambda: [Decimal(0), Decimal(0)])
    for row in silver.rows["ai_subscriptions"]:
        if row["baseline_overlap"] and row["record_status"] == "accepted" and row["contract_status"] == "Final":
            group = seats[row["product"], row["reporting_month"]]
            group[0] += Decimal(row["licences_active_30d"] or "0")
            group[1] += Decimal(row["licences_purchased"] or "0")
    assert {(row[0], row[1]): [Decimal(row[2]), Decimal(row[3])]
            for row in runs["ai_subscriptions"]["rows"]} == seats

    monthly = runs["platform_monthly_usage_cost"]["rows"]
    resources = {row["resource_id"] for row in silver.rows["data_platform_usage"]}
    expected = defaultdict(Decimal)
    for row in silver.rows["cost_facts"]:
        if (row["source_file"], row["financial_status"]) == ("azure_costs.csv", "included") and row["resource_id"] in resources:
            expected[row["resource_id"], row["reporting_month"]] += Decimal(row["cost_chf"])
    assert {(row[0], row[1]): Decimal(row[5]) for row in monthly if row[5] is not None} == expected
    ai_result = runs["ai_usage_with_cost"]
    expected_ai = sum(Decimal(row["cost_chf"]) for row in silver.rows["cost_facts"]
                      if row["source_file"] == "ai_usage.csv" and row["financial_status"] == "included")
    assert sum(Decimal(row[2]) for row in ai_result["rows"] if row[2] is not None) == expected_ai
    weekly, coverage = prepare(silver, "server_metrics_with_assets", Scope())
    assert len(weekly) == coverage["observations"]
    assert len({(row["server_id"], row["event_date"]) for row in weekly}) == len(weekly)
    assert sum(row[-1] for row in runs["server_metrics_with_assets"]["rows"]) == sum(
        row["baseline_boundary_week"] for row in weekly)
    assert all(row["asset_record_id"] for row in weekly)
    assert all(availability(silver, dataset) is None for _, dataset, _ in STARTERS)

    base = "/api/v1/analysis"
    visual = dict(version=version, dataset="cost_facts", visual=dict(columns=["record_id", "cost_chf"], sort="record_id"))
    result = client.post(base + "/query", json=visual).json()
    meta = result["metadata"]
    assert result["metadata"]["truncated"] and meta["row_count"] == 10_000 and len(result["rows"]) == 100
    assert meta["lineage_field"] == "record_id"
    key = meta["id"]
    assert client.get(f"{base}/results/{key}?offset=100").json()["rows"][0] != result["rows"][0]
    assert client.get(f"{base}/results/{key}/metadata").json() == meta
    exported = client.get(f"{base}/results/{key}/csv").text.splitlines()
    assert len(exported) == 10_001
    assert exported[1].split(",") == result["rows"][0]
    sql = client.post(base + "/preview", json=visual).json()["sql"]
    assert sql == meta["sql"]
    same = client.post(base + "/query", json=visual | {"mode": "sql", "sql": sql}).json()
    assert same["rows"] == result["rows"]

    cte = "WITH c AS (SELECT cost_chf FROM cost_facts WHERE cost_chf IS NULL) SELECT count(*) FROM c"
    response = client.post(base + "/query", json=visual | {"mode": "sql", "sql": cte})
    assert response.status_code == 200 and response.json()["rows"][0][0] > 0

    state = client.app.state.analysis
    created, metadata, rows = state.results[key]
    state.results.move_to_end(key, last=False)
    state.results[key] = (created - TTL, metadata, rows)
    assert client.get(f"{base}/results/{key}").status_code == 404


def test_saved_definitions_and_explicit_version_validation(workspace):
    client, out = workspace
    base = "/api/v1/analysis"
    definition = {"version": "previous-version", "dataset": "cost_facts", "mode": "visual"}
    response = client.post(base + "/saved", json={"name": "Department review", "definition": definition})
    assert response.status_code == 201
    item = response.json()
    key = item["id"]
    assert Runtime(out).read()[key].definition.version == "previous-version"
    assert not client.get(base + "/saved").json()[0]["definition"]["sql"]
    assert client.post(base + "/query", json=definition).status_code == 409
    current = client.get(base + "/catalog").json()["version"]
    response = client.put(f"{base}/saved/{key}", json={"name": "Rebased", "definition": definition | {"version": current}})
    assert response.json()["definition"]["version"] == current
    assert client.delete(f"{base}/saved/{key}").status_code == 204
    assert client.get(base + "/saved").json() == []


def test_cache_bounds():
    from types import SimpleNamespace
    state = Runtime(ROOT / "outputs")
    for number in range(12):
        state.add(SimpleNamespace(id=str(number)), [])
    assert len(state.results) == 10 and "1" not in state.results
    assert state.results["2"][0] <= monotonic()


def stalled_worker(pipe, *_):
    from time import sleep
    pipe.send(("ready", None))
    sleep(30)


def test_worker_timeout_and_recovery(monkeypatch):
    from backend import analysis_engine
    arguments = ("dataset", {"amount": "decimal"}, [{"amount": "0.00012345"}], "SELECT * FROM dataset")
    with monkeypatch.context() as patches:
        patches.setattr(analysis_engine, "worker", stalled_worker)
        patches.setattr(analysis_engine, "BUDGET", 0.1)
        with pytest.raises(TimeoutError, match="five seconds"):
            analysis_engine.execute(*arguments)
    fields, rows, truncated, _ = analysis_engine.execute(*arguments)
    assert fields == [("amount", "DECIMAL(38,8)")]
    assert rows == [["0.00012345"]] and not truncated
