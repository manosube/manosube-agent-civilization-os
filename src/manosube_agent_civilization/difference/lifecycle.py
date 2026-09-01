"""The single canonical Difference lifecycle transition authority.

``LEGAL_TRANSITIONS`` is the executable projection of the transition table in
``00_KERNEL/04_DIFFERENCE/DIFFERENCE_LIFECYCLE.md`` section 3. It is defined once here
and imported by every consumer, including the independent cross-record contract
validator, so no second transition table can drift from the contract.
"""

from __future__ import annotations

from typing import Any

LEGAL_TRANSITIONS: frozenset[tuple[str | None, str]] = frozenset(
    {
        (None, "DETECTED"),
        ("DETECTED", "OPEN"),
        ("DETECTED", "INVALIDATED"),
        ("OPEN", "ACTIVE"),
        ("OPEN", "BLOCKED"),
        ("OPEN", "RETAINED"),
        ("OPEN", "SUPERSEDED"),
        ("OPEN", "INVALIDATED"),
        ("ACTIVE", "VERIFYING"),
        ("ACTIVE", "BLOCKED"),
        ("ACTIVE", "RETAINED"),
        ("ACTIVE", "SUPERSEDED"),
        ("ACTIVE", "INVALIDATED"),
        ("VERIFYING", "CLOSED"),
        ("VERIFYING", "ACTIVE"),
        ("VERIFYING", "BLOCKED"),
        ("VERIFYING", "RETAINED"),
        ("VERIFYING", "SUPERSEDED"),
        ("VERIFYING", "INVALIDATED"),
        ("BLOCKED", "OPEN"),
        ("BLOCKED", "ACTIVE"),
        ("BLOCKED", "VERIFYING"),
        ("BLOCKED", "RETAINED"),
        ("BLOCKED", "SUPERSEDED"),
        ("BLOCKED", "INVALIDATED"),
        ("RETAINED", "OPEN"),
        ("RETAINED", "ACTIVE"),
        ("RETAINED", "VERIFYING"),
        ("RETAINED", "BLOCKED"),
        ("RETAINED", "SUPERSEDED"),
        ("RETAINED", "INVALIDATED"),
        ("CLOSED", "REOPENED"),
        ("CLOSED", "SUPERSEDED"),
        ("CLOSED", "INVALIDATED"),
        ("REOPENED", "ACTIVE"),
        ("REOPENED", "VERIFYING"),
        ("REOPENED", "BLOCKED"),
        ("REOPENED", "RETAINED"),
        ("REOPENED", "SUPERSEDED"),
        ("REOPENED", "INVALIDATED"),
    }
)

#: ``SUPERSEDED`` and ``INVALIDATED`` are terminal. ``CLOSED`` is not the end of history:
#: it can be reopened by contradiction, so it is not listed here.
TERMINAL_STATUSES: frozenset[str] = frozenset({"SUPERSEDED", "INVALIDATED"})

#: A status-preserving ``OBSERVATION_BOUND`` provenance append is never allowed on these.
OBSERVATION_BOUND_FORBIDDEN: frozenset[str] = frozenset(
    {"CLOSED", "SUPERSEDED", "INVALIDATED"}
)

#: Statuses whose lifecycle event must carry a Next Observation Request.
REQUIRES_NEXT_OBSERVATION: frozenset[str] = frozenset({"BLOCKED", "RETAINED", "REOPENED"})

#: A terminal status is settled: it can never request a further observation.
NEXT_OBSERVATION_FORBIDDEN: frozenset[str] = frozenset({"SUPERSEDED", "INVALIDATED"})

#: The Next Observation Request reason code each such status requires.
NEXT_OBSERVATION_REASON: dict[str, str] = {
    "BLOCKED": "BLOCKER_REOBSERVATION",
    "RETAINED": "RETAINED_REOBSERVATION",
    "REOPENED": "REOPEN_REOBSERVATION",
}


def is_legal_transition(from_status: str | None, to_status: str) -> bool:
    """Return whether the lifecycle contract permits this status transition."""

    return (from_status, to_status) in LEGAL_TRANSITIONS


def legal_supersession_sources() -> frozenset[str]:
    """Return every status whose legal transitions include ``SUPERSEDED``."""

    return frozenset(
        source
        for source, target in LEGAL_TRANSITIONS
        if target == "SUPERSEDED" and source is not None
    )


