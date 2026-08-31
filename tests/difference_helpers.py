"""Shared canonical fixtures for the deterministic Difference Engine tests.

Every Observation input is produced by the real Observation Engine, and every State
fingerprint by the real State owner. No hand-built substitute for either owner exists
in this module.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.state import fingerprint_semantic_state

PROJECT_ID = "PRJ-0001"
PREDICATE_ID = "TP-0001"
SCOPE_ID = "OBS-SCOPE-0001"
STATE_REVISION = 2
SNAPSHOT_REF = {"kind": "source_snapshot", "id": "SNAP-0001"}
METHOD_REF = {"kind": "observation_method", "id": "OBS-METHOD-0001"}
EVIDENCE_REF = {"kind": "observation_evidence", "id": "EVID-0001"}
NEGATIVE_EVIDENCE_REF = {"kind": "negative_evidence", "id": "NEG-EVID-0001"}
SUBJECT = "kernel.state"

OBSERVATION_METHOD: dict[str, Any] = {
    "method_profile": "MANOSUBE-OBSERVATION-METHOD-SHA256-0.1",
    "procedure_kind": "CANONICAL_OBSERVER",
    "procedure_ref": {
        "kind": "observer_procedure",
        "id": "OBS-PROCEDURE-0001",
        "version": "0.1",
        "semantic_fingerprint": "sha256:" + "f" * 64,
    },
    "normalization_profile": "FIXTURE-0.1",
    "input_contract_ref": {"kind": "schema", "id": "OBS-INPUT-01"},
    "output_contract_refs": {
        "collection_kind": "UNORDERED_SET",
        "members": [{"kind": "schema", "id": "NORMALIZED-FACT-01"}],
    },
    "execution_boundary_ref": {"kind": "execution_boundary", "id": "KERNEL-LOCAL"},
}


def semantic_state(status: str = "UNKNOWN") -> dict[str, Any]:
    """Return a schema-valid canonical Semantic State document."""

    domain = {
        "status": status,
        "claims": {},
        "identity_refs": [],
        "evidence_refs": [],
        "blind_spots": ["not evaluated"],
    }
    return {
        "schema_version": "0.1",
        **{
            key: deepcopy(domain)
            for key in (
                "project", "objective", "repository", "requirements", "code", "tests",
                "runtime", "infrastructure", "deployment", "authority", "lineage",
            )
        },
        "open_differences": [],
        "active_changes": [],
        "evidence": [],
    }


def state_fingerprint(status: str = "UNKNOWN") -> dict[str, Any]:
    """Return the real State owner's semantic fingerprint of the canonical State."""

    return fingerprint_semantic_state(semantic_state(status)).as_dict()


def target_predicate(
    subject: str = SUBJECT,
    operator: str = "equals",
    expected_value: Any = "READY",
    predicate_id: str = PREDICATE_ID,
    observation_scope: str = "kernel",
) -> dict[str, Any]:
    return {
        "predicate_id": predicate_id,
        "subject": subject,
        "operator": operator,
        "expected_value": expected_value,
        "observation_scope": observation_scope,
        "evidence_requirement": "E1",
        "unknown_policy": "INCOMPLETE",
        "criticality": "mandatory",
    }


def objective_revision(
    predicates: list[dict[str, Any]] | None = None,
    statement: str = "The kernel reaches the READY state.",
    change_reason: str = "initial objective",
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "objective_id": "OBJ-0001",
        "objective_revision_id": "OBJ-REV-0001",
        "project_id": PROJECT_ID,
        "statement": statement,
        "owner_authority_ref": {"kind": "human_authority", "id": "AUTH-0001"},
        "target_predicates": deepcopy(predicates) if predicates else [target_predicate()],
        "completion_policy": {"mode": "ALL", "contradiction_policy": "BLOCK"},
        "boundary_ref": {"kind": "objective_boundary", "id": "BOUND-0001"},
        "constitutional_constraints": [],
        "status": "ACTIVE",
        "revision": 0,
        "previous_objective_ref": None,
        "change_reason": change_reason,
        "base_semantic_fingerprint": None,
        "semantic_change_summary": "initial objective revision",
        "human_authority_ref": {"kind": "human_authority", "id": "AUTH-0001"},
        "recorded_at": "2026-08-30T08:00:00Z",
    }


def observation_scope(
    included: list[str] | None = None,
    scope_id: str = SCOPE_ID,
    target_identity: str = PREDICATE_ID,
    snapshot_refs: list[dict[str, str]] | None = None,
    scope_status: str = "COMPLETE",
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "scope_id": scope_id,
        "project_id": PROJECT_ID,
        "target_identity": target_identity,
        "included_subjects": list(included) if included else [SUBJECT],
        "excluded_subjects": ["kernel.secret"],
        "boundary_root": "/kernel",
        "path_policy": {
            "relative_locators_only": True,
            "symlink_escape": "BLOCK",
            "submodule_traversal": "DECLARED_ONLY",
            "mount_escape": "BLOCK",
            "credential_paths": "EXCLUDE",
        },
        "observation_window": {"start": "2026-08-30T09:00:00Z", "end": "2026-08-30T09:01:00Z"},
        "target_effective_window": {
            "start": "2026-08-30T08:00:00Z",
            "end": "2026-08-30T09:00:00Z",
        },
        "freshness_limit_seconds": 300,
        "cutoff": "2026-08-30T09:00:00Z",
        "source_snapshot_refs": deepcopy(snapshot_refs) if snapshot_refs else [deepcopy(SNAPSHOT_REF)],
        "enumeration_rule": {"kind": "enumeration_rule", "id": "ENUM-0001"},
        "completion_predicate": {"kind": "completion_predicate", "id": "COMPLETE-0001"},
        "method_ref": deepcopy(METHOD_REF),
        "attempt_policy": {"max_attempts": 1, "timeout_seconds": 60, "retry_on": []},
        "blind_spots": [],
        "scope_status": scope_status,
    }


