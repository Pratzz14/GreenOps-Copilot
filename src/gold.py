"""Build and atomically publish the Gold database and official CSV layouts."""

import argparse
import json
import tempfile
from datetime import date
from hashlib import sha256
from pathlib import Path

import duckdb

from src.cost_estimation import EstimationError, estimate_missing_costs
from src.factors import FACTORS
from src.gold_baseline import START, STOP, GoldData, build_cost, build_impact, build_licences, imputed_costs, key_for
from src.gold_measures import CAP, CARBON_TARGET, COST_TARGET, DAY_RATE, build_measures
from src.ingest import ROOT
from src.optimizer import build_packages
from src.profile import read_csv
from src.silver_storage import REPORTS, FINANCIAL, VERSION_PATTERN, atomic_csv, file_hash, pointer, published_tables, silver_directory, validate, write_csv

SCHEMA = ROOT / "docs" / "gold_schema.sql"
QUERIES = ROOT / "docs" / "gold_queries.sql"
TEMPLATES = {
    "baseline.csv": ROOT / "data" / "bronze" / "template_baseline_and_assumptions.csv",
    "measures.csv": ROOT / "data" / "bronze" / "template_measures_package.csv",
}
TABLES = (
    "analysis_run", "subject", "cost_monthly", "impact_monthly", "factor", "licence_monthly",
    "finding", "protection_window", "measure", "measure_scenario", "measure_constraint",
    "package_result", "package_member", "evidence",
)
DATABASE = "results.duckdb"
ARTIFACTS = (DATABASE, "queries.sql", *TEMPLATES)
CONDITIONAL_EXPORT = "conditional-measures.csv"
SUPPLEMENTAL_KEYS = {"data_platform_jobs.csv": "resource_id", "backup_chains.csv": "source"}


def gold_directory(out):
    return ROOT / "data" / "gold" if out.resolve() == ROOT / "outputs" else out / "gold"


def current_run(out):
    _, records = read_csv(out / "current_gold.csv", ("run_id",))
    if len(records) != 1 or not VERSION_PATTERN.fullmatch(records[0]["run_id"]):
        raise ValueError("Invalid Gold run pointer")
    return records[0]["run_id"]


def resolve_run(out, run_id):
    if not VERSION_PATTERN.fullmatch(run_id):
        raise ValueError("Invalid Gold run ID")
    directory = gold_directory(out) / run_id
    document = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    identifiers = ("silver_version", "snapshot_id", "factor_version", "calculation_version")
    if (not isinstance(document, dict) or document.get("run_id") != run_id
            or any(not isinstance(document.get(field), str) or not VERSION_PATTERN.fullmatch(document[field])
                   for field in identifiers)
            or not isinstance(document.get("artifacts"), dict)
            or set(document["artifacts"]) not in (set(ARTIFACTS), {*ARTIFACTS, CONDITIONAL_EXPORT})):
        raise ValueError("Invalid Gold manifest")
    for name in document["artifacts"]:
        if file_hash(directory / name) != document["artifacts"][name]:
            raise ValueError(f"Gold artifact checksum mismatch: {name}")
    return directory, document


def query(db, queries, number, **values):
    for variable, value in values.items():
        if variable not in {
            "run_id", "scenario", "horizon", "group_by", "seat_month", "subject_id", "action",
            "window_start", "window_end", "package_id", "evidence_set_id",
        }:
            raise ValueError(f"Unknown Gold query variable: {variable}")
        db.execute(f"SET VARIABLE gold_{variable} = ?", [value])
    return records(db.execute(queries[number - 1]))


def records(result):
    columns = [column[0] for column in result.description]
    return [dict(zip(columns, values, strict=True)) for values in result.fetchall()]


def statement_sql(db, source):
    statements = db.extract_statements(source)
    if len(statements) != 15 or any(s.type != duckdb.StatementType.SELECT for s in statements):
        raise ValueError("Gold query file must contain its 15 read-only statements")
    return tuple(statement.query for statement in statements)


