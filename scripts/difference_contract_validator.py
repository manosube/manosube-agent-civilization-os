"""Validate cross-record Difference contract invariants for conformance fixtures."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

STATUSES = {
    "DETECTED", "OPEN", "ACTIVE", "VERIFYING", "BLOCKED", "RETAINED", "CLOSED",
    "REOPENED", "SUPERSEDED", "INVALIDATED",
}
LEGAL_TRANSITIONS = {
    (None, "DETECTED"), ("DETECTED", "OPEN"), ("DETECTED", "INVALIDATED"),
    ("OPEN", "ACTIVE"), ("OPEN", "BLOCKED"), ("OPEN", "RETAINED"),
    ("OPEN", "SUPERSEDED"), ("OPEN", "INVALIDATED"),
    ("ACTIVE", "VERIFYING"), ("ACTIVE", "BLOCKED"), ("ACTIVE", "RETAINED"),
    ("ACTIVE", "SUPERSEDED"), ("ACTIVE", "INVALIDATED"),
    ("VERIFYING", "CLOSED"), ("VERIFYING", "ACTIVE"), ("VERIFYING", "BLOCKED"),
    ("VERIFYING", "RETAINED"), ("VERIFYING", "SUPERSEDED"),
    ("VERIFYING", "INVALIDATED"), ("BLOCKED", "OPEN"), ("BLOCKED", "ACTIVE"),
    ("BLOCKED", "VERIFYING"), ("BLOCKED", "RETAINED"), ("BLOCKED", "SUPERSEDED"),
    ("BLOCKED", "INVALIDATED"), ("RETAINED", "OPEN"), ("RETAINED", "ACTIVE"),
    ("RETAINED", "VERIFYING"), ("RETAINED", "BLOCKED"),
    ("RETAINED", "SUPERSEDED"), ("RETAINED", "INVALIDATED"),
    ("CLOSED", "REOPENED"), ("CLOSED", "SUPERSEDED"), ("CLOSED", "INVALIDATED"),
    ("REOPENED", "ACTIVE"), ("REOPENED", "VERIFYING"), ("REOPENED", "BLOCKED"),
    ("REOPENED", "RETAINED"), ("REOPENED", "SUPERSEDED"),
    ("REOPENED", "INVALIDATED"),
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _index(records: list[dict[str, Any]], key: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        identity = record[key]
        if identity in indexed and indexed[identity] != record:
            errors.append(f"same-ID different-payload conflict: {identity}")
        elif identity in indexed:
            errors.append(f"duplicate canonical record: {identity}")
        indexed[identity] = record
    return indexed


def _ref_id(reference: dict[str, Any] | None) -> str | None:
    return None if reference is None else str(reference["id"])


def _policy_ref_matches(reference: dict[str, Any], policy: dict[str, Any]) -> bool:
    return (
        reference["id"] == policy["closure_policy_id"]
        and reference["version"] == policy["policy_version"]
        and reference["semantic_fingerprint"] == policy["policy_semantic_fingerprint"]
    )


def validate_bundle(bundle: dict[str, Any]) -> list[str]:
    """Return deterministic Difference cross-record violations."""
    errors: list[str] = []
    differences = _index(bundle["differences"], "difference_id", errors)
    events = _index(bundle["events"], "difference_event_id", errors)
    policies = _index(bundle["policies"], "closure_policy_id", errors)
    evaluations = _index(bundle["evaluations"], "closure_evaluation_id", errors)
    relations = _index(
        bundle["supersession_relations"], "supersession_relation_id", errors
    )

    events_by_difference: dict[str, list[dict[str, Any]]] = {}
    for event in events.values():
        difference_id = event["difference_id"]
        if difference_id not in differences:
            errors.append(f"event references missing Difference: {event['difference_event_id']}")
        events_by_difference.setdefault(difference_id, []).append(event)

    reconstructed: dict[str, str] = {}
    for difference_id, chain in events_by_difference.items():
        chain.sort(key=lambda item: item["event_revision"])
        for expected_revision, event in enumerate(chain):
            if event["event_revision"] != expected_revision:
                errors.append(f"event revision gap: {difference_id}")
            expected_previous = None if expected_revision == 0 else chain[expected_revision - 1]["difference_event_id"]
            if event["previous_event_id"] != expected_previous:
                errors.append(f"event predecessor mismatch: {event['difference_event_id']}")
            if expected_revision > 0 and event["from_status"] != chain[expected_revision - 1]["to_status"]:
                errors.append(f"event status continuity mismatch: {event['difference_event_id']}")
            if event["event_kind"] == "OBSERVATION_BOUND":
                if event["from_status"] != event["to_status"]:
                    errors.append(f"observation-bound status mutation: {event['difference_event_id']}")
                if event["to_status"] in {"CLOSED", "SUPERSEDED", "INVALIDATED"}:
                    errors.append(f"observation-bound terminal event: {event['difference_event_id']}")
            elif (event["from_status"], event["to_status"]) not in LEGAL_TRANSITIONS:
                errors.append(f"illegal lifecycle transition: {event['difference_event_id']}")
            is_reopen = event["from_status"] == "CLOSED" and event["to_status"] == "REOPENED"
            reopen_lists = (
                event["revoked_evidence_refs"],
                event["invalid_evidence_refs"],
                event["contradiction_evidence_refs"],
            )
            if not is_reopen:
                if (
                    event["reopen_trigger"] is not None
                    or event["reopen_condition_ref"] is not None
                    or event["reopen_condition_evaluation_ref"] is not None
                    or any(reopen_lists)
                ):
                    errors.append(f"non-reopen event carries reopen payload: {event['difference_event_id']}")
            else:
                trigger = event["reopen_trigger"]
                if (
                    trigger is None
                    or event["closure_evaluation_ref"] is None
                    or event["next_observation_ref"] is None
                ):
                    errors.append(f"incomplete reopen payload: {event['difference_event_id']}")
                trigger_valid = {
                    "OBSERVATION_CONTRADICTION": bool(event["observation_refs"] and event["evidence_refs"]),
                    "CLOSURE_EVIDENCE_REVOKED": bool(event["revoked_evidence_refs"]),
                    "CLOSURE_EVIDENCE_INVALID": bool(event["invalid_evidence_refs"]),
                    "MATERIAL_CONTRADICTION": bool(event["contradiction_evidence_refs"]),
                    "POLICY_REOPEN_CONDITION_SATISFIED": bool(
                        event["reopen_condition_ref"]
                        and event["reopen_condition_evaluation_ref"]
                        and event["evidence_refs"]
                    ),
                }.get(trigger, False)
                condition_refs_present = bool(
                    event["reopen_condition_ref"]
                    or event["reopen_condition_evaluation_ref"]
                )
                if not trigger_valid or (
                    trigger != "POLICY_REOPEN_CONDITION_SATISFIED"
                    and condition_refs_present
                ):
                    errors.append(f"reopen trigger payload mismatch: {event['difference_event_id']}")
            if event["to_status"] == "BLOCKED":
                scope = event["blocker_scope"]
                condition = event["blocker_resolution_condition"]
                if scope is None or condition is None or event["blocker_kind"] is None:
                    errors.append(f"incomplete blocker payload: {event['difference_event_id']}")
                else:
                    difference = differences.get(difference_id)
                    if difference and scope["effective_boundary"] != difference["effective_boundary"]:
                        errors.append(f"blocker boundary mismatch: {event['difference_event_id']}")
                    if _ref_id(condition["verification_request_ref"]) != _ref_id(event["next_observation_ref"]):
                        errors.append(f"blocker verification request mismatch: {event['difference_event_id']}")
                    expected_states = {
                        "AUTHORITY_PATH_AVAILABLE": "AVAILABLE",
                        "EXECUTION_PATH_AVAILABLE": "AVAILABLE",
                        "OBSERVATION_PATH_AVAILABLE": "AVAILABLE",
                        "REQUIRED_EVIDENCE_AVAILABLE": "AVAILABLE",
                        "BINDINGS_CURRENT": "CURRENT",
                        "MATERIAL_CONFLICT_RESOLVED": "RESOLVED",
                        "INVARIANTS_PASS": "PASS",
                        "CLAIMS_PASS": "PASS",
                        "STRUCTURAL_BLOCKER_REMOVED": "REMOVED",
                    }
                    if expected_states.get(condition["condition_code"]) != condition["expected_state"]:
                        errors.append(f"blocker condition state mismatch: {event['difference_event_id']}")
            if event["to_status"] in {"RETAINED", "REOPENED"} and event["next_observation_ref"] is None:
                errors.append(f"next observation missing: {event['difference_event_id']}")
            if event["to_status"] in {"CLOSED", "BLOCKED", "RETAINED"}:
                evaluation = evaluations.get(_ref_id(event["closure_evaluation_ref"]) or "")
                difference = differences.get(difference_id)
                policy = None if difference is None else policies.get(difference["closure_policy"]["id"])
                if (
                    evaluation is None
                    or evaluation["difference_id"] != difference_id
                    or evaluation["proposed_terminal_status"] != event["to_status"]
                    or evaluation["gate_results"]["G22"] != "PASS"
                    or policy is None
                    or not _policy_ref_matches(evaluation["policy_ref"], policy)
                    or _ref_id(evaluation["difference_event_head_ref"])
                    != event["previous_event_id"]
                ):
                    errors.append(f"terminal evaluation binding mismatch: {event['difference_event_id']}")
            reconstructed[difference_id] = event["to_status"]

    for difference_id, difference in differences.items():
        genesis_id = _ref_id(difference["genesis_event_ref"])
        genesis = events.get(genesis_id or "")
        if genesis is None or genesis["difference_id"] != difference_id or genesis["event_revision"] != 0:
            errors.append(f"Difference genesis binding mismatch: {difference_id}")
        policy_ref = difference["closure_policy"]
        policy = policies.get(policy_ref["id"])
        if (
            policy is None
            or _ref_id(policy["subject_difference_ref"]) != difference_id
            or not _policy_ref_matches(policy_ref, policy)
        ):
            errors.append(f"Difference closure Policy binding mismatch: {difference_id}")
        expected_status = bundle["materialized_status"].get(difference_id)
        if expected_status != reconstructed.get(difference_id):
            errors.append(f"materialized Difference reconstruction mismatch: {difference_id}")

    for evaluation in evaluations.values():
        difference = differences.get(evaluation["difference_id"])
        if difference is None:
            errors.append(f"evaluation references missing Difference: {evaluation['closure_evaluation_id']}")
            continue
        policy = policies.get(evaluation["policy_ref"]["id"])
        if (
            policy is None
            or _ref_id(policy["subject_difference_ref"]) != evaluation["difference_id"]
            or not _policy_ref_matches(evaluation["policy_ref"], policy)
            or evaluation["policy_version_evaluated"] != policy["policy_version"]
            or evaluation["policy_semantic_fingerprint_evaluated"]
            != policy["policy_semantic_fingerprint"]
        ):
            errors.append(f"evaluation Policy binding mismatch: {evaluation['closure_evaluation_id']}")
        head = events.get(_ref_id(evaluation["difference_event_head_ref"]) or "")
        if head is None or head["difference_id"] != evaluation["difference_id"]:
            errors.append(f"evaluation event-head mismatch: {evaluation['closure_evaluation_id']}")
        if (
            evaluation["target_predicate_ref"] != difference["target_predicate_ref"]
            or evaluation["objective_revision_ref_evaluated"]
            != difference["objective_revision_ref"]
            or evaluation["objective_semantic_fingerprint_evaluated"]
            != difference["objective_semantic_fingerprint"]
            or evaluation["evaluated_state_revision"]
            != difference["observed_state_revision"]
            or evaluation["evaluated_state_fingerprint"]
            != difference["observed_state_fingerprint"]
            or (
                head is not None
                and (
                    evaluation["evaluated_state_revision"]
                    != head["state_revision_evaluated"]
                    or evaluation["evaluated_state_fingerprint"]
                    != head["state_fingerprint_evaluated"]
                )
            )
        ):
            errors.append(f"evaluation Difference input mismatch: {evaluation['closure_evaluation_id']}")
        mode = evaluation["evaluation_mode"]
        candidate = evaluation["after_state_candidate"]
        proposed = evaluation["proposed_terminal_status"]
        if evaluation["gate_results"]["G22"] != "PASS":
            errors.append(f"terminal state not allowed: {evaluation['closure_evaluation_id']}")
        if policy and proposed not in policy["allowed_terminal_states"]:
            errors.append(f"Policy disallows terminal state: {evaluation['closure_evaluation_id']}")
        if mode == "CANDIDATE_CLOSURE":
            if candidate is None or proposed != "CLOSED" or evaluation["result"] != "SATISFIED":
                errors.append(f"invalid candidate closure mode: {evaluation['closure_evaluation_id']}")
            if any(value != "PASS" for value in evaluation["gate_results"].values()):
                errors.append(f"closure has non-PASS mandatory gate: {evaluation['closure_evaluation_id']}")
            resolution_mode = evaluation["resolution_mode"]
            common_evidence_present = bool(
                evaluation["after_observation_refs"]
                and evaluation["evidence_sufficiency_ref"]
            )
            mode_evidence_present = (
                resolution_mode == "CHANGE_BOUND"
                and bool(evaluation["change_refs"])
                and bool(evaluation["change_result_evidence_refs"])
                and not evaluation["change_free_verification_evidence_refs"]
            ) or (
                resolution_mode == "CHANGE_FREE"
                and not evaluation["change_refs"]
                and not evaluation["change_result_evidence_refs"]
                and bool(evaluation["change_free_verification_evidence_refs"])
            )
            if not common_evidence_present or not mode_evidence_present:
                errors.append(f"closure Evidence binding incomplete: {evaluation['closure_evaluation_id']}")
        elif mode == "CANDIDATE_TERMINAL":
            if candidate is None or proposed not in {"BLOCKED", "RETAINED"}:
                errors.append(f"invalid candidate terminal mode: {evaluation['closure_evaluation_id']}")
            if not evaluation["terminal_reason_evidence_refs"] or evaluation["result"] == "SATISFIED":
                errors.append(f"candidate terminal loses failure Evidence: {evaluation['closure_evaluation_id']}")
            evaluated_gates = {
                "G1", "G3", "G5", "G6", "G7", "G8", "G9", "G18", "G20", "G22",
            }
            if any(
                evaluation["gate_results"][gate] == "NOT_APPLICABLE"
                for gate in evaluated_gates
            ):
                errors.append(f"candidate terminal gate omitted: {evaluation['closure_evaluation_id']}")
        elif mode == "TERMINAL_POLICY_ONLY":
            if candidate is not None or proposed not in {"BLOCKED", "RETAINED"}:
                errors.append(f"Policy-only mode contains candidate truth: {evaluation['closure_evaluation_id']}")
            if evaluation["candidate_invariant_evaluation_bindings"] or evaluation["candidate_claim_evaluation_bindings"]:
                errors.append(f"Policy-only mode contains candidate bindings: {evaluation['closure_evaluation_id']}")
            if not evaluation["terminal_reason_evidence_refs"] or evaluation["result"] != "BLOCKED":
                errors.append(f"invalid Policy-only terminal Evidence: {evaluation['closure_evaluation_id']}")
            mandatory = {"G1", "G3", "G5", "G18", "G22"}
            candidate_dependent = {
                *(f"G{index}" for index in range(6, 18)),
                "G19", "G20", "G21",
            }
            if any(evaluation["gate_results"][gate] != "PASS" for gate in mandatory):
                errors.append(f"Policy-only mandatory gate mismatch: {evaluation['closure_evaluation_id']}")
            if any(
                evaluation["gate_results"][gate] != "NOT_APPLICABLE"
                for gate in candidate_dependent
            ):
                errors.append(f"Policy-only candidate gate leakage: {evaluation['closure_evaluation_id']}")

    for relation in relations.values():
        old_id = _ref_id(relation["old_difference_ref"])
        new_id = _ref_id(relation["new_difference_ref"])
        if old_id == new_id or old_id not in differences or new_id not in differences:
            errors.append(f"invalid supersession endpoints: {relation['supersession_relation_id']}")
        old_event = events.get(_ref_id(relation["old_terminal_event_ref"]) or "")
        new_event = events.get(_ref_id(relation["new_genesis_event_ref"]) or "")
        if old_event is None or old_event["to_status"] != "SUPERSEDED" or old_event["difference_id"] != old_id:
            errors.append(f"invalid old supersession event: {relation['supersession_relation_id']}")
        if new_event is None or new_event["event_revision"] != 0 or new_event["difference_id"] != new_id:
            errors.append(f"invalid new supersession genesis: {relation['supersession_relation_id']}")
    for event in events.values():
        if event["to_status"] != "SUPERSEDED":
            continue
        matching_relations = [
            relation
            for relation in relations.values()
            if _ref_id(relation["old_difference_ref"]) == event["difference_id"]
            and _ref_id(relation["old_terminal_event_ref"]) == event["difference_event_id"]
        ]
        if len(matching_relations) != 1:
            errors.append(f"superseded event relation mismatch: {event['difference_event_id']}")
    return sorted(set(errors))


def apply_mutation(bundle: dict[str, Any], path: list[str | int], value: Any) -> dict[str, Any]:
    mutated = deepcopy(bundle)
    target: Any = mutated
    for segment in path[:-1]:
        target = target[segment]
    if value == {"$delete": True}:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return mutated


def validate_fixture_suite(root: Path) -> tuple[int, int, list[str], list[str]]:
    valid_bundle = load_json(root / "valid" / "bundle.json")
    invalid_cases = load_json(root / "invalid" / "cases.json")
    valid_errors = validate_bundle(valid_bundle)
    invalid_escapes = [
        case["name"]
        for case in invalid_cases
        if not validate_bundle(apply_mutation(valid_bundle, case["path"], case["value"]))
    ]
    return 1, len(invalid_cases), valid_errors, invalid_escapes
