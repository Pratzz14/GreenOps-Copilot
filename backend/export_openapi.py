"""Write the API schema locally for offline TypeScript generation."""

import json
from pathlib import Path

from backend.main import app

if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "outputs" / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(target)