def load_tables(db, stage, data):
    for table in TABLES:
        rows = data.tables[table]
        if not rows:
            continue
        columns = [row[0] for row in db.execute(f"DESCRIBE gold.{table}").fetchall()]
        if any(set(row) - set(columns) for row in rows):
            raise ValueError(f"Unexpected published column in {table}")
        transfer = stage / f"{table}.csv"
        write_csv(transfer, rows, columns)
        inserted = db.execute(f"""COPY gold.{table} FROM ?
                              (FORMAT CSV, HEADER TRUE, DELIMITER ',', QUOTE '"', ESCAPE '"', NULL '')""",
                              [str(transfer)]).fetchone()[0]
        if inserted != len(rows):
            raise ValueError(f"Incomplete Gold write for {table}")
        transfer.unlink()
    for table in TABLES:
        if table == "evidence":
            continue
        missing = db.execute(f"""
            SELECT COUNT(*) FROM gold.{table} t
            WHERE NOT EXISTS (SELECT 1 FROM gold.evidence e
              WHERE e.run_id=t.run_id AND e.evidence_set_id=t.evidence_set_id)
            """ if table != "factor" else "SELECT 0").fetchone()[0]
        if missing:
            raise ValueError(f"Missing evidence for {table}")


def build_exports(db, path, run_id):
    queries = statement_sql(db, (path / "queries.sql").read_text(encoding="utf-8"))
    scope = dict(run_id=run_id, package_id=run_id, scenario="mid", horizon="steady_state")
    # Check every package and every scenario before publishing.
    package_ids = db.execute("SELECT DISTINCT package_id FROM gold.package_result").fetchall()
    for (package_id,) in package_ids:
        package_scope = {**scope, "package_id": package_id}
        for check in query(db, queries, 13, **package_scope):
            if (check["partial_members"] or check["automatic_safety_violation"]
                    or any(check[key] for key in ("cost_differs", "energy_differs", "carbon_differs", "budget_differs"))):
                raise ValueError("Gold package contribution ledger does not reconcile")
        for scenario in ("low", "mid", "high"):
            for horizon in ("first_year", "steady_state"):
                if query(db, queries, 11, **{**package_scope, "scenario": scenario, "horizon": horizon}):
                    raise ValueError("Gold package violates a measure constraint")
    for filename, number in (("baseline.csv", 14), ("measures.csv", 15)):
        columns, template_rows = read_csv(TEMPLATES[filename])
        rows = query(db, queries, number, **scope)
        actual_columns = [column[0] for column in db.description]
        if columns != actual_columns:
            raise ValueError(f"Gold output headers differ from the submission template for {filename}")
        if number == 14 and [row["parameter"] for row in rows] != [row["parameter"] for row in template_rows]:
            raise ValueError(f'Gold factor output does not preserve the submission template order: '
                             f'{[row["parameter"] for row in rows]}')
        write_csv(path / filename, rows, columns, encoding="utf-8-sig")
    conditional = query(db, queries, 15, **{**scope, "package_id": f"{run_id}-conditional"})
    write_csv(path / CONDITIONAL_EXPORT, conditional, read_csv(TEMPLATES["measures.csv"])[0], encoding="utf-8-sig")


def fingerprints(supplemental_hashes=()):
    sources = ("gold", "gold_baseline", "gold_measures", "optimizer", "factors", "cost_estimation")
    paths = [SCHEMA, QUERIES, *TEMPLATES.values(), *(ROOT / "src" / f"{name}.py" for name in sources)]
    return sha256(":".join([*(file_hash(path) for path in paths), *supplemental_hashes]).encode()).hexdigest()


def load_supplemental(directory):
    result, hashes = {}, []
    for filename, key in SUPPLEMENTAL_KEYS.items():
        path = directory / filename
        if not path.is_file():
            continue
        before = file_hash(path)
        _, rows = read_csv(path)
        if file_hash(path) != before:
            raise ValueError(f"Supplemental evidence changed while reading {filename}")
        hashes.append(f"{filename}:{before}")
        for number, row in enumerate(rows, 2):
            if row.get(key):
                result.setdefault((filename, row[key]), []).append(dict(
                    row, record_id=key_for(filename, before, number),
                    source_file=f"extra/{filename}", source_row=number))
    return result, hashes


