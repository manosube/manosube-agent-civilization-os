"""Deterministic, adapter-free Difference Engine for the v0.1 canonical route.

The Engine derives canonical Difference genesis records from an exact Objective /
Project State / Observation binding. It derives *work identity* only: it never decides
Authority, never plans or executes Change, never judges Evidence sufficiency, never
evaluates Closure, never reflows State and never declares Objective Completion.

Inputs are explicit and immutable. There is no filesystem discovery, no network lookup,
no wall-clock read and no session memory anywhere in this module.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.observation.boundary import fact_boundary_observed
from manosube_agent_civilization.observation.identity import (
    binding_identity,
    fact_evaluation_identity,
    fact_identity,
)

from .canonical import (
    canonical_bytes,
    content_address,
    has_recursive_set_duplicate,
    reject_bare_arrays,
    reject_secret_material,
    walk_references,
)
from .errors import (
    BoundaryViolationError,
    DifferenceError,
    DifferenceValidationError,
    IdentityCollisionError,
    UnsupportedProfileError,
)
from .identity import (
    COMPARISON_PROFILE,
    IDENTITY_PROFILE,
    NORMALIZATION_PROFILE,
    closure_policy_id,
    completion_claim_fingerprint,
    completion_claim_id,
    difference_id as derive_difference_id,
    difference_identity_input,
    lifecycle_event_id,
    objective_semantic_fingerprint,
    policy_semantic_fingerprint,
    resolved_scope_fingerprint,
    supersession_reason_codes,
    supersession_relation_id,
)
from .lifecycle import (
    NEXT_OBSERVATION_REASON,
    OBSERVATION_BOUND_FORBIDDEN,
    TERMINAL_STATUSES,
    is_legal_transition,
    legal_supersession_sources,
)
from .projection import (
    derive_comparison_and_mismatch,
    effective_boundary,
    negative_knowledge_status,
    normalize_observed_state,
    normalize_target_state,
    structural_difference,
    value_candidate,
)
from .validation import (
    SCHEMA_BASE,
    require_schema_version,
    validate_record,
)

OBSERVATION_SCHEMA_BASE = SCHEMA_BASE + "observation/"

SCHEMA_VERSION = "0.1"
RISK_CLASSES = frozenset({"LOW", "MODERATE", "HIGH", "CRITICAL"})
_ACCEPTED_OBSERVATION_STATUS = frozenset(
    {"COMPLETE", "EMPTY", "UNKNOWN", "UNOBSERVED", "BLOCKED", "INCOMPLETE", "CONFLICTED"}
)
_REQUIRES_REOBSERVATION = frozenset({"UNKNOWN", "CONFLICT"})
_DEFAULT_POLICY: dict[str, Any] = {
    "required_observation_scope": None,
    "minimum_evidence_level": "E1",
    "required_claims": [],
    "required_invariants": [],
    "allowed_terminal_states": ["CLOSED", "BLOCKED", "RETAINED"],
    "independent_verification_required": False,
    "maximum_evidence_age": None,
    "contradiction_policy": "FAIL_CLOSED",
    "reopen_conditions": [],
}


def _ref(kind: str, identity: str) -> dict[str, str]:
    return {"kind": kind, "id": identity}


def _require_profiles(request: dict[str, Any]) -> None:
    declared = {
        "identity_profile": (request.get("identity_profile", IDENTITY_PROFILE), IDENTITY_PROFILE),
        "comparison_profile": (
            request.get("comparison_profile", COMPARISON_PROFILE),
            COMPARISON_PROFILE,
        ),
        "normalization_profile": (
            request.get("normalization_profile", NORMALIZATION_PROFILE),
            NORMALIZATION_PROFILE,
        ),
    }
    for name, (actual, expected) in declared.items():
        if actual != expected:
            raise UnsupportedProfileError(f"unsupported {name}: {actual!r}")


def _latest_contiguous(records: list[dict[str, Any]], subject_key: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
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


def _evaluation_supports_observation(
    evaluation: dict[str, Any],
    fact: dict[str, Any],
    observation: dict[str, Any],
    bindings: dict[str, dict[str, Any]],
) -> bool:
    resolved = [bindings.get(str(reference["id"])) for reference in evaluation["binding_refs"]]
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


def _closure_policy(
    requirements: dict[str, Any], target_predicate_ref: dict[str, str]
) -> tuple[dict[str, Any], str]:
    policy = {**deepcopy(_DEFAULT_POLICY), **deepcopy(requirements)}
    unknown = set(policy) - set(_DEFAULT_POLICY)
    if unknown:
        raise DifferenceError(f"unknown Closure Policy requirement fields: {sorted(unknown)}")
    if policy["contradiction_policy"] != "FAIL_CLOSED":
        raise DifferenceError("Closure Policy contradiction policy must remain FAIL_CLOSED")
    if policy["independent_verification_required"] is not False:
        raise DifferenceError("v0.1 Closure Policy cannot require independent verification")
    claims = []
    for descriptor in policy["required_claims"]:
        materialized = {
            "kind": "completion_claim",
            "id": completion_claim_id(descriptor),
            "subject_type": descriptor["subject_type"],
            "subject_ref": descriptor["subject_ref"],
            "claim": descriptor["claim"],
            "target_state_ref": descriptor.get("target_state_ref"),
            "claim_semantic_fingerprint": completion_claim_fingerprint(descriptor),
        }
        claims.append(materialized)
    policy["required_claims"] = claims
    policy["target_predicate_ref"] = deepcopy(target_predicate_ref)
    return policy, policy_semantic_fingerprint(policy)


def _observation_method(record: dict[str, Any]) -> dict[str, Any]:
    method = {
        "schema_version": SCHEMA_VERSION,
        "record_kind": "OBSERVATION_METHOD",
        **{key: deepcopy(value) for key, value in record.items() if key != "observation_method_id"},
    }

    method["observation_method_id"] = content_address(
        "OBS-METHOD-", method, "observation_method_id"
    )
    validate_record(method, "observation_method.schema.json")
    return method


def _select_observation(
    binding: dict[str, Any],
    predicate_id: str,
    scope_id: str,
    project_id: str,
    state_revision: int,
    state_fingerprint: dict[str, Any],
) -> dict[str, Any]:
    bundle = binding["observation_bundle"]
    # An append-only Observation bundle carries the whole lineage, so the Target and Scope
    # alone do not identify one Observation. The exact requested Project State does.
    scoped = [
        observation
        for observation in bundle["observations"]
        if observation["target"]["target_identity"] == predicate_id
        and observation["scope_ref"]["id"] == scope_id
    ]
    matches = [
        observation
        for observation in scoped
        if observation["state_revision_observed"] == state_revision
        and observation["state_fingerprint_observed"] == state_fingerprint
    ]
    if scoped and not matches:
        raise DifferenceError(
            "stale Observation: no Observation is bound to the exact requested Project State"
        )
    if len(matches) != 1:
        raise DifferenceError(
            f"exactly one canonical Observation must bind Target {predicate_id}; got {len(matches)}"
        )
    observation = matches[0]
    if observation["project_id"] != project_id:
        raise BoundaryViolationError("Observation project does not match the derivation request")
    if observation["status"] not in _ACCEPTED_OBSERVATION_STATUS:
        raise DifferenceError(f"unusable Observation status: {observation['status']}")
    if not isinstance(observation, dict):
        raise DifferenceError("Observation record must be a canonical object")
    return observation


def _observed_projection(
    observation: dict[str, Any],
    bundle: dict[str, Any],
    subject: str,
    scope: dict[str, Any],
    boundary: dict[str, Any],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    facts_by_id = {fact["fact_id"]: fact for fact in bundle["facts"]}
    bindings_by_id = {item["binding_id"]: item for item in bundle["bindings"]}
    latest_fact_evaluations = _latest_contiguous(bundle["fact_evaluations"], "fact_id")
    latest_negative_evaluations = _latest_contiguous(
        bundle["negative_evaluations"], "negative_observation_id"
    )
    if any(reference["id"] not in facts_by_id for reference in observation["normalized_fact_refs"]):
        raise DifferenceError("Observation references a Normalized Fact absent from the bundle")
    _verify_upstream_identities(observation, bundle, facts_by_id, bindings_by_id)
    source_facts = [
        facts_by_id[reference["id"]]
        for reference in observation["normalized_fact_refs"]
        if reference.get("kind") == "normalized_fact"
    ]
    for fact in source_facts:
        if fact["subject"] != subject:
            raise BoundaryViolationError(
                "the bound Observation carries a Fact outside the Target subject: "
                f"{fact['subject']}"
            )
        if fact["subject"] not in scope["included_subjects"] or fact["subject"] in scope["excluded_subjects"]:
            raise BoundaryViolationError(f"Fact subject escapes the resolved Scope: {fact['subject']}")
        # Every contract-legal Fact boundary form is accepted, matched by the single
        # canonical authority the Observation owner and the independent validator use.
        if not fact_boundary_observed(fact["effective_boundary"], observation):
            raise BoundaryViolationError(
                "Fact effective boundary was not observed by the bound Observation: "
                f"{fact['fact_id']}"
            )

    negatives = [
        negative
        for negative in bundle["negative_observations"]
        if negative["observation_id"] == observation["observation_id"]
        and negative["target_identity"] == observation["target"]["target_identity"]
        and negative["subject"] == subject
    ]
    for negative in negatives:
        _validate_negative_boundary(negative, observation, scope, boundary)
    if not source_facts and not negatives:
        # UNOBSERVED is not ABSENT and NO_RESULT is not EMPTY: with neither a positive
        # Fact nor a bounded Negative Observation there is no canonical observed state.
        raise DifferenceError(
            "no positive Fact and no bounded Negative Observation exist for the Target subject"
        )

    if source_facts:
        if observation["status"] not in {"COMPLETE", "CONFLICTED"}:
            # An incomplete, unknown, unobserved or blocked Observation still carries
            # positive Facts, but its knowledge is not KNOWN. Deriving an ordinary value
            # mismatch here would disguise an unresolved observation as a normal one.
            raise DifferenceError(
                "an Observation that is not COMPLETE cannot yield a KNOWN observed state: "
                f"{observation['status']}"
            )
        for fact in source_facts:
            evaluation = latest_fact_evaluations.get(fact["fact_id"])
            if evaluation is None or evaluation["evaluation_status"] not in {"SUPPORTED", "CONFLICTED"}:
                raise DifferenceError(
                    f"Normalized Fact lacks a supporting current evaluation: {fact['fact_id']}"
                )
            if not _evaluation_supports_observation(evaluation, fact, observation, bindings_by_id):
                raise DifferenceError(
                    f"Fact evaluation is not bound to this exact Observation: {fact['fact_id']}"
                )
        knowledge = (
            "CONFLICTED"
            if any(
                latest_fact_evaluations[fact["fact_id"]]["evaluation_status"] == "CONFLICTED"
                for fact in source_facts
            )
            else "KNOWN"
        )
        candidates = [value_candidate(fact, boundary) for fact in source_facts]
        return knowledge, candidates, negatives

    statuses = set()
    for negative in negatives:
        latest = latest_negative_evaluations.get(negative["negative_observation_id"])
        if latest is None:
            raise DifferenceError(
                f"Negative Observation lacks a contiguous evaluation chain: "
                f"{negative['negative_observation_id']}"
            )
        mapped = negative_knowledge_status(latest["evaluation_status"])
        if mapped == "REJECT_OR_QUARANTINE":
            raise DifferenceError("INVALID Negative Observation cannot produce a Difference")
        if mapped in {"ABSENT", "EMPTY"} and not negative["negative_evidence_refs"]:
            # NO_RESULT is not proven absence. A proven ABSENT or EMPTY conclusion is only
            # canonical while its bounded Negative Evidence is present.
            raise DifferenceError(
                f"{mapped} requires bounded Negative Evidence: "
                f"{negative['negative_observation_id']}"
            )
        statuses.add(mapped)
    if len(statuses) != 1:
        raise DifferenceError("bounded Negative Observations disagree on knowledge status")
    return statuses.pop(), [], negatives


def _verify_upstream_identities(
    observation: dict[str, Any],
    bundle: dict[str, Any],
    facts_by_id: dict[str, dict[str, Any]],
    bindings_by_id: dict[str, dict[str, Any]],
) -> None:
    """Recompute every upstream identity this derivation is about to trust.

    Reference lookup and schema validity are not enough: a caller can alter an
    identity-bearing field of a Normalized Fact, binding or evaluation while retaining its
    original id, and every lookup still resolves. The Observation element owns these
    identity algorithms, so they are recomputed here rather than re-implemented.
    """

    referenced = {
        reference["id"] for reference in observation["normalized_fact_refs"]
    }
    for fact in bundle["facts"]:
        if fact["fact_id"] not in referenced:
            continue
        require_schema_version(fact, f"normalized fact {fact['fact_id']}")
        if fact["fact_id"] != fact_identity(fact):
            raise IdentityCollisionError(
                f"Normalized Fact identity does not recompute: {fact['fact_id']}"
            )
    for binding in bindings_by_id.values():
        if binding["observation_id"] != observation["observation_id"]:
            continue
        if binding["binding_id"] != binding_identity(binding):
            raise IdentityCollisionError(
                f"Fact Observation Binding identity does not recompute: {binding['binding_id']}"
            )
        if binding["fact_id"] not in facts_by_id:
            raise DifferenceError(
                f"Fact Observation Binding references an absent Fact: {binding['binding_id']}"
            )
    for evaluation in bundle["fact_evaluations"]:
        if evaluation["fact_id"] not in referenced:
            continue
        if evaluation["evaluation_id"] != fact_evaluation_identity(evaluation):
            raise IdentityCollisionError(
                "Fact evaluation identity does not recompute: "
                f"{evaluation['evaluation_id']}"
            )


_LINEAGE_SECTIONS: dict[str, str] = {
    "observations": "observation_id",
    "normalized_facts": "fact_id",
    "fact_observation_bindings": "binding_id",
    "fact_evaluations": "evaluation_id",
    "negative_observations": "negative_observation_id",
    "negative_observation_evaluations": "evaluation_id",
}
_BUNDLE_SECTIONS: dict[str, str] = {
    "observations": "observations",
    "normalized_facts": "facts",
    "fact_observation_bindings": "bindings",
    "fact_evaluations": "fact_evaluations",
    "negative_observations": "negative_observations",
    "negative_observation_evaluations": "negative_evaluations",
}


def _require_context_agrees_with_observation_lineage(
    predecessor: dict[str, Any], observation_bundle: dict[str, Any]
) -> None:
    """Reject a predecessor context that contradicts the Observation lineage supplied.

    Where the carried context and the canonical Observation bundle name the same record,
    the payloads must be identical. A same-ID/different-payload context is a forgery, not
    provenance.
    """

    context = predecessor.get("context", {})
    for section, key in _LINEAGE_SECTIONS.items():
        authentic = {
            record[key]: record
            for record in observation_bundle.get(_BUNDLE_SECTIONS[section], [])
        }
        for record in context.get(section, []):
            existing = authentic.get(record[key])
            if existing is not None and canonical_bytes(existing) != canonical_bytes(record):
                raise IdentityCollisionError(
                    f"same-ID different-payload conflict in predecessor context: {record[key]}"
                )


def _require_resolvable_lineage(
    difference: dict[str, Any],
    retained: list[dict[str, Any]],
    resolved: dict[str, set[str]],
    retained_observations: list[dict[str, Any]],
    retained_evaluations: list[dict[str, Any]],
) -> None:
    """Reject a predecessor whose retained lineage is not self-contained.

    Every reference a retained event or the retained Difference carries must resolve
    inside the returned bundle. Defaulting a missing context to an empty mapping would
    leave an append-only chain whose own genesis cannot be read back.
    """

    def _require(reference: dict[str, Any] | None, section: str, context: str) -> None:
        if reference is None:
            return
        identity = str(reference.get("id"))
        if identity not in resolved.get(section, set()):
            raise DifferenceError(
                f"retained predecessor reference does not resolve: {context} -> "
                f"{section}:{identity}"
            )

    difference_id = difference["difference_id"]
    for reference in difference["observation_refs"]:
        _require(reference, "observations", "difference.observation_refs")
    _require(difference["objective_revision_ref"], "objective_revisions", "difference.objective")
    _require(
        difference["objective_scope_binding"]["scope_ref"],
        "observation_scopes",
        "difference.scope",
    )
    _require(difference["closure_policy"], "policies", "difference.closure_policy")
    _require(difference["genesis_event_ref"], "events", "difference.genesis_event_ref")

    for observation in retained_observations:
        for reference in observation["normalized_fact_refs"]:
            _require(reference, "normalized_facts", f"observation[{observation['observation_id']}]")
    for evaluation in retained_evaluations:
        for reference in evaluation["binding_refs"]:
            _require(
                reference,
                "fact_observation_bindings",
                f"fact_evaluation[{evaluation['evaluation_id']}]",
            )

    for event in retained:
        where = f"event[{event['event_revision']}]"
        for reference in event["observation_refs"]:
            _require(reference, "observations", f"{where}.observation_refs")
        _require(event["next_observation_ref"], "next_observation_requests", f"{where}.next")
        _require(event["closure_evaluation_ref"], "evaluations", f"{where}.closure_evaluation")
        _require(event["reflow_transition_ref"], "reflow_transitions", f"{where}.reflow")
        _require(
            event["reopen_condition_evaluation_ref"],
            "reopen_condition_evaluations",
            f"{where}.reopen_condition_evaluation",
        )
        for reference in event["change_refs"]:
            _require(reference, "changes", f"{where}.change_refs")
        scope = event["blocker_scope"]
        if scope is not None:
            for reference in scope["affected_subject_refs"]["members"]:
                if reference.get("kind") == "difference" and reference["id"] != difference_id:
                    raise DifferenceError(
                        f"retained blocker scope names another Difference: {reference['id']}"
                    )
        condition = event["blocker_resolution_condition"]
        if condition is not None:
            _require(
                condition["verification_request_ref"],
                "next_observation_requests",
                f"{where}.verification_request",
            )


def _evidence_union(
    observation: dict[str, Any], negatives: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return the exact, duplicate-free Evidence binding of both provenance channels."""

    merged: dict[bytes, dict[str, Any]] = {}
    for reference in observation["observation_evidence_refs"]:
        merged[canonical_bytes(reference)] = deepcopy(reference)
    for negative in negatives:
        for reference in negative["negative_evidence_refs"]:
            merged[canonical_bytes(reference)] = deepcopy(reference)
    return [item for _, item in sorted(merged.items())]


