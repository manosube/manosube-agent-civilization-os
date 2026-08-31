from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from scripts.difference_contract_validator import (
    _candidate_id,
    _candidate_matches_evaluation,
    _candidate_type_matches_target,
    _derive_comparison_and_mismatch,
    _difference_id,
    _negative_knowledge_status,
    _normalize_objective_value,
    _project_collection_value,
    _target_satisfied,
    apply_mutation,
    load_json,
    validate_bundle,
    validate_fixture_suite,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = ROOT / "tests" / "contract" / "fixtures" / "difference"
SCHEMA_ROOT = ROOT / "01_SCHEMA"


def _semantic_state() -> dict:
    domain = {
        "status": "UNKNOWN", "claims": {}, "identity_refs": [],
        "evidence_refs": [], "blind_spots": ["not evaluated"],
    }
    return {
        "schema_version": "0.1",
        **{key: deepcopy(domain) for key in (
            "project", "objective", "repository", "requirements", "code", "tests",
            "runtime", "infrastructure", "deployment", "authority", "lineage",
        )},
        "open_differences": [], "active_changes": [], "evidence": [],
    }


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
        "objective_revision.schema.json": bundle["objective_revisions"],
        "observation_scope.schema.json": bundle["observation_scopes"],
        "observation.schema.json": bundle["observations"],
        "normalized_fact.schema.json": bundle["normalized_facts"],
        "fact_observation_binding.schema.json": bundle["fact_observation_bindings"],
        "fact_evaluation.schema.json": bundle["fact_evaluations"],
        "difference.schema.json": bundle["differences"],
        "difference_lifecycle_event.schema.json": bundle["events"],
        "closure_policy.schema.json": bundle["policies"],
        "closure_evaluation.schema.json": bundle["evaluations"],
        "difference_supersession_relation.schema.json": bundle["supersession_relations"],
        "next_observation_request.schema.json": bundle["next_observation_requests"],
        "observation_method.schema.json": bundle["observation_methods"],
        "candidate_completion_record.schema.json": bundle["candidate_completion_records"],
        "candidate_claim_evaluation_event.schema.json": bundle["candidate_claim_evaluation_events"],
        "invariant_evaluation.schema.json": bundle["invariant_evaluations"],
        "evidence_sufficiency_result.schema.json": bundle["evidence_sufficiency_results"],
        "reopen_condition_evaluation.schema.json": bundle.get(
            "reopen_condition_evaluations", []
        ),
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
        "base_state_ref": {
            "kind": "state", "revision": 2,
            "fingerprint": {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "a" * 64},
        },
        "semantic_state": _semantic_state(),
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
    assert invalid_count == 29
    assert valid_errors == []
    assert invalid_escapes == []


def test_difference_source_observation_must_resolve_exactly() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    missing = deepcopy(bundle)
    missing["observations"] = []
    assert validate_bundle(missing)

    wrong_state = deepcopy(bundle)
    wrong_state["observations"][0]["state_revision_observed"] = 3
    assert validate_bundle(wrong_state)


def test_difference_target_must_resolve_from_authorized_objective() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    bundle["objective_revisions"] = []
    assert any(
        "Difference projection mismatch" in error for error in validate_bundle(bundle)
    )

    missing_scope = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    missing_scope["observation_scopes"] = []
    assert any(
        "Difference projection mismatch" in error
        for error in validate_bundle(missing_scope)
    )


def test_reserved_typed_objective_value_is_unwrapped() -> None:
    assert _normalize_objective_value(
        {"value_type": "DECIMAL", "value": "1.5"}
    ) == ("1.5", "DECIMAL")
    assert _project_collection_value(["a", "b"], "ORDERED_COLLECTION") == {
        "collection_kind": "ORDERED_LIST", "members": ["a", "b"],
    }
    assert not _candidate_type_matches_target(
        True,
        {"operator": "equals", "expected_value_type": "INTEGER"},
    )


def test_same_semantic_editorial_objective_can_be_evaluated() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    original = bundle["objective_revisions"][0]
    editorial = deepcopy(original)
    editorial["objective_revision_id"] = "OBJ-REV-0002"
    editorial["revision"] = 1
    editorial["previous_objective_ref"] = {
        "kind": "objective_revision", "id": original["objective_revision_id"],
    }
    editorial["base_semantic_fingerprint"] = {
        "profile": "MANOSUBE-OBJECTIVE-SHA256-0.1",
        "digest": bundle["differences"][0]["objective_semantic_fingerprint"].split(":")[1],
    }
    bundle["objective_revisions"].append(editorial)
    bundle["evaluations"][0]["objective_revision_ref_evaluated"] = {
        "kind": "objective_revision", "id": editorial["objective_revision_id"],
    }
    assert validate_bundle(bundle) == []

    inactive_tail = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    proposal = deepcopy(inactive_tail["objective_revisions"][0])
    proposal["objective_revision_id"] = "OBJ-REV-DRAFT"
    proposal["revision"] = 1
    proposal["status"] = "DRAFT"
    proposal["previous_objective_ref"] = {
        "kind": "objective_revision", "id": "OBJ-REV-0001",
    }
    proposal["base_semantic_fingerprint"] = editorial["base_semantic_fingerprint"]
    inactive_tail["objective_revisions"].append(proposal)
    assert validate_bundle(inactive_tail) == []

    assert _negative_knowledge_status("INVALID") == "REJECT_OR_QUARANTINE"


def test_v01_cardinality_fields_must_remain_null() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    difference = bundle["differences"][0]
    difference["structural_difference"]["target_cardinality"] = 1
    difference["difference_id"] = _difference_id(difference)
    bundle["events"][0]["difference_id"] = difference["difference_id"]
    bundle["policies"][0]["subject_difference_ref"]["id"] = difference["difference_id"]
    assert validate_bundle(bundle)


def test_canonical_collection_wrapper_is_unwrapped_for_contains() -> None:
    target = {
        "operator": "contains", "expected_value": "READY",
        "expected_value_type": "STRING",
    }
    observed = {
        "knowledge_status": "KNOWN",
        "value_candidates": {
            "collection_kind": "UNORDERED_SET",
            "members": [{
                "value": {
                    "collection_kind": "UNORDERED_SET",
                    "members": ["READY", "STABLE"],
                },
                "value_type": "UNORDERED_COLLECTION",
            }],
        },
    }
    assert _derive_comparison_and_mismatch(observed, target) == ("SATISFIED", None)


def test_mismatch_precedence_is_closed_and_deterministic() -> None:
    target = {
        "operator": "equals", "expected_value": "READY",
        "expected_value_type": "STRING",
    }
    observed = {
        "knowledge_status": "KNOWN",
        "value_candidates": {"collection_kind": "UNORDERED_SET", "members": []},
    }
    assert _derive_comparison_and_mismatch(observed, target) == (
        "NOT_SATISFIED", "MISSING",
    )
    observed["knowledge_status"] = "UNKNOWN"
    assert _derive_comparison_and_mismatch(observed, target) == ("UNKNOWN", "UNKNOWN")
    observed["knowledge_status"] = "KNOWN"
    observed["value_candidates"]["members"] = [
        {"value": "READY", "value_type": "STRING"},
        {"value": "NOT-READY", "value_type": "STRING"},
    ]
    assert _derive_comparison_and_mismatch(observed, target) == ("UNKNOWN", "CONFLICT")

    observed["value_candidates"]["members"] = [
        {"value": True, "value_type": "BOOLEAN"}
    ]
    integer_target = {
        "operator": "equals", "expected_value": 1,
        "expected_value_type": "INTEGER",
    }
    assert _derive_comparison_and_mismatch(observed, integer_target) == (
        "NOT_SATISFIED", "TYPE_MISMATCH",
    )


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
        "base_state_ref": {
            "kind": "state", "revision": 2,
            "fingerprint": base["evaluated_state_fingerprint"],
        },
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
    candidate = {
        "kind": "after_state_candidate",
        "candidate_id": "STATE-CANDIDATE-" + "A" * 64,
        "kernel_source_ref": evaluation["kernel_source_ref_evaluated"],
        "base_state_ref": evaluation["before_state_ref"],
        "semantic_state": _semantic_state(),
        "semantic_fingerprint": {
            "profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "a" * 64,
        },
        "source_snapshot_refs": {"collection_kind": "UNORDERED_SET", "members": []},
        "producing_change_refs": {"collection_kind": "UNORDERED_SET", "members": []},
    }
    candidate["candidate_id"] = _candidate_id(candidate)
    evaluation["after_state_candidate"] = candidate
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


def test_supersession_cycle_is_rejected() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    second = deepcopy(bundle["differences"][0])
    second_id = "D-" + "B" * 64
    second["difference_id"] = second_id
    bundle["differences"].append(second)
    first_id = bundle["differences"][0]["difference_id"]
    bundle["supersession_relations"] = [
        {
            "supersession_relation_id": "D-SUP-" + "A" * 64,
            "old_difference_ref": {"kind": "difference", "id": first_id},
            "new_difference_ref": {"kind": "difference", "id": second_id},
            "old_terminal_event_ref": {"kind": "difference_event", "id": "D-EVT-X"},
            "new_genesis_event_ref": {"kind": "difference_event", "id": "D-EVT-Y"},
        },
        {
            "supersession_relation_id": "D-SUP-" + "B" * 64,
            "old_difference_ref": {"kind": "difference", "id": second_id},
            "new_difference_ref": {"kind": "difference", "id": first_id},
            "old_terminal_event_ref": {"kind": "difference_event", "id": "D-EVT-Y"},
            "new_genesis_event_ref": {"kind": "difference_event", "id": "D-EVT-X"},
        },
    ]
    assert any("supersession cycle" in error for error in validate_bundle(bundle))


def test_reopen_condition_and_blocked_evidence_are_closed() -> None:
    validators = _validators()
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    policy = deepcopy(bundle["policies"][0])
    policy["reopen_conditions"] = [{
        "kind": "target_predicate",
        "id": "TP-REOPEN-1",
        "objective_revision_ref": {"kind": "objective_revision", "id": "OBJ-REV-2"},
        "predicate_semantic_fingerprint": "sha256:" + "a" * 64,
    }]
    assert not list(validators["closure_policy.schema.json"].iter_errors(policy))
    del policy["reopen_conditions"][0]["objective_revision_ref"]
    assert list(validators["closure_policy.schema.json"].iter_errors(policy))

    blocked = deepcopy(bundle["events"][2])
    blocked["evidence_refs"] = []
    assert list(validators["difference_lifecycle_event.schema.json"].iter_errors(blocked))
    mutated = deepcopy(bundle)
    mutated["events"][2]["evidence_refs"] = []
    assert any("blocked lifecycle Evidence missing" in error for error in validate_bundle(mutated))
    wrong_subject = deepcopy(bundle)
    wrong_subject["events"][2]["blocker_resolution_condition"]["subject_ref"] = {
        "kind": "difference", "id": "D-WRONG",
    }
    assert any("blocker condition subject mismatch" in error for error in validate_bundle(wrong_subject))


def test_after_state_candidate_identity_binds_semantic_bytes() -> None:
    base = load_json(FIXTURE_ROOT / "valid" / "bundle.json")["evaluations"][0]
    candidate = {
        "kind": "after_state_candidate",
        "candidate_id": "",
        "kernel_source_ref": base["kernel_source_ref_evaluated"],
        "base_state_ref": base["before_state_ref"],
        "semantic_state": {"value": 1},
        "semantic_fingerprint": base["evaluated_state_fingerprint"],
        "source_snapshot_refs": {"collection_kind": "UNORDERED_SET", "members": []},
        "producing_change_refs": {"collection_kind": "UNORDERED_SET", "members": []},
    }
    candidate["candidate_id"] = _candidate_id(candidate)
    original = candidate["candidate_id"]
    candidate["semantic_state"]["value"] = 2
    assert _candidate_id(candidate) != original
    candidate["semantic_fingerprint"] = {
        "profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64,
    }
    candidate["candidate_id"] = _candidate_id(candidate)
    assert not _candidate_matches_evaluation(candidate, base)


def test_difference_identity_canonicalizes_nested_unordered_sets() -> None:
    difference = load_json(FIXTURE_ROOT / "valid" / "bundle.json")["differences"][0]
    left = deepcopy(difference)
    left["effective_boundary"]["source_snapshot_refs"]["members"] = [
        {"kind": "snapshot", "id": "SNAP-A"},
        {"kind": "snapshot", "id": "SNAP-B"},
    ]
    right = deepcopy(left)
    right["effective_boundary"]["source_snapshot_refs"]["members"].reverse()
    assert _difference_id(left) == _difference_id(right)


def test_difference_boundary_is_bound_to_resolved_scope() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    mutations = (
        ("scope_ref", {"kind": "observation_scope", "id": "OBS-SCOPE-FABRICATED"}),
        ("resolved_scope_record_sha256", "sha256:" + "0" * 64),
    )
    for field, value in mutations:
        mutated = deepcopy(bundle)
        mutated["differences"][0]["effective_boundary"][field] = value
        assert any("Difference projection mismatch" in error for error in validate_bundle(mutated))


def test_unordered_target_comparison_uses_canonical_semantics() -> None:
    target = {
        "operator": "equals",
        "expected_value_type": "UNORDERED_COLLECTION",
        "expected_value": {
            "collection_kind": "UNORDERED_SET", "members": ["a", "b"],
        },
    }
    observed = {"collection_kind": "UNORDERED_SET", "members": ["b", "a"]}
    assert _target_satisfied([observed], target)


def test_difference_rejects_nonprojectable_latest_fact_evaluation() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    mutated = deepcopy(bundle)
    mutated["fact_evaluations"][0]["evaluation_status"] = "INVALID"
    assert any("Difference projection mismatch" in error for error in validate_bundle(mutated))


def test_difference_rejects_missing_fact_without_raising() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    mutated = deepcopy(bundle)
    mutated["observations"][0]["normalized_fact_refs"][0]["id"] = "FACT-MISSING"
    assert any("Difference projection mismatch" in error for error in validate_bundle(mutated))


def test_nested_unordered_fact_projection_is_recursive() -> None:
    value = [
        {"collection_kind": "UNORDERED_SET", "members": ["b", "a"]},
        {"collection_kind": "UNORDERED_SET", "members": ["d", "c"]},
    ]
    projected = _project_collection_value(value, "UNORDERED_COLLECTION")
    assert projected == {
        "collection_kind": "UNORDERED_SET",
        "members": [
            {"collection_kind": "UNORDERED_SET", "members": ["a", "b"]},
            {"collection_kind": "UNORDERED_SET", "members": ["c", "d"]},
        ],
    }


def test_verifying_and_closed_transitions_enforce_minimum_gates() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    verifying = deepcopy(bundle)
    event = verifying["events"][2]
    event["from_status"] = "ACTIVE"
    event["to_status"] = "VERIFYING"
    event["blocker_kind"] = None
    event["blocker_scope"] = None
    event["blocker_resolution_condition"] = None
    event["next_observation_ref"] = None
    event["evidence_refs"] = []
    assert any("verifying minimum gate missing" in error for error in validate_bundle(verifying))

    event["change_refs"] = [{"kind": "change", "id": "CHANGE-NOT-RESOLVED"}]
    event["next_observation_ref"] = {
        "kind": "next_observation_request", "id": "OBS-REQ-NOT-RESOLVED",
    }
    assert any("verifying minimum gate missing" in error for error in validate_bundle(verifying))

    closed = deepcopy(event)
    closed["from_status"] = "VERIFYING"
    closed["to_status"] = "CLOSED"
    closed["reflow_transition_ref"] = None
    validator = _validators()["difference_lifecycle_event.schema.json"]
    assert list(validator.iter_errors(closed))


def test_reflow_claim_and_terminal_invariant_references_are_resolved() -> None:
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")

    closed = deepcopy(bundle)
    event = closed["events"][2]
    evaluation = closed["evaluations"][0]
    transition_ref = {"kind": "state_transition", "id": "TX-NOT-RESOLVED"}
    event["to_status"] = "CLOSED"
    event["reflow_transition_ref"] = transition_ref
    evaluation["proposed_terminal_status"] = "CLOSED"
    evaluation["reflow_transition_ref"] = transition_ref
    closed["materialized_status"][event["difference_id"]] = "CLOSED"
    assert any(
        "terminal evaluation binding mismatch" in error
        for error in validate_bundle(closed)
    )

    invalid_claim = deepcopy(bundle)
    invalid_claim["policies"][0]["required_claims"] = [{
        "kind": "completion_claim",
        "id": "CLAIM-" + "A" * 64,
        "subject_type": "DIFFERENCE",
        "subject_ref": {"kind": "difference", "id": event["difference_id"]},
        "claim": {"status": "CLOSED"},
        "target_state_ref": None,
        "claim_semantic_fingerprint": "sha256:" + "a" * 64,
    }]
    assert any(
        "Policy required Claim identity mismatch" in error
        for error in validate_bundle(invalid_claim)
    )

    terminal = deepcopy(bundle)
    evaluation = terminal["evaluations"][0]
    evaluation["candidate_invariant_evaluation_bindings"] = [{
        "kind": "candidate_invariant_evaluation_binding",
        "binding_id": "CAND-INV-EVAL-" + "A" * 64,
        "candidate_id": "STATE-CANDIDATE-" + "A" * 64,
        "candidate_semantic_fingerprint": {
            "profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "a" * 64,
        },
        "base_state_ref": evaluation["before_state_ref"],
        "invariant_ref": {"kind": "kernel_invariant", "id": "K-001"},
        "invariant_definition_ref": {
            "repository": "manosube/manosube-agent-civilization-os",
            "path": "00_KERNEL/KERNEL_INVARIANTS.md",
            "invariant_definition_sha256": "sha256:" + "a" * 64,
        },
        "invariant_evaluation_ref": {
            "kind": "invariant_evaluation", "id": "INV-EVAL-NOT-RESOLVED",
        },
        "evaluation_record_fingerprint": "sha256:" + "a" * 64,
        "evaluation_result": "FAIL",
        "evaluation_evidence_refs": {
            "collection_kind": "UNORDERED_SET", "members": [],
        },
        "evaluated_at": evaluation["evaluated_at"],
    }]
    evaluation["evaluation_mode"] = "CANDIDATE_TERMINAL"
    evaluation["after_state_candidate"] = {
        "kind": "after_state_candidate",
        "candidate_id": "STATE-CANDIDATE-" + "A" * 64,
    }
    assert any(
        "candidate invariant binding mismatch" in error
        for error in validate_bundle(terminal)
    )


def test_policy_claim_rejects_bare_nested_collections() -> None:
    policy = deepcopy(load_json(FIXTURE_ROOT / "valid" / "bundle.json")["policies"][0])
    descriptor = {
        "kind": "completion_claim",
        "id": "CLAIM-" + "A" * 64,
        "subject_type": "DIFFERENCE",
        "subject_ref": {"kind": "difference", "id": "D-EXAMPLE"},
        "claim": {"values": [1, 2]},
        "target_state_ref": None,
        "claim_semantic_fingerprint": "sha256:" + "a" * 64,
    }
    policy["required_claims"] = [descriptor]
    validator = _validators()["closure_policy.schema.json"]
    assert list(validator.iter_errors(policy))

    descriptor["claim"]["values"] = {
        "collection_kind": "UNORDERED_SET", "members": [1, 2],
    }
    assert not list(validator.iter_errors(policy))

    descriptor["claim"]["values"] = 1.5
    assert list(validator.iter_errors(policy))

    descriptor["claim"]["values"] = {
        "collection_kind": "UNORDERED_SET",
        "members": [
            {"collection_kind": "UNORDERED_SET", "members": [1, 2]},
            {"collection_kind": "UNORDERED_SET", "members": [2, 1]},
        ],
    }
    bundle = load_json(FIXTURE_ROOT / "valid" / "bundle.json")
    bundle["policies"][0] = policy
    assert any(
        "Policy required Claim identity mismatch" in error
        for error in validate_bundle(bundle)
    )