def publish(out, decision, evidence_dir=None, *, estimate_missing=False):
    version = pointer(out, "current")
    silver = silver_directory(out) / version
    tables = published_tables(silver)
    snapshot, _ = validate(silver, version, (*tables, *REPORTS, *FINANCIAL))
    full = 'supplemental_comparisons' in tables
    if full and evidence_dir is not None:
        raise ValueError("Full builds use supplemental evidence from versioned Silver.")
    if evidence_dir is None and not full and out.resolve() == ROOT / "outputs":
        evidence_dir = ROOT / "sprintd-basel-green-ai-data" / "extra"
    supplemental, hashes = load_supplemental(evidence_dir) if evidence_dir is not None else ({}, [])
    if full:
        for filename, key in SUPPLEMENTAL_KEYS.items():
            for row in read_csv(silver / filename)[1]:
                if row['record_status'] == 'accepted' and row.get(key):
                    supplemental.setdefault((filename, row[key]), []).append(row)
    data = GoldData("", silver, decision, supplemental)
    estimates = None
    if estimate_missing:
        estimates = imputed_costs(data)
        fallback = estimate_missing_costs(data, estimates)
        if fallback:
            evidence = [
                (record_id, str(estimate.amount_chf), estimate.target["evidence_detail"],
                 [row["record_id"] for row in estimate.comparables])
                for record_id, estimate in sorted(fallback.items())
            ]
            hashes.append("openai-cost-estimates:" + sha256(json.dumps(evidence).encode()).hexdigest())
            estimates.update(fallback)
    calculation = fingerprints(hashes)
    factor_version = file_hash(ROOT / "src" / "factors.py")
    run_id = sha256(f"{version}:{calculation}:{decision.isoformat()}".encode()).hexdigest()
    root = gold_directory(out)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / run_id
    if not destination.exists():
        data.run_id = run_id
        cost_coverage, unresolved = build_cost(data, estimates)
        build_licences(data)
        energy_coverage, carbon_coverage = build_impact(data)
        build_measures(data)
        if full:
            from src.gold_measures import build_supplemental_measures

            build_supplemental_measures(data)
        build_packages(data, cost_coverage, carbon_coverage)
        run_evidence = data.evidence(
            "run", "Official annual baseline. Missing, unsupported and ambiguously attributed "
            "activity is kept in coverage gaps. Undated charge exceptions are attached here.",
            unresolved, ["allocation", "grid_ch_context"],
        )
        data.add("analysis_run", snapshot_id=snapshot, silver_version=version,
                 calculation_version=calculation, baseline_start=START, baseline_end_exclusive=STOP,
                 decision_as_of=decision, schedule_timezone="Europe/Zurich", emissions_basis="CO2e",
                 cost_coverage=cost_coverage, energy_coverage=energy_coverage, carbon_coverage=carbon_coverage,
                 cost_reduction_target=COST_TARGET, carbon_reduction_target=CARBON_TARGET,
                 implementation_cap_chf=CAP, day_rate_chf=DAY_RATE, evidence_set_id=run_evidence)
        data.tables["factor"] = [factor.row(key, run_id) for key, factor in FACTORS.items()]
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            path = Path(temporary)
            stage = path / run_id
            stage.mkdir()
            (stage / "queries.sql").write_bytes(QUERIES.read_bytes())
            with duckdb.connect(str(stage / DATABASE)) as db:
                db.execute("SET threads = 2")
                db.execute("BEGIN TRANSACTION")
                db.execute(SCHEMA.read_text(encoding="utf-8"))
                load_tables(db, stage, data)
                build_exports(db, stage, run_id)
                db.execute("COMMIT")
                db.execute("CHECKPOINT")
            metadata = dict(run_id=run_id, silver_version=version, snapshot_id=snapshot,
                            factor_version=factor_version, calculation_version=calculation,
                            artifacts={name: file_hash(stage / name) for name in (*ARTIFACTS, CONDITIONAL_EXPORT)})
            (stage / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
            try:
                stage.rename(destination)
            except OSError:
                if not destination.is_dir():
                    raise
    resolve_run(out, run_id)
    if pointer(out, "current") != version:
        raise ValueError("Silver changed during the Gold build. Run Gold again against the new Silver version.")
    atomic_csv(out / "current_gold.csv", [{"run_id": run_id}])
    return run_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs")
    parser.add_argument("--decision-as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--evidence-dir", type=Path, help="Optional scheduler and backup evidence directory")
    parser.add_argument("--estimate-missing-costs", action="store_true",
                        help="Use OpenAI to estimate remaining missing charges from comparable bills")
    parser.add_argument("--tag-recommendations", action="store_true",
                        help="Add OpenAI review tags after publishing Gold")
    args = parser.parse_args()
    try:
        run_id = publish(args.out, args.decision_as_of, args.evidence_dir, estimate_missing=args.estimate_missing_costs)
        if args.tag_recommendations:
            from backend.recommendations import tag_run

            print(f"Saved {tag_run(args.out, run_id)} recommendation tags.")
        print(run_id)
    except EstimationError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
