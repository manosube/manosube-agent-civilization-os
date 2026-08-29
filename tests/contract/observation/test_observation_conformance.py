from __future__ import annotations

from pathlib import Path

from scripts.observation_contract_validator import (
    apply_mutation,
    load_json,
    validate_bundle,
    validate_fixture_suite,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "observation"


def test_valid_observation_bundle_preserves_append_only_provenance() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    assert validate_bundle(bundle) == []
    assert len(bundle["bindings"]) == 3
    assert {binding["fact_id"] for binding in bundle["bindings"]} == {"FACT-0001"}
    assert {binding["observation_id"] for binding in bundle["bindings"]} == {
        "OBS-0001",
        "OBS-0002",
    }


def test_every_invalid_cross_record_fixture_fails_closed() -> None:
    valid_bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    invalid_cases = load_json(FIXTURE_ROOT / "invalid" / "cases.json")
    for case in invalid_cases:
        mutated = apply_mutation(valid_bundle, case["path"], case["value"])
        assert validate_bundle(mutated), case["name"]


def test_observation_fixture_suite_has_no_escape() -> None:
    valid_count, invalid_count, valid_errors, invalid_escapes = validate_fixture_suite(FIXTURE_ROOT)
    assert valid_count == 1
    assert invalid_count == 10
    assert valid_errors == []
    assert invalid_escapes == []
