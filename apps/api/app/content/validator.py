"""Content validator (task 1.5). Validates rubric, task template and golden sample files.

Rules beyond JSON Schema (Architecture section 7):
- criterion weights sum to 100
- every bound check names a checker registered for the rubric's role profile
- every checker listed is registered for the role profile
- criterion ids are unique
- mandatory_min_level must have a level descriptor
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


def find_contracts_dir() -> Path:
    """CONTRACTS_DIR if set (containers), otherwise packages/contracts above this file."""
    import os

    configured = os.environ.get("CONTRACTS_DIR")
    if configured:
        return Path(configured)
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "packages" / "contracts"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("packages/contracts not found")


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_schema(name: str, contracts: Path) -> Draft202012Validator:
    schema = json.loads((contracts / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def load_document(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yml", ".yaml"}:
        return yaml.safe_load(text)
    return json.loads(text)


def _schema_errors(validator: Draft202012Validator, doc: Any) -> list[str]:
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    ]


def validate_rubric(doc: Any, contracts: Path | None = None) -> ValidationReport:
    contracts = contracts or find_contracts_dir()
    report = ValidationReport(_schema_errors(_load_schema("rubric", contracts), doc))
    if report.errors:  # structural problems make the semantic checks meaningless
        return report

    registry: dict[str, list[str]] = json.loads(
        (contracts / "checkers.json").read_text(encoding="utf-8")
    )
    allowed = set(registry.get(doc["role_profile"], []))
    criteria = doc["criteria"]

    ids = [c["id"] for c in criteria]
    if len(set(ids)) != len(ids):
        report.errors.append("criteria: duplicate criterion ids")

    total = sum(c["weight"] for c in criteria)
    if total != 100:
        report.errors.append(f"criteria: weights must sum to 100, got {total}")

    for checker in doc["checkers"]:
        if checker not in allowed:
            report.errors.append(
                f"checkers: '{checker}' is not registered for role '{doc['role_profile']}'"
            )

    for c in criteria:
        for bound in c.get("bound_checks", []):
            checker = bound.split(".", 1)[0]
            if checker not in allowed:
                report.errors.append(
                    f"criteria/{c['id']}: bound check '{bound}' uses unregistered checker"
                )
            elif checker not in doc["checkers"]:
                report.errors.append(
                    f"criteria/{c['id']}: bound check '{bound}' not listed in rubric checkers"
                )
        minimum = c.get("mandatory_min_level")
        if minimum is not None and str(minimum) not in c["levels"]:
            report.errors.append(
                f"criteria/{c['id']}: mandatory_min_level {minimum} has no level descriptor"
            )

    report.errors += deliverable_errors(doc.get("deliverables", []))
    return report


def deliverable_errors(deliverables: list[dict[str, Any]]) -> list[str]:
    """Rules for a deliverable manifest beyond its JSON Schema (shared by rubrics and tasks)."""
    errors: list[str] = []
    ids = [d["id"] for d in deliverables]
    if len(set(ids)) != len(ids):
        errors.append("deliverables: duplicate deliverable ids")
    for d in deliverables:
        for low, high in (("min_words", "max_words"), ("min_count", "max_count")):
            if low in d and high in d and d[low] > d[high]:
                errors.append(f"deliverables/{d['id']}: {low} is greater than {high}")
        kinds = d["kind"] if isinstance(d["kind"], list) else [d["kind"]]
        if "accept" in d and "file" not in kinds:
            errors.append(f"deliverables/{d['id']}: 'accept' only applies to file deliverables")
    return errors


def validate_task_template(doc: Any, contracts: Path | None = None) -> ValidationReport:
    contracts = contracts or find_contracts_dir()
    report = ValidationReport(_schema_errors(_load_schema("task-template", contracts), doc))
    if report.ok and "deliverables" in doc:
        report.errors += deliverable_errors(doc["deliverables"])
    return report


def validate_golden_sample(doc: Any, contracts: Path | None = None) -> ValidationReport:
    contracts = contracts or find_contracts_dir()
    return ValidationReport(_schema_errors(_load_schema("golden-sample", contracts), doc))


# Folder name under content/ decides which validator applies.
VALIDATORS = {
    "rubrics": validate_rubric,
    "tasks": validate_task_template,
    "golden": validate_golden_sample,
}


def validate_content_tree(
    root: Path, contracts: Path | None = None
) -> dict[Path, ValidationReport]:
    results: dict[Path, ValidationReport] = {}
    for folder, validate in VALIDATORS.items():
        for path in sorted((root / folder).rglob("*")) if (root / folder).is_dir() else []:
            if path.suffix not in {".json", ".yml", ".yaml"}:
                continue
            try:
                doc = load_document(path)
            except (ValueError, yaml.YAMLError) as exc:
                results[path] = ValidationReport([f"cannot parse: {exc}"])
                continue
            # Task files may hold a track's tasks as {"tasks": [...]}.
            if folder == "tasks" and isinstance(doc, dict) and "tasks" in doc:
                combined = ValidationReport()
                for index, item in enumerate(doc["tasks"]):
                    combined.errors += [
                        f"tasks[{index}]: {e}" for e in validate(item, contracts).errors
                    ]
                results[path] = combined
            else:
                results[path] = validate(doc, contracts)
    return results


def main(argv: list[str] | None = None) -> int:
    import sys

    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]) if args else Path("content")
    results = validate_content_tree(root)
    failed = 0
    for path, report in results.items():
        if report.ok:
            print(f"ok    {path}")
        else:
            failed += 1
            print(f"FAIL  {path}")
            for error in report.errors:
                print(f"      {error}")
    print(f"{len(results)} files checked, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
