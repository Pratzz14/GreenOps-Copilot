"""Load lightweight snapshot metadata once on startup, never ETL on GET."""

import json
import re
from pathlib import Path

from backend.schemas import Health


def load_health(outputs: Path) -> Health:
    try:
        identity = json.loads((outputs / "current_snapshot.json").read_text(encoding="utf-8"))["snapshot_id"]
        if not isinstance(identity, str) or not re.fullmatch(r"[a-f0-9]{64}", identity):
            raise ValueError("Invalid snapshot ID")
        manifest = json.loads((outputs / "snapshots" / identity / "manifest.json").read_text(encoding="utf-8"))
        if manifest["snapshot_id"] != identity or manifest["core_source_count"] != 13:
            raise ValueError("Invalid snapshot manifest")
        return Health(snapshot_id=identity, core_source_count=13,
                      reason="Source snapshot loaded. Reconciliation and calculation phases are pending.")
    except (OSError, ValueError, KeyError, TypeError):
        return Health(reason="No valid source snapshot loaded. Run python -m src.ingest, then restart the API.")
