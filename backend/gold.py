"""Read Gold runs from their validated local publication."""

from contextlib import contextmanager
from datetime import timedelta
import re

import duckdb
from fastapi import HTTPException

from backend.gold_models import GoldRun
from src.gold import DATABASE, TABLES, current_run, gold_directory, query, records, resolve_run, statement_sql
from src.silver_storage import VERSION_PATTERN, pointer


def unavailable():
    return HTTPException(503, detail={
        "code": "not_ready",
        "message": "A validated Gold run for the current Silver data is unavailable.",
    })


def not_found():
    return HTTPException(404, detail={"code": "not_found", "message": "Unknown Gold result"})


class GoldRead:
    def __init__(self, db, queries, metadata, run, directory, output=None):
        self.db = db
        self.queries = queries
        self.run_id = metadata["run_id"]
        self.metadata = metadata
        self.run = run
        self.directory = directory
        self.output = output

    def select(self, statement, *values):
        return records(self.db.execute(statement, [self.run_id, *values]))

    def analysis(self, number, **variables):
        rows = query(self.db, self.queries, number, run_id=self.run_id, **variables)
        if number in (1, 2):
            for row in rows:
                if "reporting_kg_co2e" in row:
                    continue
                values = [row.get(key) for key in ("estimated_location_kg", "swiss_operating_kg_co2e")]
                known = [value for value in values if value is not None]
                row["reporting_kg_co2e"] = sum(known) if known else None
        return rows

    def breakdowns(self, scenario, group):
        rows = self.analysis(2, scenario=scenario, group_by=group)
        columns = {name for (name,) in self.db.execute(
            "SELECT name FROM pragma_table_info('gold.impact_monthly')"
        ).fetchall()}
        if not {"planning_kwh", "planning_kg_co2e"} <= columns:
            return rows
        dimension = {"subject": "subject_id", "provider": "provider", "department": "department",
                     "tool": "tool", "location": "location"}[group]
        estimates = self.select(f"""
            SELECT report_month, {dimension} AS driver,
                   sum(planning_kwh) AS planning_kwh,
                   sum(planning_kg_co2e) AS planning_kg_co2e,
                   list(DISTINCT boundary_id) FILTER (WHERE planning_kwh IS NOT NULL) AS planning_energy_boundaries,
                   bool_or(energy_gap_reason = 'missing_energy_factor') AS needs_energy_factor
            FROM gold.impact_monthly WHERE run_id=? AND scenario=?
            GROUP BY GROUPING SETS ((report_month, {dimension}), ({dimension}))
        """, scenario)
        by_period = {(row["report_month"], row["driver"]): row for row in estimates}
        for row in rows:
            row.update(by_period.get((row["report_month"], row["driver"]), {}))
            row["planning_energy_boundaries"] = row.get("planning_energy_boundaries") or []
        return rows

    def tables(self):
        counts = " UNION ALL ".join(
            f"SELECT '{table}' AS name, count(*) AS row_count "
            f"FROM gold.{table} WHERE run_id=(SELECT id FROM selected)"
            for table in TABLES
        )
        return self.select("WITH selected AS (SELECT ? AS id) " + counts)

    def table_page(self, table, offset, limit):
        if table not in TABLES:
            raise not_found()
        columns = records(self.db.execute("""
            SELECT name, type, pk AS primary_key FROM pragma_table_info(?) ORDER BY cid
        """, [f"gold.{table}"]))
        fields, keys = [], []
        for column in columns:
            identifier = '"' + column["name"].replace('"', '""') + '"'
            field = f"t.{identifier}"
            # Preserve exact DECIMALs and avoid driver-dependent timezone formatting.
            value = (f"strftime({field} AT TIME ZONE 'UTC', '%Y-%m-%dT%H:%M:%SZ')"
                     if column["type"] == "TIMESTAMP WITH TIME ZONE" else f"CAST({field} AS VARCHAR)")
            fields.append(f"{value} AS {identifier}")
            if column["primary_key"]:
                keys.append(field)
        count = self.select(f"SELECT count(*) AS total FROM gold.{table} WHERE run_id=?")[0]["total"]
        items = self.select(f"""
            SELECT {', '.join(fields)} FROM gold.{table} t WHERE t.run_id=?
            ORDER BY {', '.join(keys)} LIMIT ? OFFSET ?
        """, limit, offset)
        return {"run_id": self.run_id, "table": table, "row_count": count, "offset": offset,
                "limit": limit, "columns": columns, "items": items}

    def coverage(self, scenario):
        """Explain every workload boundary: its activity, its estimate, or the reason one is absent."""
        columns = {row["name"] for row in records(self.db.execute(
            "SELECT name FROM pragma_table_info(?)", ["gold.impact_monthly"]))}
        if not {"activity_quantity", "energy_gap_reason", "carbon_gap_reason"} <= columns:
            raise not_found()  # Runs published before gap reasons were recorded.
        reported = "reporting_kg_co2e" if "reporting_kg_co2e" in columns else "coalesce(location_kg, swiss_operating_kg_co2e)"
        planning_kwh = "planning_kwh" if "planning_kwh" in columns else "NULL"
        planning_carbon = "planning_kg_co2e" if "planning_kg_co2e" in columns else "NULL"
        rows = self.select(f"""
            SELECT boundary_id, provider, tool, location, any_value(activity_unit) AS activity_unit,
                   sum(activity_quantity) AS activity_quantity, sum(energy_kwh) AS energy_kwh,
                   sum(location_kg) AS location_kg, sum(swiss_operating_kg_co2e) AS swiss_operating_kg_co2e,
                   sum(reporting_kg_co2e) AS reporting_kg_co2e, sum(planning_kwh) AS planning_kwh,
                   sum(planning_kg_co2e) AS planning_kg_co2e, count(*) AS months,
                   count(*) FILTER (WHERE energy_gap_reason = 'missing_activity') AS months_missing_activity,
                   count(*) FILTER (WHERE energy_gap_reason = 'missing_energy_factor') AS months_missing_factor,
                   count(*) FILTER (WHERE energy_gap_reason = 'partial_activity') AS months_partial_activity,
                   min(evidence_set_id) AS evidence_set_id
            FROM (SELECT report_month, boundary_id, provider, tool, location, any_value(activity_unit) AS activity_unit,
                         sum(activity_quantity) AS activity_quantity, sum(energy_kwh) AS energy_kwh,
                         sum(location_kg) AS location_kg, sum(swiss_operating_kg_co2e) AS swiss_operating_kg_co2e,
                         sum({reported}) AS reporting_kg_co2e, sum({planning_kwh}) AS planning_kwh,
                         sum({planning_carbon}) AS planning_kg_co2e,
                         CASE WHEN bool_or(energy_gap_reason = 'missing_energy_factor') THEN 'missing_energy_factor'
                              WHEN count(*) FILTER (WHERE energy_gap_reason = 'missing_activity') = count(*) THEN 'missing_activity'
                              WHEN bool_or(energy_gap_reason IS NOT NULL) THEN 'partial_activity' END AS energy_gap_reason,
                         min(evidence_set_id) AS evidence_set_id
                  FROM gold.impact_monthly WHERE run_id=? AND scenario=?
                  GROUP BY report_month, boundary_id, provider, tool, location)
            GROUP BY boundary_id, provider, tool, location
            ORDER BY energy_kwh DESC NULLS LAST, boundary_id, provider, tool, location
        """, scenario)
        sources = {}
        for row in self.select("""
            SELECT DISTINCT e.evidence_set_id, f.factor_id, f.factor_name, f.source_reference
            FROM gold.evidence e JOIN gold.factor f USING (run_id, factor_id)
            WHERE e.run_id=? ORDER BY f.factor_id
        """):
            sources.setdefault(row.pop("evidence_set_id"), []).append(row)
        for row in rows:
            missing_factor = row.pop("months_missing_factor")
            if row["energy_kwh"] is None:
                state = "missing_energy_factor" if missing_factor else "missing_activity"
            elif row["reporting_kg_co2e"] is None and row["planning_kg_co2e"] is None:
                state = "missing_grid_factor"
            elif row["months_missing_activity"] or row["months_partial_activity"]:
                state = "partial_activity"
            else:
                state = "estimated"
            row["state"] = state
            row["emissions_basis"] = (self.run["emissions_basis"] if row["location_kg"] is not None else
                                      "CO2e" if row["swiss_operating_kg_co2e"] is not None else None)
            row["factor_sources"] = sources.get(row["evidence_set_id"], [])
        return rows

    def identity(self, scenario="mid"):
        conditional = f"{self.run_id}-conditional"
        result = self.select(
            "SELECT package_id FROM gold.package_result WHERE run_id=? AND package_id=? LIMIT 1", conditional,
        )
        return GoldRun(
            run_id=self.run_id, data_version=self.run["silver_version"], snapshot_id=self.run["snapshot_id"],
            factor_version=self.metadata["factor_version"], package_id=self.run_id,
            conditional_package_id=conditional if result else None, scenario=scenario, horizon="steady_state",
            period_start=self.run["baseline_start"].isoformat(),
            period_end=(self.run["baseline_end_exclusive"] - timedelta(days=1)).isoformat(),
            decision_as_of=self.run["decision_as_of"],
        )

    def measures(self, only_review=False):
        rows = self.select("""
            SELECT m.* EXCLUDE (run_id, subject_id, finding_id), s.subject_name
            FROM gold.measure m JOIN gold.subject s USING (run_id, subject_id)
            WHERE m.run_id=? ORDER BY m.safety_status, m.measure_id
        """)
        estimates = self.select("""
            SELECT measure_id, scenario, horizon, estimate_status,
                   gross_avoided_chf - new_recurring_chf AS net_chf,
                   before_energy_kwh - after_energy_kwh AS savings_kwh,
                   before_location_kg - after_location_kg AS savings_location_kg, evidence_set_id
            FROM gold.measure_scenario WHERE run_id=? ORDER BY measure_id, horizon, scenario
        """)
        by_measure = {}
        for row in estimates:
            by_measure.setdefault(row.pop("measure_id"), []).append(row)
        return [dict(row, estimates=by_measure.get(row["measure_id"], []))
                for row in rows if not only_review or row["safety_status"] != "eligible"]

    def protections(self):
        return self.select("""
            SELECT s.subject_name, p.* EXCLUDE (run_id, subject_id, protection_id, starts_at, ends_at),
                   strftime(p.starts_at AT TIME ZONE 'UTC', '%Y-%m-%dT%H:%M:%SZ') AS starts_at,
                   strftime(p.ends_at AT TIME ZONE 'UTC', '%Y-%m-%dT%H:%M:%SZ') AS ends_at
            FROM gold.protection_window p JOIN gold.subject s USING (run_id, subject_id)
            WHERE p.run_id=? ORDER BY s.subject_name, p.starts_at NULLS FIRST, p.rule_key
        """)

    def package(self, package_id):
        rows = self.analysis(10, package_id=package_id)
        if not rows:
            raise not_found()
        primary = rows[0]
        fields = (
            "scenario", "horizon", "evaluation_start", "evaluation_end_exclusive", "target_status",
            "meets_all_three_scenarios", "baseline_cost_chf", "baseline_energy_kwh", "baseline_location_kg",
            "after_cost_chf", "after_energy_kwh", "after_location_kg", "net_savings_chf", "savings_energy_kwh",
            "savings_location_kg", "implementation_chf", "cost_reduction", "carbon_reduction",
            "cost_margin_chf", "carbon_margin_kg", "budget_remaining_chf",
        )
        members = self.select("""
            SELECT pm.measure_id, m.description, pm.scenario, pm.horizon, pm.credited_cost_chf,
                   pm.credited_energy_kwh, pm.credited_location_kg, pm.credited_implementation_chf,
                   pm.evidence_set_id
            FROM gold.package_member pm JOIN gold.measure m USING (run_id, measure_id)
            WHERE pm.run_id=? AND pm.package_id=? ORDER BY pm.measure_id, pm.horizon, pm.scenario
        """, package_id)
        return {
            "run_id": self.run_id, "package_id": package_id, "package_kind": primary["package_kind"],
            "selection_status": primary["selection_status"], "candidate_set_note": primary["candidate_set_note"],
            "evidence_set_id": primary["evidence_set_id"], "emissions_basis": self.run["emissions_basis"],
            "cost_target": self.run["cost_reduction_target"], "carbon_target": self.run["carbon_reduction_target"],
            "implementation_cap_chf": self.run["implementation_cap_chf"],
            "scores": [{key: row[key] for key in fields} for row in rows], "members": members,
        }


