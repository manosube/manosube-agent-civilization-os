from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from scripts.difference_contract_validator import (
    apply_mutation,
    load_json,
    validate_bundle,
    validate_fixture_suite,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "difference"
SCHEMA_ROOT = ROOT / "01_SCHEMA"


def _validators() -> dict[str, Draft202012Validator]:
    schemas = [load_json(path) for path in SCHEMA_ROOT.rglob("*.schema.json")]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    return {
        schema["$id"].rsplit("/", 1)[-1]: Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
        for schema in schemas
    }


def test_valid_bundle_is_schema_valid_and_reconstructable() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    validators = _validators()
    record_groups = {
        "difference.schema.json": bundle["differences"],
        "difference_lifecycle_event.schema.json": bundle["events"],
        "closure_policy.schema.json": bundle["policies"],
        "closure_evaluation.schema.json": bundle["evaluations"],
        "difference_supersession_relation.schema.json": bundle["supersession_relations"],
    }
    for schema_name, records in record_groups.items():
        for record in records:
            assert not list(validators[schema_name].iter_errors(record)), schema_name
    assert validate_bundle(bundle) == []


def test_invalid_cross_record_fixtures_fail_closed() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    cases = load_json(FIXTURE_ROOT / "invalid" / "cases.json")
    for case in cases:
        assert validate_bundle(apply_mutation(bundle, case["path"], case["value"])), case["name"]


def test_three_evaluation_modes_are_distinct() -> None:
    base = load_json(FIXTURE_ROOT / "valid" / "bundle.json")["evaluations"][0]
    validator = _validators()["closure_evaluation.schema.json"]
    policy_only = deepcopy(base)
    assert not list(validator.iter_errors(policy_only))

    candidate = {
        "kind": "after_state_candidate",
        "candidate_id": "STATE-CANDIDATE-" + "A" * 64,
        "kernel_source_ref": {
            "kind": "git_tree",
            "repository": "manosube/manosube-agent-civilization-os",
            "commit_sha": "1" * 40,
            "tree_sha": "2" * 40,
        },
        "base_state_ref": {"kind": "state", "id": "STATE-0002"},
        "semantic_state": {},
        "semantic_fingerprint": {
            "profile": "MANOSUBE-STATE-SHA256-0.1",
            "digest": "a" * 64,
        },
        "source_snapshot_refs": {"collection_kind": "UNORDERED_SET", "members": []},
        "producing_change_refs": {"collection_kind": "UNORDERED_SET", "members": []},
    }
    candidate_terminal = deepcopy(base)
    candidate_terminal.update(
        {
            "evaluation_mode": "CANDIDATE_TERMINAL",
            "after_state_candidate": candidate,
            "result": "NOT_SATISFIED",
        }
    )
    assert not list(validator.iter_errors(candidate_terminal))

    closure = deepcopy(base)
    closure.update(
        {
            "evaluation_mode": "CANDIDATE_CLOSURE",
            "after_state_candidate": candidate,
            "terminal_reason_evidence_refs": [],
            "proposed_terminal_status": "CLOSED",
            "result": "SATISFIED",
            "gate_results": {f"G{index}": "PASS" for index in range(1, 23)},
        }
    )
    assert not list(validator.iter_errors(closure))

    policy_only["after_state_candidate"] = candidate
    assert list(validator.iter_errors(policy_only))
    candidate_terminal["evaluation_mode"] = "TERMINAL_POLICY_ONLY"
    assert list(validator.iter_errors(candidate_terminal))


def test_difference_fixture_suite_has_no_escape() -> None:
    valid_count, invalid_count, valid_errors, invalid_escapes = validate_fixture_suite(
        FIXTURE_ROOT
    )
    assert valid_count == 1
    assert invalid_count == 14
    assert valid_errors == []
    assert invalid_escapes == []