def _validate_negative_boundary(
    negative: dict[str, Any],
    observation: dict[str, Any],
    scope: dict[str, Any],
    boundary: dict[str, Any],
) -> None:
    """Reject a Negative Observation that does not match the exact Observation boundary.

    A Negative Observation is only bounded proof while every canonical binding it carries
    is the same one the requested Observation carries. Matching the Observation ID, Target
    and subject alone would let a record from another project, scope, method, time window
    or source snapshot be interpreted as an absence conclusion, and its Evidence bound
    into the Difference.
    """

    if negative.get("schema_version") != SCHEMA_VERSION:
        raise DifferenceValidationError(
            f"unsupported schema_version at negative observation "
            f"{negative['negative_observation_id']}"
        )
    exact = {
        "project_id": (negative["project_id"], observation["project_id"]),
        "scope_ref": (negative["scope_ref"], observation["scope_ref"]),
        "method_ref": (negative["method_ref"], observation["method_ref"]),
        "time_boundary": (negative["time_boundary"], observation["time_boundary"]),
        "source_snapshot_refs": (
            negative["source_snapshot_refs"],
            observation["source_snapshot_refs"],
        ),
    }
    for field, (actual, expected) in exact.items():
        if canonical_bytes(actual) != canonical_bytes(expected):
            raise BoundaryViolationError(
                f"Negative Observation {field} does not match the bound Observation: "
                f"{negative['negative_observation_id']}"
            )
    if negative["scope_ref"]["id"] != scope["scope_id"]:
        raise BoundaryViolationError(
            "Negative Observation is bound to a different resolved Scope: "
            f"{negative['negative_observation_id']}"
        )
    if negative["method_ref"] != scope["method_ref"]:
        raise BoundaryViolationError(
            "Negative Observation method is outside the declared Scope: "
            f"{negative['negative_observation_id']}"
        )
    if (
        negative["subject"] not in scope["included_subjects"]
        or negative["subject"] in scope["excluded_subjects"]
    ):
        raise BoundaryViolationError(
            f"Negative Observation subject escapes the resolved Scope: {negative['subject']}"
        )
    effective = negative["effective_boundary"]
    declared = {
        reference["id"] for reference in boundary["source_snapshot_refs"]["members"]
    }
    if (
        effective["kind"] != "SOURCE_SNAPSHOT"
        or effective["identity"] not in declared
        or effective["start"] is not None
        or effective["end"] is not None
    ):
        raise BoundaryViolationError(
            "Negative Observation effective boundary escapes the declared source snapshots: "
            f"{negative['negative_observation_id']}"
        )


