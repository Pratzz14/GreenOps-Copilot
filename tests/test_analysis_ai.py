"""Drafting sends only question and schema, and applies the regular SQL validator."""
import json as jsonlib
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from backend import analysis, analysis_ai
from backend.main import create_app


def test_draft_validates_provider_output_and_does_not_execute(monkeypatch, tmp_path):
    columns = {"cost_chf": "decimal", "baseline_eligible": "boolean", "record_status": "text"}
    dataset = {"name": "cost_facts", "unavailable": None, "fields": [
        {"name": name, "type": kind} for name, kind in columns.items()
    ]}
    app = create_app(tmp_path, tmp_path / "dist")
    app.state.silver = SimpleNamespace(version="version", columns={"cost_facts": columns})
    monkeypatch.setattr(analysis, "catalog", lambda request: (app.state.silver, [dataset]))
    client = TestClient(app)
    url = "/api/v1/analysis/draft"
    question = {"version": "version", "question": "How much did we spend?"}
    monkeypatch.setattr(analysis_ai, "ENV_FILE", tmp_path / ".env")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert client.post(url, json=question).status_code == 503

    (tmp_path / ".env").write_text("OPENAI_API_KEY=test-credential\n", encoding="utf-8")

    def reply(url, *, headers, json, timeout):
        assert url == "https://api.openai.com/v1/responses"
        assert headers == {"Authorization": "Bearer test-credential"}
        assert json["store"] is False
        assert jsonlib.loads(json["input"]) == {
            "datasets": [dataset],
            "scope": {"period": "baseline", "disposition": "accepted", "financial": "eligible"},
            "question": question["question"],
        }
        return httpx.Response(200, json={"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": encoded}]}
        ]})

    monkeypatch.setattr(httpx, "post", reply)
    encoded = jsonlib.dumps({
        "dataset": "cost_facts", "sql": "SELECT SUM(cost_chf) FROM cost_facts WHERE baseline_eligible AND "
               "(record_status = 'accepted' OR record_status IS NULL)",
        "explanation": "Totals recorded CHF.",
    })
    assert client.post(url, json=question).json() == jsonlib.loads(encoded)
    encoded = jsonlib.dumps({"dataset": "cost_facts", "sql": "SELECT unknown FROM cost_facts", "explanation": ""})
    assert client.post(url, json=question).status_code == 422
    encoded = jsonlib.dumps({"dataset": "cost_facts", "sql": "SELECT * FROM read_csv('data.csv')", "explanation": ""})
    assert client.post(url, json=question).status_code == 422
    encoded = jsonlib.dumps({"dataset": "unknown_table", "sql": "SELECT cost_chf FROM cost_facts", "explanation": ""})
    assert client.post(url, json=question).status_code == 422
    encoded = jsonlib.dumps({"dataset": None, "sql": None, "explanation": "Choose a dataset with department information."})
    assert client.post(url, json=question).json()["sql"] is None
