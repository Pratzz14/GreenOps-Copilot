"""Create a content-addressed source manifest without modifying raw inputs."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_FILES = (
    "azure_costs.csv", "aws_costs.csv", "hoster_invoice.csv",
    "data_platform_usage.csv", "server_inventory.csv", "server_metrics_weekly.csv",
    "ai_usage.csv", "ai_subscriptions.csv", "saas_contracts.csv",
    "mapping_departments_tools.csv", "exchange_rates.csv", "it_tickets.csv",
    "business_calendar.csv",
)
TEMPLATES = ("template_baseline_and_assumptions.csv", "template_measures_package.csv")


def snapshot(data: Path, out: Path) -> dict:
    """Hash only the allowlisted P0 files; this is not a calculated run."""
    files = []
    for name in (*CORE_FILES, *TEMPLATES):
        content = (data / name).read_bytes()
        files.append({"name": name, "sha256": hashlib.sha256(content).hexdigest()})
    version = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    manifest = {"schema_version": 1, "snapshot_id": version, "core_source_count": 13,
                "template_count": 2, "files": files, "stage": "sources_hashed"}
    destination = out / "snapshots" / version / "manifest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(manifest, indent=2) + "\n"
    if destination.exists():
        if destination.read_text(encoding="utf-8") != content:
            raise ValueError("Existing immutable snapshot does not match its content ID")
    else:
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    pointer = out / "current_snapshot.json"
    temporary = out / "current_snapshot.tmp"
    temporary.write_text(json.dumps({"snapshot_id": version}) + "\n", encoding="utf-8")
    temporary.replace(pointer)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs")
    args = parser.parse_args()
    try:
        result = snapshot(args.data, args.out)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Snapshot failed: {error}\n")
    print(json.dumps({"snapshot_id": result["snapshot_id"], "stage": result["stage"],
                      "data_ready": False}, indent=2))


if __name__ == "__main__":
    main()