def _genesis_event(
    difference_id: str,
    state_revision: int,
    state_fingerprint: dict[str, Any],
    observation_refs: list[dict[str, str]],
    evidence_refs: list[dict[str, str]],
) -> dict[str, Any]:
    event = _empty_event(difference_id, state_revision, state_fingerprint)
    event.update(
        {
            "event_kind": "TRANSITION",
            "event_revision": 0,
            "previous_event_id": None,
            "from_status": None,
            "to_status": "DETECTED",
            "reason_code": "DIFFERENCE_DERIVED",
            "reason": "Structural mismatch derived from the exact Target/State/Observation binding.",
            "observation_refs": deepcopy(observation_refs),
            "evidence_refs": deepcopy(evidence_refs),
        }
    )
    event["difference_event_id"] = lifecycle_event_id(event)
    return event


def _empty_event(
    difference_id: str, state_revision: int, state_fingerprint: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "difference_event_id": "",
        "difference_id": difference_id,
        "event_kind": "TRANSITION",
        "event_revision": 0,
        "previous_event_id": None,
        "from_status": None,
        "to_status": "DETECTED",
        "state_revision_evaluated": state_revision,
        "state_fingerprint_evaluated": deepcopy(state_fingerprint),
        "reason_code": "DIFFERENCE_DERIVED",
        "reason": "",
        "blocker_kind": None,
        "blocker_scope": None,
        "blocker_resolution_condition": None,
        "observation_refs": [],
        "evidence_refs": [],
        "authority_ref": None,
        "change_refs": [],
        "closure_evaluation_ref": None,
        "reflow_transition_ref": None,
        "next_observation_ref": None,
        "reopen_trigger": None,
        "reopen_condition_ref": None,
        "reopen_condition_evaluation_ref": None,
        "revoked_evidence_refs": [],
        "invalid_evidence_refs": [],
        "contradiction_evidence_refs": [],
    }


