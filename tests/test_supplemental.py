"""Extra-source dispositions, units, reporting boundaries and comparison grain."""
import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.ingest import CORE_FILES, ROOT, TEMPLATES, snapshot
from src.normalize import Record, build, parse_field
from src.profile import read_csv
from src.silver_rules import dates
from src.silver_storage import write_csv
from src.source_specs import EXTRA_FILES, EXTRA_SPECS, GRAINS, SPECS
from src.supplemental import records, schedule_class, standardize
from src.supplemental_comparisons import comparisons

RUN = {"run_id": "R1", "agent": "support-agent", "start": "2026-01-05 10:00:00", "trigger": "ticket",
       "steps": 1, "tool_calls": 0, "retries": 1, "model": {"provider": "Anthropic", "name": "Claude Sonnet 4.6"},
       "usage": {"tokens_in": 100, "cache_read_tokens": 40, "tokens_out": 10}, "duration_s": 8,
       "outcome": "resolved", "department": "IT", "project_id": "p-001"}
BUILD = {"pipeline": "nightly-full", "repo": "r1", "trigger": "schedule", "started_at": "2026-01-05 02:00:00",
         "status": "ok", "team": "T", "project_id": "P-001", "runner": "aws-eu-west-1 (Dublin)",
         "commits_since_last_nightly": 0, "metrics": {"duration_sec": 120, "cpu_h": 0.1}}
EXTRA_ROWS = {
    "ai_invoice_monthly": [("2026-01-01", "Anthropic", "large", 1000, 100, "USD", 5)],
    "backup_chains": [("Finance database", "DB", "Tool A", 100, "daily", 3650, "2026-01-30", "yes", "high", "confidential", 4200),
                      ("Scratch share", "File share", "Tool A", 50, "weekly", 365, "", "no", "low", "internal", 4000)],
    "data_catalog_tables": [("old", "mart", 10, 5, "2024-01-01", "2023-01-01", 4000, "P-001", "internal", "no"),
                            ("keep", "mart", 10, 5, "2024-01-01", "2023-01-01", 4000, "P-001", "internal", "yes"),
                            ("unknown", "mart", 10, 5, "2024-01-01", "2023-01-01", 4000, "P-001", "internal", "")],
    "data_center_locations": [("Azure", "Germany (Frankfurt)", "Frankfurt", "no"),
                              ("Azure", "Nowhere", "Nowhere", "no")],
    "data_platform_jobs": [("2026-01-05", "flexible", "vm-test", "01:00", 2, "ok", "schedule", "flexible: within 24 h"),
                           ("2026-01-05", "deadline", "vm-test", "02:00", 2, "ok", "schedule", "fixed: done by 06:00 (morning reports)"),
                           ("2026-01-05", "close", "vm-test", "03:00", 2, "ok", "schedule", "fixed: month-end close (protection window)"),
                           ("2026-01-05", "unclear", "absent-resource", "04:00", 2, "ok", "manual", "whenever")],
    "headcount": [("2026-01-01", "IT", 10)],
    "log_volume": [("2026-01-05", "api", 2000, "MB", 180, "P-001", 4000)],
    "m365_usage": [("2026-08-31", "IT", 4000, 5, 10000, 700, 14, "MB"),
                   ("2026-08-24", "IT", 4000, 5, 3, 700, 14, "TB")],
    "powerbi_usage": [("2026-01-05", "pbi-01", "Report", "IT", 2, 30, 0, 0, "management")],
    "project_hours_monthly": [("2026-01-01", "P-001", "IT", 100)],
    "projects": [("P-001", "Project", "internal", "", 4000, "2025-01-01", "", "no", "active")],
    "provider_monthly_report": [("2026-01-01", 1000, "Total cost all services")],
    # 23:30 UTC on 31 January is already 1 February in Zurich.
    "web_traffic": [("2026-01-31T23:30:00Z", 10, 2, 5, 10, 0), ("2026-01-10T10:00:00Z", 10, 3, 5, "0.5", 0)],
}


