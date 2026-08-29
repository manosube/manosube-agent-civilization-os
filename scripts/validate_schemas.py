"""Validate the canonical schema registry and contract fixtures."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "01_SCHEMA"
FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "schema"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        if isinstance(value.get("$ref"), str):
            refs.append(value["$ref"])
        for child in value.values():
            refs.extend(iter_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(iter_refs(child))
    return refs


def main() -> int:
    paths = sorted(SCHEMA_ROOT.rglob("*.schema.json"))
    schemas = [load_json(path) for path in paths]
    ids = [schema.get("$id") for schema in schemas]
    if len(paths) != 14 or len(set(ids)) != 14 or None in ids:
        raise SystemExit("schema inventory or unique $id gate failed")

    for schema in schemas:
        Draft202012Validator.check_schema(schema)

    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    schema_by_id = {schema["$id"]: schema for schema in schemas}
    unresolved_refs: list[str] = []
    for schema in schemas:
        resolver = registry.resolver(schema["$id"])
        for reference in iter_refs(schema):
            try:
                resolver.lookup(reference)
            except Exception:
                unresolved_refs.append(f"{schema['$id']} -> {reference}")

    valid_cases = load_json(FIXTURE_ROOT / "valid" / "cases.json")
    invalid_cases = load_json(FIXTURE_ROOT / "invalid" / "cases.json")
    valid_failures: list[str] = []
    invalid_escapes: list[str] = []

    for case in valid_cases:
        validator = Draft202012Validator(
            schema_by_id[case["schema_id"]], registry=registry, format_checker=FormatChecker()
        )
        errors = list(validator.iter_errors(case["instance"]))
        if errors:
            valid_failures.append(case["name"])

    for case in invalid_cases:
        validator = Draft202012Validator(
            schema_by_id[case["schema_id"]], registry=registry, format_checker=FormatChecker()
        )
        if not list(validator.iter_errors(case["instance"])):
            invalid_escapes.append(case["name"])

    print(f"SCHEMA_COUNT={len(paths)}")
    print(f"UNIQUE_SCHEMA_ID_COUNT={len(set(ids))}")
    print(f"UNRESOLVED_REF_COUNT={len(unresolved_refs)}")
    print(f"VALID_FIXTURE_COUNT={len(valid_cases)}")
    print(f"INVALID_FIXTURE_COUNT={len(invalid_cases)}")
    print(f"VALID_FIXTURE_FAILURE_COUNT={len(valid_failures)}")
    print(f"INVALID_FIXTURE_ESCAPE_COUNT={len(invalid_escapes)}")
    if unresolved_refs or valid_failures or invalid_escapes:
        print(f"UNRESOLVED_REFS={unresolved_refs}")
        print(f"VALID_FAILURES={valid_failures}")
        print(f"INVALID_ESCAPES={invalid_escapes}")
        return 1
    print("SCHEMA_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
