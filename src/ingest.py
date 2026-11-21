"""Create a content-addressed source manifest without modifying raw inputs."""

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from src.source_specs import EXTRA_FILES

ROOT = Path(__file__).resolve().parents[1]
EXTRA_DIRECTORY = ROOT / "data" / "extra"
CORE_FILES = (
    "azure_costs.csv", "aws_costs.csv", "hoster_invoice.csv",
    "data_platform_usage.csv", "server_inventory.csv", "server_metrics_weekly.csv",
    "ai_usage.csv", "ai_subscriptions.csv", "saas_contracts.csv",
    "mapping_departments_tools.csv", "exchange_rates.csv", "it_tickets.csv",
    "business_calendar.csv",
)
TEMPLATES = ("template_baseline_and_assumptions.csv", "template_measures_package.csv")


def bronze_directory(data: Path) -> Path:
    """Accept either a layered data directory or a flat external export."""
    bronze = data / "bronze"
    return bronze if bronze.is_dir() else data


def inputs(data, extra=None):
    paths = {name: bronze_directory(data) / name for name in (*CORE_FILES, *TEMPLATES)}
    if extra is not None:
        paths.update({name: extra / name for name in EXTRA_FILES.values()})
    return paths


def identities(paths):
    return [{"name": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in paths.items()]


def record_count(path):
    """Logical CSV records below the header, or non-blank JSONL lines."""
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            if path.suffix == ".jsonl":
                return sum(1 for line in handle if line.strip())
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    except (csv.Error, UnicodeDecodeError):
        return None  # Profiling reports the malformed file. The count stays unknown.


def details(paths):
    """Descriptive facts per input. The snapshot identity uses names and hashes only."""
    rows = []
    for name, path in paths.items():
        try:
            source = path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            source = path.as_posix()
        rows.append({"name": name, "kind": "submission_template" if name in TEMPLATES else
                     "core_source" if name in CORE_FILES else "extra_source",
                     "bytes": path.stat().st_size, "record_count": record_count(path), "source_path": source})
    return rows


def snapshot(data: Path, out: Path, extra=None) -> dict:
    """Hash allowlisted inputs, and archive the complete input set for full builds."""
    paths = inputs(data, extra)
    files = identities(paths)
    version = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    manifest = {"schema_version": 1, "snapshot_id": version, "core_source_count": 13,
                "template_count": 2, "extra_source_count": len(files) - len(CORE_FILES) - len(TEMPLATES),
                "files": files, "file_details": details(paths), "stage": "sources_hashed"}
    destination = out / "snapshots" / version / "manifest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(manifest, indent=2) + "\n"
    if destination.exists():
        # Identity is the name and hash list. Descriptive detail may differ by location or age.
        existing = json.loads(destination.read_text(encoding="utf-8"))
        if existing.get("snapshot_id") != version or existing.get("files") != files:
            raise ValueError("Existing immutable snapshot does not match its content ID")
        manifest = existing
    else:
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    if extra is not None:
        raw = destination.parent / "raw"
        if not raw.exists():
            with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
                stage = Path(temporary) / "raw"
                stage.mkdir()
                for name, path in paths.items():
                    shutil.copyfile(path, stage / name)
                if identities({name: stage / name for name in paths}) != files:
                    raise ValueError("Inputs changed during Bronze snapshot")
                stage.rename(raw)
        if identities({name: raw / name for name in paths}) != files:
            raise ValueError("Archived Bronze inputs failed checksum validation")
    pointer = out / "current_snapshot.json"
    temporary = out / "current_snapshot.tmp"
    temporary.write_text(json.dumps({"snapshot_id": version}) + "\n", encoding="utf-8")
    temporary.replace(pointer)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs")
    parser.add_argument("--extra", type=Path)
    args = parser.parse_args()
    try:
        result = snapshot(args.data, args.out, args.extra)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Snapshot failed: {error}\n")
    print(json.dumps({"snapshot_id": result["snapshot_id"], "stage": result["stage"],
                      "data_ready": False}, indent=2))


if __name__ == "__main__":
    main()