#: The resolution state each blocker condition code requires, transcribed from the
#: ``blocker_resolution_condition`` conditional schema in
#: ``01_SCHEMA/difference/difference_lifecycle_event.schema.json``.
BLOCKER_CONDITION_EXPECTED_STATE: dict[str, str] = {
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

#: The blocker payload fields a ``BLOCKED`` event must carry and every other event must
#: leave null.
BLOCKER_PAYLOAD_FIELDS: tuple[str, ...] = (
    "blocker_kind",
    "blocker_scope",
    "blocker_resolution_condition",
)


def _reference_id(reference: Any) -> str | None:
    if not isinstance(reference, dict):
        return None
    identity = reference.get("id")
    return identity if isinstance(identity, str) else None


def blocker_payload_errors(
    event: dict[str, Any], difference: dict[str, Any] | None
) -> list[str]:
    """Return every ``BLOCKED`` payload violation this event carries.

    The blocker payload is outside lifecycle event identity, so a schema-valid event can
    retain its ``difference_event_id`` while its blocker scope, effective boundary or
    resolution condition is forged. These rules are the executable projection of
    ``DIFFERENCE_LIFECYCLE.md`` section 4, owned here so the Engine and the independent
    cross-record validator decide them one way.
    """

    identity = event["difference_event_id"]
    errors: list[str] = []
    if event["to_status"] != "BLOCKED":
        if any(event[field] is not None for field in BLOCKER_PAYLOAD_FIELDS):
            errors.append(f"non-BLOCKED event carries blocker payload: {identity}")
        return errors

    if not event["evidence_refs"]:
        errors.append(f"blocked lifecycle Evidence missing: {identity}")
    scope = event["blocker_scope"]
    condition = event["blocker_resolution_condition"]
    if scope is None or condition is None or event["blocker_kind"] is None:
        errors.append(f"incomplete blocker payload: {identity}")
        return errors

    if not scope["affected_subject_refs"]["members"]:
        errors.append(f"empty blocker subject set: {identity}")
    if difference is not None and scope["effective_boundary"] != difference["effective_boundary"]:
        errors.append(f"blocker boundary mismatch: {identity}")
    if _reference_id(condition["verification_request_ref"]) != _reference_id(
        event["next_observation_ref"]
    ):
        errors.append(f"blocker verification request mismatch: {identity}")
    if condition["subject_ref"] not in scope["affected_subject_refs"]["members"]:
        errors.append(f"blocker condition subject mismatch: {identity}")
    if BLOCKER_CONDITION_EXPECTED_STATE.get(condition["condition_code"]) != condition[
        "expected_state"
    ]:
        errors.append(f"blocker condition state mismatch: {identity}")
    return errors


def next_observation_binding_errors(
    event: dict[str, Any],
    difference: dict[str, Any] | None,
    requests: dict[str, dict[str, Any]],
    methods: dict[str, dict[str, Any]],
    content_address: Any,
) -> list[str]:
    """Return every Next Observation Request binding violation this event carries.

    A request's content address covers its whole payload, so recomputing it is what makes
    a retained ``observation_request_id`` over an altered ``reason_code``, Scope, method or
    State binding fail closed. *content_address* is passed in so this authority stays free
    of an import cycle while every consumer supplies the same canonical function.
    """

    identity = event["difference_event_id"]
    errors: list[str] = []
    # BLOCKED's own requirement is stated by the blocker payload rule, which pins the
    # resolution condition's verification request to this same reference.
    if (
        event["to_status"] in REQUIRES_NEXT_OBSERVATION - {"BLOCKED"}
        and event["next_observation_ref"] is None
    ):
        errors.append(f"next observation missing: {identity}")
    if (
        event["to_status"] in NEXT_OBSERVATION_FORBIDDEN
        and event["next_observation_ref"] is not None
    ):
        errors.append(f"terminal status must not request a further observation: {identity}")
    reference = event["next_observation_ref"]
    if reference is None:
        return errors

    request = requests.get(_reference_id(reference) or "")
    method = None if request is None else methods.get(_reference_id(request["method_ref"]) or "")
    # A status that requires a Next Observation Request also fixes the reason that request
    # must carry: the reason states what the next observation has to resolve. The forward
    # reference is outside event identity, so without this a RETAINED event could point at
    # a REOPEN_REOBSERVATION request whose own content address recomputes perfectly, and
    # both producer and auditor would accept forged status provenance.
    if request is not None and event["to_status"] in NEXT_OBSERVATION_REASON:
        required = NEXT_OBSERVATION_REASON[event["to_status"]]
        if request["reason_code"] != required:
            errors.append(
                f"next observation reason does not match status: {identity} "
                f"({event['to_status']} requires {required}, got {request['reason_code']})"
            )
    if (
        reference.get("kind") != "next_observation_request"
        or request is None
        or difference is None
        or _reference_id(request["difference_ref"]) != difference["difference_id"]
        or _reference_id(request["derived_from_event_ref"]) != identity
        or request["state_revision_requested"] != event["state_revision_evaluated"]
        or request["state_fingerprint_requested"] != event["state_fingerprint_evaluated"]
        or request["target_ref"] != difference["target_predicate_ref"]
        or request["scope_ref"] != difference["objective_scope_binding"]["scope_ref"]
        or request["method_ref"].get("kind") != "observation_method"
        or method is None
        or request["observation_request_id"]
        != content_address("OBS-REQ-", request, "observation_request_id")
        or method["observation_method_id"]
        != content_address("OBS-METHOD-", method, "observation_method_id")
    ):
        errors.append(f"next observation binding mismatch: {identity}")
    return errors


#: Statuses whose ``TRANSITION`` event must carry the Closure Evaluation that authorised
#: it. ``REOPENED`` is not one of them: it re-references the *closure* it contradicts,
#: which is a different rule, stated below.
REQUIRES_CLOSURE_EVALUATION: frozenset[str] = frozenset({"CLOSED", "BLOCKED", "RETAINED"})


def _policy_binding_valid(
    reference: Any, policy: dict[str, Any] | None, policy_fingerprint: Any
) -> bool:
    if not isinstance(reference, dict) or policy is None:
        return False
    return bool(
        reference.get("id") == policy["closure_policy_id"]
        and reference.get("version") == policy["policy_version"]
        and reference.get("semantic_fingerprint") == policy["policy_semantic_fingerprint"]
        and policy["policy_semantic_fingerprint"] == policy_fingerprint(policy)
    )


def closure_evaluation_input_errors(
    evaluation: dict[str, Any],
    difference: dict[str, Any] | None,
    policies: dict[str, dict[str, Any]],
    events: dict[str, dict[str, Any]],
    policy_fingerprint: Any,
) -> list[str]:
    """Return every input-binding violation *one* Closure Evaluation carries.

    This decides the Evaluation against the records it names -- not against the lifecycle
    event that cites it, which is a separate rule. It therefore applies to **every**
    Evaluation the bundle carries, including one no transition references. That gap was
    real: an extra schema-valid Evaluation naming an existing Difference and resolvable
    policy and event records, but a different Target Predicate, was emitted unchallenged
    because the relational pass reached Evaluations only through events.

    An unreferenced Evaluation is *permitted* -- the contract carries Closure Evaluations
    as provenance and does not require a citing transition -- but it is not exempt: it must
    be as conformant as one that is cited.

    What is decided here is what the bundle alone can decide: subject Difference, Closure
    Policy binding, event head, Target Predicate, evaluated Objective semantics, and
    evaluated-State self-consistency. The Objective *editorial-revision chain* is left to
    the independent validator, which owns the multi-revision analysis this phase does not
    carry; ``LATER_PHASE_SEMANTICS_CLAIMED=false`` still applies to Evaluation execution.
    """

    identity = evaluation["closure_evaluation_id"]
    errors: list[str] = []
    if difference is None:
        errors.append(f"evaluation references missing Difference: {identity}")
        return errors

    policy = policies.get(_reference_id(evaluation["policy_ref"]) or "")
    if (
        policy is None
        or _reference_id(policy["subject_difference_ref"]) != evaluation["difference_id"]
        or policy["target_predicate_ref"] != difference["target_predicate_ref"]
        or not _policy_binding_valid(evaluation["policy_ref"], policy, policy_fingerprint)
        or evaluation["policy_version_evaluated"] != policy["policy_version"]
        or evaluation["policy_semantic_fingerprint_evaluated"]
        != policy["policy_semantic_fingerprint"]
    ):
        errors.append(f"evaluation Policy binding mismatch: {identity}")

    head = events.get(_reference_id(evaluation["difference_event_head_ref"]) or "")
    if head is None or head["difference_id"] != evaluation["difference_id"]:
        errors.append(f"evaluation event-head mismatch: {identity}")

    if (
        evaluation["target_predicate_ref"] != difference["target_predicate_ref"]
        or evaluation["objective_semantic_fingerprint_evaluated"]
        != difference["objective_semantic_fingerprint"]
        or evaluation["before_state_ref"]["revision"] != evaluation["evaluated_state_revision"]
        or evaluation["before_state_ref"]["fingerprint"]
        != evaluation["evaluated_state_fingerprint"]
        or (
            head is not None
            and (
                evaluation["evaluated_state_revision"] != head["state_revision_evaluated"]
                or evaluation["evaluated_state_fingerprint"]
                != head["state_fingerprint_evaluated"]
            )
        )
    ):
        errors.append(f"evaluation Difference input mismatch: {identity}")
    return errors


def closure_evaluation_binding_errors(
    event: dict[str, Any],
    previous_event: dict[str, Any] | None,
    difference: dict[str, Any] | None,
    evaluations: dict[str, dict[str, Any]],
    policies: dict[str, dict[str, Any]],
    policy_fingerprint: Any,
) -> list[str]:
    """Return every Closure Evaluation binding violation this lifecycle event carries.

    A Closure Evaluation is provenance a later canonical owner produces; this phase does
    not execute one and claims nothing about how it was decided. What it does decide is
    whether the *binding* between an event and the Evaluation it names is authentic --
    which is entirely outside lifecycle event identity, so a schema-valid event can retain
    its ``difference_event_id`` while naming an Evaluation belonging to another Difference,
    another event head, another Closure Policy, another evaluated State, or proposing a
    different terminal status than the one the event actually entered.

    The rules are the executable projection of ``DIFFERENCE_LIFECYCLE.md`` sections 5 and
    7. They are owned here so the Engine and the independent cross-record validator decide
    them one way; *policy_fingerprint* is passed in for the same reason ``content_address``
    is, so neither consumer has to import the other.

    The ``CLOSED`` Reflow commitment window is *not* decided here: Reflow is a later
    element with no schema in v0.1, and its own owner enforces it. The independent
    validator keeps that check, and this phase claims nothing about it.
    """

    identity = event["difference_event_id"]
    errors: list[str] = []
    reference = event.get("closure_evaluation_ref")
    evaluation = evaluations.get(_reference_id(reference) or "")
    difference_id = event["difference_id"]

    # Whatever the status, an event that names a Closure Evaluation must name one that
    # resolves and that belongs to this same Difference.
    if reference is not None:
        if evaluation is None:
            errors.append(f"closure evaluation does not resolve: {identity}")
            return errors
        if evaluation["difference_id"] != difference_id:
            errors.append(f"closure evaluation names another Difference: {identity}")

    if event["event_kind"] == "TRANSITION" and event["to_status"] in REQUIRES_CLOSURE_EVALUATION:
        policy = (
            None
            if difference is None
            else policies.get(difference["closure_policy"]["id"])
        )
        if (
            evaluation is None
            or evaluation["proposed_terminal_status"] != event["to_status"]
            or evaluation["gate_results"]["G22"] != "PASS"
            or not _policy_binding_valid(evaluation["policy_ref"], policy, policy_fingerprint)
            or _reference_id(evaluation["difference_event_head_ref"])
            != event["previous_event_id"]
            or evaluation["evaluated_state_revision"] != event["state_revision_evaluated"]
            or evaluation["evaluated_state_fingerprint"] != event["state_fingerprint_evaluated"]
            or (
                difference is not None
                and (
                    evaluation["target_predicate_ref"] != difference["target_predicate_ref"]
                    # The *semantic* fingerprint is the binding, not the revision
                    # reference: an editorial Objective revision carrying the same
                    # semantics is a legitimate evaluation subject, and equating the
                    # revision ids would reject it.
                    or evaluation["objective_semantic_fingerprint_evaluated"]
                    != difference["objective_semantic_fingerprint"]
                )
            )
        ):
            errors.append(f"terminal evaluation binding mismatch: {identity}")

    # A reopen contradicts one specific closure: the Evaluation the CLOSED head named.
    is_reopen = event["from_status"] == "CLOSED" and event["to_status"] == "REOPENED"
    if is_reopen and (
            previous_event is None
            or _reference_id(previous_event.get("closure_evaluation_ref"))
            != _reference_id(reference)
            or evaluation is None
            or evaluation["proposed_terminal_status"] != "CLOSED"
            or evaluation["result"] != "SATISFIED"
            or evaluation["gate_results"]["G22"] != "PASS"
    ):
        errors.append(f"reopen closure binding mismatch: {identity}")
    return errors
