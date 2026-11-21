"""Build and select a complete Bronze, Silver and Gold release."""
import argparse
import hashlib
import json
import os
import tempfile
from datetime import date
from pathlib import Path

from src import gold, ingest, normalize, profile, reconciliation
from src.silver_storage import VERSION_PATTERN, atomic_csv


def release_directory(out, release):
    # Keep room for nested artifact names under the Windows path-length limit.
    return out / "releases" / release[:24]


def active_output(out):
    pointer = out / "current_release.csv"
    if not pointer.exists():
        return out
    rows = profile.read_csv(pointer, ("release",))[1]
    if rows == [{"release": "legacy"}]:
        return out
    if len(rows) != 1 or not VERSION_PATTERN.fullmatch(rows[0]["release"]):
        raise ValueError("Invalid pipeline release pointer")
    return release_directory(out, rows[0]["release"])


def validate_release(out):
    from backend.quality import load_quality
    from backend.services import load_health

    run = gold.current_run(out)
    _, metadata = gold.resolve_run(out, run)
    version = gold.pointer(out, "current")
    silver = gold.silver_directory(out) / version
    snapshot, _ = gold.validate(silver, version,
                                (*gold.published_tables(silver), *gold.REPORTS, *gold.FINANCIAL))
    if metadata["silver_version"] != version or metadata["snapshot_id"] != snapshot:
        raise ValueError("Release version chain failed validation")
    report, error = load_quality(out, load_health(out).snapshot_id)
    if report is None or report.snapshot_id != snapshot:
        raise ValueError(error or "Release Bronze identity does not match Silver")
    raw = out / "snapshots" / snapshot / "raw"
    if "supplemental_comparisons" in gold.published_tables(silver) and not raw.is_dir():
        raise ValueError("Full pipeline release is missing its raw Bronze archive")
    if raw.is_dir():
        for entry in report.inputs:
            if gold.file_hash(raw / entry.name) != entry.sha256:
                raise ValueError(f"Bronze archive hash mismatch for {entry.name}")
    return hashlib.sha256(f"{run}:{report.report_id}".encode()).hexdigest()


def activate(out, release):
    if release == "legacy":
        validate_release(out)
        atomic_csv(out / "current_release.csv", [{"release": release}])
        return
    if not VERSION_PATTERN.fullmatch(release):
        raise ValueError("Invalid release identifier")
    if validate_release(release_directory(out, release)) != release:
        raise ValueError("Release directory does not match requested identity")
    atomic_csv(out / "current_release.csv", [{"release": release}])


def build(data, extra, out, decision):
    releases = out / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=releases) as temporary:
        stage = Path(temporary) / "release"
        manifest = ingest.snapshot(data, stage, extra)
        archive = stage / "snapshots" / manifest["snapshot_id"] / "raw"
        core_path = archive if extra is not None else data
        extra_path = archive if extra is not None else None
        report = profile.profile(core_path, extra_path)
        (stage / "data_quality.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
        del report
        normalize.build(core_path, stage, extra_path)
        reconciliation.publish(stage, consume_staging=True)
        gold.publish(stage, decision)
        release = validate_release(stage)
        destination = release_directory(out, release)
        if not destination.exists():
            try:
                os.rename(stage, destination)
            except OSError:
                if not destination.is_dir():
                    raise
    activate(out, release)
    return release


def main():
    root = ingest.ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=root / "data")
    parser.add_argument("--extra", type=Path, default=root / "sprintd-basel-green-ai-data" / "extra")
    parser.add_argument("--out", type=Path, default=root / "outputs")
    parser.add_argument("--core-only", action="store_true")
    parser.add_argument("--decision-as-of", type=date.fromisoformat)
    parser.add_argument("--activate", metavar="RELEASE")
    args = parser.parse_args()
    if args.activate:
        activate(args.out, args.activate)
        print(args.activate)
    elif args.decision_as_of:
        print(build(args.data, None if args.core_only else args.extra, args.out, args.decision_as_of))
    else:
        parser.error("--decision-as-of is required when building")


if __name__ == "__main__":
    main()
