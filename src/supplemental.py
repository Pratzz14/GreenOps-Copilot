"""Readers and standardization for the optional Bronze sources."""
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from src.source_specs import EXTRA_FILES

ZURICH = ZoneInfo("Europe/Zurich")
# The data dictionary dates the catalogue export. Backup chains carry no export date of their own.
INVENTORY_DATE = date(2026, 9, 6)
STALE_READ_DAYS = 365
LONG_RETENTION_DAYS = 3650
CLOCK = re.compile(r"\b([01]\d|2[0-3]):[0-5]\d\b")


def schedule_class(window):
    """Classify the documented job window. Unrecognised text stays unknown."""
    text = (window or "").casefold()
    if "protection window" in text or "backup window" in text:
        return "protection_window"
    if text.startswith("fixed"):
        return "fixed_deadline"
    if text.startswith("flexible"):
        return "flexible"
    if text.startswith("by arrangement"):
        return "by_arrangement"
    return None


def records(path, spec):
    if path.suffix == ".csv":
        from src.profile import read_csv

        yield from ((number, row, None) for number, row in
                    enumerate(read_csv(path, spec.types)[1], 2))
        return

    with path.open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            try:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError("Expected a JSON object")
                flat = dict(value)
                for section in ("model", "usage", "metrics"):
                    nested = value.get(section)
                    if isinstance(nested, dict):
                        flat.update(nested)
                        if section == "model":
                            flat["model"] = nested.get("name")
                flat["duration_seconds"] = next((flat[k] for k in
                    ("duration_seconds", "duration_s", "duration_sec") if flat.get(k) is not None), None)
                row = {field: "" if flat.get(field) is None else str(flat[field]) for field in spec.types}
                yield number, row, None
            except ValueError as error:
                yield number, dict.fromkeys(spec.types, ""), str(error)


def local_day(timestamp):
    value = datetime.fromisoformat(timestamp)
    return (value.astimezone(ZURICH) if value.tzinfo else value).date()


