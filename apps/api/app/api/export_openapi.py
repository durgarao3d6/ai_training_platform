"""Export OpenAPI specification to packages/contracts/openapi.json."""

import json
from pathlib import Path

from app.main import app


def export() -> Path:
    spec = app.openapi()
    repo_root = Path(__file__).resolve().parents[4]
    contracts_dir = repo_root / "packages" / "contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    out_file = contracts_dir / "openapi.json"
    out_file.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return out_file


if __name__ == "__main__":
    path = export()
    print(f"Exported OpenAPI specification to {path}")
