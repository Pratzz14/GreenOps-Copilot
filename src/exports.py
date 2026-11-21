"""Export the two challenge CSVs from the active, validated Gold run."""

import argparse
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

import duckdb

from src.gold import DATABASE, current_run, resolve_run
from src.ingest import ROOT
from src.pipeline import active_output

BASELINE = "template_baseline_and_assumptions.csv"
MEASURES = "template_measures_package.csv"


def submission_package(db, run_id):
    return db.execute("""
        SELECT p.package_id
        FROM gold.package_result p JOIN gold.analysis_run r USING (run_id)
        WHERE p.run_id = ? AND p.scenario = 'mid' AND p.horizon = 'steady_state'
          AND p.implementation_chf <= r.implementation_cap_chf
        ORDER BY least(
            p.net_savings_chf / nullif(p.baseline_cost_chf * r.cost_reduction_target, 0),
            p.savings_location_kg / nullif(p.baseline_location_kg * r.carbon_reduction_target, 0)
        ) DESC NULLS LAST,
        (p.package_kind = 'automatic') DESC, p.savings_location_kg DESC, p.net_savings_chf DESC
        LIMIT 1
    """, [run_id]).fetchone()[0]


def export_submission(out):
    active = active_output(out)
    run = current_run(active)
    source, _ = resolve_run(active, run)
    with duckdb.connect(str(source / DATABASE), read_only=True) as db:
        package = submission_package(db, run)
    measures = "conditional-measures.csv" if package.endswith("-conditional") else "measures.csv"
    target = out / "submission" / run
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if all((target / name).is_file() and (target / name).read_bytes() == (source / artifact).read_bytes()
               for name, artifact in ((BASELINE, "baseline.csv"), (MEASURES, measures))):
            return target
        raise ValueError(f"Existing submission differs from Gold: {target}")
    with TemporaryDirectory(dir=target.parent) as temporary:
        stage = Path(temporary) / "submission"
        stage.mkdir()
        copyfile(source / "baseline.csv", stage / BASELINE)
        copyfile(source / measures, stage / MEASURES)
        stage.rename(target)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs")
    print(export_submission(parser.parse_args().out))


if __name__ == "__main__":
    main()
