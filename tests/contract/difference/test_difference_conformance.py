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
        "next_observation_request.schema.json": bundle["next_observation_requests"],
        "observation_method.schema.json": bundle["observation_methods"],
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
            "resolution_mode": "CHANGE_FREE",
            "after_observation_refs": [{"kind": "observation", "id": "OBS-AFTER"}],
            "change_free_verification_evidence_refs": [
                {"kind": "observation_evidence", "id": "EVID-AFTER"}
            ],
            "evidence_sufficiency_ref": {
                "kind": "evidence_sufficiency",
                "id": "EVID-SUFF-0001",
            },
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
    assert invalid_count == 24
    assert valid_errors == []
    assert invalid_escapes == []


def test_supersession_relation_uses_canonical_contract_shape() -> None:
    validator = _validators()["difference_supersession_relation.schema.json"]
    relation = {
        "schema_version": "0.1",
        "supersession_relation_id": "D-SUP-" + "A" * 64,
        "old_difference_ref": {"kind": "difference", "id": "D-OLD"},
        "new_difference_ref": {"kind": "difference", "id": "D-NEW"},
        "old_terminal_event_ref": {"kind": "difference_event", "id": "D-EVT-OLD"},
        "new_genesis_event_ref": {"kind": "difference_event", "id": "D-EVT-NEW"},
        "reason_codes": ["TARGET_PREDICATE_CHANGED"],
        "evidence_refs": [],
    }
    assert not list(validator.iter_errors(relation))
    invented = deepcopy(relation)
    invented["relation_id"] = invented.pop("supersession_relation_id")
    assert list(validator.iter_errors(invented))


def test_target_value_type_and_closure_evidence_fail_closed() -> None:
    validators = _validators()
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    difference = deepcopy(bundle["differences"][0])
    difference["normalized_target_state"]["expected_value_type"] = "INTEGER"
    assert list(validators["difference.schema.json"].iter_errors(difference))

    base = deepcopy(bundle["evaluations"][0])
    candidate = {
        "kind": "after_state_candidate",
        "candidate_id": "STATE-CANDIDATE-" + "A" * 64,
        "kernel_source_ref": base["kernel_source_ref_evaluated"],
        "base_state_ref": {"kind": "state", "id": "STATE-0002"},
        "semantic_state": {},
        "semantic_fingerprint": base["evaluated_state_fingerprint"],
        "source_snapshot_refs": {"collection_kind": "UNORDERED_SET", "members": []},
        "producing_change_refs": {"collection_kind": "UNORDERED_SET", "members": []},
    }
    base.update(
        {
            "evaluation_mode": "CANDIDATE_CLOSURE",
            "after_state_candidate": candidate,
            "proposed_terminal_status": "CLOSED",
            "result": "SATISFIED",
            "terminal_reason_evidence_refs": [],
            "gate_results": {f"G{index}": "PASS" for index in range(1, 23)},
        }
    )
    assert list(validators["closure_evaluation.schema.json"].iter_errors(base))


def test_candidate_terminal_gates_and_retained_handoff_are_enforced() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    candidate_terminal = deepcopy(bundle)
    evaluation = candidate_terminal["evaluations"][0]
    evaluation["evaluation_mode"] = "CANDIDATE_TERMINAL"
    evaluation["after_state_candidate"] = {
        "kind": "after_state_candidate",
        "candidate_id": "STATE-CANDIDATE-" + "A" * 64,
    }
    assert any("candidate terminal gate omitted" in error for error in validate_bundle(candidate_terminal))

    retained = deepcopy(bundle)
    retained["events"][2]["to_status"] = "RETAINED"
    retained["events"][2]["blocker_kind"] = None
    retained["events"][2]["blocker_scope"] = None
    retained["events"][2]["blocker_resolution_condition"] = None
    retained["events"][2]["next_observation_ref"] = None
    retained["evaluations"][0]["proposed_terminal_status"] = "RETAINED"
    retained["materialized_status"][retained["differences"][0]["difference_id"]] = "RETAINED"
    assert any("next observation missing" in error for error in validate_bundle(retained))