def standardize(record, start, end):
    row = record.row
    table = record.table
    if table == "web_traffic":
        if row.get("time_utc"):
            day = local_day(row["time_utc"])
            record.set("event_date", day.isoformat(), "zurich_date", "Convert UTC to Zurich reporting date.")
            record.set("reporting_month", day.isoformat()[:7], "zurich_date", "Zurich reporting month.")
            record.set("baseline_overlap", start <= day <= end, "zurich_date", "Zurich baseline window.")
        amount, sampling = row.get("gb_out"), row.get("sample_rate")
        if sampling is not None and sampling < 1:
            record.issue("invalid_sample_rate", "sample_rate", "Expected at least one.", "review")
        record.set("expanded_gb", amount * sampling if amount is not None and sampling and sampling >= 1 else None,
                   "traffic_sampling", "Recorded volume multiplied by the documented sampling rate.")
    if table in {"m365_usage", "log_volume"}:
        field, unit = ("storage", "storage_unit") if table == "m365_usage" else ("log_gb", "unit")
        amount, units = row.get(field), (row.get(unit) or "").upper()
        if amount is not None and units not in {"MB", "GB"}:
            record.issue("unsupported_unit", unit, "Expected decimal MB or GB.", "review")
        gb = amount / 1000 if amount is not None and units == "MB" else amount if units == "GB" else None
        record.set("storage_gb" if table == "m365_usage" else "ingested_gb", gb,
                   "decimal_gb", "Normalize using 1 GB = 1000 MB.")
        if table == "m365_usage" and row.get("week_start"):
            first = datetime.fromisoformat(row["week_start"]).date()
            days = max(0, (min(first + timedelta(days=6), end) - max(first, start)).days + 1)
            record.set("baseline_days", days, "week_overlap", "Days of the observation week inside the baseline.")
            record.set("baseline_storage_gb_days", gb * days if gb is not None else None,
                       "storage_stock_days", "Assume the observed storage stock over covered days of the week.")
            for metric in ("teams_video_minutes", "mails_sent"):
                value = row.get(metric)
                record.set(f"baseline_{metric}", value * Decimal(days) / 7 if value is not None else None,
                           "week_overlap", "Allocate weekly activity uniformly over its seven days.")
    if table == "ci_pipeline_runs":
        if row.get("cpu_h") is None or row.get("duration_seconds") is None:
            record.issue("missing_run_metrics", "cpu_h", "Runner duration or CPU-hours absent.")
        runner = row.get("runner") or ""
        record.set("region", "Ireland (Dublin)" if runner == "aws-eu-west-1 (Dublin)" else None,
                   "verified_runner_region", "Explicit Dublin AWS runner identifier.")
    if table == "ai_agent_runs":
        inbound, cached = row.get("tokens_in"), row.get("cache_read_tokens")
        if inbound is not None and cached is not None and cached > inbound:
            record.issue("invalid_cache_subset", "cache_read_tokens", "Cached input exceeds total input.", "review")
        record.set("uncached_input_tokens",
                   inbound - cached if inbound is not None and cached is not None and cached <= inbound else None,
                   "cache_subset", "Cached tokens are part of input and are counted once.")
    if table == "log_volume":
        ingested, retention = row.get("ingested_gb"), row.get("retention_days")
        record.set("retained_gb_days", ingested * retention if ingested is not None and retention is not None else None,
                   "modeled_retention", "Modeled stock: one day of ingestion held for the stated retention period.")
    if table == "data_platform_jobs":
        window = row.get("time_window") or ""
        kind = schedule_class(window)
        if kind is None:
            record.issue("unclassified_time_window", "time_window", "The job window matches no documented schedule class.")
        clocks = [match.group(0) for match in CLOCK.finditer(window)]
        record.set("schedule_class", kind, "job_window", "Class from the documented time window text.")
        record.set("deadline_local", clocks[-1] if kind in {"fixed_deadline", "protection_window"} and clocks else None,
                   "job_window", "Latest clock time named in a fixed window, Zurich local time.")
        record.set("window_start_local", clocks[0] if len(clocks) == 2 else None,
                   "job_window", "Start of a two-sided window, Zurich local time.")
    if table == "backup_chains":
        reasons = [label for label, applies in (
            ("ten_year_retention", (row.get("retention_days") or 0) >= LONG_RETENTION_DAYS),
            ("high_criticality", (row.get("criticality") or "").casefold() == "high"),
            ("personal_data", (row.get("data_class") or "").casefold() == "personal data"),
            ("criticality_unknown", not row.get("criticality")),
        ) if applies]
        tested = row.get("last_restore_test")
        record.set("protection_reasons", ";".join(reasons) or None, "backup_protection",
                   "Retention, criticality and data class that require owner review before any change.")
        record.set("restore_test_age_days",
                   (INVENTORY_DATE - date.fromisoformat(tested)).days if tested else None,
                   "backup_protection", "Days from the last restore test to the 2026-09-06 inventory date.")
        record.set("retention_review_candidate", not reasons, "backup_protection",
                   "No protection reason is recorded. A candidate still needs the restore requirement confirmed.")
    if table == "data_catalog_tables":
        required = (row.get("retention_required") or "").casefold()
        read = row.get("last_read")
        idle = (INVENTORY_DATE - date.fromisoformat(read)).days if read else None
        record.set("days_since_last_read", idle, "catalogue_snapshot",
                   "Days from the last read to the 2026-09-06 catalogue export.")
        record.set("retention_status", {"yes": "protected", "no": "not_required"}.get(required, "unknown"),
                   "catalogue_snapshot", "A blank retention requirement stays unknown.")
        # Unknown retention or an unknown read date never becomes a candidate.
        record.set("storage_review_candidate",
                   (idle > STALE_READ_DAYS if required == "no" and idle is not None
                    else False if required == "yes" else None),
                   "catalogue_snapshot", "Retention is not required and the table was last read over a year ago.")


def source_filename(table):
    return EXTRA_FILES.get(table, f"{table}.csv")
