"""Full-pipeline release checks: reruns, interruption, rollback, history and unknown values."""
import os
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from src import gold, pipeline
from src.ingest import ROOT
from src.profile import read_csv
from test_supplemental import write_sources

DAY = date(2026, 11, 21)


@pytest.fixture
def sources(tmp_path):
    data, extra = write_sources(tmp_path)
    return data, extra, tmp_path / "out"


def pointer(out):
    return read_csv(out / "current_release.csv", ("release",))[1][0]["release"]


def test_identical_rerun_keeps_one_release(sources):
    data, extra, out = sources
    release = pipeline.build(data, extra, out, DAY)
    directory = pipeline.release_directory(out, release)
    manifest = (directory / "gold" / gold.current_run(directory) / "manifest.json").read_bytes()
    assert pipeline.build(data, extra, out, DAY) == release == pointer(out)
    assert [path.name for path in (out / "releases").iterdir()] == [directory.name]
    assert (directory / "gold" / gold.current_run(directory) / "manifest.json").read_bytes() == manifest
    assert pipeline.active_output(out) == directory


def test_interrupted_build_leaves_the_active_release_untouched(sources, monkeypatch):
    data, extra, out = sources
    release = pipeline.build(data, None, out, DAY)

    def interrupt(*args, **kwargs):
        raise RuntimeError("interrupted")
    monkeypatch.setattr(pipeline.gold, "publish", interrupt)
    with pytest.raises(RuntimeError):
        pipeline.build(data, extra, out, DAY)
    assert pointer(out) == release
    assert [path.name for path in (out / "releases").iterdir()] == [pipeline.release_directory(out, release).name]


def test_rollback_history_coverage_and_unknown_values(sources, tmp_path):
    data, extra, out = sources
    core = pipeline.build(data, None, out, DAY)
    full = pipeline.build(data, extra, out, DAY)
    assert core != full and pointer(out) == full
    full_directory = pipeline.release_directory(out, full)
    full_run = gold.current_run(full_directory)

    # An unknown value stays unknown in the published activity, the API and the export.
    with TestClient(create_app(out, tmp_path / "dist")) as client:
        coverage = client.get(f"/api/v1/runs/{full_run}/coverage")
        assert coverage.status_code == 200
        storage = [row for row in coverage.json() if row["boundary_id"] == "m365:storage-gb-days"]
        assert len(storage) == 1 and storage[0]["state"] == "missing_energy_factor"
        assert Decimal(storage[0]["activity_quantity"]) == 10 and storage[0]["activity_unit"] == "GB-days"
        assert storage[0]["energy_kwh"] is None and storage[0]["location_kg"] is None
        assert Decimal(storage[0]["planning_kwh"]) == Decimal("0.00026244")
        assert storage[0]["planning_kg_co2e"] is None
        breakdown = client.get(f"/api/v1/runs/{full_run}/breakdowns?group=tool").json()
        m365 = next(row for row in breakdown if row["driver"] == "Microsoft 365" and row["report_month"] is None)
        assert Decimal(m365["planning_kwh"]) == Decimal(storage[0]["planning_kwh"])
        assert m365["planning_energy_boundaries"] == ["m365:storage-gb-days"]
        assert m365["estimated_kwh"] is None and m365["reporting_kg_co2e"] is None
        assert all(row["energy_kwh"] is None or row["state"] != "missing_activity" for row in coverage.json())
        findings = {row["finding_id"] for row in client.get(f"/api/v1/runs/{full_run}/findings").json()}
        assert {"m365-electricity-coverage", "powerbi-report-ranking", "catalogue-retention", "backup-retention"} <= findings
        measures = {row["measure_id"]: row for row in client.get(f"/api/v1/runs/{full_run}/measures").json()}
        assert measures["flexible-jobs"]["safety_status"] == "human_review"
        assert all(estimate["estimate_status"] == "unquantified" for estimate in measures["flexible-jobs"]["estimates"])
        sources_api = {row["name"]: row for row in client.get("/api/v1/data-quality").json()["sources"]}
        assert len(sources_api) == 28
        assert sources_api["backup_chains.csv"]["additivity"] == "point_in_time"
        assert sources_api["m365_usage.csv"]["grain"] == "One department per week"
    export = {row["parameter"]: row for row in read_csv(full_directory / "gold" / full_run / "baseline.csv")[1]}
    assert export["total_co2_market_based_baseline_year_kg"]["value_mid"] == ""
    assert export["grid_mix_location_based_switzerland"]["value_mid"] == ""
    assert all(row[field].strip().lower() not in {"nan", "inf", "-inf", "infinity", "-infinity"}
               for row in export.values() for field in ("value_low", "value_mid", "value_high"))

    pipeline.activate(out, core)
    assert pipeline.active_output(out) == pipeline.release_directory(out, core)
    with TestClient(create_app(out, tmp_path / "dist")) as client:
        assert client.get("/api/v1/runs/current").json()["run_id"] != full_run
        # The earlier full run stays readable after the rollback.
        assert client.get(f"/api/v1/runs/{full_run}/overview").status_code == 200
        assert len(client.get("/api/v1/data-quality").json()["sources"]) == 13

    archived = next((full_directory / "snapshots").iterdir()) / "raw" / "web_traffic.csv"
    archived.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError):
        pipeline.activate(out, full)
    assert pointer(out) == core
    with pytest.raises(ValueError):
        pipeline.activate(out, "not-a-release")


@pytest.mark.skipif(not os.environ.get("GREENOPS_FULL_PIPELINE"),
                    reason="Builds the complete case data. Set GREENOPS_FULL_PIPELINE=1 to run it.")
def test_full_case_data_reproduces_the_pinned_baseline(tmp_path):
    out = tmp_path / "out"
    release = pipeline.build(ROOT / "data", ROOT / "sprintd-basel-green-ai-data" / "extra", out, DAY)
    directory = pipeline.release_directory(out, release)
    rows = {row["parameter"]: row for row in
            read_csv(directory / "gold" / gold.current_run(directory) / "baseline.csv")[1]}
    pinned = {"total_cost_baseline_year_chf": "463471.49", "total_energy_baseline_year_kwh": "128061.32",
              "total_co2_location_based_baseline_year_kg": "13218.68"}
    for parameter, value in pinned.items():
        assert Decimal(rows[parameter]["value_mid"]).quantize(Decimal("0.01")) == Decimal(value)
    with TestClient(create_app(out, tmp_path / "dist")) as client:
        run = client.get("/api/v1/runs/current").json()["run_id"]
        overview = client.get(f"/api/v1/runs/{run}/overview").json()
        # Swiss operating estimate: published Swiss kWh times 0.049 kg CO2e per kWh.
        assert Decimal(overview["swiss_operating_kg_co2e"]).quantize(Decimal("0.01")) == Decimal("3959.23")
    silver = directory / "silver" / gold.pointer(directory, "current")
    scopes = {row["entity"] for row in read_csv(silver / "supplemental_comparisons.csv")[1]
              if row["comparison"] == "provider_spend"}
    assert "Azure + AWS + Swiss Hoster" in scopes and "All recorded charges" in scopes
