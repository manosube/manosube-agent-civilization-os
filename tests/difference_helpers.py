"""Shared canonical fixtures for the deterministic Difference Engine tests.

Every Observation input is produced by the real Observation Engine, and every State
fingerprint by the real State owner. No hand-built substitute for either owner exists
in this module.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.state import fingerprint_semantic_state

ROOT = Path(__file__).resolve().parents[1]
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
    prior_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request: dict[str, Any] = {
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
    if prior_bundle is not None:
        request["prior_bundle"] = deepcopy(prior_bundle)
    return request


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


def negative_claim(
    negative_status: str = "ABSENT",
    subject: str = SUBJECT,
    predicate: str = "equals@v1",
    snapshot_id: str = "SNAP-0001",
) -> dict[str, Any]:
    """Return a bounded Negative Observation claim for the pure-negative route."""

    return {
        "subject": subject,
        "predicate": predicate,
        "negative_status": negative_status,
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
    prior_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the real Observation Engine and return its canonical bundle.

    Passing *prior_bundle* continues the real append-only Observation lineage, which is
    what an equivalent re-observation of the same subject actually does.
    """

    return observe(
        observation_request(
            scope,
            facts,
            fingerprint,
            state_revision,
            negative_claims,
            collection_complete,
            prior_bundle,
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


def binding_request(
    facts: list[dict[str, Any]],
    predicate: dict[str, Any] | None = None,
    negative_claims: list[dict[str, Any]] | None = None,
    status: str = "UNKNOWN",
) -> dict[str, Any]:
    """Build a one-predicate derivation request over the real upstream owners."""

    fingerprint = state_fingerprint(status)
    scope = observation_scope()
    bundle = observed_bundle(scope, facts, fingerprint, negative_claims=negative_claims)
    objective = objective_revision([predicate or target_predicate()])
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


def reobservation_pair(
    facts: list[dict[str, Any]] | None = None,
    later_facts: list[dict[str, Any]] | None = None,
    later_state_revision: int = 7,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a baseline request and a real append-only re-observation of the same subject.

    The second Observation continues the first through the real Observation Engine, so the
    returned bundle carries the whole append-only lineage rather than an independent
    second Observation that would collide with it.
    """

    observed = facts if facts is not None else [raw_fact()]
    later = later_facts if later_facts is not None else observed
    first_fingerprint = state_fingerprint()
    later_fingerprint = state_fingerprint("KNOWN")
    scope = observation_scope()
    first_bundle = observed_bundle(scope, observed, first_fingerprint)
    later_bundle = observed_bundle(
        scope,
        later,
        later_fingerprint,
        state_revision=later_state_revision,
        prior_bundle=first_bundle,
    )
    objective = objective_revision()
    baseline = derivation_request(
        objective,
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": first_bundle,
            }
        ],
        first_fingerprint,
    )
    later_request = derivation_request(
        objective,
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": later_bundle,
            }
        ],
        later_fingerprint,
        later_state_revision,
    )
    return baseline, later_request


#: The contract-legal path from OPEN to each status a predecessor may already hold.
LEGAL_PATH_FROM_OPEN: dict[str, list[str]] = {
    "OPEN": [],
    "ACTIVE": ["ACTIVE"],
    "VERIFYING": ["ACTIVE", "VERIFYING"],
    "BLOCKED": ["BLOCKED"],
    "RETAINED": ["RETAINED"],
    "CLOSED": ["ACTIVE", "VERIFYING", "CLOSED"],
    "REOPENED": ["ACTIVE", "VERIFYING", "CLOSED", "REOPENED"],
}
_TERMINAL_REASON = {
    "BLOCKED": "OBSERVATION_PATH_BLOCKED",
    "RETAINED": "UNRESOLVED_CARRIED_FORWARD",
    "REOPENED": "CLOSURE_CONTRADICTED",
}


def _content_addressed_request(
    difference: dict[str, Any],
    event: dict[str, Any],
    method_id: str,
    reason_code: str,
) -> dict[str, Any]:
    from scripts.difference_contract_validator import _content_address

    request = {
        "schema_version": "0.1",
        "observation_request_id": "",
        "record_kind": "NEXT_OBSERVATION_REQUEST",
        "difference_ref": {"kind": "difference", "id": difference["difference_id"]},
        "derived_from_event_ref": {
            "kind": "difference_event",
            "id": event["difference_event_id"],
        },
        "state_revision_requested": event["state_revision_evaluated"],
        "state_fingerprint_requested": deepcopy(event["state_fingerprint_evaluated"]),
        "target_ref": {"kind": "target_predicate", "id": difference["target_predicate_ref"]["id"]},
        "scope_ref": {
            "kind": "observation_scope",
            "id": difference["objective_scope_binding"]["scope_ref"]["id"],
        },
        "method_ref": {"kind": "observation_method", "id": method_id},
        "reason_code": reason_code,
    }
    request["observation_request_id"] = _content_address(
        "OBS-REQ-", request, "observation_request_id"
    )
    return request


def retained_status_predecessor(
    status: str, reason_code: str = "BLOCKER_REOBSERVATION"
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a baseline bundle and a re-observation request whose predecessor is *status*.

    Statuses beyond ``OPEN`` are produced by later canonical owners, so the predecessor's
    terminal transition and its Closure Evaluation are supplied by the caller here, exactly
    as the Difference Engine would receive them. The Engine never creates them.
    """

    from manosube_agent_civilization.difference import derive_differences
    from manosube_agent_civilization.difference.identity import lifecycle_event_id

    fixture = json.loads(
        (
            ROOT / "tests" / "contract" / "fixtures" / "difference" / "valid" / "bundle.json"
        ).read_text(encoding="utf-8")
    )
    method = deepcopy(fixture["observation_methods"][0])

    baseline_request, later_request = reobservation_pair()
    baseline = derive_differences(baseline_request)
    difference = baseline["differences"][0]
    difference_id = difference["difference_id"]
    head = sorted(baseline["events"], key=lambda item: item["event_revision"])[-1]

    # OPEN cannot reach every status directly; walk the contract's own legal path.
    path = LEGAL_PATH_FROM_OPEN[status]
    upstream: list[dict[str, Any]] = []
    for target in path:
        previous = upstream[-1] if upstream else head
        event = deepcopy(previous)
        event.update(
            {
                "event_kind": "TRANSITION",
                "event_revision": previous["event_revision"] + 1,
                "previous_event_id": previous["difference_event_id"],
                "from_status": previous["to_status"],
                "to_status": target,
                "reason_code": _TERMINAL_REASON.get(target, "UPSTREAM_OWNER_TRANSITION"),
                "reason": "",
                "observation_refs": [],
                "evidence_refs": [{"kind": "observation_evidence", "id": "EVID-TERMINAL-0001"}],
                "blocker_kind": None,
                "blocker_scope": None,
                "blocker_resolution_condition": None,
                "next_observation_ref": None,
                "reflow_transition_ref": None,
                "closure_evaluation_ref": None,
                "reopen_trigger": None,
            }
        )
        if target == "CLOSED":
            event["reflow_transition_ref"] = {
                "kind": "reflow_transition",
                "id": "REFLOW-TX-0001",
            }
        event["difference_event_id"] = lifecycle_event_id(event)
        upstream.append(event)
    terminal = upstream[-1] if upstream else deepcopy(head)

    request = _content_addressed_request(
        difference, terminal, method["observation_method_id"], reason_code
    )
    reference = {"kind": "next_observation_request", "id": request["observation_request_id"]}
    subject_ref = {"kind": "difference", "id": difference_id}
    if status in {"BLOCKED", "RETAINED", "REOPENED"}:
        terminal["next_observation_ref"] = deepcopy(reference)
    if status == "BLOCKED":
        terminal.update(
            {
                "blocker_kind": "OBSERVATION_PATH",
                "blocker_scope": {
                    "kind": "difference_blocker_scope",
                    "effective_boundary": deepcopy(difference["effective_boundary"]),
                    "affected_subject_refs": {
                        "collection_kind": "UNORDERED_SET",
                        "members": [deepcopy(subject_ref)],
                    },
                    "blocked_stage": "OBSERVATION",
                },
                "blocker_resolution_condition": {
                    "kind": "blocker_resolution_condition",
                    "condition_code": "OBSERVATION_PATH_AVAILABLE",
                    "subject_ref": deepcopy(subject_ref),
                    "expected_state": "AVAILABLE",
                    "verification_request_ref": deepcopy(reference),
                },
            }
        )

    evaluation = deepcopy(fixture["evaluations"][0])
    evaluation.update(
        {
            "difference_id": difference_id,
            "difference_event_head_ref": {
                "kind": "difference_event",
                "id": head["difference_event_id"],
            },
            "target_predicate_ref": deepcopy(difference["target_predicate_ref"]),
            "objective_revision_ref_evaluated": deepcopy(difference["objective_revision_ref"]),
            "objective_semantic_fingerprint_evaluated": difference[
                "objective_semantic_fingerprint"
            ],
            "before_state_ref": {
                "kind": "state",
                "revision": difference["observed_state_revision"],
                "fingerprint": deepcopy(difference["observed_state_fingerprint"]),
            },
            "evaluated_state_revision": difference["observed_state_revision"],
            "evaluated_state_fingerprint": deepcopy(difference["observed_state_fingerprint"]),
            "policy_ref": deepcopy(difference["closure_policy"]),
            "proposed_terminal_status": status,
            "result": status,
        }
    )
    if status in {"BLOCKED", "RETAINED", "CLOSED", "REOPENED"}:
        terminal["closure_evaluation_ref"] = {
            "kind": "closure_evaluation",
            "id": evaluation["closure_evaluation_id"],
        }
    if status == "OPEN":
        upstream = []
        terminal = head
    if status == "REOPENED":
        terminal["reopen_trigger"] = "OBSERVATION_CONTRADICTION"
        terminal["observation_refs"] = deepcopy(baseline["differences"][0]["observation_refs"])
        for event in upstream[:-1]:
            event["closure_evaluation_ref"] = deepcopy(terminal["closure_evaluation_ref"])
            event["difference_event_id"] = lifecycle_event_id(event)


    previous = head
    for event in upstream:
        event["previous_event_id"] = previous["difference_event_id"]
        event["difference_event_id"] = lifecycle_event_id(event)
        previous = event
    if upstream:
        request = _content_addressed_request(
            difference, upstream[-1], method["observation_method_id"], reason_code
        )
        reference = {"kind": "next_observation_request", "id": request["observation_request_id"]}
        if upstream[-1]["next_observation_ref"] is not None:
            upstream[-1]["next_observation_ref"] = deepcopy(reference)
        if upstream[-1]["blocker_resolution_condition"] is not None:
            upstream[-1]["blocker_resolution_condition"]["verification_request_ref"] = deepcopy(
                reference
            )
        upstream[-1]["difference_event_id"] = lifecycle_event_id(upstream[-1])
        evaluation["difference_event_head_ref"] = {
            "kind": "difference_event",
            "id": (upstream[-2] if len(upstream) > 1 else head)["difference_event_id"],
        }

    context = deepcopy(baseline)
    context["evaluations"] = [evaluation]
    context["next_observation_requests"] = [request]
    context["observation_methods"] = [method]

    later_request["bindings"][0]["predecessor"] = {
        "difference": difference,
        "events": [*deepcopy(baseline["events"]), *upstream],
        "context": context,
    }
    later_request["observation_method"] = {
        key: value
        for key, value in method.items()
        if key not in {"observation_method_id", "schema_version", "record_kind"}
    }
    return baseline, later_request