def write_sources(root):
    """Two real rows per core source plus a small, deliberately flawed copy of every extra source."""
    data, extra = root / "data", root / "extra"
    data.mkdir()
    extra.mkdir()
    for name in CORE_FILES:
        columns, rows = read_csv(ROOT / "data" / "bronze" / name)
        write_csv(data / name, rows[:2], columns)
    for name in TEMPLATES:
        (data / name).write_bytes((ROOT / "data" / "bronze" / name).read_bytes())
    for table, rows in EXTRA_ROWS.items():
        columns = list(EXTRA_SPECS[table].types)
        write_csv(extra / f"{table}.csv", [dict(zip(columns, row, strict=True)) for row in rows], columns)
    conflict = {**RUN, "run_id": "R2"}
    agent_lines = [RUN, RUN, conflict, {**conflict, "retries": 3},
                   {**RUN, "run_id": "R3", "usage": {"tokens_in": 100, "cache_read_tokens": 500, "tokens_out": 1}}]
    (extra / "ai_agent_runs.jsonl").write_text(
        "\n".join(json.dumps(line) for line in agent_lines) + "\nnot json\n", encoding="utf-8")
    rerun = {**BUILD, "metrics": {"duration_s": 60, "cpu_h": 0.05}}
    unmeasured = {**BUILD, "pipeline": "app-build", "trigger": "commit", "started_at": "2026-01-06 09:00:00", "metrics": {}}
    (extra / "ci_pipeline_runs.jsonl").write_text(
        "\n".join(json.dumps(line) for line in (BUILD, rerun, BUILD, unmeasured)) + "\n", encoding="utf-8")
    return data, extra


@pytest.fixture
def small_full(tmp_path):
    data, extra = write_sources(tmp_path)
    out = tmp_path / "out"
    snapshot(data, out, extra)
    version = build(data, out, extra)
    directory = out / ".silver-staging" / version

    def table(name):
        return read_csv(directory / f"{name}.csv")[1]
    return SimpleNamespace(data=data, extra=extra, out=out, version=version, table=table,
                           issues={(row["source_file"], row["code"]) for row in table("unresolved_issues")})


def test_ci_jsonl_field_variants_and_malformed_record(tmp_path):
    source = tmp_path / "ci_pipeline_runs.jsonl"
    source.write_text(
        '{"metrics":{"cpu_h":2,"duration_sec":120}}\n'
        '{"metrics":{"duration_s":80}}\n'
        '[1]\n', encoding="utf-8",
    )
    first, second, malformed = records(source, EXTRA_SPECS["ci_pipeline_runs"])
    assert first[1]["duration_seconds"] == "120"
    assert second[1]["duration_seconds"] == "80"
    assert second[1]["cpu_h"] == ""
    assert malformed[0] == 3 and malformed[2]


def test_m365_weekly_stock_is_prorated_and_unit_is_normalized():
    spec = EXTRA_SPECS["m365_usage"]
    record = Record("m365_usage", 2, dict.fromkeys(spec.types, "") | {
        "week_start": "2026-08-31", "storage": "10000", "storage_unit": "MB",
        "teams_video_minutes": "700",
    }, "snapshot")
    for field, kind in spec.types.items():
        parse_field(record, field, kind)
    dates(record, spec.date)
    standardize(record, date(2025, 9, 1), date(2026, 8, 31))
    assert record.row["baseline_days"] == 1
    assert record.row["baseline_storage_gb_days"] == Decimal("10")
    assert record.row["baseline_teams_video_minutes"] == Decimal("100")
    assert record.row["baseline_mails_sent"] is None


def test_registry_covers_every_source_and_keeps_templates_apart():
    assert len(CORE_FILES) == 13 and len(TEMPLATES) == 2
    assert sum(name.endswith(".csv") for name in EXTRA_FILES.values()) == 13
    assert sum(name.endswith(".jsonl") for name in EXTRA_FILES.values()) == 2
    assert set(GRAINS) == set(SPECS) == {*CORE_FILES, *EXTRA_FILES.values()}
    assert not set(TEMPLATES) & set(SPECS)
    assert GRAINS["m365_usage.csv"][1] == "mixed" and GRAINS["backup_chains.csv"][1] == "point_in_time"


