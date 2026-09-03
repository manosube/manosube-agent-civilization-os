"""Mint the one ``difference_lifecycle_event`` a Reflow decision admits.

Difference owns the lifecycle event schema, its legality table (``is_legal_transition``)
and its binding validators (``closure_evaluation_binding_errors``,
``blocker_payload_errors``, ``next_observation_binding_errors`` in
``difference/lifecycle.py``). This module mints one conformant record and then runs those
same validators against it before returning -- so a record this module produces is proven
against the one authority that decides whether it is real, not merely schema-shaped.

``next_observation_ref`` and the ``BLOCKED`` blocker payload are the one thing this module
does not mint: they are Next Observation Request and blocker-scope provenance Difference's
own Observation-binding machinery owns (``difference/engine.py``'s private
``_next_observation_request`` and ``_retained_blocker_payload``), and duplicating that here
would be a second, drifting copy of the same minting logic. A caller of
:func:`mint_transition_event` supplies them already minted, for the ``BLOCKED``/``RETAINED``
routes that require one; this module still refuses to return a record whose binding to them
does not check out.
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.identity import lifecycle_event_id
from manosube_agent_civilization.difference.lifecycle import (
    NEXT_OBSERVATION_FORBIDDEN,
    REQUIRES_CLOSURE_EVALUATION,
    REQUIRES_NEXT_OBSERVATION,
    blocker_payload_errors,
    is_legal_transition,
)

from .errors import ReflowValidationError

SCHEMA_VERSION = "0.1"


def mint_transition_event(
    *,
    difference: dict[str, Any],
    current_status: str,
    previous_event_id: str,
    event_revision: int,
    decision: dict[str, Any],
    evaluation: dict[str, Any] | None,
    observation_refs: list[Any],
    evidence_refs: list[Any],
    authority_ref: Any | None = None,
    change_refs: list[Any] | None = None,
    blocker_kind: str | None = None,
    blocker_scope: dict[str, Any] | None = None,
    blocker_resolution_condition: dict[str, Any] | None = None,
    next_observation_ref: dict[str, Any] | None = None,
    reflow_transition_ref: dict[str, Any] | None = None,
    reopen_trigger: str | None = None,
    contradiction_evidence_refs: list[Any] | None = None,
) -> dict[str, Any]:
    """Return one schema-conformant, binding-valid ``TRANSITION`` lifecycle event.

    *decision* is :func:`~manosube_agent_civilization.reflow.engine.decide_transition`'s
    return value for every route except Reopen, which instead is
    :func:`~manosube_agent_civilization.reflow.reopen.decide_reopen`'s -- Reopen does not
    run a fresh Closure Evaluation, so its own ``closure_evaluation_ref`` re-references the
    Evaluation being contradicted rather than one just computed, and this function accepts
    either shape because both carry the same three keys (``to_status``, ``reason_code``,
    ``reason``, ``closure_evaluation_ref``). *evaluation* is the Closure Evaluation the
    decision was decided from -- required whenever *decision*'s ``to_status`` is one of
    ``CLOSED``/``BLOCKED``/``RETAINED``
    (:data:`~manosube_agent_civilization.difference.lifecycle.REQUIRES_CLOSURE_EVALUATION`)
    or ``REOPENED`` from ``CLOSED`` -- and used only to bind
    ``state_revision_evaluated``/``state_fingerprint_evaluated`` to the exact State the
    Evaluation itself was computed against.
    """

    to_status = decision["to_status"]
    if not is_legal_transition(current_status, to_status):
        raise ReflowValidationError(
            f"not a legal transition: {current_status!r} -> {to_status!r}"
        )
    is_reopen = current_status == "CLOSED" and to_status == "REOPENED"

    if evaluation is None:
        raise ReflowValidationError("a Closure Evaluation is required to mint any transition")
    state_revision = evaluation["evaluated_state_revision"]
    state_fingerprint = evaluation["evaluated_state_fingerprint"]

    if to_status in REQUIRES_NEXT_OBSERVATION and next_observation_ref is None:
        raise ReflowValidationError(f"{to_status} requires a next_observation_ref")
    if to_status in NEXT_OBSERVATION_FORBIDDEN and next_observation_ref is not None:
        raise ReflowValidationError(f"{to_status} must not carry a next_observation_ref")
    if to_status == "CLOSED" and reflow_transition_ref is None:
        # The schema itself requires this non-null for CLOSED. The Atomic State commit
        # (a later step of this same Reflow element, not this module) is what mints the
        # real reference; this module never fabricates one, so a caller reaching CLOSED
        # without having committed first is refused here rather than let through with a
        # placeholder.
        raise ReflowValidationError(
            "CLOSED requires reflow_transition_ref from a completed Atomic State commit"
        )
    if is_reopen and reopen_trigger is None:
        raise ReflowValidationError("CLOSED -> REOPENED requires a reopen_trigger")
    if not is_reopen and reopen_trigger is not None:
        raise ReflowValidationError("reopen_trigger is only valid on CLOSED -> REOPENED")

    event: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "difference_event_id": "",
        "difference_id": difference["difference_id"],
        "event_kind": "TRANSITION",
        "event_revision": event_revision,
        "previous_event_id": previous_event_id,
        "from_status": current_status,
        "to_status": to_status,
        "state_revision_evaluated": state_revision,
        "state_fingerprint_evaluated": state_fingerprint,
        "reason_code": decision["reason_code"],
        "reason": decision["reason"],
        "blocker_kind": blocker_kind,
        "blocker_scope": blocker_scope,
        "blocker_resolution_condition": blocker_resolution_condition,
        "observation_refs": list(observation_refs),
        "evidence_refs": list(evidence_refs),
        "authority_ref": authority_ref,
        "change_refs": list(change_refs) if change_refs is not None else [],
        "closure_evaluation_ref": decision.get("closure_evaluation_ref")
        if (to_status in REQUIRES_CLOSURE_EVALUATION or is_reopen)
        else None,
        "reflow_transition_ref": reflow_transition_ref,
        "next_observation_ref": next_observation_ref,
        "reopen_trigger": reopen_trigger,
        "reopen_condition_ref": None,
        "reopen_condition_evaluation_ref": None,
        "revoked_evidence_refs": [],
        "invalid_evidence_refs": [],
        "contradiction_evidence_refs": list(contradiction_evidence_refs)
        if contradiction_evidence_refs is not None
        else [],
    }
    event["difference_event_id"] = lifecycle_event_id(event)

    errors = blocker_payload_errors(event, difference)
    if errors:
        raise ReflowValidationError(f"minted event fails blocker payload validation: {errors[0]}")

    return event