def _transition_event(
    difference_id: str,
    state_revision: int,
    state_fingerprint: dict[str, Any],
    revision: int,
    previous_event_id: str,
    from_status: str,
    to_status: str,
    reason_code: str,
    reason: str,
) -> dict[str, Any]:
    event = _empty_event(difference_id, state_revision, state_fingerprint)
    event.update(
        {
            "event_revision": revision,
            "previous_event_id": previous_event_id,
            "from_status": from_status,
            "to_status": to_status,
            "reason_code": reason_code,
            "reason": reason,
        }
    )
    event["difference_event_id"] = lifecycle_event_id(event)
    return event


def _retained_blocker_payload(
    head: dict[str, Any], difference_id: str, boundary: dict[str, Any]
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Re-derive the blocker payload a retained ``BLOCKED`` status still requires.

    The kind, blocked stage, condition code and affected subjects are carried from the
    predecessor's own blocker payload; the effective boundary and the verification request
    are re-derived against the current Difference so that no stale forward reference is
    copied.
    """

    kind = head["blocker_kind"]
    scope = deepcopy(head["blocker_scope"])
    condition = deepcopy(head["blocker_resolution_condition"])
    if kind is None or scope is None or condition is None:
        raise DifferenceError(
            "a retained BLOCKED status requires the predecessor's blocker payload: "
            f"{head['difference_event_id']}"
        )
    scope["effective_boundary"] = deepcopy(boundary)
    subjects = scope["affected_subject_refs"]["members"]
    if not subjects:
        raise DifferenceError(
            f"a retained BLOCKED status requires affected subjects: {head['difference_event_id']}"
        )
    if condition["subject_ref"] not in subjects:
        raise DifferenceError(
            "the blocker resolution condition subject is outside the blocker scope: "
            f"{head['difference_event_id']}"
        )
    if any(reference["id"] == difference_id for reference in subjects) is False:
        # The subject set is carried verbatim; it must still resolve to this Difference.
        raise DifferenceError(
            f"the blocker scope does not resolve to this Difference: {difference_id}"
        )
    return str(kind), scope, condition


def _observation_bound_event(
    difference_id: str,
    state_revision: int,
    state_fingerprint: dict[str, Any],
    revision: int,
    head: dict[str, Any],
    observation_refs: list[dict[str, str]],
    evidence_refs: list[dict[str, str]],
    boundary: dict[str, Any],
) -> tuple[dict[str, Any], str | None, dict[str, Any] | None]:
    """Build the status-preserving provenance append for an equivalent re-observation.

    The returned tuple is the event, the Next Observation Request reason code its retained
    status requires (or ``None``), and the blocker resolution condition that must be bound
    to that request (or ``None``).
    """

    status = head["to_status"]
    event = _empty_event(difference_id, state_revision, state_fingerprint)
    event.update(
        {
            "event_kind": "OBSERVATION_BOUND",
            "event_revision": revision,
            "previous_event_id": head["difference_event_id"],
            "from_status": status,
            "to_status": status,
            "reason_code": "EQUIVALENT_REOBSERVATION_BOUND",
            "reason": "Equivalent re-observation appended to the existing Difference identity.",
            "observation_refs": deepcopy(observation_refs),
            "evidence_refs": deepcopy(evidence_refs),
        }
    )
    condition: dict[str, Any] | None = None
    if status == "BLOCKED":
        kind, scope, condition = _retained_blocker_payload(head, difference_id, boundary)
        event["blocker_kind"] = kind
        event["blocker_scope"] = scope
        event["blocker_resolution_condition"] = condition
    # The identity input excludes the forward-looking next_observation_ref and the blocker
    # payload, so the event identity is stable before the request it points at exists.
    event["difference_event_id"] = lifecycle_event_id(event)
    return event, NEXT_OBSERVATION_REASON.get(status), condition


def _next_observation_request(
    difference_id: str,
    event: dict[str, Any],
    target_predicate_ref: dict[str, str],
    scope_ref: dict[str, str],
    method_id: str,
    reason_code: str = "BLOCKER_REOBSERVATION",
) -> dict[str, Any]:

    request = {
        "schema_version": SCHEMA_VERSION,
        "observation_request_id": "",
        "record_kind": "NEXT_OBSERVATION_REQUEST",
        "difference_ref": {"kind": "difference", "id": difference_id},
        "derived_from_event_ref": {"kind": "difference_event", "id": event["difference_event_id"]},
        "state_revision_requested": event["state_revision_evaluated"],
        "state_fingerprint_requested": deepcopy(event["state_fingerprint_evaluated"]),
        "target_ref": {"kind": "target_predicate", "id": target_predicate_ref["id"]},
        "scope_ref": {"kind": "observation_scope", "id": scope_ref["id"]},
        "method_ref": {"kind": "observation_method", "id": method_id},
        "reason_code": reason_code,
    }
    request["observation_request_id"] = content_address(
        "OBS-REQ-", request, "observation_request_id"
    )
    validate_record(request, "next_observation_request.schema.json")
    return request


def _reject_hostile_input(request: dict[str, Any]) -> None:
    reject_secret_material(request, "request")
    walk_references(request, "request")


def _validate_predecessor(predecessor: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    difference = predecessor["difference"]
    events = sorted(predecessor["events"], key=lambda item: item["event_revision"])
    if difference["difference_id"] != derive_difference_id(difference):
        raise DifferenceError("predecessor Difference identity does not recompute")
    if not events or events[0]["event_revision"] != 0 or events[0]["to_status"] != "DETECTED":
        raise DifferenceError("predecessor lineage does not start at a null to DETECTED genesis")
    for revision, event in enumerate(events):
        expected_previous = None if revision == 0 else events[revision - 1]["difference_event_id"]
        if event["event_revision"] != revision or event["previous_event_id"] != expected_previous:
            raise DifferenceError("predecessor lineage is not a contiguous append-only chain")
        if event["difference_id"] != difference["difference_id"]:
            raise DifferenceError("predecessor event is bound to a different Difference")
        # Every event in the chain, not only its head, must recompute to the identity it
        # carries. Without this a caller could alter an identity-bearing field such as
        # reason_code, observation_refs or evidence_refs while keeping the old event ID,
        # and the forged event would be copied into the returned append-only lineage.
        validate_record(event, "difference_lifecycle_event.schema.json")
        if event["difference_event_id"] != lifecycle_event_id(event):
            raise DifferenceError(
                f"predecessor event identity does not recompute: {event['difference_event_id']}"
            )
        expected_from = None if revision == 0 else events[revision - 1]["to_status"]
        if event["from_status"] != expected_from:
            raise DifferenceError(
                f"predecessor lineage breaks status continuity: {event['difference_event_id']}"
            )
        if event["event_kind"] == "OBSERVATION_BOUND":
            # A provenance append never changes status and never lands on a status that
            # forbids one.
            if event["from_status"] != event["to_status"]:
                raise DifferenceError(
                    "predecessor observation-bound event mutates status: "
                    f"{event['difference_event_id']}"
                )
            if event["to_status"] in OBSERVATION_BOUND_FORBIDDEN:
                raise DifferenceError(
                    "predecessor observation-bound event is bound to a forbidden status: "
                    f"{event['to_status']}"
                )
        elif not is_legal_transition(event["from_status"], event["to_status"]):
            # The single canonical lifecycle transition authority decides legality.
            raise DifferenceError(
                f"predecessor lineage contains an illegal lifecycle transition: "
                f"{event['from_status']} -> {event['to_status']}"
            )
    if events[-1]["to_status"] in TERMINAL_STATUSES:
        raise DifferenceError(
            f"predecessor Difference is already terminal: {events[-1]['to_status']}"
        )
    return difference, events


def derive_differences(request: dict[str, Any]) -> dict[str, Any]:
    """Derive canonical Difference genesis records from one exact binding.

    The returned bundle carries every generated record plus the exact input records that
    a cross-record conformance validator needs to resolve them. The Engine returns only
    schema-valid output, never mutates *request*, and fails closed on any incomplete,
    conflicted, stale, out-of-boundary or secret-bearing input.
    """

    request = deepcopy(request)
    require_schema_version(request, "derivation request")
    _require_profiles(request)
    _reject_hostile_input(request)

    project_id = request["project_id"]
    objective = request["objective_revision"]
    require_schema_version(objective, "objective revision")
    if objective["project_id"] != project_id:
        raise BoundaryViolationError("Objective revision belongs to a different project")
    if objective["status"] != "ACTIVE":
        raise DifferenceError("only an ACTIVE Objective revision can bind a Difference derivation")
    objective_fingerprint = objective_semantic_fingerprint(objective)
    objective_revisions: dict[str, dict[str, Any]] = {
        objective["objective_revision_id"]: deepcopy(objective)
    }
    objective_revision_ref = _ref("objective_revision", objective["objective_revision_id"])

    state_revision = request["state_revision"]
    if not isinstance(state_revision, int) or isinstance(state_revision, bool) or state_revision < 0:
        raise DifferenceError("State revision must be a non-negative integer")
    state_fingerprint = request["state_fingerprint"]
    if state_fingerprint.get("profile") != "MANOSUBE-STATE-SHA256-0.1":
        raise UnsupportedProfileError("unsupported State fingerprint profile")

    default_requirements = request.get("closure_policy_requirements", {})
    default_risk_class = request.get("risk_class", "LOW")
    if default_risk_class not in RISK_CLASSES:
        raise DifferenceError(f"unknown risk class: {default_risk_class!r}")

    method: dict[str, Any] | None = None
    if "observation_method" in request:
        method = _observation_method(request["observation_method"])

    predicates = {item["predicate_id"]: item for item in objective["target_predicates"]}
    differences: dict[str, dict[str, Any]] = {}
    identity_payloads: dict[str, bytes] = {}
    events: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    methods: dict[str, dict[str, Any]] = {}
    policies: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    scopes: dict[str, dict[str, Any]] = {}
    observations: dict[str, dict[str, Any]] = {}
    facts: dict[str, dict[str, Any]] = {}
    fact_bindings: dict[str, dict[str, Any]] = {}
    fact_evaluations: dict[str, dict[str, Any]] = {}
    negative_observations: dict[str, dict[str, Any]] = {}
    negative_evaluations: dict[str, dict[str, Any]] = {}
    materialized_status: dict[str, str] = {}
    carried: dict[str, dict[str, dict[str, Any]]] = {}
    satisfied: list[str] = []

    for binding in sorted(request["bindings"], key=lambda item: item["target_predicate_id"]):
        predicate_id = binding["target_predicate_id"]
        predicate = predicates.get(predicate_id)
        if predicate is None:
            raise DifferenceError(f"Target Predicate is not declared by the Objective: {predicate_id}")
        target_predicate_ref = _ref("target_predicate", predicate_id)
        subject = predicate["subject"]

        scope = binding["observation_scope"]
        require_schema_version(scope, "observation scope")
        validate_record(scope, "observation_scope.schema.json", base=OBSERVATION_SCHEMA_BASE)
        if scope["project_id"] != project_id:
            raise BoundaryViolationError("resolved Scope belongs to a different project")
        if scope["target_identity"] != predicate_id:
            raise BoundaryViolationError("resolved Scope is not bound to this Target Predicate")
        if subject not in scope["included_subjects"] or subject in scope["excluded_subjects"]:
            raise BoundaryViolationError(f"Target subject is outside the resolved Scope: {subject}")
        scope_fingerprint = resolved_scope_fingerprint(scope)
        scope_binding = {
            "objective_scope_name": predicate["observation_scope"],
            "scope_ref": _ref("observation_scope", scope["scope_id"]),
            "scope_schema_version": scope["schema_version"],
            "resolved_scope_record_sha256": scope_fingerprint,
        }

        observation = _select_observation(
            binding, predicate_id, scope["scope_id"], project_id, state_revision, state_fingerprint
        )
        boundary = effective_boundary(scope, scope_fingerprint, observation["source_snapshot_refs"])
        knowledge, candidates, source_negatives = _observed_projection(
            observation, binding["observation_bundle"], subject, scope, boundary
        )

        target = normalize_target_state(predicate)
        reject_bare_arrays(target, "normalized_target_state")
        observed = normalize_observed_state(subject, scope_binding, boundary, knowledge, candidates)
        reject_bare_arrays(observed, "normalized_observed_state")
        comparison, mismatch_kind = derive_comparison_and_mismatch(observed, target)
        if comparison == "SATISFIED":
            # A satisfied route yields no open Difference. The empty result is legitimate
            # only when the evaluation scope is complete: an incomplete scope may never
            # claim satisfaction. It is still not a Completion claim -- Objective
            # Completion has a later canonical owner.
            if scope["scope_status"] != "COMPLETE" or observation["status"] not in {
                "COMPLETE",
                "EMPTY",
            }:
                raise DifferenceError(
                    "an incomplete evaluation scope cannot claim a satisfied Target Predicate"
                )
            satisfied.append(predicate_id)
            continue
        if mismatch_kind is None:
            raise DifferenceError("unsatisfied comparison produced no mismatch kind")

        structural = structural_difference(observed, target, comparison, mismatch_kind)
        reject_bare_arrays(structural, "structural_difference")

        requirements = binding.get("closure_policy_requirements", default_requirements)
        policy, policy_fingerprint = _closure_policy(requirements, target_predicate_ref)
        # Observation Evidence and bounded Negative Evidence are distinct provenance
        # channels carrying distinct reference kinds. The Difference binds the exact union
        # so that a negative-derived observed state keeps its own bounded proof, and so
        # that neither channel is silently equated with, or absorbed into, the other.
        evidence_refs = _evidence_union(observation, source_negatives)
        if not evidence_refs:
            raise DifferenceError("a Difference requires at least one Observation Evidence reference")

        difference: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "difference_id": "",
            "project_id": project_id,
            "objective_revision_ref": deepcopy(objective_revision_ref),
            "objective_semantic_fingerprint": objective_fingerprint,
            "target_predicate_ref": deepcopy(target_predicate_ref),
            "normalized_target_state": target,
            "objective_scope_binding": scope_binding,
            "observed_state_revision": state_revision,
            "observed_state_fingerprint": deepcopy(state_fingerprint),
            "observation_refs": [_ref("observation", observation["observation_id"])],
            "observation_evidence_refs": evidence_refs,
            "normalized_observed_state": observed,
            "structural_difference": structural,
            "subject": subject,
            "observation_scope": predicate["observation_scope"],
            "effective_boundary": boundary,
            "impact": {},
            "risk_class": binding.get("risk_class", default_risk_class),
            "authority_required": [],
            "closure_policy": {
                "kind": "closure_policy",
                "id": "",
                "version": SCHEMA_VERSION,
                "semantic_fingerprint": policy_fingerprint,
            },
            "genesis_event_ref": {"kind": "difference_event", "id": ""},
        }
        if difference["risk_class"] not in RISK_CLASSES:
            raise DifferenceError(f"unknown risk class: {difference['risk_class']!r}")
        for projection in ("normalized_target_state", "normalized_observed_state", "structural_difference"):
            if has_recursive_set_duplicate(difference[projection]):
                raise DifferenceError(f"{projection} carries a duplicate unordered-set member")

        difference_id = derive_difference_id(difference)
        identity_payload = canonical_bytes(difference_identity_input(difference))
        existing_payload = identity_payloads.get(difference_id)
        if existing_payload is not None and existing_payload != identity_payload:
            raise IdentityCollisionError(f"Difference identity collision: {difference_id}")
        identity_payloads[difference_id] = identity_payload
        difference["difference_id"] = difference_id
        difference["closure_policy"]["id"] = closure_policy_id(policy_fingerprint, difference_id)

        policy_record = {
            "schema_version": SCHEMA_VERSION,
            "closure_policy_id": difference["closure_policy"]["id"],
            "policy_version": SCHEMA_VERSION,
            "policy_semantic_fingerprint": policy_fingerprint,
            "subject_difference_ref": {"kind": "difference", "id": difference_id},
            **policy,
        }
        validate_record(policy_record, "closure_policy.schema.json")

        observation_refs = deepcopy(difference["observation_refs"])
        predecessor = binding.get("predecessor")
        chain: list[dict[str, Any]] = []
        pending_lineage: list[tuple[dict[str, Any], list[dict[str, Any]], set[str]]] = []
        if predecessor is None:
            genesis = _genesis_event(
                difference_id, state_revision, state_fingerprint, observation_refs, evidence_refs
            )
            chain.append(genesis)
            chain.append(
                _transition_event(
                    difference_id,
                    state_revision,
                    state_fingerprint,
                    1,
                    genesis["difference_event_id"],
                    "DETECTED",
                    "OPEN",
                    "IDENTITY_ACCEPTED",
                    "Difference identity, schema and exact input bindings validated.",
                )
            )
        else:
            _require_context_agrees_with_observation_lineage(
                predecessor, binding["observation_bundle"]
            )
            prior_difference, prior_events = _validate_predecessor(predecessor)
            if prior_difference["difference_id"] == difference_id:
                prior_payload = canonical_bytes(difference_identity_input(prior_difference))
                if prior_payload != identity_payload:
                    raise IdentityCollisionError(
                        f"Difference identity collision: {difference_id}"
                    )
                chain = deepcopy(prior_events)
                bound_event, retained_reason, retained_condition = _observation_bound_event(
                    difference_id,
                    state_revision,
                    state_fingerprint,
                    len(chain),
                    chain[-1],
                    observation_refs,
                    evidence_refs,
                    boundary,
                )
                if retained_reason is not None:
                    # A retained BLOCKED, RETAINED or REOPENED status still requires a
                    # Next Observation Request. It is re-derived against this event, never
                    # copied from the predecessor, so the reference resolves inside the
                    # returned bundle.
                    if method is None:
                        raise DifferenceError(
                            f"a retained {bound_event['to_status']} status requires an "
                            "Observation Method projection"
                        )
                    retained_request = _next_observation_request(
                        difference_id,
                        bound_event,
                        target_predicate_ref,
                        scope_binding["scope_ref"],
                        method["observation_method_id"],
                        retained_reason,
                    )
                    reference = {
                        "kind": "next_observation_request",
                        "id": retained_request["observation_request_id"],
                    }
                    bound_event["next_observation_ref"] = reference
                    if retained_condition is not None:
                        retained_condition["verification_request_ref"] = deepcopy(reference)
                    requests.append(retained_request)
                    methods[method["observation_method_id"]] = method
                chain.append(bound_event)
                difference["genesis_event_ref"] = {
                    "kind": "difference_event",
                    "id": chain[0]["difference_event_id"],
                }
                # The retained genesis and every earlier event still reference the prior
                # Observation and Evidence. Those records must travel with the lineage or
                # the append-only chain returned here cannot be resolved.
                _absorb_predecessor_context(
                    predecessor, objective_revisions, policies, scopes, observations,
                    facts, fact_bindings, fact_evaluations, negative_observations,
                    negative_evaluations, requests, methods, carried,
                )
                pending_lineage.append(
                    (
                        difference,
                        deepcopy(prior_events),
                        {event["difference_event_id"] for event in chain},
                    )
                )
            else:
                chain = _material_change_chain(
                    difference_id,
                    state_revision,
                    state_fingerprint,
                    observation_refs,
                    evidence_refs,
                )
                relation, old_terminal = _supersede(
                    prior_difference,
                    prior_events,
                    difference,
                    chain[0],
                    state_revision,
                    state_fingerprint,
                )
                relations.append(relation)
                superseded_chain = [*deepcopy(prior_events), old_terminal]
                for event in superseded_chain:
                    validate_record(event, "difference_lifecycle_event.schema.json")
                events.extend(superseded_chain)
                differences[prior_difference["difference_id"]] = deepcopy(prior_difference)
                materialized_status[prior_difference["difference_id"]] = "SUPERSEDED"
                pending_lineage.append(
                    (
                        prior_difference,
                        superseded_chain,
                        {event["difference_event_id"] for event in superseded_chain},
                    )
                )
                _absorb_predecessor_context(
                    predecessor, objective_revisions, policies, scopes, observations,
                    facts, fact_bindings, fact_evaluations, negative_observations,
                    negative_evaluations, requests, methods, carried,
                )
        if difference["genesis_event_ref"]["id"] == "":
            difference["genesis_event_ref"] = {
                "kind": "difference_event",
                "id": chain[0]["difference_event_id"],
            }

        head = chain[-1]
        if mismatch_kind in _REQUIRES_REOBSERVATION:
            # FAIL_CLOSED contradiction policy: an unresolved or conflicted observed state
            # cannot be evaluated, so the Policy requires a further bounded observation.
            if method is None:
                raise DifferenceError(
                    "an unresolved or conflicted route requires an Observation Method projection"
                )
            next_request = _next_observation_request(
                difference_id, head, target_predicate_ref, scope_binding["scope_ref"],
                method["observation_method_id"],
            )
            head["next_observation_ref"] = {
                "kind": "next_observation_request",
                "id": next_request["observation_request_id"],
            }
            requests.append(next_request)
            methods[method["observation_method_id"]] = method

        validate_record(difference, "difference.schema.json")
        for event in chain:
            validate_record(event, "difference_lifecycle_event.schema.json")

        existing = differences.get(difference_id)
        if existing is not None and canonical_bytes(existing) != canonical_bytes(difference):
            raise IdentityCollisionError(f"Difference identity collision: {difference_id}")
        differences[difference_id] = difference
        policies.append(policy_record)
        events.extend(chain)
        materialized_status[difference_id] = head["to_status"]
        scopes[scope["scope_id"]] = deepcopy(scope)
        _absorb_observation_context(
            binding["observation_bundle"], observation, observations, facts,
            fact_bindings, fact_evaluations, negative_observations, negative_evaluations,
        )
        for retained_difference, retained_events, chain_ids in pending_lineage:
            _require_resolvable_lineage(
                retained_difference,
                retained_events,
                {
                    "observations": set(observations),
                    "objective_revisions": set(objective_revisions),
                    "observation_scopes": set(scopes),
                    "policies": {item["closure_policy_id"] for item in policies},
                    "events": chain_ids,
                    "next_observation_requests": {
                        item["observation_request_id"] for item in requests
                    },
                    "evaluations": set(carried.get("evaluations", {})),
                    "reflow_transitions": set(carried.get("reflow_transitions", {})),
                    "changes": set(carried.get("changes", {})),
                    "reopen_condition_evaluations": set(
                        carried.get("reopen_condition_evaluations", {})
                    ),
                    "normalized_facts": set(facts),
                    "fact_observation_bindings": set(fact_bindings),
                },
                list(observations.values()),
                list(fact_evaluations.values()),
            )

    return _finalize(
        request, objective_revisions, differences, events, policies, relations, requests, methods,
        scopes, observations, facts, fact_bindings, fact_evaluations,
        negative_observations, negative_evaluations, materialized_status, satisfied,
        state_revision, state_fingerprint, carried,
    )


def _material_change_chain(
    difference_id: str,
    state_revision: int,
    state_fingerprint: dict[str, Any],
    observation_refs: list[dict[str, str]],
    evidence_refs: list[dict[str, str]],
) -> list[dict[str, Any]]:
    genesis = _genesis_event(
        difference_id, state_revision, state_fingerprint, observation_refs, evidence_refs
    )
    return [
        genesis,
        _transition_event(
            difference_id,
            state_revision,
            state_fingerprint,
            1,
            genesis["difference_event_id"],
            "DETECTED",
            "OPEN",
            "IDENTITY_ACCEPTED",
            "Difference identity, schema and exact input bindings validated.",
        ),
    ]


def _supersede(
    old_difference: dict[str, Any],
    old_events: list[dict[str, Any]],
    new_difference: dict[str, Any],
    new_genesis: dict[str, Any],
    state_revision: int,
    state_fingerprint: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Prepare the append-only bidirectional supersession lineage for a material change."""

    reason_codes = supersession_reason_codes(old_difference, new_difference)
    if not reason_codes:
        raise DifferenceError("a superseding Difference must record at least one material change")
    head = old_events[-1]
    if not is_legal_transition(head["to_status"], "SUPERSEDED"):
        raise DifferenceError(
            "the lifecycle contract does not permit supersession from "
            f"{head['to_status']}; legal sources are "
            f"{sorted(legal_supersession_sources())}"
        )
    terminal = _transition_event(
        old_difference["difference_id"],
        state_revision,
        state_fingerprint,
        len(old_events),
        head["difference_event_id"],
        head["to_status"],
        "SUPERSEDED",
        "MATERIAL_IDENTITY_CHANGE",
        "Superseded by a materially different Difference derived from the same Target.",
    )
    relation = {
        "schema_version": SCHEMA_VERSION,
        "supersession_relation_id": "",
        "old_difference_ref": {"kind": "difference", "id": old_difference["difference_id"]},
        "new_difference_ref": {"kind": "difference", "id": new_difference["difference_id"]},
        "old_terminal_event_ref": {
            "kind": "difference_event",
            "id": terminal["difference_event_id"],
        },
        "new_genesis_event_ref": {
            "kind": "difference_event",
            "id": new_genesis["difference_event_id"],
        },
        "reason_codes": sorted(reason_codes),
        "evidence_refs": [],
    }
    relation["supersession_relation_id"] = supersession_relation_id(relation)
    validate_record(relation, "difference_supersession_relation.schema.json")
    return relation, terminal


#: Records produced by later canonical owners that a retained predecessor event may
#: reference. This Engine never creates them; it preserves what the caller supplied.
_CARRIED_SECTIONS: dict[str, str] = {
    "evaluations": "closure_evaluation_id",
    "reflow_transitions": "transaction_id",
    "changes": "change_id",
    "reopen_condition_evaluations": "evaluation_id",
    "candidate_completion_records": "completion_id",
    "candidate_claim_evaluation_events": "event_id",
    "invariant_evaluations": "evaluation_id",
    "evidence_sufficiency_results": "evidence_sufficiency_id",
}


def _merge(target: dict[str, dict[str, Any]], records: list[dict[str, Any]], key: str) -> None:
    for record in records:
        identity = record[key]
        existing = target.get(identity)
        if existing is not None and canonical_bytes(existing) != canonical_bytes(record):
            raise IdentityCollisionError(f"same-ID different-payload conflict: {identity}")
        target[identity] = deepcopy(record)


def _absorb_observation_context(
    bundle: dict[str, Any],
    observation: dict[str, Any],
    observations: dict[str, dict[str, Any]],
    facts: dict[str, dict[str, Any]],
    fact_bindings: dict[str, dict[str, Any]],
    fact_evaluations: dict[str, dict[str, Any]],
    negative_observations: dict[str, dict[str, Any]],
    negative_evaluations: dict[str, dict[str, Any]],
) -> None:
    """Carry the exact Observation records a cross-record validator must resolve."""

    _merge(observations, [observation], "observation_id")
    referenced = {reference["id"] for reference in observation["normalized_fact_refs"]}
    _merge(facts, [item for item in bundle["facts"] if item["fact_id"] in referenced], "fact_id")
    _merge(
        fact_bindings,
        [
            item
            for item in bundle["bindings"]
            if item["observation_id"] == observation["observation_id"]
        ],
        "binding_id",
    )
    _merge(
        fact_evaluations,
        [item for item in bundle["fact_evaluations"] if item["fact_id"] in referenced],
        "evaluation_id",
    )
    negatives = [
        item
        for item in bundle["negative_observations"]
        if item["observation_id"] == observation["observation_id"]
    ]
    _merge(negative_observations, negatives, "negative_observation_id")
    negative_ids = {item["negative_observation_id"] for item in negatives}
    _merge(
        negative_evaluations,
        [
            item
            for item in bundle["negative_evaluations"]
            if item["negative_observation_id"] in negative_ids
        ],
        "evaluation_id",
    )


def _absorb_predecessor_context(
    predecessor: dict[str, Any],
    objective_revisions: dict[str, dict[str, Any]],
    policies: list[dict[str, Any]],
    scopes: dict[str, dict[str, Any]],
    observations: dict[str, dict[str, Any]],
    facts: dict[str, dict[str, Any]],
    fact_bindings: dict[str, dict[str, Any]],
    fact_evaluations: dict[str, dict[str, Any]],
    negative_observations: dict[str, dict[str, Any]],
    negative_evaluations: dict[str, dict[str, Any]],
    requests: list[dict[str, Any]],
    methods: dict[str, dict[str, Any]],
    carried: dict[str, dict[str, dict[str, Any]]],
) -> None:
    """Carry forward every record that keeps the retained predecessor lineage resolvable.

    The Engine never creates any of these; it only preserves what the caller supplied, so
    that a retained event's own references still resolve inside the returned bundle.
    """

    context = predecessor.get("context", {})
    _merge(objective_revisions, context.get("objective_revisions", []), "objective_revision_id")
    policies.extend(deepcopy(context.get("policies", [])))
    _merge(scopes, context.get("observation_scopes", []), "scope_id")
    _merge(observations, context.get("observations", []), "observation_id")
    _merge(facts, context.get("normalized_facts", []), "fact_id")
    _merge(fact_bindings, context.get("fact_observation_bindings", []), "binding_id")
    _merge(fact_evaluations, context.get("fact_evaluations", []), "evaluation_id")
    _merge(
        negative_observations, context.get("negative_observations", []), "negative_observation_id"
    )
    _merge(
        negative_evaluations,
        context.get("negative_observation_evaluations", []),
        "evaluation_id",
    )
    existing_requests = {item["observation_request_id"] for item in requests}
    for request in context.get("next_observation_requests", []):
        if request["observation_request_id"] not in existing_requests:
            requests.append(deepcopy(request))
            existing_requests.add(request["observation_request_id"])
    _merge(methods, context.get("observation_methods", []), "observation_method_id")
    for section, key in _CARRIED_SECTIONS.items():
        _merge(carried.setdefault(section, {}), context.get(section, []), key)


def _carried(
    carried: dict[str, dict[str, dict[str, Any]]], section: str, key: str
) -> list[dict[str, Any]]:
    """Return one carried-forward dependency section in deterministic identity order."""

    return sorted(carried.get(section, {}).values(), key=lambda item: str(item[key]))


def _finalize(
    request: dict[str, Any],
    objective_revisions: dict[str, dict[str, Any]],
    differences: dict[str, dict[str, Any]],
    events: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    requests: list[dict[str, Any]],
    methods: dict[str, dict[str, Any]],
    scopes: dict[str, dict[str, Any]],
    observations: dict[str, dict[str, Any]],
    facts: dict[str, dict[str, Any]],
    fact_bindings: dict[str, dict[str, Any]],
    fact_evaluations: dict[str, dict[str, Any]],
    negative_observations: dict[str, dict[str, Any]],
    negative_evaluations: dict[str, dict[str, Any]],
    materialized_status: dict[str, str],
    satisfied: list[str],
    state_revision: int,
    state_fingerprint: dict[str, Any],
    carried: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    unique_events: dict[str, dict[str, Any]] = {}
    _merge(unique_events, events, "difference_event_id")
    unique_policies: dict[str, dict[str, Any]] = {}
    _merge(unique_policies, policies, "closure_policy_id")
    bundle: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "identity_profile": IDENTITY_PROFILE,
        "comparison_profile": COMPARISON_PROFILE,
        "normalization_profile": NORMALIZATION_PROFILE,
        "current_state_ref": {
            "kind": "state",
            "revision": state_revision,
            "fingerprint": deepcopy(state_fingerprint),
        },
        "objective_revisions": sorted(
            objective_revisions.values(), key=lambda item: item["objective_revision_id"]
        ),
        "differences": sorted(differences.values(), key=lambda item: item["difference_id"]),
        "events": sorted(
            unique_events.values(),
            key=lambda item: (item["difference_id"], item["event_revision"]),
        ),
        "policies": sorted(unique_policies.values(), key=lambda item: item["closure_policy_id"]),
        "evaluations": _carried(carried, "evaluations", "closure_evaluation_id"),
        "supersession_relations": sorted(
            relations, key=lambda item: item["supersession_relation_id"]
        ),
        "next_observation_requests": sorted(
            requests, key=lambda item: item["observation_request_id"]
        ),
        "observation_methods": sorted(
            methods.values(), key=lambda item: item["observation_method_id"]
        ),
        "observation_scopes": sorted(scopes.values(), key=lambda item: item["scope_id"]),
        "observations": sorted(observations.values(), key=lambda item: item["observation_id"]),
        "normalized_facts": sorted(facts.values(), key=lambda item: item["fact_id"]),
        "fact_observation_bindings": sorted(
            fact_bindings.values(), key=lambda item: item["binding_id"]
        ),
        "fact_evaluations": sorted(
            fact_evaluations.values(), key=lambda item: item["evaluation_id"]
        ),
        "negative_observations": sorted(
            negative_observations.values(), key=lambda item: item["negative_observation_id"]
        ),
        "negative_observation_evaluations": sorted(
            negative_evaluations.values(), key=lambda item: item["evaluation_id"]
        ),
        "candidate_completion_records": _carried(
            carried, "candidate_completion_records", "completion_id"
        ),
        "candidate_claim_evaluation_events": _carried(
            carried, "candidate_claim_evaluation_events", "event_id"
        ),
        "invariant_evaluations": _carried(carried, "invariant_evaluations", "evaluation_id"),
        "evidence_sufficiency_results": _carried(
            carried, "evidence_sufficiency_results", "evidence_sufficiency_id"
        ),
        "materialized_status": dict(sorted(materialized_status.items())),
        "satisfied_target_predicates": sorted(satisfied),
    }
    for section, key in _CARRIED_SECTIONS.items():
        if section in bundle:
            continue
        records = _carried(carried, section, key)
        if records:
            bundle[section] = records
    if set(bundle["materialized_status"]) != set(differences):
        raise DifferenceValidationError("materialized status does not cover every Difference")
    return bundle