def test_snapshot_records_bytes_counts_and_paths_without_changing_identity(tmp_path):
    data, extra = write_sources(tmp_path)
    manifest = snapshot(data, tmp_path / "out", extra)
    details = {entry["name"]: entry for entry in manifest["file_details"]}
    assert len(manifest["files"]) == len(details) == 30 and manifest["extra_source_count"] == 15
    assert details["ai_agent_runs.jsonl"]["record_count"] == 6
    assert details["web_traffic.csv"]["record_count"] == 2
    assert details["web_traffic.csv"]["bytes"] == (extra / "web_traffic.csv").stat().st_size
    assert details["template_measures_package.csv"]["kind"] == "submission_template"
    assert all(set(entry) == {"name", "sha256"} for entry in manifest["files"])
    raw = tmp_path / "out" / "snapshots" / manifest["snapshot_id"] / "raw"
    assert (raw / "ci_pipeline_runs.jsonl").read_bytes() == (extra / "ci_pipeline_runs.jsonl").read_bytes()


def test_jsonl_duplicates_conflicts_reruns_and_malformed_lines(small_full):
    runs = {int(row["source_row"]): row for row in small_full.table("ai_agent_runs")}
    assert [runs[line]["record_status"] for line in range(1, 7)] == [
        "accepted", "duplicate", "review", "review", "review", "quarantined"]
    assert runs[2]["duplicate_of"] == runs[1]["record_id"]
    assert runs[1]["uncached_input_tokens"] == "60" and runs[5]["uncached_input_tokens"] == ""
    assert runs[1]["verified_project_id"] == "P-001"
    assert ("ai_agent_runs.jsonl", "invalid_cache_subset") in small_full.issues
    builds = {int(row["source_row"]): row for row in small_full.table("ci_pipeline_runs")}
    # A rerun shares the run key and stays a separate accepted record. Only the exact copy is excluded.
    assert [builds[line]["record_status"] for line in range(1, 5)] == ["accepted", "accepted", "duplicate", "accepted"]
    assert builds[2]["duration_seconds"] == "60" and builds[4]["duration_seconds"] == ""
    assert builds[1]["region"] == "Ireland (Dublin)"
    assert ("ci_pipeline_runs.jsonl", "missing_run_metrics") in small_full.issues


def test_units_sampling_and_zurich_reporting_dates(small_full):
    late, undersampled = small_full.table("web_traffic")
    assert (late["event_date"], late["reporting_month"], late["expanded_gb"]) == ("2026-02-01", "2026-02", "20")
    assert late["time_utc"].endswith("Z")
    assert undersampled["record_status"] == "review" and undersampled["expanded_gb"] == ""
    boundary, unsupported = small_full.table("m365_usage")
    assert (boundary["storage_gb"], boundary["baseline_days"], boundary["baseline_storage_gb_days"]) == ("10", "1", "10")
    assert unsupported["record_status"] == "review" and unsupported["baseline_storage_gb_days"] == ""
    log = small_full.table("log_volume")[0]
    assert (log["ingested_gb"], log["retained_gb_days"]) == ("2", "360")


def test_locations_jobs_and_protected_inventories(small_full):
    assert ("data_center_locations.csv", "billing_location_conflict") in small_full.issues
    jobs = {row["job_name"]: row for row in small_full.table("data_platform_jobs")}
    assert [jobs[name]["schedule_class"] for name in ("flexible", "deadline", "close", "unclear")] == [
        "flexible", "fixed_deadline", "protection_window", ""]
    assert jobs["deadline"]["deadline_local"] == "06:00" and jobs["flexible"]["deadline_local"] == ""
    assert jobs["flexible"]["owner_department"] == "IT" and jobs["unclear"]["owner_department"] == ""
    assert {("data_platform_jobs.csv", "unclassified_time_window"),
            ("data_platform_jobs.csv", "unmatched_resource")} <= small_full.issues
    protected, candidate = small_full.table("backup_chains")
    assert protected["protection_reasons"] == "ten_year_retention;high_criticality"
    assert (protected["retention_review_candidate"], candidate["retention_review_candidate"]) == ("False", "True")
    assert [row["storage_review_candidate"] for row in small_full.table("data_catalog_tables")] == ["True", "False", ""]


def test_extras_never_enter_the_cost_ledger(small_full, tmp_path):
    core = tmp_path / "core-out"
    core_version = build(small_full.data, core)
    core_facts = read_csv(core / ".silver-staging" / core_version / "cost_facts.csv")[1]
    full_facts = small_full.table("cost_facts")
    assert len(core_facts) == len(full_facts)
    assert [(row["source_file"], row["source_row"], row["cost_chf"], row["financial_status"]) for row in core_facts] == [
        (row["source_file"], row["source_row"], row["cost_chf"], row["financial_status"]) for row in full_facts]
    assert not (core / ".silver-staging" / core_version / "supplemental_comparisons.csv").exists()


def rows(**tables):
    return {name: [SimpleNamespace(row={"record_status": "accepted", "baseline_overlap": True, **row})
                   for row in group] for name, group in tables.items()}


def test_comparisons_aggregate_before_joining():
    empty = dict.fromkeys(("ai_invoice_monthly", "ai_usage", "ai_agent_runs", "ci_pipeline_runs", "aws_costs",
                           "web_traffic", "hoster_invoice", "powerbi_usage", "azure_costs",
                           "project_hours_monthly"), [])
    tables = rows(**empty,
                  provider_monthly_report=[{"reporting_month": "2026-01", "total_cost_chf": Decimal(100)}],
                  headcount=[{"reporting_month": "2026-01", "department": "IT", "fte": Decimal(4)}])
    fact = dict(baseline_eligible=True, financial_status="included", reporting_month="2026-01",
                source_file="azure_costs.csv", reporting_department="IT")
    facts = [dict(fact, provider="Azure", cost_chf=Decimal(30)), dict(fact, provider="Azure", cost_chf=Decimal(20)),
             dict(fact, provider="AWS", cost_chf=Decimal(40), source_file="aws_costs.csv"),
             dict(fact, provider="Vendor", cost_chf=Decimal(999), financial_status="draft")]
    result = {(row["comparison"], row["entity"]): row for row in comparisons(tables, facts)}
    ledger = result["provider_spend", "All recorded charges"]
    # Three ledger rows meet one report row. The report is counted once and the ledger sums once.
    assert (ledger["extra_quantity"], ledger["core_quantity"], ledger["core_rows"]) == (Decimal(100), Decimal(90), 3)
    assert result["provider_spend", "Azure"]["core_quantity"] == Decimal(50)
    assert result["provider_spend", "Azure + AWS"]["difference"] == Decimal(10)
    assert "Closest tested scope" in result["provider_spend", "Azure + AWS"]["interpretation"]
    allocation = result["allocation_cost_per_fte", "IT"]
    assert allocation["core_to_extra_ratio"] == Decimal("22.5") and allocation["difference"] is None
    assert allocation["basis"] == "allocation_view"


def test_agent_tokens_are_compared_without_assuming_gateway_coverage():
    empty = dict.fromkeys(("ai_invoice_monthly", "aws_costs", "web_traffic", "hoster_invoice", "powerbi_usage",
                           "azure_costs", "project_hours_monthly", "provider_monthly_report", "headcount"), [])
    month = {"reporting_month": "2026-01"}
    tables = rows(**empty,
                  ai_usage=[{**month, "provider": "Anthropic", "model": "Sonnet", "model_class": "large",
                             "tokens_in": Decimal(1000), "tokens_out": Decimal(100)}],
                  ai_agent_runs=[{**month, "provider": "Anthropic", "model": "Sonnet",
                                  "tokens_in": Decimal(250), "tokens_out": None}],
                  ci_pipeline_runs=[{**month, "region": "Ireland (Dublin)", "duration_seconds": Decimal(120)},
                                    {**month, "region": "Ireland (Dublin)", "duration_seconds": None}])
    result = {(row["comparison"], row["unit"]): row for row in comparisons(tables, [])}
    share = result["ai_agent_tokens", "tokens_in"]
    assert (share["extra_quantity"], share["core_quantity"], share["difference"]) == (Decimal(250), Decimal(1000), None)
    assert share["basis"] == "overlapping_activity"
    assert share["core_to_extra_ratio"] == Decimal(4)
    # Unknown agent output tokens publish no ratio.
    assert ("ai_agent_tokens", "tokens_out") not in result
    ci = result["ci_runtime", "runner-minute"]
    assert (ci["extra_quantity"], ci["extra_rows"], ci["core_quantity"]) == (Decimal(2), 1, None)
    assert "1 accepted runs have no logged duration" in ci["interpretation"]


def test_job_window_classes():
    assert schedule_class("flexible: within the week") == "flexible"
    assert schedule_class("fixed: backup window 22:00 to 06:00") == "protection_window"
    assert schedule_class("fixed: done by 07:30") == "fixed_deadline"
    assert schedule_class("by arrangement with the project") == "by_arrangement"
    assert schedule_class("") is None
