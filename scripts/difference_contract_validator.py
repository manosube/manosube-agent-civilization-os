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
from manosube_agent_civilization.state.errors import SchemaValidationError
from manosube_agent_civilization.state.fingerprint import fingerprint_semantic_state

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
    return prefix + hashlib.sha256(canonical_json_bytes(_canonical_semantic(payload))).hexdigest().upper()


def _canonical_semantic(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {key: _canonical_semantic(item) for key, item in value.items()}
        if normalized.get("collection_kind") == "UNORDERED_SET" and "members" in normalized:
            normalized["members"] = sorted(normalized["members"], key=canonical_json_bytes)
        return normalized
    if isinstance(value, list):
        return [_canonical_semantic(item) for item in value]
    return value


def _has_recursive_set_duplicate(value: Any) -> bool:
    if isinstance(value, dict):
        if any(_has_recursive_set_duplicate(item) for item in value.values()):
            return True
        if value.get("collection_kind") == "UNORDERED_SET":
            canonical_members = [
                canonical_json_bytes(_canonical_semantic(item))
                for item in value.get("members", [])
            ]
            return len(canonical_members) != len(set(canonical_members))
    elif isinstance(value, list):
        return any(_has_recursive_set_duplicate(item) for item in value)
    return False


def _subject_value(document: dict[str, Any], subject: str) -> Any:
    value: Any = document
    for segment in subject.split("."):
        if not isinstance(value, dict) or segment not in value:
            return None
        value = value[segment]
    return value


def _target_satisfied(values: list[Any], target: dict[str, Any]) -> bool:
    expected = target["expected_value"]
    operator = target["operator"]
    if operator == "equals":
        return bool(values) and all(value == expected for value in values)
    if operator == "not_equals":
        return bool(values) and all(value != expected for value in values)
    if operator == "contains":
        return bool(values) and all(
            isinstance(value, (list, dict))
            and any(
                member == expected
                and _value_matches_declared_type(
                    member, target["expected_value_type"]
                )
                for member in (value if isinstance(value, list) else value.values())
            )
            for value in values
        )
    if operator == "exists":
        return bool(values)
    if operator == "all":
        return bool(values) and all(value == expected for value in values)
    if operator == "none":
        return all(value != expected for value in values)
    return False


def _value_matches_declared_type(value: Any, value_type: str) -> bool:
    return {
        "NULL": value is None,
        "BOOLEAN": isinstance(value, bool),
        "INTEGER": isinstance(value, int) and not isinstance(value, bool),
        "STRING": isinstance(value, str),
        "STRUCTURED": isinstance(value, dict),
        "DECIMAL": isinstance(value, str) and bool(re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?", value)),
        "TIMESTAMP": isinstance(value, str),
        "DURATION": isinstance(value, str) and value.startswith("P"),
        "IDENTITY_REFERENCE": isinstance(value, dict) and {"kind", "id"} <= value.keys(),
        "ORDERED_COLLECTION": isinstance(value, list),
        "UNORDERED_COLLECTION": isinstance(value, list),
    }.get(value_type, False)


def _evaluation_supports_observation(
    evaluation: dict[str, Any], fact: dict[str, Any], observation: dict[str, Any],
    bindings: dict[str, dict[str, Any]],
) -> bool:
    resolved = [bindings.get(_ref_id(reference) or "") for reference in evaluation["binding_refs"]]
    if not resolved or any(binding is None for binding in resolved):
        return False
    if not all(
        reference.get("kind") == "fact_observation_binding"
        and binding is not None
        and binding["fact_id"] == fact["fact_id"]
        and binding["observed_quality_status"] == "SUPPORTED"
        for reference, binding in zip(evaluation["binding_refs"], resolved, strict=True)
    ):
        return False
    return any(
        binding is not None
        and binding["observation_id"] == observation["observation_id"]
        and binding["state_revision_observed"] == observation["state_revision_observed"]
        and binding["state_fingerprint_observed"] == observation["state_fingerprint_observed"]
        and binding["source_ref"] in observation["source_snapshot_refs"]
        for binding in resolved
    )


def _fact_type_matches_target(fact: dict[str, Any], target: dict[str, Any]) -> bool:
    operator = target["operator"]
    if operator == "exists":
        return True
    if operator == "contains":
        return fact["value_type"] in {"ORDERED_COLLECTION", "UNORDERED_COLLECTION"}
    return fact["value_type"] == target["expected_value_type"]


def _resolved_scope_fingerprint(scope: dict[str, Any]) -> str:
    projection = deepcopy(scope)
    for key in ("included_subjects", "excluded_subjects", "source_snapshot_refs", "blind_spots"):
        projection[key] = {
            "collection_kind": "UNORDERED_SET",
            "members": sorted(
                (_canonical_semantic(item) for item in projection[key]),
                key=canonical_json_bytes,
            ),
        }
    projection["attempt_policy"]["retry_on"] = {
        "collection_kind": "UNORDERED_SET",
        "members": sorted(
            projection["attempt_policy"]["retry_on"], key=canonical_json_bytes
        ),
    }
    for item in projection["blind_spots"]["members"]:
        item["affected_subjects"] = {
            "collection_kind": "UNORDERED_SET",
            "members": sorted(item["affected_subjects"], key=canonical_json_bytes),
        }
    domain = b"MANOSUBE:RESOLVED_OBSERVATION_SCOPE_RECORD:0.1:"
    return "sha256:" + hashlib.sha256(
        domain + canonical_json_bytes(_canonical_semantic(projection))
    ).hexdigest()


def _policy_fingerprint(policy: dict[str, Any]) -> str:
    projection = {key: policy[key] for key in (
        "target_predicate_ref", "required_observation_scope", "minimum_evidence_level",
        "required_claims", "required_invariants", "allowed_terminal_states",
        "independent_verification_required", "maximum_evidence_age",
        "contradiction_policy", "reopen_conditions",
    )}
    projection["required_claims"] = sorted(
        (_canonical_semantic(item) for item in projection["required_claims"]),
        key=canonical_json_bytes,
    )
    projection["allowed_terminal_states"] = sorted(
        projection["allowed_terminal_states"], key=canonical_json_bytes
    )
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
    return "sha256:" + hashlib.sha256(
        canonical_json_bytes(_canonical_semantic(projection))
    ).hexdigest()


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
    return "D-" + hashlib.sha256(canonical_json_bytes(_canonical_semantic(identity))).hexdigest().upper()


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


def _candidate_matches_evaluation(candidate: dict[str, Any], evaluation: dict[str, Any]) -> bool:
    required = {
        "candidate_id", "base_state_ref", "kernel_source_ref", "producing_change_refs",
        "semantic_fingerprint", "semantic_state", "source_snapshot_refs",
    }
    if not required.issubset(candidate):
        return False
    try:
        fingerprint = fingerprint_semantic_state(candidate["semantic_state"]).as_dict()
    except SchemaValidationError:
        return False
    return (
        candidate["candidate_id"] == _candidate_id(candidate)
        and candidate["semantic_fingerprint"] == fingerprint
        and candidate["base_state_ref"] == evaluation["before_state_ref"]
        and candidate["kernel_source_ref"] == evaluation["kernel_source_ref_evaluated"]
    )


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


def _mandatory_completion_claim() -> dict[str, Any]:
    projection = {
        "subject_type": "CONTRACT_COMPLETION",
        "subject_ref": {"kind": "kernel_invariant", "id": "X-003"},
        "claim": {"AGENT_REQUIRED_FOR_KERNEL": False, "SESSION_INDEPENDENT": True},
        "target_state_ref": None,
    }
    semantic_fingerprint = "sha256:" + hashlib.sha256(
        canonical_json_bytes(projection)
    ).hexdigest()
    identity = {
        "subject_type": projection["subject_type"],
        "subject_ref": projection["subject_ref"],
        "claim_semantic_fingerprint": semantic_fingerprint,
    }
    claim_id = "CLAIM-" + hashlib.sha256(
        b"MANOSUBE:COMPLETION_CLAIM_IDENTITY:0.1:" + canonical_json_bytes(identity)
    ).hexdigest().upper()
    return {"kind": "completion_claim", "id": claim_id, **projection,
            "claim_semantic_fingerprint": semantic_fingerprint}


def _resolved_record_fingerprint(record: dict[str, Any], kind: str) -> str:
    fields = {
        "completion": (
            "completion_id", "subject_type", "subject_ref", "claim", "target_state_ref",
            "observed_state_ref", "closure_policy_ref", "evaluation_status",
            "evaluated_state_revision", "evaluated_state_fingerprint", "evaluated_at",
            "required_evidence_refs", "invariant_evaluation_refs", "material_contradiction_refs",
        ),
        "invariant": (
            "evaluation_id", "invariant_id", "subject_ref", "state_revision",
            "state_fingerprint", "verification_stage", "method", "expected", "observed",
            "status", "evaluated_at", "evaluator_capability", "authority_ref",
            "evidence_refs", "remaining_differences",
        ),
    }[kind]
    domain = {
        "completion": b"MANOSUBE:COMPLETION_RECORD:0.1:",
        "invariant": b"MANOSUBE:INVARIANT_EVALUATION:0.1:",
    }[kind]
    projection = _canonical_semantic({key: record[key] for key in fields})
    return "sha256:" + hashlib.sha256(domain + canonical_json_bytes(projection)).hexdigest()


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
    for heading in headings:
        boundary = re.search(r"^(?:# |## |---\s*$)", source[heading.end():], re.MULTILINE)
        end = len(source) if boundary is None else heading.end() + boundary.start()
        section = re.sub(r"\n---\s*$", "", source[heading.start():end].rstrip()) + "\n"
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
    completion_records = _index(
        bundle.get("candidate_completion_records", []), "completion_id", errors
    )
    claim_events = _index(
        bundle.get("candidate_claim_evaluation_events", []), "event_id", errors
    )
    invariant_evaluations = _index(
        bundle.get("invariant_evaluations", []), "evaluation_id", errors
    )
    evidence_sufficiency = _index(
        bundle.get("evidence_sufficiency_results", []), "evidence_sufficiency_id", errors
    )
    reflow_transitions = _index(
        bundle.get("reflow_transitions", []), "transaction_id", errors
    )
    changes = _index(bundle.get("changes", []), "change_id", errors)
    reopen_evaluations = _index(
        bundle.get("reopen_condition_evaluations", []), "evaluation_id", errors
    )
    observations = _index(
        bundle.get("observations", []), "observation_id", errors
    )
    observation_scopes = _index(
        bundle.get("observation_scopes", []), "scope_id", errors
    )
    normalized_facts = _index(
        bundle.get("normalized_facts", []), "fact_id", errors
    )
    fact_bindings = _index(
        bundle.get("fact_observation_bindings", []), "binding_id", errors
    )
    fact_evaluations = _index(
        bundle.get("fact_evaluations", []), "evaluation_id", errors
    )
    evidence_observed_at: dict[bytes, datetime] = {}
    for observation in observations.values():
        observed_at = datetime.fromisoformat(
            observation["time_boundary"]["source_snapshot_time"].replace("Z", "+00:00")
        )
        for reference in observation["observation_evidence_refs"]:
            key = canonical_json_bytes(reference)
            previous_time = evidence_observed_at.get(key)
            evidence_observed_at[key] = (
                observed_at if previous_time is None else min(previous_time, observed_at)
            )

    for policy in policies.values():
        claims_by_id: dict[str, dict[str, Any]] = {}
        for descriptor in policy["required_claims"]:
            semantic_projection = {
                key: descriptor[key]
                for key in ("subject_type", "subject_ref", "claim", "target_state_ref")
            }
            semantic_fingerprint = "sha256:" + hashlib.sha256(
                canonical_json_bytes(_canonical_semantic(semantic_projection))
            ).hexdigest()
            identity_projection = {
                "subject_type": descriptor["subject_type"],
                "subject_ref": descriptor["subject_ref"],
                "claim_semantic_fingerprint": semantic_fingerprint,
            }
            expected_id = "CLAIM-" + hashlib.sha256(
                b"MANOSUBE:COMPLETION_CLAIM_IDENTITY:0.1:"
                + canonical_json_bytes(_canonical_semantic(identity_projection))
            ).hexdigest().upper()
            previous = claims_by_id.get(descriptor["id"])
            if (
                descriptor["claim_semantic_fingerprint"] != semantic_fingerprint
                or descriptor["id"] != expected_id
                or _has_recursive_set_duplicate(semantic_projection)
                or (previous is not None and previous != descriptor)
            ):
                errors.append(
                    f"Policy required Claim identity mismatch: {policy['closure_policy_id']}"
                )
            claims_by_id[descriptor["id"]] = descriptor

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
            if (
                event["from_status"] == "ACTIVE"
                and event["to_status"] == "VERIFYING"
            ):
                resolved_changes = [
                    changes.get(_ref_id(reference) or "")
                    for reference in event["change_refs"]
                ]
                change_bound = bool(resolved_changes) and all(
                    change is not None
                    and change["status"] == "EXECUTED"
                    and _ref_id(change["difference_ref"]) == difference_id
                    and change["after_state_observation_request_ref"]
                    == event["next_observation_ref"]
                    for change in resolved_changes
                )
                change_free = bool(event["observation_refs"] and event["evidence_refs"])
                if not (change_bound or change_free):
                    errors.append(
                        f"verifying minimum gate missing: {event['difference_event_id']}"
                    )
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
                previous = chain[expected_revision - 1] if expected_revision > 0 else None
                closure = evaluations.get(_ref_id(event["closure_evaluation_ref"]) or "")
                committed_transition = None if previous is None else reflow_transitions.get(
                    _ref_id(previous["reflow_transition_ref"]) or ""
                )
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
                if trigger == "POLICY_REOPEN_CONDITION_SATISFIED":
                    difference = differences.get(difference_id)
                    policy = None if difference is None else policies.get(
                        difference["closure_policy"]["id"]
                    )
                    condition_ref = event["reopen_condition_ref"]
                    condition = next(
                        (
                            item for item in (policy or {}).get("reopen_conditions", [])
                            if item["id"] == _ref_id(condition_ref)
                        ),
                        None,
                    )
                    condition_evaluation = reopen_evaluations.get(
                        _ref_id(event["reopen_condition_evaluation_ref"]) or ""
                    )
                    expected_condition_ref = None if condition is None else {
                        "kind": "target_predicate", "id": condition["id"],
                    }
                    matching_evaluations = [
                        item for item in reopen_evaluations.values()
                        if condition is not None
                        and item["condition_ref"] == condition
                        and _ref_id(item["difference_ref"]) == difference_id
                        and policy is not None
                        and _policy_ref_matches(item["policy_ref"], policy)
                    ]
                    latest_evaluation = max(
                        matching_evaluations,
                        key=lambda item: (
                            datetime.fromisoformat(
                                item["evaluated_at"].replace("Z", "+00:00")
                            ),
                            item["evaluation_id"],
                        ),
                        default=None,
                    )
                    if (
                        condition_ref is None
                        or condition_ref != expected_condition_ref
                        or event["reopen_condition_evaluation_ref"] is None
                        or event["reopen_condition_evaluation_ref"].get("kind")
                        != "reopen_condition_evaluation"
                        or condition_evaluation is None
                        or condition is None
                        or condition_evaluation is not latest_evaluation
                        or condition_evaluation["evaluation_id"]
                        != _content_address(
                            "REOPEN-EVAL-", condition_evaluation, "evaluation_id"
                        )
                        or condition_evaluation["condition_ref"] != condition
                        or _ref_id(condition_evaluation["difference_ref"]) != difference_id
                        or not (policy and _policy_ref_matches(
                            condition_evaluation["policy_ref"], policy
                        ))
                        or condition_evaluation["state_revision"]
                        != event["state_revision_evaluated"]
                        or condition_evaluation["state_fingerprint"]
                        != event["state_fingerprint_evaluated"]
                        or committed_transition is None
                        or condition_evaluation["state_revision"]
                        != committed_transition["after_state"]["state_revision"]
                        or condition_evaluation["state_fingerprint"]
                        != committed_transition["after_state"]["semantic_fingerprint"]
                        or datetime.fromisoformat(
                            condition_evaluation["evaluated_at"].replace("Z", "+00:00")
                        ) < datetime.fromisoformat(
                            committed_transition["committed_at"].replace("Z", "+00:00")
                        )
                        or condition_evaluation["status"] != "SATISFIED"
                        or closure is None
                        or datetime.fromisoformat(
                            condition_evaluation["evaluated_at"].replace("Z", "+00:00")
                        ) < datetime.fromisoformat(
                            closure["evaluated_at"].replace("Z", "+00:00")
                        )
                        or _canonical_semantic(
                            condition_evaluation["evidence_refs"]["members"]
                        )
                        != _canonical_semantic(event["evidence_refs"])
                    ):
                        errors.append(
                            f"reopen condition evaluation mismatch: {event['difference_event_id']}"
                        )
                if (
                    previous is None
                    or _ref_id(previous["closure_evaluation_ref"])
                    != _ref_id(event["closure_evaluation_ref"])
                    or closure is None
                    or closure["difference_id"] != difference_id
                    or closure["proposed_terminal_status"] != "CLOSED"
                    or closure["result"] != "SATISFIED"
                    or closure["gate_results"]["G22"] != "PASS"
                ):
                    errors.append(f"reopen closure binding mismatch: {event['difference_event_id']}")
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
                    if condition["subject_ref"] not in scope["affected_subject_refs"]["members"]:
                        errors.append(f"blocker condition subject mismatch: {event['difference_event_id']}")
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
            elif any(
                event[key] is not None
                for key in ("blocker_kind", "blocker_scope", "blocker_resolution_condition")
            ):
                errors.append(f"non-BLOCKED event carries blocker payload: {event['difference_event_id']}")
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
                transition_ref = event["reflow_transition_ref"]
                transition = reflow_transitions.get(_ref_id(transition_ref) or "")
                candidate = None if evaluation is None else evaluation["after_state_candidate"]
                commit_before_expiry = (
                    transition is not None
                    and evaluation is not None
                    and (
                        datetime.fromisoformat(transition["committed_at"].replace("Z", "+00:00"))
                        >= datetime.fromisoformat(
                            evaluation["evaluated_at"].replace("Z", "+00:00")
                        )
                    )
                    and (
                        evaluation["evaluation_expires_at"] is None
                        or datetime.fromisoformat(transition["committed_at"].replace("Z", "+00:00"))
                        <= datetime.fromisoformat(
                            evaluation["evaluation_expires_at"].replace("Z", "+00:00")
                        )
                    )
                )
                reflow_valid = event["to_status"] != "CLOSED" or (
                    transition_ref is not None
                    and transition_ref.get("kind") == "state_transition"
                    and transition is not None
                    and evaluation is not None
                    and candidate is not None
                    and difference is not None
                    and commit_before_expiry
                    and transition["event_type"] == "TRANSITION"
                    and transition["project_id"] == difference["project_id"]
                    and transition["after_state"]["project_id"] == difference["project_id"]
                    and transition["after_state"]["objective_revision_id"]
                    == evaluation["objective_revision_ref_evaluated"]["id"]
                    and transition["from_revision"] == evaluation["before_state_ref"]["revision"]
                    and transition["to_revision"] == transition["from_revision"] + 1
                    and transition["before_fingerprint"]
                    == evaluation["before_state_ref"]["fingerprint"]
                    and transition["after_fingerprint"] == candidate["semantic_fingerprint"]
                    and transition["after_state"]["state_revision"] == transition["to_revision"]
                    and transition["after_state"]["previous_state_fingerprint"]
                    == transition["before_fingerprint"]
                    and transition["after_state"]["semantic_fingerprint"]
                    == transition["after_fingerprint"]
                    and transition["after_state"]["semantic_state"] == candidate["semantic_state"]
                    and transition["after_state"]["lineage_head_ref"] == transition_ref
                    and {("closure_evaluation", evaluation["closure_evaluation_id"]),
                         ("difference", difference_id)}
                    <= {(reference["kind"], reference["id"])
                        for reference in transition["evidence_refs"]}
                )
                if (
                    evaluation is None
                    or evaluation["difference_id"] != difference_id
                    or evaluation["proposed_terminal_status"] != event["to_status"]
                    or evaluation["gate_results"]["G22"] != "PASS"
                    or policy is None
                    or not _policy_ref_matches(evaluation["policy_ref"], policy)
                    or _ref_id(evaluation["difference_event_head_ref"])
                    != event["previous_event_id"]
                    or (
                        event["to_status"] == "CLOSED"
                        and (
                            event["reflow_transition_ref"]
                            != evaluation["reflow_transition_ref"]
                            or not reflow_valid
                        )
                    )
                ):
                    errors.append(f"terminal evaluation binding mismatch: {event['difference_event_id']}")
            reconstructed[difference_id] = event["to_status"]

    for difference_id, difference in differences.items():
        target = difference["normalized_target_state"]
        observed = difference["normalized_observed_state"]
        structural = difference["structural_difference"]
        observed_values = [item["value"] for item in observed["value_candidates"]["members"]]
        observed_types = [item["value_type"] for item in observed["value_candidates"]["members"]]
        derived_comparison = (
            "UNKNOWN" if observed["knowledge_status"] != "KNOWN" else
            "SATISFIED" if _target_satisfied(observed_values, target) else
            "NOT_SATISFIED"
        )
        derived_mismatch = (
            "UNKNOWN" if derived_comparison == "UNKNOWN" else
            None if derived_comparison == "SATISFIED" else
            "TYPE_MISMATCH" if any(
                not _fact_type_matches_target(item, target)
                for item in observed["value_candidates"]["members"]
            ) else "VALUE_MISMATCH"
        )
        if (
            _has_recursive_set_duplicate(difference["normalized_target_state"])
            or _has_recursive_set_duplicate(difference["normalized_observed_state"])
            or _has_recursive_set_duplicate(difference["structural_difference"])
            or difference_id != _difference_id(difference)
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
            or structural["comparison_result"] != derived_comparison
            or derived_comparison == "SATISFIED"
            or structural["mismatch_kind"] != derived_mismatch
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
            or evaluation["objective_revision_ref_evaluated"]
            != difference["objective_revision_ref"]
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
            required_evidence_refs = (
                evaluation["terminal_reason_evidence_refs"]
                + evaluation["change_result_evidence_refs"]
                + evaluation["change_free_verification_evidence_refs"]
                + [
                    reference
                    for binding in evaluation["candidate_invariant_evaluation_bindings"]
                    for reference in binding["evaluation_evidence_refs"]
                ]
                + [
                    reference
                    for binding in evaluation["candidate_claim_evaluation_bindings"]
                    for reference in binding["evaluation_evidence_refs"]
                ]
            )
            evidence_times = [
                evidence_observed_at.get(canonical_json_bytes(reference))
                for reference in required_evidence_refs
            ]
            oldest_evidence = (
                None if not evidence_times or any(item is None for item in evidence_times)
                else min(item for item in evidence_times if item is not None)
            )
            expected_expiry = (
                None if oldest_evidence is None
                else oldest_evidence + timedelta(seconds=maximum_age)
            )
            if (
                expected_expiry is None
                or expires_at != expected_expiry
                or evaluated_at < oldest_evidence
                or evaluated_at > expected_expiry
            ):
                errors.append(f"invalid evaluation expiry: {evaluation['closure_evaluation_id']}")
        if evaluation["gate_results"]["G22"] != "PASS":
            errors.append(f"terminal state not allowed: {evaluation['closure_evaluation_id']}")
        if policy and proposed not in policy["allowed_terminal_states"]:
            errors.append(f"Policy disallows terminal state: {evaluation['closure_evaluation_id']}")
        if candidate is not None and not _candidate_matches_evaluation(candidate, evaluation):
            errors.append(f"candidate input binding mismatch: {evaluation['closure_evaluation_id']}")
        invariant_definitions = _kernel_invariant_definitions(
            evaluation["kernel_source_ref_evaluated"]
        )
        if candidate is not None:
            for binding in evaluation["candidate_invariant_evaluation_bindings"]:
                record = invariant_evaluations.get(
                    _ref_id(binding["invariant_evaluation_ref"]) or ""
                )
                if (
                    binding["binding_id"]
                    != _content_address("CAND-INV-EVAL-", binding, "binding_id")
                    or binding["candidate_id"] != candidate["candidate_id"]
                    or binding["candidate_semantic_fingerprint"]
                    != candidate["semantic_fingerprint"]
                    or binding["base_state_ref"] != evaluation["before_state_ref"]
                    or binding["invariant_definition_ref"]["invariant_definition_sha256"]
                    != invariant_definitions.get(binding["invariant_ref"]["id"])
                    or record is None
                    or record["invariant_id"] != binding["invariant_ref"]["id"]
                    or record["subject_ref"]
                    != {"kind": "after_state_candidate", "id": candidate["candidate_id"]}
                    or record["state_revision"] != evaluation["before_state_ref"]["revision"]
                    or record["state_fingerprint"] != candidate["semantic_fingerprint"]
                    or record["status"] != binding["evaluation_result"]
                    or _canonical_semantic(record["evidence_refs"])
                    != _canonical_semantic(binding["evaluation_evidence_refs"])
                    or record["evaluated_at"] != binding["evaluated_at"]
                    or binding["evaluation_record_fingerprint"]
                    != (None if record is None else _resolved_record_fingerprint(record, "invariant"))
                ):
                    errors.append(
                        f"candidate invariant binding mismatch: {binding['binding_id']}"
                    )
        if mode == "CANDIDATE_CLOSURE":
            if candidate is None or proposed != "CLOSED" or evaluation["result"] != "SATISFIED":
                errors.append(f"invalid candidate closure mode: {evaluation['closure_evaluation_id']}")
            if any(value != "PASS" for value in evaluation["gate_results"].values()):
                errors.append(f"closure has non-PASS mandatory gate: {evaluation['closure_evaluation_id']}")
            if evaluation["contradiction_refs"]:
                errors.append(
                    f"closure has unresolved contradiction: "
                    f"{evaluation['closure_evaluation_id']}"
                )
            resolution_mode = evaluation["resolution_mode"]
            after_observations = [
                observations.get(_ref_id(reference) or "")
                if reference.get("kind") == "observation" else None
                for reference in evaluation["after_observation_refs"]
            ]
            required_scope_ref = (
                (policy or {}).get("required_observation_scope")
                or (difference or {}).get("objective_scope_binding", {}).get("scope_ref")
            )
            scope_reference = None if required_scope_ref is None else {
                "kind": required_scope_ref["kind"], "id": required_scope_ref["id"],
            }
            required_scope = observation_scopes.get(
                "" if required_scope_ref is None else required_scope_ref["id"]
            )
            scope_binding_valid = required_scope_ref is not None and (
                "schema_version" not in required_scope_ref
                or (
                    required_scope is not None
                    and required_scope["schema_version"] == required_scope_ref["schema_version"]
                    and _resolved_scope_fingerprint(required_scope)
                    == required_scope_ref["resolved_record_sha256"]
                )
            )
            resolution_evidence_refs = (
                evaluation["change_result_evidence_refs"]
                + evaluation["change_free_verification_evidence_refs"]
            )
            resolution_evidence = {
                canonical_json_bytes(reference) for reference in resolution_evidence_refs
            }
            candidate_snapshot_set = (
                None if candidate is None else candidate["source_snapshot_refs"]
            )
            resolved_fact_sets = [
                [normalized_facts.get(_ref_id(reference) or "") for reference in observation["normalized_fact_refs"]]
                if observation is not None else []
                for observation in after_observations
            ]
            fact_evaluation_chains: dict[str, list[dict[str, Any]]] = {}
            for fact_evaluation in fact_evaluations.values():
                fact_evaluation_chains.setdefault(
                    fact_evaluation["fact_id"], []
                ).append(fact_evaluation)
            latest_fact_evaluations: dict[str, dict[str, Any]] = {}
            for fact_id, chain in fact_evaluation_chains.items():
                chain.sort(key=lambda item: item["evaluation_revision"])
                valid_chain = all(
                    item["evaluation_revision"] == revision
                    and item["previous_evaluation_id"]
                    == (None if revision == 0 else chain[revision - 1]["evaluation_id"])
                    for revision, item in enumerate(chain)
                )
                if valid_chain:
                    latest_fact_evaluations[fact_id] = chain[-1]
            facts_valid = all(
                facts
                and all(
                    fact is not None
                    and difference is not None
                    and fact["project_id"] == difference["project_id"]
                    and fact["subject"] == difference["subject"]
                    and _fact_type_matches_target(
                        fact, difference["normalized_target_state"]
                    )
                    and (latest_evaluation := latest_fact_evaluations.get(fact["fact_id"]))
                    is not None
                    and latest_evaluation["evaluation_status"] == "SUPPORTED"
                    and not latest_evaluation["conflict_fact_refs"]
                    and not latest_evaluation["conflict_negative_observation_refs"]
                    and observation is not None
                    and _evaluation_supports_observation(
                        latest_evaluation, fact, observation, fact_bindings
                    )
                    for fact in facts
                )
                and difference is not None
                and _target_satisfied(
                    [fact["value"] for fact in facts if fact is not None],
                    difference["normalized_target_state"],
                )
                for observation, facts in zip(after_observations, resolved_fact_sets, strict=True)
            )
            candidate_value = (
                None if candidate is None or difference is None else
                _subject_value(candidate["semantic_state"], difference["subject"])
            )
            candidate_target_valid = (
                candidate is not None
                and difference is not None
                and _target_satisfied(
                    [candidate_value], difference["normalized_target_state"]
                )
                and all(
                    fact is not None and fact["value"] == candidate_value
                    for facts in resolved_fact_sets for fact in facts
                )
            )
            after_observations_valid = bool(after_observations) and scope_binding_valid and facts_valid and candidate_target_valid and all(
                observation is not None
                and difference is not None
                and candidate is not None
                and observation["project_id"] == difference["project_id"]
                and observation["state_revision_observed"]
                == evaluation["before_state_ref"]["revision"]
                and observation["state_fingerprint_observed"]
                == evaluation["before_state_ref"]["fingerprint"]
                and observation["target"]["target_identity"]
                == difference["target_predicate_ref"]["id"]
                and observation["scope_ref"] == scope_reference
                and observation["status"] == "COMPLETE"
                and observation["blind_spots"]["status"] == "NONE_KNOWN"
                and bool(observation["normalized_fact_refs"])
                and {
                    "collection_kind": "UNORDERED_SET",
                    "members": sorted(
                        observation["source_snapshot_refs"], key=canonical_json_bytes
                    ),
                } == candidate_snapshot_set
                and bool(observation["observation_evidence_refs"])
                and all(
                    canonical_json_bytes(reference) in resolution_evidence
                    for reference in observation["observation_evidence_refs"]
                )
                for observation in after_observations
            )
            common_evidence_present = bool(
                after_observations_valid
                and evaluation["evidence_sufficiency_ref"]
            )
            if not after_observations_valid:
                errors.append(
                    f"after-state Observation binding mismatch: "
                    f"{evaluation['closure_evaluation_id']}"
                )
            sufficiency = evidence_sufficiency.get(
                _ref_id(evaluation["evidence_sufficiency_ref"]) or ""
            )
            levels = {f"E{index}": index for index in range(7)}
            if (
                sufficiency is None
                or sufficiency["result"] != "SUFFICIENT"
                or _ref_id(sufficiency["difference_ref"]) != evaluation["difference_id"]
                or not (policy and _policy_ref_matches(sufficiency["policy_ref"], policy))
                or sufficiency["evaluated_at"] != evaluation["evaluated_at"]
                or levels[sufficiency["evidence_level"]]
                < levels[(policy or {})["minimum_evidence_level"]]
                or sufficiency["evidence_refs"] != {
                    "collection_kind": "UNORDERED_SET",
                    "members": sorted(
                        evaluation["change_result_evidence_refs"]
                        + evaluation["change_free_verification_evidence_refs"],
                        key=canonical_json_bytes,
                    ),
                }
            ):
                errors.append(f"Evidence Sufficiency binding mismatch: {evaluation['closure_evaluation_id']}")
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
            definitions = invariant_definitions
            if set(definitions) - {"X-003"} != _mandatory_invariant_ids() | {"P-003"}:
                errors.append(f"kernel invariant source mismatch: {evaluation['closure_evaluation_id']}")
            repository = evaluation["kernel_source_ref_evaluated"]["repository"]
            path = "00_KERNEL/KERNEL_INVARIANTS.md"
            required_invariants = {
                (identity, repository, path, digest)
                for identity, digest in definitions.items()
                if identity not in {"P-003", "X-003"}
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
            mandatory_claim = _mandatory_completion_claim()
            policy_claims = {
                item["id"]: item for item in (policy or {}).get("required_claims", [])
            }
            if (
                mandatory_claim["id"] in policy_claims
                and policy_claims[mandatory_claim["id"]] != mandatory_claim
            ):
                errors.append(f"mandatory claim definition conflict: {evaluation['closure_evaluation_id']}")
            required_claims = set(policy_claims) | {mandatory_claim["id"]}
            claim_descriptors = {**policy_claims, mandatory_claim["id"]: mandatory_claim}
            bound_claims = [item["required_claim_ref"]["id"] for item in claim_bindings]
            if (
                set(bound_claims) != required_claims
                or len(bound_claims) != len(set(bound_claims))
            ):
                errors.append(f"candidate claim binding set mismatch: {evaluation['closure_evaluation_id']}")
            for binding in invariant_bindings:
                record = invariant_evaluations.get(_ref_id(binding["invariant_evaluation_ref"]) or "")
                if (
                    binding["binding_id"]
                    != _content_address("CAND-INV-EVAL-", binding, "binding_id")
                    or binding["candidate_id"] != candidate["candidate_id"]
                    or binding["candidate_semantic_fingerprint"] != candidate["semantic_fingerprint"]
                    or binding["base_state_ref"] != evaluation["before_state_ref"]
                    or binding["evaluation_result"] != "PASS"
                    or binding["invariant_definition_ref"]["invariant_definition_sha256"]
                    != definitions.get(binding["invariant_ref"]["id"])
                    or record is None
                    or record["invariant_id"] != binding["invariant_ref"]["id"]
                    or record["subject_ref"] != {"kind": "after_state_candidate", "id": candidate["candidate_id"]}
                    or record["state_revision"] != evaluation["before_state_ref"]["revision"]
                    or record["state_fingerprint"] != candidate["semantic_fingerprint"]
                    or record["status"] != binding["evaluation_result"]
                    or _canonical_semantic(record["evidence_refs"])
                    != _canonical_semantic(binding["evaluation_evidence_refs"])
                    or record["evaluated_at"] != binding["evaluated_at"]
                    or binding["evaluation_record_fingerprint"]
                    != (None if record is None else _resolved_record_fingerprint(record, "invariant"))
                ):
                    errors.append(f"candidate invariant binding mismatch: {binding['binding_id']}")
            for binding in claim_bindings:
                descriptor = claim_descriptors.get(binding["required_claim_ref"]["id"])
                series = [
                    item for item in claim_events.values()
                    if item["evaluation_series_id"] == binding["evaluation_series_id"]
                ]
                series.sort(key=lambda item: item["event_revision"])
                head = series[-1] if series else None
                completion = completion_records.get(_ref_id(binding["completion_record_ref"]) or "")
                series_payload = {
                    "difference_id": binding["difference_id"],
                    "policy_ref": binding["policy_ref"],
                    "candidate_id": binding["candidate_id"],
                    "required_claim_ref": binding["required_claim_ref"],
                }
                expected_series = "CAND-CLAIM-SERIES-" + hashlib.sha256(
                    b"MANOSUBE:CANDIDATE_CLAIM_EVALUATION_SERIES:0.1:"
                    + canonical_json_bytes(series_payload)
                ).hexdigest().upper()
                chain_valid = all(
                    item["event_revision"] == revision
                    and item["difference_id"] == binding["difference_id"]
                    and item["policy_ref"] == binding["policy_ref"]
                    and item["candidate_id"] == binding["candidate_id"]
                    and item["required_claim_ref"] == binding["required_claim_ref"]
                    and _ref_id(item["predecessor_event_ref"])
                    == (None if revision == 0 else series[revision - 1]["event_id"])
                    and item["event_id"]
                    == "CAND-CLAIM-EVT-" + hashlib.sha256(
                        b"MANOSUBE:CANDIDATE_CLAIM_EVALUATION_EVENT:0.1:"
                        + canonical_json_bytes({key: value for key, value in item.items() if key != "event_id"})
                    ).hexdigest().upper()
                    for revision, item in enumerate(series)
                )
                completion_fingerprint = None
                completion_id = None
                if completion is not None:
                    completion_fingerprint = _resolved_record_fingerprint(completion, "completion")
                    completion_payload = {
                        key: value for key, value in completion.items()
                        if key not in {"completion_id", "reflow_transition_ref"}
                    }
                    completion_id = "CMP-" + hashlib.sha256(
                        b"MANOSUBE:CANDIDATE_COMPLETION_RECORD:0.1:"
                        + canonical_json_bytes(_canonical_semantic(completion_payload))
                    ).hexdigest().upper()
                if (
                    binding["binding_id"]
                    != _content_address("CAND-CLAIM-EVAL-", binding, "binding_id")
                    or binding["difference_id"] != evaluation["difference_id"]
                    or not (policy and _policy_ref_matches(binding["policy_ref"], policy))
                    or binding["candidate_id"] != candidate["candidate_id"]
                    or binding["candidate_semantic_fingerprint"] != candidate["semantic_fingerprint"]
                    or binding["base_state_ref"] != evaluation["before_state_ref"]
                    or binding["evaluation_status"] != "SATISFIED"
                    or binding["evaluation_series_id"] != expected_series
                    or not chain_valid
                    or head is None
                    or _ref_id(binding["evaluation_head_event_ref"])
                    != (None if head is None else head["event_id"])
                    or completion is None
                    or completion_id != _ref_id(binding["completion_record_ref"])
                    or binding["evaluation_record_fingerprint"] != completion_fingerprint
                    or head is None
                    or head["completion_record_ref"] != binding["completion_record_ref"]
                    or head["completion_record_fingerprint"] != binding["evaluation_record_fingerprint"]
                    or head["evaluation_status"] != binding["evaluation_status"]
                    or head["required_claim_ref"] != binding["required_claim_ref"]
                    or head["candidate_id"] != binding["candidate_id"]
                    or completion is None
                    or completion["evaluation_status"] != binding["evaluation_status"]
                    or completion["evaluated_at"] != binding["evaluated_at"]
                    or _canonical_semantic(completion["required_evidence_refs"])
                    != _canonical_semantic(binding["evaluation_evidence_refs"])
                    or descriptor is None
                    or binding["required_claim_ref"]
                    != {"kind": "completion_claim", "id": descriptor["id"]}
                    or completion["subject_type"] != descriptor["subject_type"]
                    or completion["subject_ref"] != descriptor["subject_ref"]
                    or _canonical_semantic(completion["claim"])
                    != _canonical_semantic(descriptor["claim"])
                    or completion["target_state_ref"] != descriptor["target_state_ref"]
                    or completion["observed_state_ref"]
                    != {"kind": "after_state_candidate", "id": candidate["candidate_id"]}
                    or not (policy and _policy_ref_matches(completion["closure_policy_ref"], policy))
                    or completion["evaluated_state_revision"]
                    != evaluation["before_state_ref"]["revision"]
                    or completion["evaluated_state_fingerprint"]
                    != candidate["semantic_fingerprint"]
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
            mandatory_claim = _mandatory_completion_claim()
            claim_descriptors = {
                item["id"]: item for item in (policy or {}).get("required_claims", [])
            }
            claim_descriptors[mandatory_claim["id"]] = mandatory_claim
            for binding in evaluation["candidate_claim_evaluation_bindings"]:
                descriptor = claim_descriptors.get(binding["required_claim_ref"]["id"])
                completion = completion_records.get(
                    _ref_id(binding["completion_record_ref"]) or ""
                )
                series = sorted(
                    (
                        item for item in claim_events.values()
                        if item["evaluation_series_id"] == binding["evaluation_series_id"]
                    ),
                    key=lambda item: item["event_revision"],
                )
                head_event = series[-1] if series else None
                completion_id = None
                if completion is not None:
                    completion_payload = {
                        key: value for key, value in completion.items()
                        if key not in {"completion_id", "reflow_transition_ref"}
                    }
                    completion_id = "CMP-" + hashlib.sha256(
                        b"MANOSUBE:CANDIDATE_COMPLETION_RECORD:0.1:"
                        + canonical_json_bytes(_canonical_semantic(completion_payload))
                    ).hexdigest().upper()
                series_payload = {
                    "difference_id": binding["difference_id"],
                    "policy_ref": binding["policy_ref"],
                    "candidate_id": binding["candidate_id"],
                    "required_claim_ref": binding["required_claim_ref"],
                }
                expected_series = "CAND-CLAIM-SERIES-" + hashlib.sha256(
                    b"MANOSUBE:CANDIDATE_CLAIM_EVALUATION_SERIES:0.1:"
                    + canonical_json_bytes(series_payload)
                ).hexdigest().upper()
                chain_valid = all(
                    item["event_revision"] == revision
                    and item["difference_id"] == binding["difference_id"]
                    and item["policy_ref"] == binding["policy_ref"]
                    and item["candidate_id"] == binding["candidate_id"]
                    and item["required_claim_ref"] == binding["required_claim_ref"]
                    and _ref_id(item["predecessor_event_ref"])
                    == (None if revision == 0 else series[revision - 1]["event_id"])
                    and item["event_id"]
                    == "CAND-CLAIM-EVT-" + hashlib.sha256(
                        b"MANOSUBE:CANDIDATE_CLAIM_EVALUATION_EVENT:0.1:"
                        + canonical_json_bytes({
                            key: value for key, value in item.items()
                            if key != "event_id"
                        })
                    ).hexdigest().upper()
                    for revision, item in enumerate(series)
                )
                if (
                    binding["binding_id"]
                    != _content_address("CAND-CLAIM-EVAL-", binding, "binding_id")
                    or binding["difference_id"] != evaluation["difference_id"]
                    or not (policy and _policy_ref_matches(binding["policy_ref"], policy))
                    or binding["candidate_id"] != candidate["candidate_id"]
                    or binding["candidate_semantic_fingerprint"]
                    != candidate["semantic_fingerprint"]
                    or binding["base_state_ref"] != evaluation["before_state_ref"]
                    or descriptor is None
                    or binding["required_claim_ref"]
                    != {"kind": "completion_claim", "id": descriptor["id"]}
                    or binding["evaluation_series_id"] != expected_series
                    or not chain_valid
                    or completion is None
                    or completion_id != _ref_id(binding["completion_record_ref"])
                    or descriptor is None
                    or completion["subject_type"] != descriptor["subject_type"]
                    or completion["subject_ref"] != descriptor["subject_ref"]
                    or _canonical_semantic(completion["claim"])
                    != _canonical_semantic(descriptor["claim"])
                    or completion["target_state_ref"] != descriptor["target_state_ref"]
                    or completion["observed_state_ref"]
                    != {"kind": "after_state_candidate", "id": candidate["candidate_id"]}
                    or not (policy and _policy_ref_matches(
                        completion["closure_policy_ref"], policy
                    ))
                    or completion["evaluated_state_revision"]
                    != evaluation["before_state_ref"]["revision"]
                    or completion["evaluated_state_fingerprint"]
                    != candidate["semantic_fingerprint"]
                    or completion["evaluation_status"] != binding["evaluation_status"]
                    or _canonical_semantic(completion["required_evidence_refs"])
                    != _canonical_semantic(binding["evaluation_evidence_refs"])
                    or completion["evaluated_at"] != binding["evaluated_at"]
                    or binding["evaluation_record_fingerprint"]
                    != (None if completion is None else _resolved_record_fingerprint(
                        completion, "completion"
                    ))
                    or head_event is None
                    or _ref_id(binding["evaluation_head_event_ref"])
                    != (None if head_event is None else head_event["event_id"])
                    or head_event is None
                    or head_event["completion_record_ref"]
                    != binding["completion_record_ref"]
                    or head_event["completion_record_fingerprint"]
                    != binding["evaluation_record_fingerprint"]
                    or head_event["required_claim_ref"] != binding["required_claim_ref"]
                    or head_event["candidate_id"] != binding["candidate_id"]
                    or head_event["evaluation_status"] != binding["evaluation_status"]
                ):
                    errors.append(
                        f"candidate claim binding mismatch: {binding['binding_id']}"
                    )
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
