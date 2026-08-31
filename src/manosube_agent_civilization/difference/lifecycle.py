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
    if event["to_status"] in {"RETAINED", "REOPENED"} and event["next_observation_ref"] is None:
        errors.append(f"next observation missing: {identity}")
    reference = event["next_observation_ref"]
    if reference is None:
        return errors

    request = requests.get(_reference_id(reference) or "")
    method = None if request is None else methods.get(_reference_id(request["method_ref"]) or "")
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
