"""Validate the canonical schema registry and contract fixtures."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from difference_contract_validator import validate_fixture_suite as validate_difference_fixtures
from jsonschema import Draft202012Validator, FormatChecker
from observation_contract_validator import validate_fixture_suite
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "01_SCHEMA"
FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "schema"
OBSERVATION_FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "observation"
DIFFERENCE_FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "difference"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixture_cases(directory: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        document = load_json(path)
        if not isinstance(document, list):
            raise SystemExit(f"fixture case file must contain an array: {path}")
        cases.extend(document)
    names = [case.get("name") for case in cases]
    if None in names or len(names) != len(set(names)):
        raise SystemExit(f"fixture names must be present and unique: {directory}")
    return cases


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
    if len(paths) < 21 or len(set(ids)) != len(paths) or None in ids:
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

    valid_cases = load_fixture_cases(FIXTURE_ROOT / "valid")
    invalid_cases = load_fixture_cases(FIXTURE_ROOT / "invalid")
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
    print("OBSERVATION_SCHEMA_COUNT=7")
    (
        observation_valid_count,
        observation_invalid_count,
        observation_valid_errors,
        observation_invalid_escapes,
    ) = validate_fixture_suite(OBSERVATION_FIXTURE_ROOT)
    print(f"OBSERVATION_CONFORMANCE_VALID_FIXTURE_COUNT={observation_valid_count}")
    print(f"OBSERVATION_CONFORMANCE_INVALID_FIXTURE_COUNT={observation_invalid_count}")
    print(f"OBSERVATION_CONFORMANCE_VALID_FAILURE_COUNT={len(observation_valid_errors)}")
    print(f"OBSERVATION_CONFORMANCE_INVALID_ESCAPE_COUNT={len(observation_invalid_escapes)}")
    (
        difference_valid_count,
        difference_invalid_count,
        difference_valid_errors,
        difference_invalid_escapes,
    ) = validate_difference_fixtures(DIFFERENCE_FIXTURE_ROOT)
    difference_schema_count = len(list((SCHEMA_ROOT / "difference").glob("*.schema.json")))
    print(f"DIFFERENCE_SCHEMA_COUNT={difference_schema_count}")
    print(f"DIFFERENCE_CONFORMANCE_VALID_FIXTURE_COUNT={difference_valid_count}")
    print(f"DIFFERENCE_CONFORMANCE_INVALID_FIXTURE_COUNT={difference_invalid_count}")
    print(f"DIFFERENCE_CONFORMANCE_VALID_FAILURE_COUNT={len(difference_valid_errors)}")
    print(f"DIFFERENCE_CONFORMANCE_INVALID_ESCAPE_COUNT={len(difference_invalid_escapes)}")
    if (
        unresolved_refs
        or valid_failures
        or invalid_escapes
        or observation_valid_errors
        or observation_invalid_escapes
        or difference_valid_errors
        or difference_invalid_escapes
    ):
        print(f"UNRESOLVED_REFS={unresolved_refs}")
        print(f"VALID_FAILURES={valid_failures}")
        print(f"INVALID_ESCAPES={invalid_escapes}")
        print(f"OBSERVATION_VALID_ERRORS={observation_valid_errors}")
        print(f"OBSERVATION_INVALID_ESCAPES={observation_invalid_escapes}")
        print(f"DIFFERENCE_VALID_ERRORS={difference_valid_errors}")
        print(f"DIFFERENCE_INVALID_ESCAPES={difference_invalid_escapes}")
        return 1
    print("SCHEMA_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
