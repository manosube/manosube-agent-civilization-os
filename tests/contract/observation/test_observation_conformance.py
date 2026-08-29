from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from scripts.observation_contract_validator import (
    apply_mutation,
    load_json,
    validate_bundle,
    validate_fixture_suite,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "observation"
SCHEMA_ROOT = ROOT / "01_SCHEMA" / "observation"


def _negative_validator() -> Draft202012Validator:
    schema = load_json(SCHEMA_ROOT / "negative_observation.schema.json")
    schemas = [load_json(path) for path in (ROOT / "01_SCHEMA").rglob("*.schema.json")]
    registry = Registry().with_resources(
        (candidate["$id"], Resource.from_contents(candidate)) for candidate in schemas
    )
    return Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )


def _valid_negative_observation() -> dict[str, object]:
    cases = load_json(
        ROOT / "tests" / "contract" / "fixtures" / "schema" / "valid" / "observation_cases.json"
    )
    return deepcopy(
        next(case["instance"] for case in cases if case["name"] == "bounded_proven_absence")
    )


def test_valid_observation_bundle_preserves_append_only_provenance() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    assert validate_bundle(bundle) == []
    assert len(bundle["bindings"]) == 4
    assert {binding["fact_id"] for binding in bundle["bindings"]} == {
        "FACT-0001",
        "FACT-0002",
    }
    assert {binding["observation_id"] for binding in bundle["bindings"]} == {
        "OBS-0001",
        "OBS-0002",
    }
    shared_occurrence = [
        binding
        for binding in bundle["bindings"]
        if binding["observation_id"] == "OBS-0001"
        and binding["source_occurrence_id"] == "SOURCE-OCC-0001"
    ]
    assert {binding["fact_id"] for binding in shared_occurrence} == {
        "FACT-0001",
        "FACT-0002",
    }


def test_every_invalid_cross_record_fixture_fails_closed() -> None:
    valid_bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    invalid_cases = load_json(FIXTURE_ROOT / "invalid" / "cases.json")
    for case in invalid_cases:
        mutated = apply_mutation(valid_bundle, case["path"], case["value"])
        assert validate_bundle(mutated), case["name"]


def test_every_negative_status_rejects_an_incorrect_state_candidate() -> None:
    validator = _negative_validator()
    mappings = {
        "NO_RESULT": "UNKNOWN",
        "UNKNOWN": "UNKNOWN",
        "UNOBSERVED": "UNOBSERVED",
        "BLOCKED": "BLOCKED",
        "INCOMPLETE": "INCOMPLETE",
        "FAILED": "UNKNOWN",
        "INVALID": "REJECT_OR_QUARANTINE",
    }
    for status, expected_candidate in mappings.items():
        instance = _valid_negative_observation()
        instance["negative_status"] = status
        instance["conclusion"]["state_candidate"] = "ABSENT"
        assert list(validator.iter_errors(instance)), status

        instance["conclusion"]["state_candidate"] = expected_candidate
        assert not list(validator.iter_errors(instance)), status


def test_empty_requires_complete_collection_enumeration() -> None:
    validator = _negative_validator()
    instance = _valid_negative_observation()
    instance["negative_status"] = "EMPTY"
    instance["conclusion"]["state_candidate"] = "EMPTY"

    assert list(validator.iter_errors(instance))

    instance["completion_evaluation"].update(
        {
            "collection_defined": True,
            "enumeration_complete": True,
            "zero_valid_members": True,
        }
    )
    assert not list(validator.iter_errors(instance))


def test_observation_fixture_suite_has_no_escape() -> None:
    valid_count, invalid_count, valid_errors, invalid_escapes = validate_fixture_suite(FIXTURE_ROOT)
    assert valid_count == 1
    assert invalid_count == 15
    assert valid_errors == []
    assert invalid_escapes == []