def observation_request(
    scope: dict[str, Any],
    facts: list[dict[str, Any]],
    fingerprint: dict[str, Any],
    state_revision: int = STATE_REVISION,
    negative_claims: list[dict[str, Any]] | None = None,
    collection_complete: bool = True,
) -> dict[str, Any]:
    return {
        "project_id": PROJECT_ID,
        "state_revision_observed": state_revision,
        "state_fingerprint_observed": deepcopy(fingerprint),
        "target_identity": scope["target_identity"],
        "target_kind": "FIXTURE",
        "scope": deepcopy(scope),
        "method_ref": deepcopy(scope["method_ref"]),
        "time_boundary": {
            "observation_started_at": "2026-08-30T09:00:00Z",
            "observation_ended_at": "2026-08-30T09:01:00Z",
            "target_effective_start": "2026-08-30T08:00:00Z",
            "target_effective_end": "2026-08-30T09:00:00Z",
            "source_snapshot_time": "2026-08-30T08:59:00Z",
        },
        "source_snapshot_refs": deepcopy(scope["source_snapshot_refs"]),
        "normalization_profile": "FIXTURE-0.1",
        "source_occurrences": [
            {
                "source_ref": deepcopy(scope["source_snapshot_refs"][0]),
                "source_locator": "kernel/state.json",
                "facts": deepcopy(facts),
            }
        ],
        "attempts": [
            {
                "attempt_id": "ATTEMPT-0001",
                "method_ref": deepcopy(scope["method_ref"]),
                "started_at": "2026-08-30T09:00:00Z",
                "ended_at": "2026-08-30T09:01:00Z",
                "result": "COMPLETE" if facts else "EMPTY",
                "failure_class": None,
            }
        ],
        "blind_spots": [],
        "observation_evidence_refs": [deepcopy(EVIDENCE_REF)],
        "negative_evidence_refs": [deepcopy(NEGATIVE_EVIDENCE_REF)],
        "negative_claims": deepcopy(negative_claims) if negative_claims else [],
        "collection_complete": collection_complete,
    }


def raw_fact(
    subject: str = SUBJECT,
    predicate: str = "equals@v1",
    value: Any = "NOT-READY",
    value_type: str = "STRING",
    snapshot_id: str = "SNAP-0001",
) -> dict[str, Any]:
    return {
        "subject": subject,
        "predicate": predicate,
        "value": value,
        "value_type": value_type,
        "unit": None,
        "effective_boundary": {
            "kind": "SOURCE_SNAPSHOT",
            "identity": snapshot_id,
            "start": None,
            "end": None,
        },
    }


def observed_bundle(
    scope: dict[str, Any],
    facts: list[dict[str, Any]],
    fingerprint: dict[str, Any],
    state_revision: int = STATE_REVISION,
    negative_claims: list[dict[str, Any]] | None = None,
    collection_complete: bool = True,
) -> dict[str, Any]:
    """Run the real Observation Engine and return its canonical bundle."""

    return observe(
        observation_request(
            scope, facts, fingerprint, state_revision, negative_claims, collection_complete
        )
    )


def derivation_request(
    objective: dict[str, Any],
    bindings: list[dict[str, Any]],
    fingerprint: dict[str, Any],
    state_revision: int = STATE_REVISION,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "identity_profile": "MANOSUBE-DIFFERENCE-SHA256-0.1",
        "comparison_profile": "MANOSUBE-DIFFERENCE-COMPARISON-0.1",
        "normalization_profile": "MANOSUBE-DIFFERENCE-NORMALIZATION-0.1",
        "project_id": PROJECT_ID,
        "objective_revision": deepcopy(objective),
        "state_revision": state_revision,
        "state_fingerprint": deepcopy(fingerprint),
        "closure_policy_requirements": {"minimum_evidence_level": "E1"},
        "observation_method": deepcopy(OBSERVATION_METHOD),
        "bindings": deepcopy(bindings),
    }


def single_binding_request(
    value: Any = "NOT-READY",
    value_type: str = "STRING",
    expected_value: Any = "READY",
    operator: str = "equals",
    status: str = "UNKNOWN",
) -> dict[str, Any]:
    """Build the canonical one-predicate derivation request via the real owners."""

    fingerprint = state_fingerprint(status)
    scope = observation_scope()
    bundle = observed_bundle(scope, [raw_fact(value=value, value_type=value_type)], fingerprint)
    objective = objective_revision(
        [target_predicate(operator=operator, expected_value=expected_value)]
    )
    return derivation_request(
        objective,
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )
