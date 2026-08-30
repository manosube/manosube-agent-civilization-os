"""Validate cross-record Difference contract invariants for conformance fixtures."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

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
        and policy["policy_semantic_fingerprint"] == _policy_fingerprint(policy)
    )


def _mandatory_invariant_ids() -> set[str]:
    source = (Path(__file__).resolve().parents[1] / "00_KERNEL" / "KERNEL_INVARIANTS.md").read_text(encoding="utf-8")
    ids = set(re.findall(r"^([KASODCERBXP]-[0-9]{3}) PASS$", source, re.MULTILINE))
    ids.discard("P-003")
    return ids


def _content_address(prefix: str, record: dict[str, Any], identity_field: str) -> str:
    payload = {key: value for key, value in record.items() if key != identity_field}
    return prefix + hashlib.sha256(canonical_json_bytes(payload)).hexdigest().upper()


def _policy_fingerprint(policy: dict[str, Any]) -> str:
    projection = {key: policy[key] for key in (
        "target_predicate_ref", "required_observation_scope", "minimum_evidence_level",
        "required_claims", "required_invariants", "allowed_terminal_states",
        "independent_verification_required", "maximum_evidence_age",
        "contradiction_policy", "reopen_conditions",
    )}
    for key in ("required_claims", "allowed_terminal_states"):
        projection[key] = sorted(projection[key], key=canonical_json_bytes)
    projection["reopen_conditions"] = sorted(
        ({key: item[key] for key in ("kind", "id", "predicate_semantic_fingerprint")}
         for item in projection["reopen_conditions"]), key=canonical_json_bytes,
    )
    projection["required_invariants"] = sorted(({
        "kind": item["kind"], "id": item["id"],
        "contract_source_blob": {
            "kind": item["contract_source_ref"]["kind"],
            "repository": item["contract_source_ref"]["repository"],
            "path": item["contract_source_ref"]["path"],
            "invariant_definition_sha256": item["contract_source_ref"]["invariant_definition_sha256"],
        },
    } for item in projection["required_invariants"]), key=canonical_json_bytes)
    return "sha256:" + hashlib.sha256(canonical_json_bytes(projection)).hexdigest()


def _difference_id(difference: dict[str, Any]) -> str:
    identity = {
        "project_id": difference["project_id"],
        "objective_semantic_fingerprint": difference["objective_semantic_fingerprint"],
        "target_predicate_ref": difference["target_predicate_ref"],
        "subject": difference["subject"],
        "observation_scope": difference["observation_scope"],
        "effective_boundary": difference["effective_boundary"],
        "normalized_target_state": difference["normalized_target_state"],
        "normalized_structural_difference": difference["structural_difference"],
        "closure_policy_semantic_fingerprint": difference["closure_policy"]["semantic_fingerprint"],
        "identity_profile": "MANOSUBE-DIFFERENCE-SHA256-0.1",
    }
    return "D-" + hashlib.sha256(canonical_json_bytes(identity)).hexdigest().upper()


def _candidate_id(candidate: dict[str, Any]) -> str:
    payload = {key: candidate[key] for key in (
        "base_state_ref", "kernel_source_ref", "producing_change_refs",
        "semantic_fingerprint", "semantic_state", "source_snapshot_refs",
    )}
    for key in ("producing_change_refs", "source_snapshot_refs"):
        payload[key] = {
            "collection_kind": "UNORDERED_SET",
            "members": sorted(payload[key]["members"], key=canonical_json_bytes),
        }
    preimage = b"MANOSUBE:AFTER_STATE_CANDIDATE:0.1:" + canonical_json_bytes(payload)
    return "STATE-CANDIDATE-" + hashlib.sha256(preimage).hexdigest().upper()


def _supersession_reason_codes(old: dict[str, Any], new: dict[str, Any]) -> set[str]:
    comparisons = {
        "PROJECT_CHANGED": ("project_id",),
        "OBJECTIVE_SEMANTICS_CHANGED": ("objective_semantic_fingerprint",),
        "TARGET_PREDICATE_CHANGED": ("target_predicate_ref",),
        "SUBJECT_OR_PREDICATE_CHANGED": ("subject",),
        "BOUNDARY_CHANGED": ("observation_scope", "effective_boundary"),
        "TARGET_STATE_SEMANTICS_CHANGED": ("normalized_target_state",),
        "MISMATCH_SEMANTICS_CHANGED": ("structural_difference",),
    }
    reasons = {
        reason for reason, fields in comparisons.items()
        if any(old[field] != new[field] for field in fields)
    }
    if old["closure_policy"]["semantic_fingerprint"] != new["closure_policy"]["semantic_fingerprint"]:
        reasons.add("CLOSURE_POLICY_SEMANTICS_CHANGED")
    return reasons


def _kernel_invariant_definitions(kernel_source: dict[str, Any]) -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    commit = kernel_source["commit_sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        return {}
    git = shutil.which("git")
    if git is None:
        return {}
    try:
        tree = subprocess.run(  # noqa: S603 -- fixed Git executable; SHA is closed above
            [git, "rev-parse", f"{commit}^{{tree}}"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        source = subprocess.run(  # noqa: S603 -- fixed Git executable; SHA is closed above
            [git, "show", f"{commit}:00_KERNEL/KERNEL_INVARIANTS.md"], cwd=root,
            check=True, capture_output=True, text=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError):
        return {}
    if tree != kernel_source["tree_sha"]:
        return {}
    headings = list(re.finditer(r"^## ([KASODCERBXP]-[0-9]{3}) — .+$", source, re.MULTILINE))
    definitions: dict[str, str] = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        section = source[heading.start():end].rstrip() + "\n"
        definitions[heading.group(1)] = "sha256:" + hashlib.sha256(section.encode()).hexdigest()
    return definitions


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
    requests = _index(
        bundle.get("next_observation_requests", []), "observation_request_id", errors
    )
    methods = _index(
        bundle.get("observation_methods", []), "observation_method_id", errors
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
                if not event["evidence_refs"]:
                    errors.append(f"blocked lifecycle Evidence missing: {event['difference_event_id']}")
                scope = event["blocker_scope"]
                condition = event["blocker_resolution_condition"]
                if scope is None or condition is None or event["blocker_kind"] is None:
                    errors.append(f"incomplete blocker payload: {event['difference_event_id']}")
                else:
                    difference = differences.get(difference_id)
                    if not scope["affected_subject_refs"]["members"]:
                        errors.append(f"empty blocker subject set: {event['difference_event_id']}")
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
            if event["next_observation_ref"] is not None:
                request_ref = event["next_observation_ref"]
                request = requests.get(_ref_id(request_ref) or "")
                difference = differences.get(difference_id)
                method = None if request is None else methods.get(_ref_id(request["method_ref"]) or "")
                if (
                    request_ref.get("kind") != "next_observation_request"
                    or request is None
                    or difference is None
                    or _ref_id(request["difference_ref"]) != difference_id
                    or _ref_id(request["derived_from_event_ref"]) != event["difference_event_id"]
                    or request["state_revision_requested"] != event["state_revision_evaluated"]
                    or request["state_fingerprint_requested"] != event["state_fingerprint_evaluated"]
                    or request["target_ref"] != difference["target_predicate_ref"]
                    or request["scope_ref"] != difference["objective_scope_binding"]["scope_ref"]
                    or request["method_ref"].get("kind") != "observation_method"
                    or method is None
                    or request["observation_request_id"]
                    != _content_address("OBS-REQ-", request, "observation_request_id")
                    or (
                        method is not None
                        and method["observation_method_id"]
                        != _content_address("OBS-METHOD-", method, "observation_method_id")
                    )
                ):
                    errors.append(f"next observation binding mismatch: {event['difference_event_id']}")
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
        target = difference["normalized_target_state"]
        observed = difference["normalized_observed_state"]
        structural = difference["structural_difference"]
        observed_values = [item["value"] for item in observed["value_candidates"]["members"]]
        observed_types = [item["value_type"] for item in observed["value_candidates"]["members"]]
        if (
            difference_id != _difference_id(difference)
            or difference["subject"] != target["subject"]
            or difference["subject"] != observed["subject"]
            or difference["observation_scope"] != target["observation_scope"]
            or difference["observation_scope"]
            != difference["objective_scope_binding"]["objective_scope_name"]
            or observed["objective_scope_binding"] != difference["objective_scope_binding"]
            or observed["effective_boundary"] != difference["effective_boundary"]
            or structural["observed_knowledge_status"] != observed["knowledge_status"]
            or structural["target_value"] != target["expected_value"]
            or structural["target_value_type"] != target["expected_value_type"]
            or sorted(structural["observed_values"]["members"], key=repr)
            != sorted(observed_values, key=repr)
            or sorted(structural["observed_value_types"]["members"])
            != sorted(observed_types)
        ):
            errors.append(f"Difference projection mismatch: {difference_id}")
        genesis_id = _ref_id(difference["genesis_event_ref"])
        genesis = events.get(genesis_id or "")
        if genesis is None or genesis["difference_id"] != difference_id or genesis["event_revision"] != 0:
            errors.append(f"Difference genesis binding mismatch: {difference_id}")
        policy_ref = difference["closure_policy"]
        policy = policies.get(policy_ref["id"])
        if (
            policy is None
            or _ref_id(policy["subject_difference_ref"]) != difference_id
            or policy["target_predicate_ref"] != difference["target_predicate_ref"]
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
            or policy["target_predicate_ref"] != difference["target_predicate_ref"]
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
            or evaluation["objective_semantic_fingerprint_evaluated"]
            != difference["objective_semantic_fingerprint"]
            or evaluation["evaluated_state_revision"]
            != difference["observed_state_revision"]
            or evaluation["evaluated_state_fingerprint"]
            != difference["observed_state_fingerprint"]
            or evaluation["before_state_ref"]["revision"]
            != evaluation["evaluated_state_revision"]
            or evaluation["before_state_ref"]["fingerprint"]
            != evaluation["evaluated_state_fingerprint"]
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
        maximum_age = None if policy is None else policy["maximum_evidence_age"]
        expiry = evaluation["evaluation_expires_at"]
        if maximum_age is None:
            if expiry is not None:
                errors.append(f"unexpected evaluation expiry: {evaluation['closure_evaluation_id']}")
        elif expiry is None:
            errors.append(f"missing evaluation expiry: {evaluation['closure_evaluation_id']}")
        else:
            evaluated_at = datetime.fromisoformat(evaluation["evaluated_at"].replace("Z", "+00:00"))
            expires_at = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            if expires_at < evaluated_at or expires_at > evaluated_at + timedelta(seconds=maximum_age):
                errors.append(f"invalid evaluation expiry: {evaluation['closure_evaluation_id']}")
        if evaluation["gate_results"]["G22"] != "PASS":
            errors.append(f"terminal state not allowed: {evaluation['closure_evaluation_id']}")
        if policy and proposed not in policy["allowed_terminal_states"]:
            errors.append(f"Policy disallows terminal state: {evaluation['closure_evaluation_id']}")
        if mode == "CANDIDATE_CLOSURE":
            if candidate is None or proposed != "CLOSED" or evaluation["result"] != "SATISFIED":
                errors.append(f"invalid candidate closure mode: {evaluation['closure_evaluation_id']}")
            if candidate is not None and (
                candidate["candidate_id"] != _candidate_id(candidate)
                or candidate["base_state_ref"] != evaluation["before_state_ref"]
                or candidate["kernel_source_ref"] != evaluation["kernel_source_ref_evaluated"]
            ):
                errors.append(f"candidate input binding mismatch: {evaluation['closure_evaluation_id']}")
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
            invariant_bindings = evaluation["candidate_invariant_evaluation_bindings"]
            claim_bindings = evaluation["candidate_claim_evaluation_bindings"]
            definitions = _kernel_invariant_definitions(evaluation["kernel_source_ref_evaluated"])
            if set(definitions) != _mandatory_invariant_ids() | {"P-003"}:
                errors.append(f"kernel invariant source mismatch: {evaluation['closure_evaluation_id']}")
            repository = evaluation["kernel_source_ref_evaluated"]["repository"]
            path = "00_KERNEL/KERNEL_INVARIANTS.md"
            required_invariants = {
                (identity, repository, path, digest)
                for identity, digest in definitions.items() if identity != "P-003"
            } | {
                (item["id"], item["contract_source_ref"]["repository"],
                 item["contract_source_ref"]["path"],
                 item["contract_source_ref"]["invariant_definition_sha256"])
                for item in (policy or {}).get("required_invariants", [])
            }
            bound_invariants = [
                (item["invariant_ref"]["id"], item["invariant_definition_ref"]["repository"],
                 item["invariant_definition_ref"]["path"],
                 item["invariant_definition_ref"]["invariant_definition_sha256"])
                for item in invariant_bindings
            ]
            if set(bound_invariants) != required_invariants or len(bound_invariants) != len(set(bound_invariants)):
                errors.append(f"candidate invariant binding set mismatch: {evaluation['closure_evaluation_id']}")
            required_claims = {item["id"] for item in (policy or {}).get("required_claims", [])}
            bound_claims = [item["required_claim_ref"]["id"] for item in claim_bindings]
            if (
                not required_claims.issubset(bound_claims)
                or len(bound_claims) != len(set(bound_claims))
                or len(set(bound_claims) - required_claims) != 1
            ):
                errors.append(f"candidate claim binding set mismatch: {evaluation['closure_evaluation_id']}")
            for binding in invariant_bindings:
                if (
                    binding["candidate_id"] != candidate["candidate_id"]
                    or binding["candidate_semantic_fingerprint"] != candidate["semantic_fingerprint"]
                    or binding["base_state_ref"] != evaluation["before_state_ref"]
                    or binding["evaluation_result"] != "PASS"
                    or binding["invariant_definition_ref"]["invariant_definition_sha256"]
                    != definitions.get(binding["invariant_ref"]["id"])
                ):
                    errors.append(f"candidate invariant binding mismatch: {binding['binding_id']}")
            for binding in claim_bindings:
                if (
                    binding["difference_id"] != evaluation["difference_id"]
                    or not (policy and _policy_ref_matches(binding["policy_ref"], policy))
                    or binding["candidate_id"] != candidate["candidate_id"]
                    or binding["candidate_semantic_fingerprint"] != candidate["semantic_fingerprint"]
                    or binding["base_state_ref"] != evaluation["before_state_ref"]
                    or binding["evaluation_status"] != "SATISFIED"
                ):
                    errors.append(f"candidate claim binding mismatch: {binding['binding_id']}")
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
        elif set(relation.get("reason_codes", [])) != _supersession_reason_codes(
            differences[old_id], differences[new_id]
        ):
            errors.append(f"supersession reason mismatch: {relation['supersession_relation_id']}")
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
    supersession_edges = {
        _ref_id(relation["old_difference_ref"]): _ref_id(relation["new_difference_ref"])
        for relation in relations.values()
    }
    for start in supersession_edges:
        seen: set[str | None] = set()
        current: str | None = start
        while current in supersession_edges:
            if current in seen:
                errors.append(f"supersession cycle: {start}")
                break
            seen.add(current)
            current = supersession_edges[current]
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