@contextmanager
def read_gold(request, run_id=None):
    out = request.app.state.outputs
    is_current = run_id is None
    if is_current:
        try:
            run_id = current_run(out)
            silver_version = pointer(out, "current")
        except (ValueError, OSError) as exc:
            raise unavailable() from exc
    elif not VERSION_PATTERN.fullmatch(run_id):
        if not (out / "current_gold.csv").is_file():
            raise unavailable()
        raise not_found()
    elif not (gold_directory(out) / run_id).is_dir():
        root = request.app.state.output_root
        releases = root / "releases"
        candidates = [root, *(path for path in releases.iterdir()
                              if re.fullmatch(r"[0-9a-f]{24}", path.name))] if releases.is_dir() else [root]
        previous = next((path for path in candidates if (gold_directory(path) / run_id).is_dir()), None)
        if previous is None:
            if not (out / "current_gold.csv").is_file():
                raise unavailable()
            raise not_found()
        out = previous
    with open_published_gold(out, run_id) as gold:
        if is_current and (gold.metadata["silver_version"] != silver_version or (
                request.app.state.health.snapshot_id and gold.metadata["snapshot_id"] != request.app.state.health.snapshot_id)):
            raise unavailable()
        yield gold


@contextmanager
def open_published_gold(out, run_id):
    try:
        directory, metadata = resolve_run(out, run_id)
        with duckdb.connect(str(directory / DATABASE), read_only=True, config={"threads": 1}) as db:
            result = records(db.execute("SELECT * FROM gold.analysis_run WHERE run_id=?", [run_id]))
            if len(result) != 1 or any(result[0][field] != metadata[field] for field in
                                       ("silver_version", "snapshot_id", "calculation_version")):
                raise unavailable()
            sql = statement_sql(db, (directory / "queries.sql").read_text(encoding="utf-8"))
            yield GoldRead(db, sql, metadata, result[0], directory, out)
    except (OSError, ValueError, KeyError, duckdb.Error) as exc:
        raise unavailable() from exc
