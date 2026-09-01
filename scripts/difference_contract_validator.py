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

from manosube_agent_civilization.difference.envelope import (
    satisfaction_reconciliation_errors,
)
from manosube_agent_civilization.difference.graph import reference_closure_errors
from manosube_agent_civilization.difference.lifecycle import (
    LEGAL_TRANSITIONS,
    blocker_payload_errors,
    closure_evaluation_binding_errors,
    closure_evaluation_input_errors,
    next_observation_binding_errors,
)
from manosube_agent_civilization.difference.objective import objective_chain_errors
from manosube_agent_civilization.difference.policy import (
    closure_policy_semantic_errors,
    reopen_condition_provenance_errors,
)
from manosube_agent_civilization.difference.selection import contributing_facts
from manosube_agent_civilization.observation.boundary import fact_boundary_observed
from manosube_agent_civilization.observation.verification import (
    negative_evaluation_evidence_errors,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.state.errors import SchemaValidationError
from manosube_agent_civilization.state.fingerprint import fingerprint_semantic_state

STATUSES = {
    "DETECTED", "OPEN", "ACTIVE", "VERIFYING", "BLOCKED", "RETAINED", "CLOSED",
    "REOPENED", "SUPERSEDED", "INVALIDATED",
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
        return bool(values) and all(_exact_value_equal(value, expected) for value in values)
    if operator == "not_equals":
        return bool(values) and all(not _exact_value_equal(value, expected) for value in values)
    if operator == "contains":
        return bool(values) and all(
            (members := _collection_members(value)) is not None
            and any(
                _exact_value_equal(member, expected)
                and _value_matches_declared_type(
                    member, target["expected_value_type"]
                )
                for member in members
            )
            for value in values
        )
    if operator == "exists":
        return bool(values)
    if operator == "all":
        return bool(values) and all(_exact_value_equal(value, expected) for value in values)
    if operator == "none":
        return all(not _exact_value_equal(value, expected) for value in values)
    return False


def _collection_members(value: Any) -> list[Any] | None:
    if isinstance(value, list):
        return value
    if (
        isinstance(value, dict)
        and value.get("collection_kind") in {"ORDERED_LIST", "UNORDERED_SET"}
        and isinstance(value.get("members"), list)
    ):
        return value["members"]
    return None


def _is_empty_collection(value: Any) -> bool:
    members = _collection_members(value)
    return members == []


def _observation_attempts_complete(
    observation: dict[str, Any], scope: dict[str, Any],
) -> bool:
    attempts = observation["attempts"]
    started = datetime.fromisoformat(
        observation["time_boundary"]["observation_started_at"].replace(
            "Z", "+00:00"
        )
    )
    ended = datetime.fromisoformat(
        observation["time_boundary"]["observation_ended_at"].replace(
            "Z", "+00:00"
        )
    )
    timeout = scope["attempt_policy"]["timeout_seconds"]
    return (
        observation["method_ref"] == scope["method_ref"]
        and _observation_time_boundary_complete(observation, scope)
        and
        0 < len(attempts) <= scope["attempt_policy"]["max_attempts"]
        and all(
            attempt["method_ref"] == observation["method_ref"]
            and attempt["result"] in {"COMPLETE", "EMPTY"}
            and attempt["failure_class"] is None
            and started
            <= (attempt_started := datetime.fromisoformat(
                attempt["started_at"].replace("Z", "+00:00")
            ))
            <= (attempt_ended := datetime.fromisoformat(
                attempt["ended_at"].replace("Z", "+00:00")
            ))
            <= ended
            and (attempt_ended - attempt_started).total_seconds() <= timeout
            for attempt in attempts
        )
    )


def _observation_time_boundary_complete(
    observation: dict[str, Any], scope: dict[str, Any],
) -> bool:
    try:
        boundary = observation["time_boundary"]
        observed_start = datetime.fromisoformat(
            boundary["observation_started_at"].replace("Z", "+00:00")
        )
        observed_end = datetime.fromisoformat(
            boundary["observation_ended_at"].replace("Z", "+00:00")
        )
        effective_start = datetime.fromisoformat(
            boundary["target_effective_start"].replace("Z", "+00:00")
        )
        effective_end = datetime.fromisoformat(
            boundary["target_effective_end"].replace("Z", "+00:00")
        )
        snapshot = datetime.fromisoformat(
            boundary["source_snapshot_time"].replace("Z", "+00:00")
        )
        scope_observed_start = datetime.fromisoformat(
            scope["observation_window"]["start"].replace("Z", "+00:00")
        )
        scope_observed_end = datetime.fromisoformat(
            scope["observation_window"]["end"].replace("Z", "+00:00")
        )
        scope_effective_start = datetime.fromisoformat(
            scope["target_effective_window"]["start"].replace("Z", "+00:00")
        )
        scope_effective_end = datetime.fromisoformat(
            scope["target_effective_window"]["end"].replace("Z", "+00:00")
        )
        cutoff = datetime.fromisoformat(scope["cutoff"].replace("Z", "+00:00"))
        freshness_limit = scope["freshness_limit_seconds"]
        if isinstance(freshness_limit, bool) or not isinstance(freshness_limit, (int, float)):
            return False
        # A naive instant would compare against an aware one and raise, or silently
        # compare against another naive one; both fail closed here instead.
        if any(
            moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None
            for moment in (
                observed_start, observed_end, effective_start, effective_end,
                snapshot, scope_observed_start, scope_observed_end,
                scope_effective_start, scope_effective_end, cutoff,
            )
        ):
            return False
    except (AttributeError, KeyError, TypeError, ValueError):
        return False
    return (
        observed_start <= observed_end
        and effective_start <= effective_end
        and scope_observed_start <= observed_start <= observed_end <= scope_observed_end
        and scope_effective_start <= effective_start <= effective_end <= scope_effective_end
        and effective_start <= snapshot <= observed_end
        and snapshot <= cutoff
        and (cutoff - snapshot).total_seconds() <= freshness_limit
    )


def _fact_boundary_observed(
    fact: dict[str, Any], observation: dict[str, Any],
) -> bool:
    """Delegate to the single canonical Fact boundary authority."""

    return fact_boundary_observed(fact["effective_boundary"], observation)


def _fact_id(fact: dict[str, Any]) -> str:
    value = deepcopy(fact["value"])
    if fact["value_type"] == "UNORDERED_COLLECTION" and isinstance(value, list):
        value = sorted(value, key=canonical_json_bytes)
    semantic = {
        key: (value if key == "value" else fact[key])
        for key in (
            "project_id", "subject", "predicate", "value", "value_type",
            "unit", "effective_boundary", "normalization_profile",
        )
    }
    domain = b"MANOSUBE_AGENT_CIVILIZATION_OS\x00OBSERVATION\x000.1\x00"
    return "FACT-" + hashlib.sha256(
        domain + canonical_json_bytes(semantic)
    ).hexdigest().upper()


def _derive_comparison_and_mismatch(
    observed: dict[str, Any], target: dict[str, Any],
) -> tuple[str, str | None]:
    candidates = observed["value_candidates"]["members"]
    values = [item["value"] for item in candidates]
    distinct = {canonical_json_bytes(_canonical_semantic(value)) for value in values}
    operator = target["operator"]
    knowledge = observed["knowledge_status"]
    if knowledge == "CONFLICTED" or (
        operator in {"equals", "not_equals", "contains"} and len(distinct) > 1
    ):
        return "UNKNOWN", "CONFLICT"
    if knowledge in {"UNKNOWN", "UNOBSERVED", "BLOCKED", "INCOMPLETE"}:
        return "UNKNOWN", "UNKNOWN"
    type_mismatch = any(not _fact_type_matches_target(item, target) for item in candidates)
    if type_mismatch:
        return "NOT_SATISFIED", "TYPE_MISMATCH"
    # ABSENT and EMPTY are bounded proven absence, not unresolved knowledge: they are
    # evaluable, so a `none` Target over a proven-empty evaluated set is satisfied. The
    # unresolved statuses returned above never reach here.
    comparison = (
        ("SATISFIED" if _target_satisfied(values, target) else "NOT_SATISFIED")
        if knowledge in {"KNOWN", "ABSENT", "EMPTY"} else "UNKNOWN"
    )
    if not candidates and operator in {"equals", "not_equals", "contains", "exists", "all"}:
        return "NOT_SATISFIED", "MISSING"
    if comparison == "SATISFIED":
        return comparison, None
    if operator == "contains":
        return comparison, "RELATION_MISMATCH"
    if operator == "none":
        return comparison, "UNEXPECTED"
    return comparison, "VALUE_MISMATCH"


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
        "ORDERED_COLLECTION": isinstance(value, list) or (
            isinstance(value, dict) and value.get("collection_kind") == "ORDERED_LIST"
            and isinstance(value.get("members"), list)
        ),
        "UNORDERED_COLLECTION": isinstance(value, list) or (
            isinstance(value, dict) and value.get("collection_kind") == "UNORDERED_SET"
            and isinstance(value.get("members"), list)
        ),
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


def _objective_semantic_fingerprint(revision: dict[str, Any]) -> str:
    projection = {
        key: revision[key]
        for key in (
            "objective_id", "project_id", "statement", "owner_authority_ref",
            "target_predicates", "completion_policy", "boundary_ref",
            "constitutional_constraints", "status",
        )
    }
    return "sha256:" + hashlib.sha256(
        canonical_json_bytes(_canonical_semantic(projection))
    ).hexdigest()


def _derived_value_type(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, str):
        return "STRING"
    if isinstance(value, list):
        return "ORDERED_COLLECTION"
    if isinstance(value, dict):
        if value.get("collection_kind") == "ORDERED_LIST":
            return "ORDERED_COLLECTION"
        if value.get("collection_kind") == "UNORDERED_SET":
            return "UNORDERED_COLLECTION"
        return "STRUCTURED"
    return "UNKNOWN"


def _normalize_objective_value(value: Any) -> tuple[Any, str]:
    # The contract declares a typed *scalar* wrapper for exactly the four types JSON's own
    # shape cannot express. An ordinary structured object is never unwrapped, so a Fact
    # carrying only an inner object cannot satisfy a full structured Target.
    reserved_types = {"DECIMAL", "TIMESTAMP", "DURATION", "IDENTITY_REFERENCE"}
    if (
        isinstance(value, dict)
        and set(value) == {"value_type", "value"}
        and value["value_type"] in reserved_types
    ):
        return value["value"], value["value_type"]
    return value, _derived_value_type(value)


def _project_collection_value(value: Any, value_type: str) -> Any:
    if value_type == "ORDERED_COLLECTION" and isinstance(value, list):
        return {
            "collection_kind": "ORDERED_LIST",
            "members": [_canonical_semantic(item) for item in value],
        }
    if value_type == "UNORDERED_COLLECTION" and isinstance(value, list):
        members = [_canonical_semantic(item) for item in value]
        return {
            "collection_kind": "UNORDERED_SET",
            "members": sorted(members, key=canonical_json_bytes),
        }
    return _canonical_semantic(value)


def _exact_value_equal(left: Any, right: Any) -> bool:
    return canonical_json_bytes(_canonical_semantic(left)) == canonical_json_bytes(
        _canonical_semantic(right)
    )


def _candidate_type_matches_target(value: Any, target: dict[str, Any]) -> bool:
    if target["operator"] == "exists":
        return True
    if target["operator"] == "contains":
        return _collection_members(value) is not None
    return _value_matches_declared_type(value, target["expected_value_type"])


def _latest_contiguous_evaluations(
    records: dict[str, dict[str, Any]], subject_key: str,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records.values():
        grouped.setdefault(record[subject_key], []).append(record)
    latest: dict[str, dict[str, Any]] = {}
    for subject_id, chain in grouped.items():
        chain.sort(key=lambda item: item["evaluation_revision"])
        if all(
            item["evaluation_revision"] == revision
            and item["previous_evaluation_id"]
            == (None if revision == 0 else chain[revision - 1]["evaluation_id"])
            for revision, item in enumerate(chain)
        ):
            latest[subject_id] = chain[-1]
    return latest


def _observation_id(observation: dict[str, Any]) -> str:
    """Recompute an Observation identity independently of the Observation package."""

    projection = {
        "project_id": observation["project_id"],
        "state_revision_observed": observation["state_revision_observed"],
        "state_fingerprint_observed": observation["state_fingerprint_observed"],
        "target_identity": observation["target"]["target_identity"],
        "scope_id": observation["scope_ref"]["id"],
        "method_ref": observation["method_ref"],
        "time_boundary": observation["time_boundary"],
        "source_snapshot_refs": observation["source_snapshot_refs"],
        "normalization_profile": observation["normalization_profile"],
    }
    domain = b"MANOSUBE_AGENT_CIVILIZATION_OS\x00OBSERVATION\x000.1\x00"
    digest = hashlib.sha256(domain + canonical_json_bytes(projection)).hexdigest().upper()
    return f"OBS-{digest}"


def _contiguous_evaluation_chains(
    records: dict[str, dict[str, Any]], subject_key: str,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records.values():
        grouped.setdefault(record[subject_key], []).append(record)
    chains: dict[str, list[dict[str, Any]]] = {}
    for subject_id, chain in grouped.items():
        chain.sort(key=lambda item: item["evaluation_revision"])
        if all(
            item["evaluation_revision"] == revision
            and item["previous_evaluation_id"]
            == (None if revision == 0 else chain[revision - 1]["evaluation_id"])
            for revision, item in enumerate(chain)
        ):
            chains[subject_id] = chain
    return chains


def _observation_scoped_evaluation(
    chain: list[dict[str, Any]],
    observation: dict[str, Any],
    bindings: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Return the Fact evaluation contemporaneous with *observation*.

    A Difference Record is immutable and binds one exact Observation. Under an append-only
    Observation lineage a re-observation appends a further evaluation bound to the next
    Observation; reading the globally latest evaluation would invalidate every earlier
    record the moment its subject is re-observed. Selection is by highest revision bound to
    this Observation, taken before any status is read, so a later re-evaluation of this
    same Observation still governs.
    """

    bound = [
        evaluation
        for evaluation in chain
        if any(
            (binding := bindings.get(str(reference.get("id")))) is not None
            and binding["observation_id"] == observation["observation_id"]
            for reference in evaluation["binding_refs"]
        )
    ]
    if not bound:
        return None
    return max(bound, key=lambda item: item["evaluation_revision"])


def _negative_knowledge_status(status: str) -> str:
    if status in {"NO_RESULT", "FAILED"}:
        return "UNKNOWN"
    if status == "INVALID":
        return "REJECT_OR_QUARANTINE"
    return status


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
    objective_revisions = _index(
        bundle.get("objective_revisions", []), "objective_revision_id", errors
    )
    # The chain rule is read from its owner, which the Engine's relational gate reads too.
    # This validator used to compute the same condition and spend it only on deciding
    # whether to *trust* an Objective head -- so a discontinuous history was never reported,
    # and what surfaced instead was an unrelated head mismatch further down.
    objective_groups: dict[str, list[dict[str, Any]]] = {}
    for revision in objective_revisions.values():
        objective_groups.setdefault(revision["objective_id"], []).append(revision)
    chain_errors, intact_objectives = objective_chain_errors(objective_revisions)
    errors.extend(chain_errors)
    active_objective_heads: dict[str, dict[str, Any]] = {}
    valid_objective_chains: dict[str, list[dict[str, Any]]] = {}
    for objective_id, chain in objective_groups.items():
        chain.sort(key=lambda item: item["revision"])
        if objective_id not in intact_objectives:
            continue
        valid_objective_chains[objective_id] = chain
        active_members = [item for item in chain if item["status"] == "ACTIVE"]
        if active_members:
            active_objective_heads[objective_id] = active_members[-1]
    observation_scopes = _index(
        bundle.get("observation_scopes", []), "scope_id", errors
    )
    normalized_facts = _index(
        bundle.get("normalized_facts", []), "fact_id", errors
    )
    for fact in normalized_facts.values():
        if fact["fact_id"] != _fact_id(fact):
            errors.append(f"Normalized Fact identity mismatch: {fact['fact_id']}")
    negative_observations = _index(
        bundle.get("negative_observations", []), "negative_observation_id", errors
    )
    negative_evaluations = _index(
        bundle.get("negative_observation_evaluations", []), "evaluation_id", errors
    )
    latest_negative_evaluations = _latest_contiguous_evaluations(
        negative_evaluations, "negative_observation_id"
    )
    fact_bindings = _index(
        bundle.get("fact_observation_bindings", []), "binding_id", errors
    )
    fact_evaluations = _index(
        bundle.get("fact_evaluations", []), "evaluation_id", errors
    )
    # A carried record's own references must resolve inside the bundle. Reading an
    # evaluation chain whose bindings are absent is not possible, so a partial lineage is
    # a defect regardless of which Difference cites it.
    for carried_evaluation in fact_evaluations.values():
        if carried_evaluation["fact_id"] not in normalized_facts:
            errors.append(
                "Fact evaluation references a missing Fact: "
                f"{carried_evaluation['evaluation_id']}"
            )
        for reference in carried_evaluation["binding_refs"]:
            carried_binding = fact_bindings.get(_ref_id(reference) or "")
            if reference.get("kind") != "fact_observation_binding" or carried_binding is None:
                errors.append(
                    "Fact evaluation references a missing binding: "
                    f"{carried_evaluation['evaluation_id']}"
                )
            elif carried_binding["fact_id"] != carried_evaluation["fact_id"]:
                errors.append(
                    f"cross-Fact evaluation binding: {carried_evaluation['evaluation_id']}"
                )
    for carried_binding in fact_bindings.values():
        if carried_binding["observation_id"] not in observations:
            errors.append(
                f"binding references a missing Observation: {carried_binding['binding_id']}"
            )
        if carried_binding["fact_id"] not in normalized_facts:
            errors.append(
                f"binding references a missing Fact: {carried_binding['binding_id']}"
            )
    for carried_observation in observations.values():
        for reference in carried_observation["normalized_fact_refs"]:
            if _ref_id(reference) not in normalized_facts:
                errors.append(
                    "Observation references a missing Normalized Fact: "
                    f"{carried_observation['observation_id']}"
                )
    fact_evaluation_chains = _contiguous_evaluation_chains(fact_evaluations, "fact_id")
    latest_fact_evaluations = _latest_contiguous_evaluations(
        fact_evaluations, "fact_id"
    )
    current_state_ref = bundle.get("current_state_ref")
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
    for negative in negative_observations.values():
        observed_at = datetime.fromisoformat(
            negative["time_boundary"]["source_snapshot_time"].replace(
                "Z", "+00:00"
            )
        )
        related_evidence = list(negative["negative_evidence_refs"])
        related_evidence.extend(
            reference
            for evaluation in negative_evaluations.values()
            if evaluation["negative_observation_id"]
            == negative["negative_observation_id"]
            for reference in evaluation["evidence_refs"]
        )
        for reference in related_evidence:
            key = canonical_json_bytes(reference)
            previous_time = evidence_observed_at.get(key)
            evidence_observed_at[key] = (
                observed_at
                if previous_time is None
                else min(previous_time, observed_at)
            )

    # Closure Policy semantic conformance and reopen-condition provenance are read from the
    # one owner the Engine's own gate reads. This block used to restate the required-Claim
    # rule here alone, which made it an auditor-only rule: the Engine emitted a forged
    # Policy and only this validator objected. The rules live in one place now, so the
    # producer cannot emit what the auditor rejects.
    for policy in policies.values():
        errors.extend(
            closure_policy_semantic_errors(policy, policy["closure_policy_id"])
        )
        errors.extend(reopen_condition_provenance_errors(policy, objective_revisions))

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
            # Blocker payload and Next Observation Request binding are decided by the
            # single shared lifecycle authority, so this validator and the Engine cannot
            # disagree about them.
            errors.extend(blocker_payload_errors(event, differences.get(difference_id)))
            errors.extend(
                next_observation_binding_errors(
                    event, differences.get(difference_id), requests, methods, _content_address
                )
            )
            errors.extend(
                closure_evaluation_binding_errors(
                    event,
                    chain[expected_revision - 1] if expected_revision > 0 else None,
                    differences.get(difference_id),
                    evaluations,
                    policies,
                    _policy_fingerprint,
                )
            )

            # A status-preserving OBSERVATION_BOUND event is a provenance append, not a
            # lifecycle transition, so it does not re-enter the terminal status and must
            # not demand a fresh Closure Evaluation. The TRANSITION that entered the
            # status owns that Evaluation.
            if (
                event["event_kind"] == "TRANSITION"
                and event["to_status"] in {"CLOSED", "BLOCKED", "RETAINED"}
            ):
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
                # Every rule that binds this event to its Closure Evaluation now lives in
                # the shared lifecycle authority. What remains here is the Reflow
                # commitment window, which belongs to a later element the Difference phase
                # does not implement and therefore never claims.
                if event["to_status"] == "CLOSED" and (
                    evaluation is None
                    or event["reflow_transition_ref"] != evaluation["reflow_transition_ref"]
                    or not reflow_valid
                ):
                    errors.append(f"closed reflow commitment mismatch: {event['difference_event_id']}")
            reconstructed[difference_id] = event["to_status"]

    for difference_id, difference in differences.items():
        target = difference["normalized_target_state"]
        observed = difference["normalized_observed_state"]
        structural = difference["structural_difference"]
        objective = objective_revisions.get(
            _ref_id(difference["objective_revision_ref"]) or ""
        )
        objective_predicate = next(
            (
                predicate for predicate in (objective or {}).get("target_predicates", [])
                if predicate["predicate_id"] == difference["target_predicate_ref"]["id"]
            ),
            None,
        )
        normalized_expected_value, normalized_expected_type = (
            _normalize_objective_value(objective_predicate["expected_value"])
            if objective_predicate is not None else (None, "UNKNOWN")
        )
        scope_binding = difference["objective_scope_binding"]
        resolved_scope = observation_scopes.get(_ref_id(scope_binding["scope_ref"]) or "")
        difference_scope_valid = (
            resolved_scope is not None
            and resolved_scope["schema_version"] == scope_binding["scope_schema_version"]
            and _resolved_scope_fingerprint(resolved_scope)
            == scope_binding["resolved_scope_record_sha256"]
            and resolved_scope["project_id"] == difference["project_id"]
            and resolved_scope["target_identity"] == difference["target_predicate_ref"]["id"]
            and difference["subject"] in resolved_scope["included_subjects"]
            and difference["subject"] not in resolved_scope["excluded_subjects"]
            and difference["effective_boundary"]["scope_ref"]
            == scope_binding["scope_ref"]
            and difference["effective_boundary"]["resolved_scope_record_sha256"]
            == scope_binding["resolved_scope_record_sha256"]
            and difference["effective_boundary"]["target_effective_window"]
            == resolved_scope["target_effective_window"]
        )
        target_projection_valid = (
            objective is not None
            and objective["project_id"] == difference["project_id"]
            and objective["status"] == "ACTIVE"
            and _objective_semantic_fingerprint(objective)
            == difference["objective_semantic_fingerprint"]
            and objective_predicate is not None
            and target == {
                "subject": objective_predicate["subject"],
                "operator": objective_predicate["operator"],
                "expected_value": normalized_expected_value,
                "expected_value_type": normalized_expected_type,
                "observation_scope": objective_predicate["observation_scope"],
                "evidence_requirement": objective_predicate["evidence_requirement"],
                "unknown_policy": objective_predicate["unknown_policy"],
                "criticality": objective_predicate["criticality"],
            }
        )
        observed_values = [item["value"] for item in observed["value_candidates"]["members"]]
        observed_types = [item["value_type"] for item in observed["value_candidates"]["members"]]
        source_observations = [
            observations.get(_ref_id(reference) or "")
            if reference.get("kind") == "observation" else None
            for reference in difference["observation_refs"]
        ]
        # A canonical Observation over a multi-subject Scope legitimately references
        # Facts this Target does not bind, and a Fact minted for another project must
        # never contribute. Selection is decided by the shared authority the Engine also
        # uses, so producer and auditor cannot disagree about the source set.
        source_facts = [
            fact
            for observation in source_observations if observation is not None
            for fact in contributing_facts(
                observation,
                normalized_facts,
                difference["subject"],
                difference["project_id"],
            )
        ]
        # The evaluation that justifies this Difference is the one contemporaneous with
        # the Observation it binds, not the globally latest revision: a later
        # re-observation appends an evaluation bound to the *next* Observation, and an
        # immutable record must remain revalidatable across its own lineage.
        source_fact_evaluations = [
            None
            if fact is None
            else next(
                (
                    evaluation
                    for observation in source_observations
                    if observation is not None
                    and (
                        evaluation := _observation_scoped_evaluation(
                            fact_evaluation_chains.get(fact["fact_id"], []),
                            observation,
                            fact_bindings,
                        )
                    )
                    is not None
                    and _evaluation_supports_observation(
                        evaluation, fact, observation, fact_bindings
                    )
                ),
                None,
            )
            for fact in source_facts
        ]
        source_facts_valid = bool(source_facts) and all(
            evaluation is not None
            and evaluation["evaluation_status"] in {"SUPPORTED", "CONFLICTED"}
            for evaluation in source_fact_evaluations
        )
        source_fact_knowledge = (
            "CONFLICTED"
            if any(
                evaluation is not None
                and evaluation["evaluation_status"] == "CONFLICTED"
                for evaluation in source_fact_evaluations
            )
            else "KNOWN"
        )
        source_negatives = [
            negative
            for observation in source_observations if observation is not None
            for negative in negative_observations.values()
            if negative["observation_id"] == observation["observation_id"]
            and negative["target_identity"] == difference["target_predicate_ref"]["id"]
            and negative["subject"] == difference["subject"]
        ]
        source_negatives_valid = bool(source_negatives) and all(
            (latest := latest_negative_evaluations.get(
                negative["negative_observation_id"]
            )) is not None
            and (revision_zero := next(
                (
                    evaluation for evaluation in negative_evaluations.values()
                    if evaluation["negative_observation_id"]
                    == negative["negative_observation_id"]
                    and evaluation["evaluation_revision"] == 0
                ),
                None,
            )) is not None
            and revision_zero["evaluation_status"] == negative["negative_status"]
            and {
                canonical_json_bytes(reference)
                for reference in revision_zero["conflict_fact_refs"]
            } == {
                canonical_json_bytes(reference)
                for reference in negative["positive_fact_refs"]
            }
            and observation is not None
            and negative["project_id"] == difference["project_id"]
            and negative["scope_ref"] == observation["scope_ref"]
            and negative["method_ref"] == observation["method_ref"]
            and negative["time_boundary"] == observation["time_boundary"]
            and negative["source_snapshot_refs"] == observation["source_snapshot_refs"]
            and negative["effective_boundary"]["kind"] == "SOURCE_SNAPSHOT"
            and negative["effective_boundary"]["identity"]
            in {reference["id"] for reference in observation["source_snapshot_refs"]}
            and negative["effective_boundary"]["start"] is None
            and negative["effective_boundary"]["end"] is None
            and _negative_knowledge_status(latest["evaluation_status"])
            == observed["knowledge_status"]
            and {
                canonical_json_bytes(reference)
                for reference in latest["evidence_refs"]
            } <= {
                canonical_json_bytes(reference)
                for reference in negative["negative_evidence_refs"]
            }
            and {
                canonical_json_bytes(reference)
                for reference in latest["evidence_refs"]
            } <= {
                canonical_json_bytes(reference)
                for reference in difference["observation_evidence_refs"]
            }
            and (
                latest["evaluation_status"] == "CONFLICTED"
                or not latest["conflict_fact_refs"]
            )
            for observation in source_observations if observation is not None
            for negative in source_negatives
            if negative["observation_id"] == observation["observation_id"]
        )
        source_evidence = {
            canonical_json_bytes(reference)
            for observation in source_observations if observation is not None
            for reference in observation["observation_evidence_refs"]
        }
        # Observation Evidence and bounded Negative Evidence are distinct provenance
        # channels with distinct reference kinds. The Difference binds the exact union of
        # both, so a negative-derived observed state keeps its own bounded proof instead
        # of being equated with the Evidence that the Observation itself ran.
        negative_evidence = {
            canonical_json_bytes(reference)
            for negative in source_negatives
            for reference in negative["negative_evidence_refs"]
        }
        required_evidence = source_evidence | negative_evidence
        source_observations_valid = bool(source_observations) and all(
            observation is not None
            and observation["project_id"] == difference["project_id"]
            and observation["state_revision_observed"] == difference["observed_state_revision"]
            and observation["state_fingerprint_observed"] == difference["observed_state_fingerprint"]
            and observation["target"]["target_identity"] == difference["target_predicate_ref"]["id"]
            and observation["scope_ref"] == difference["objective_scope_binding"]["scope_ref"]
            and observation["status"] in {
                "COMPLETE", "EMPTY", "UNKNOWN", "UNOBSERVED", "BLOCKED",
                "INCOMPLETE", "CONFLICTED",
            }
            and {
                "collection_kind": "UNORDERED_SET",
                "members": sorted(observation["source_snapshot_refs"], key=canonical_json_bytes),
            } == difference["effective_boundary"]["source_snapshot_refs"]
            for observation in source_observations
        )
        source_projection_valid = (
            source_observations_valid
            and (bool(source_facts) or bool(source_negatives))
            and (
                not source_facts
                or (
                    source_facts_valid
                    and observed["knowledge_status"] == source_fact_knowledge
                )
            )
            and (
                bool(source_facts)
                or (
                    not observed_values
                    and source_negatives_valid
                    and all(
                        negative["negative_evidence_refs"]
                        for negative in source_negatives
                        if negative["negative_status"] in {"ABSENT", "EMPTY"}
                    )
                )
            )
            and all(
                fact is not None
                and fact["project_id"] == difference["project_id"]
                and fact["subject"] == difference["subject"]
                for fact in source_facts
            )
            # Selection above already excludes non-contributing Facts; this restates the
            # binding the Difference claims, so a selector regression cannot pass silently.
            and sorted(
                (
                    _project_collection_value(fact["value"], fact["value_type"])
                    for fact in source_facts if fact is not None
                ),
                key=canonical_json_bytes,
            ) == sorted(observed_values, key=canonical_json_bytes)
            and sorted(
                fact["value_type"] for fact in source_facts if fact is not None
            ) == sorted(observed_types)
            and all(
                any(
                    fact is not None
                    and _exact_value_equal(
                        _project_collection_value(fact["value"], fact["value_type"]),
                        candidate["value"],
                    )
                    and fact["value_type"] == candidate["value_type"]
                    and fact["unit"] == candidate["unit"]
                    and fact["predicate"] == candidate["fact_predicate"]
                    # Every contract-legal Fact boundary form is accepted, matched
                    # against a Observation this Difference actually binds.
                    and any(
                        bound is not None and _fact_boundary_observed(fact, bound)
                        for bound in source_observations
                    )
                    for fact in source_facts
                )
                for candidate in observed["value_candidates"]["members"]
            )
            and required_evidence == {
                canonical_json_bytes(reference)
                for reference in difference["observation_evidence_refs"]
            }
        )
        derived_comparison, derived_mismatch = _derive_comparison_and_mismatch(
            observed, target
        )
        if (
            _has_recursive_set_duplicate(difference["normalized_target_state"])
            or _has_recursive_set_duplicate(difference["normalized_observed_state"])
            or _has_recursive_set_duplicate(difference["structural_difference"])
            or difference_id != _difference_id(difference)
            or not target_projection_valid
            or not difference_scope_valid
            or not source_projection_valid
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
            or structural["observed_values"]["members"] != observed_values
            or structural["observed_value_types"]["members"] != observed_types
            or structural["comparison_result"] != derived_comparison
            or derived_comparison == "SATISFIED"
            or structural["mismatch_kind"] != derived_mismatch
            or structural["target_cardinality"] is not None
            or structural["observed_cardinality"] is not None
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
        # Subject Difference, Policy binding, event head, Target Predicate, evaluated
        # Objective semantics and evaluated-State self-consistency are decided by the
        # shared authority the Engine also applies to every carried Evaluation.
        input_errors = closure_evaluation_input_errors(
            evaluation, difference, policies, events, _policy_fingerprint
        )
        errors.extend(input_errors)
        if difference is None:
            continue
        policy = policies.get(evaluation["policy_ref"]["id"])
        head = events.get(_ref_id(evaluation["difference_event_head_ref"]) or "")
        promotion_events = [
            event
            for event in events.values()
            if _ref_id(event["closure_evaluation_ref"])
            == evaluation["closure_evaluation_id"]
            and event["to_status"] in {"CLOSED", "BLOCKED", "RETAINED"}
        ]
        evaluated_objective = objective_revisions.get(
            _ref_id(evaluation["objective_revision_ref_evaluated"]) or ""
        )
        original_objective = objective_revisions.get(
            _ref_id(difference["objective_revision_ref"]) or ""
        )
        objective_chain = (
            [] if original_objective is None else
            valid_objective_chains.get(original_objective["objective_id"], [])
        )
        editorial_path = [
            revision for revision in objective_chain
            if original_objective is not None
            and revision["revision"] >= original_objective["revision"]
            and evaluated_objective is not None
            and revision["revision"] <= evaluated_objective["revision"]
        ]
        objective_evaluation_valid = (
            evaluated_objective is not None
            and original_objective is not None
            and evaluated_objective["objective_id"] == original_objective["objective_id"]
            and evaluated_objective["project_id"] == difference["project_id"]
            and evaluated_objective["status"] == "ACTIVE"
            and _objective_semantic_fingerprint(evaluated_objective)
            == difference["objective_semantic_fingerprint"]
            and active_objective_heads.get(evaluated_objective["objective_id"])
            is evaluated_objective
            and bool(editorial_path)
            and all(
                _objective_semantic_fingerprint(revision)
                == difference["objective_semantic_fingerprint"]
                for revision in editorial_path
            )
            and evaluation["objective_semantic_fingerprint_evaluated"]
            == difference["objective_semantic_fingerprint"]
        )
        # The multi-revision editorial Objective chain, and the current-State binding of an
        # Evaluation no transition has promoted, stay with this auditor: they need the
        # objective-chain analysis and bundle-wide State head the Difference phase does not
        # carry. Everything else is the shared rule above.
        if not objective_evaluation_valid or (
            not promotion_events
            and (
                evaluation["evaluated_state_revision"]
                != (current_state_ref or {}).get("revision")
                or evaluation["evaluated_state_fingerprint"]
                != (current_state_ref or {}).get("fingerprint")
            )
        ):
            errors.append(f"evaluation Objective or State head mismatch: {evaluation['closure_evaluation_id']}")
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
                    for reference in binding["evaluation_evidence_refs"]["members"]
                ]
                + [
                    reference
                    for binding in evaluation["candidate_claim_evaluation_bindings"]
                    for reference in binding["evaluation_evidence_refs"]["members"]
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
                or (
                    {
                        **(difference or {}).get("objective_scope_binding", {}).get(
                            "scope_ref", {}
                        ),
                        "schema_version": (difference or {}).get(
                            "objective_scope_binding", {}
                        ).get("scope_schema_version"),
                        "resolved_record_sha256": (difference or {}).get(
                            "objective_scope_binding", {}
                        ).get("resolved_scope_record_sha256"),
                    }
                    if difference is not None else None
                )
            )
            scope_reference = None if required_scope_ref is None else {
                "kind": required_scope_ref["kind"], "id": required_scope_ref["id"],
            }
            required_scope = observation_scopes.get(
                "" if required_scope_ref is None else required_scope_ref["id"]
            )
            scope_binding_valid = (
                required_scope_ref is not None
                and required_scope is not None
                and required_scope["schema_version"] == required_scope_ref["schema_version"]
                and _resolved_scope_fingerprint(required_scope)
                == required_scope_ref["resolved_record_sha256"]
                and required_scope["scope_status"] == "COMPLETE"
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
            resolved_negative_sets = [
                [
                    negative
                    for negative in negative_observations.values()
                    if observation is not None
                    and negative["observation_id"] == observation["observation_id"]
                    and negative["target_identity"]
                    == difference["target_predicate_ref"]["id"]
                    and negative["subject"] == difference["subject"]
                ]
                for observation in after_observations
            ]
            # The contiguous-chain and latest-evaluation projections are already built
            # once above, from the same records; this section reuses them instead of
            # shadowing them with a second, identical derivation.
            positive_facts_valid = [
                bool(facts)
                and all(
                    fact is not None
                    and difference is not None
                    and fact["project_id"] == difference["project_id"]
                    and fact["subject"] == difference["subject"]
                    and _fact_boundary_observed(fact, observation)
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
                    [
                        _project_collection_value(fact["value"], fact["value_type"])
                        for fact in facts if fact is not None
                    ],
                    difference["normalized_target_state"],
                )
                for observation, facts in zip(
                    after_observations, resolved_fact_sets, strict=True
                )
            ]
            bounded_empty_valid = [
                difference is not None
                and required_scope is not None
                and required_scope["scope_status"] == "COMPLETE"
                and _observation_attempts_complete(observation, required_scope)
                and difference["normalized_target_state"]["operator"] == "none"
                and not facts
                and bool(negatives)
                and all(
                    (latest := latest_negative_evaluations.get(
                        negative["negative_observation_id"]
                    )) is not None
                    and (revision_zero := next(
                        (
                            item
                            for item in negative_evaluations.values()
                            if item["negative_observation_id"]
                            == negative["negative_observation_id"]
                            and item["evaluation_revision"] == 0
                        ),
                        None,
                    )) is not None
                    and revision_zero["evaluation_status"]
                    == negative["negative_status"]
                    and {
                        canonical_json_bytes(reference)
                        for reference in revision_zero["conflict_fact_refs"]
                    } == {
                        canonical_json_bytes(reference)
                        for reference in negative["positive_fact_refs"]
                    }
                    and latest["evaluation_status"] == "EMPTY"
                    and negative["negative_status"] == "EMPTY"
                    and observation is not None
                    and negative["project_id"] == difference["project_id"]
                    and negative["scope_ref"] == observation["scope_ref"]
                    and negative["method_ref"] == observation["method_ref"]
                    and negative["time_boundary"] == observation["time_boundary"]
                    and negative["source_snapshot_refs"]
                    == observation["source_snapshot_refs"]
                    and {
                        canonical_json_bytes(reference)
                        for reference in negative["attempt_refs"]
                    } == {
                        canonical_json_bytes(
                            {
                                "kind": "observation_attempt",
                                "id": attempt["attempt_id"],
                            }
                        )
                        for attempt in observation["attempts"]
                    }
                    and 0 < len(observation["attempts"])
                    <= required_scope["attempt_policy"]["max_attempts"]
                    and all(
                        attempt["method_ref"] == observation["method_ref"]
                        and attempt["result"] in {"COMPLETE", "EMPTY"}
                        and attempt["failure_class"] is None
                        and datetime.fromisoformat(
                            attempt["started_at"].replace("Z", "+00:00")
                        )
                        >= datetime.fromisoformat(
                            observation["time_boundary"][
                                "observation_started_at"
                            ].replace("Z", "+00:00")
                        )
                        and datetime.fromisoformat(
                            attempt["ended_at"].replace("Z", "+00:00")
                        )
                        >= datetime.fromisoformat(
                            attempt["started_at"].replace("Z", "+00:00")
                        )
                        and datetime.fromisoformat(
                            attempt["ended_at"].replace("Z", "+00:00")
                        )
                        <= datetime.fromisoformat(
                            observation["time_boundary"][
                                "observation_ended_at"
                            ].replace("Z", "+00:00")
                        )
                        and (
                            datetime.fromisoformat(
                                attempt["ended_at"].replace("Z", "+00:00")
                            )
                            - datetime.fromisoformat(
                                attempt["started_at"].replace("Z", "+00:00")
                            )
                        ).total_seconds()
                        <= required_scope["attempt_policy"]["timeout_seconds"]
                        for attempt in observation["attempts"]
                    )
                    and negative["effective_boundary"]["kind"]
                    == "SOURCE_SNAPSHOT"
                    and negative["effective_boundary"]["identity"]
                    in {
                        reference["id"]
                        for reference in observation["source_snapshot_refs"]
                    }
                    and negative["effective_boundary"]["start"] is None
                    and negative["effective_boundary"]["end"] is None
                    and all(negative["completion_evaluation"].values())
                    and negative["completion_evaluation"].get(
                        "collection_defined"
                    ) is True
                    and negative["completion_evaluation"].get(
                        "enumeration_complete"
                    ) is True
                    and negative["completion_evaluation"].get(
                        "zero_valid_members"
                    ) is True
                    and {
                        canonical_json_bytes(reference)
                        for reference in latest["evidence_refs"]
                    } <= resolution_evidence
                    and bool(latest["evidence_refs"])
                    and bool(negative["negative_evidence_refs"])
                    and {
                        canonical_json_bytes(reference)
                        for reference in negative["negative_evidence_refs"]
                    } <= resolution_evidence
                    for negative in negatives
                )
                and _target_satisfied(
                    [], difference["normalized_target_state"]
                )
                for observation, facts, negatives in zip(
                    after_observations,
                    resolved_fact_sets,
                    resolved_negative_sets,
                    strict=True,
                )
            ]
            facts_valid = all(
                positive or empty
                for positive, empty in zip(
                    positive_facts_valid, bounded_empty_valid, strict=True
                )
            )
            bounded_empty_closure = bool(bounded_empty_valid) and all(
                bounded_empty_valid
            )
            candidate_value = (
                None if candidate is None or difference is None else
                _subject_value(candidate["semantic_state"], difference["subject"])
            )
            candidate_projected_value = (
                None
                if difference is None
                else (
                    candidate_value
                    if difference["normalized_target_state"]["operator"] == "contains"
                    else _project_collection_value(
                        candidate_value,
                        difference["normalized_target_state"]["expected_value_type"],
                    )
                )
            )
            candidate_target_valid = (
                candidate is not None
                and difference is not None
                and (
                    (
                        bounded_empty_closure
                        and _is_empty_collection(candidate_value)
                        and _target_satisfied(
                            [candidate_value],
                            difference["normalized_target_state"],
                        )
                    )
                    or (
                        _candidate_type_matches_target(
                            candidate_value,
                            difference["normalized_target_state"],
                        )
                        and _target_satisfied(
                            [candidate_projected_value],
                            difference["normalized_target_state"],
                        )
                    )
                )
                and all(
                    fact is not None
                    and _exact_value_equal(
                        _project_collection_value(fact["value"], fact["value_type"]),
                        _project_collection_value(candidate_value, fact["value_type"]),
                    )
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
                and (
                    (
                        positive_facts_valid[index]
                        and observation["status"] == "COMPLETE"
                    )
                    or (
                        bounded_empty_valid[index]
                        and observation["status"] == "EMPTY"
                    )
                )
                and observation["blind_spots"]["status"] == "NONE_KNOWN"
                and _observation_attempts_complete(
                    observation, required_scope
                )
                and (
                    bool(observation["normalized_fact_refs"])
                    or bounded_empty_valid[index]
                )
                and {
                    "collection_kind": "UNORDERED_SET",
                    "members": sorted(
                        observation["source_snapshot_refs"], key=canonical_json_bytes
                    ),
                } == candidate_snapshot_set
                and candidate_snapshot_set
                == {
                    "collection_kind": "UNORDERED_SET",
                    "members": sorted(
                        required_scope["source_snapshot_refs"],
                        key=canonical_json_bytes,
                    ),
                }
                and bool(observation["observation_evidence_refs"])
                and all(
                    canonical_json_bytes(reference) in resolution_evidence
                    for reference in observation["observation_evidence_refs"]
                )
                for index, observation in enumerate(after_observations)
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
            resolved_changes = [
                changes.get(_ref_id(reference) or "")
                for reference in evaluation["change_refs"]
            ]
            candidate_change_refs = (
                None if candidate is None else candidate["producing_change_refs"]
            )
            change_binding_valid = (
                bool(resolved_changes)
                and candidate_change_refs
                == {
                    "collection_kind": "UNORDERED_SET",
                    "members": sorted(
                        evaluation["change_refs"], key=canonical_json_bytes
                    ),
                }
                and all(
                    change is not None
                    and change.get("status") == "EXECUTED"
                    and _ref_id(change.get("difference_ref"))
                    == evaluation["difference_id"]
                    and change.get("base_state_ref")
                    == evaluation["before_state_ref"]
                    and change.get("before_kernel_source_ref")
                    == evaluation["base_kernel_source_ref_evaluated"]
                    and change.get("after_kernel_source_ref")
                    == evaluation["kernel_source_ref_evaluated"]
                    for change in resolved_changes
                )
            )
            kernel_source_binding_valid = (
                (
                    resolution_mode == "CHANGE_FREE"
                    and candidate is not None
                    and evaluation["base_kernel_source_ref_evaluated"]
                    == candidate["kernel_source_ref"]
                )
                or (
                    resolution_mode == "CHANGE_BOUND"
                    and change_binding_valid
                )
            )
            mode_evidence_present = (
                resolution_mode == "CHANGE_BOUND"
                and change_binding_valid
                and bool(evaluation["change_result_evidence_refs"])
                and not evaluation["change_free_verification_evidence_refs"]
            ) or (
                resolution_mode == "CHANGE_FREE"
                and not evaluation["change_refs"]
                and not evaluation["change_result_evidence_refs"]
                and bool(evaluation["change_free_verification_evidence_refs"])
            )
            if (
                not common_evidence_present
                or not mode_evidence_present
                or not kernel_source_binding_valid
            ):
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

    # The typed reference-edge authority is shared with the Engine, so the producer and
    # this auditor cannot hold two drifting maps of what a reference is or where it must
    # resolve. Every record of every section is traversed, not only the Difference lineage.
    errors.extend(reference_closure_errors(bundle))
    errors.extend(satisfaction_reconciliation_errors(bundle))
    # Bounded Negative Evidence ownership is owned by the Observation element; this
    # auditor imports that one rule rather than restating it.
    errors.extend(
        negative_evaluation_evidence_errors(
            {
                "negative_observations": bundle.get("negative_observations", []) or [],
                "negative_evaluations": bundle.get("negative_observation_evaluations", [])
                or [],
                "observations": bundle.get("observations", []) or [],
            }
        )
    )
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
    """Validate every valid bundle in *root* against its own invalid mutation cases.

    ``valid/<stem>.json`` is paired with ``invalid/<stem with "bundle" replaced by
    "cases">.json``, so ``valid/bundle.json`` keeps its original ``invalid/cases.json``
    pairing while each additional canonical route carries its own mutation suite.
    """

    valid_count = 0
    invalid_count = 0
    valid_errors: list[str] = []
    invalid_escapes: list[str] = []
    for bundle_path in sorted((root / "valid").glob("*.json")):
        cases_path = root / "invalid" / f"{bundle_path.stem.replace('bundle', 'cases')}.json"
        valid_bundle = load_json(bundle_path)
        valid_count += 1
        valid_errors.extend(
            f"{bundle_path.stem}: {error}" for error in validate_bundle(valid_bundle)
        )
        if not cases_path.exists():
            valid_errors.append(f"{bundle_path.stem}: missing invalid mutation cases")
            continue
        cases = load_json(cases_path)
        invalid_count += len(cases)
        invalid_escapes.extend(
            f"{bundle_path.stem}: {case['name']}"
            for case in cases
            if not validate_bundle(apply_mutation(valid_bundle, case["path"], case["value"]))
        )
    return valid_count, invalid_count, valid_errors, invalid_escapes
