import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.main import create_app
from backend.schemas import Measurement
from src.ingest import CORE_FILES, TEMPLATES, snapshot


@pytest.fixture
def sources(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for name in (*CORE_FILES, *TEMPLATES):
        (data / name).write_bytes(b"id,note\r\n1,\"quoted, text\"\r\n")
    return data


def test_snapshot_is_reproducible_immutable_and_leaves_sources_unchanged(sources, tmp_path):
    out = tmp_path / "outputs"
    before = {p.name: p.read_bytes() for p in sources.iterdir()}
    (sources / "extra.csv").write_text("excluded", encoding="utf-8")
    first = snapshot(sources, out)
    assert snapshot(sources, out) == first
    assert len(first["files"]) == 15
    assert all((sources / name).read_bytes() == content for name, content in before.items())
    original = out / "snapshots" / first["snapshot_id"] / "manifest.json"
    original_bytes = original.read_bytes()
    (sources / CORE_FILES[0]).write_text("changed", encoding="utf-8")
    second = snapshot(sources, out)
    assert second["snapshot_id"] != first["snapshot_id"]
    assert original.read_bytes() == original_bytes


def test_missing_source_does_not_publish_snapshot(sources, tmp_path):
    (sources / CORE_FILES[0]).unlink()
    out = tmp_path / "outputs"
    with pytest.raises(FileNotFoundError):
        snapshot(sources, out)
    assert not (out / "current_snapshot.json").exists()


def test_health_works_before_ingestion_and_results_fail_closed(tmp_path):
    with TestClient(create_app(tmp_path, tmp_path)) as client:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["data_ready"] is False
        assert health.json()["snapshot_id"] is None
        for route in (
            "/runs/current", "/runs/a/overview", "/runs/a/findings",
            "/runs/a/findings/b", "/runs/a/measures", "/runs/a/safety-decisions",
            "/runs/a/factors", "/packages/b", "/packages/b/exports/baseline.csv",
            "/packages/b/exports/measures.csv",
        ):
            response = client.get("/api/v1" + route)
            assert response.status_code == 503
            assert response.json()["detail"]["code"] == "not_ready"
        assert client.get("/api/v1/runs/a/unknown").status_code == 422
        assert client.get("/api/v1/runs/bad.id/overview").status_code == 422


def test_gets_do_not_reopen_snapshot_or_raw_sources(sources, tmp_path, monkeypatch):
    manifest = snapshot(sources, tmp_path / "outputs")
    with TestClient(create_app(tmp_path / "outputs", tmp_path / "no-dist")) as client:
        def unexpected_read(*args, **kwargs):
            raise AssertionError("GET reloaded a file")
        monkeypatch.setattr(Path, "read_text", unexpected_read)
        monkeypatch.setattr(Path, "read_bytes", unexpected_read)
        for _ in range(2):
            assert client.get("/api/v1/health").json()["snapshot_id"] == manifest["snapshot_id"]
            assert client.get("/api/v1/runs/current").status_code == 503


def test_bad_snapshot_pointer_stays_not_ready(tmp_path):
    (tmp_path / "current_snapshot.json").write_text(json.dumps({"snapshot_id": "../../data"}))
    with TestClient(create_app(tmp_path, tmp_path)) as client:
        result = client.get("/api/v1/health").json()
        assert result["snapshot_id"] is None
        assert result["data_ready"] is False


def test_static_build_and_api_namespace_do_not_overlap(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<h1>GreenOps</h1>")
    (dist / "assets" / "app.js").write_text("console.log('local')")
    with TestClient(create_app(tmp_path / "outputs", dist)) as client:
        assert "<h1>GreenOps</h1>" in client.get("/").text
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/api/v1/health").status_code == 200
        response = client.get("/api/v1/typo")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "not_found"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_measurements_are_rejected(value):
    with pytest.raises(ValidationError):
        Measurement(value=value, unit="CHF", estimated=False, quality_flags=["unknown"])


def test_unknown_measurement_preserves_null():
    result = Measurement(value=None, unit="kWh", estimated=True, quality_flags=["missing_factor"])
    assert result.model_dump()["value"] is None
