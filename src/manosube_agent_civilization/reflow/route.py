"""Reflow's single composed entry point: evaluate, decide, mint, commit -- once.

``00_KERNEL/08_REFLOW/REFLOW_CONTRACT.md`` names Reflow as
``EVIDENCE EVALUATION + CLOSURE EVALUATION + ATOMIC STATE TRANSITION + LINEAGE APPEND +
MATERIALIZED STATE UPDATE + NEXT OBSERVATION DERIVATION``. This module is the one function
that runs all of it. The transaction identity a ``CLOSED`` event's ``reflow_transition_ref``
must carry (``difference_lifecycle_event.schema.json`` requires it non-null) is a pure
function of already-known inputs (:func:`~manosube_agent_civilization.reflow.identity.
transaction_id`), so it is computed and the event minted with it *before* the commit that
makes it real -- the mint and the bookkeeping mutation it feeds are pure and produce
nothing this function returns on their own. Only :func:`~manosube_agent_civilization.
reflow.commit.commit_reflow` has an externally visible effect, and every value this
function returns is returned strictly after that call has actually succeeded; a failed
commit raises before any of the pre-computed records are handed back, so no lifecycle
event or bookkeeping mutation for an uncommitted transition is ever observable outside
this function.

Every Reflow outcome commits a State transition, not only a closing one -- R-005
(``FAILED_AND_BLOCKED_RESULTS_REFLOWED`` in ``KERNEL_INVARIANTS.md`` section 11) is why a
``BLOCKED``/``RETAINED``/``STALE``/``NOT_SATISFIED``/``CONTRADICTED`` Closure Evaluation
still reaches :func:`reflow` and still produces a real, committed ``state_transition``: the
Difference's status, the Evidence it now carries, any Material Contradiction, and
``reflow_state.last_transaction_ref`` are Kernel bookkeeping the Kernel loop needs updated
regardless of whether the Difference closed.

**Provenance by reproduction, restored (Phase 7 structural-review correction).** Neither
``reflow`` nor :func:`reopen` trusts a caller-restated predecessor any more: the canonical
predecessor State is always obtained from ``store.load_current`` (F1), the Closure
Evaluation's own ``current_state`` is always overridden to that exact loaded State before
it is evaluated (F2), the committed ``evidence_refs`` are always derived from what the
Evaluation itself admitted rather than taken from a second, caller-selected list (F6), and
:func:`reopen` resolves the Closure Evaluation it is reopening from the Store's own
committed lifecycle chain rather than accepting one directly (F7). Every immutable record
either function's committed ``state_transition`` references -- the Closure Evaluation, the
minted lifecycle event, and any admitted Evidence this vertical can reproduce from a raw
request rather than a bare reference -- is staged and promoted in the *same* atomic Store
transaction (F3), and a Closure Evaluation's own ``evaluation_expires_at`` is re-checked
against the explicit ``reflow_instant`` immediately before that commit (F5/G18).
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.identity import lifecycle_event_id
from manosube_agent_civilization.evidence.engine import derive_evidence
from manosube_agent_civilization.evidence.sufficiency import evaluate_sufficiency

from .bookkeeping import apply_reflow_bookkeeping
from .closure import evaluate_closure
from .commit import commit_reflow
from .engine import decide_transition
from .errors import ReflowValidationError, StaleReflowError
from .identity import closure_evaluation_decision_fingerprint, closure_evaluation_id, transaction_id
from .lifecycle import mint_transition_event
from .reopen import decide_reopen


def _check_expected_state(
    before_project_state: dict[str, Any],
    *,
    expected_state_revision: int | None,
    expected_state_fingerprint: dict[str, Any] | None,
) -> None:
    """F1: refuse fast if a caller's own expectation of the predecessor State has moved.

    Neither check is what makes the commit atomic -- ``FileStateStore.commit`` still does
    that with its own Compare-And-Swap against whatever revision/fingerprint this function
    goes on to load -- this is only an early, more specific refusal for a caller who built
    its request against a State that has already been superseded by the time it calls in.
    """

    if (
        expected_state_revision is not None
        and before_project_state["state_revision"] != expected_state_revision
    ):
        raise StaleReflowError(
            f"expected_state_revision {expected_state_revision} does not match the "
            f"Store's current revision {before_project_state['state_revision']}"
        )
    if (
        expected_state_fingerprint is not None
        and before_project_state["semantic_fingerprint"] != dict(expected_state_fingerprint)
    ):
        raise StaleReflowError(
            "expected_state_fingerprint does not match the Store's current State"
        )


def _derive_evidence_refs(
    evaluation: dict[str, Any], sufficiency: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """F6: the committed Evidence reference set, derived only from admitted inputs.

    Every source here is something the Closure Evaluation itself recorded, or the real
    Evidence Sufficiency Result the same ``evidence_sufficiency_request`` reproduces --
    never a second, caller-selected ``evidence_refs`` list a caller could otherwise
    substitute, omit, duplicate, or point at a foreign Evidence record.
    """

    refs: dict[tuple[str, str], dict[str, Any]] = {}
    for ref in evaluation["change_result_evidence_refs"]:
        refs[(ref["kind"], ref["id"])] = ref
    for ref in evaluation["change_free_verification_evidence_refs"]:
        refs[(ref["kind"], ref["id"])] = ref
    for ref in evaluation["terminal_reason_evidence_refs"]:
        refs[(ref["kind"], ref["id"])] = ref
    if sufficiency is not None:
        for ref in sufficiency["evidence_refs"]["members"]:
            refs[(ref["kind"], ref["id"])] = ref
    return [refs[key] for key in sorted(refs)]


def _admitted_records(
    evaluation: dict[str, Any],
    lifecycle_event: dict[str, Any],
    closure_request: dict[str, Any],
) -> list[tuple[str, str, dict[str, Any]]]:
    """F3: every immutable record this transition's commit must make reference-resolvable.

    The Closure Evaluation and the minted lifecycle event are always included. Admitted
    Evidence is included wherever this vertical can *reproduce* the record from a raw
    request the caller supplied (the Evidence Sufficiency request's own ``evidence_requests``,
    and, for a CHANGE_BOUND resolution, ``change_result_evidence_requests``) -- Evidence
    named only by a bare reference (``change_free_verification_evidence_refs``,
    ``terminal_reason_evidence_refs``) has no body this vertical can independently derive,
    and is committed by reference only, exactly as before this correction.
    """

    records: dict[tuple[str, str], dict[str, Any]] = {
        ("closure_evaluation", evaluation["closure_evaluation_id"]): evaluation,
        ("difference_lifecycle_event", lifecycle_event["difference_event_id"]): lifecycle_event,
    }
    sufficiency_request = closure_request.get("evidence_sufficiency_request")
    if isinstance(sufficiency_request, dict):
        for item in sufficiency_request.get("evidence_requests") or []:
            record = derive_evidence(item)
            records[("observation_evidence", record["evidence_id"])] = record
    for item in closure_request.get("change_result_evidence_requests") or []:
        record = derive_evidence(item)
        records[("observation_evidence", record["evidence_id"])] = record
    return [(kind, record_id, body) for (kind, record_id), body in sorted(records.items())]


def reflow(
    store: Any,
    *,
    project_id: str,
    difference: dict[str, Any],
    current_status: str,
    previous_event_id: str,
    event_revision: int,
    closure_request: dict[str, Any],
    observation_refs: list[Any],
    reflow_instant: str,
    expected_state_revision: int | None = None,
    expected_state_fingerprint: dict[str, Any] | None = None,
    authority_ref: Any | None = None,
    change_refs: list[Any] | None = None,
    contradiction_refs: list[Any] | None = None,
    blocker_kind: str | None = None,
    blocker_scope: dict[str, Any] | None = None,
    blocker_resolution_condition: dict[str, Any] | None = None,
    next_observation_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one Reflow cycle to completion and return every record it produced.

    *closure_request* is :func:`~manosube_agent_civilization.reflow.closure.
    evaluate_closure`'s own request, except its ``current_state`` is always overridden here
    (F2) to the canonical predecessor State this function itself loads from *store* (F1) --
    a caller-supplied ``current_state`` is silently replaced, never trusted. *evidence_refs*
    is no longer a caller parameter: it is derived (F6) from what the Evaluation itself
    admits. Returns ``{"evaluation", "decision", "next_semantic_state", "committed_state",
    "state_transition_ref", "event"}``.
    """

    before_project_state = store.load_current(project_id)
    if before_project_state["project_id"] != project_id:
        raise ReflowValidationError("the Store's current State belongs to a different project")
    _check_expected_state(
        before_project_state,
        expected_state_revision=expected_state_revision,
        expected_state_fingerprint=expected_state_fingerprint,
    )

    closure_request = dict(closure_request)
    closure_request["current_state"] = {
        "revision": before_project_state["state_revision"],
        "fingerprint": before_project_state["semantic_fingerprint"],
    }

    evaluation = evaluate_closure(closure_request)
    decision = decide_transition(evaluation, current_status)

    sufficiency_request = closure_request.get("evidence_sufficiency_request")
    sufficiency = (
        evaluate_sufficiency(sufficiency_request)["evidence_sufficiency_result"]
        if isinstance(sufficiency_request, dict)
        else None
    )
    evidence_refs = _derive_evidence_refs(evaluation, sufficiency)

    difference_ref = {"kind": "difference", "id": difference["difference_id"]}
    tx = transaction_id(
        project_id=project_id,
        difference_id=difference["difference_id"],
        closure_decision_fingerprint=closure_evaluation_decision_fingerprint(evaluation),
        evidence_sufficiency_id=(
            evaluation["evidence_sufficiency_ref"]["id"]
            if evaluation["evidence_sufficiency_ref"] is not None
            else None
        ),
        expected_revision=before_project_state["state_revision"],
        reflow_instant=reflow_instant,
    )

    # tx is a pure function of already-known inputs, so the reference a CLOSED event must
    # carry is known before the commit that makes it real. Minting now is safe only
    # because nothing below is returned unless commit_reflow, below, actually succeeds.
    state_transition_ref = {"kind": "state_transition", "id": tx}
    lifecycle_event_placeholder = mint_transition_event(
        difference=difference,
        current_status=current_status,
        previous_event_id=previous_event_id,
        event_revision=event_revision,
        decision=decision,
        evaluation=evaluation,
        observation_refs=observation_refs,
        evidence_refs=evidence_refs,
        authority_ref=authority_ref,
        change_refs=change_refs,
        blocker_kind=blocker_kind,
        blocker_scope=blocker_scope,
        blocker_resolution_condition=blocker_resolution_condition,
        next_observation_ref=next_observation_ref,
        reflow_transition_ref=state_transition_ref if decision["to_status"] == "CLOSED" else None,
    )
    lifecycle_event_ref = {
        "kind": "difference_event",
        "id": lifecycle_event_placeholder["difference_event_id"],
    }

    next_semantic_state = apply_reflow_bookkeeping(
        before_project_state["semantic_state"],
        difference_ref=difference_ref,
        to_status=decision["to_status"],
        new_evidence_refs=evidence_refs,
        lifecycle_event_ref=lifecycle_event_ref,
        contradiction_refs=contradiction_refs or [],
        transaction_ref=state_transition_ref,
    )

    records = _admitted_records(evaluation, lifecycle_event_placeholder, closure_request)

    committed_state, committed_ref = commit_reflow(
        store,
        project_id=project_id,
        before_project_state=before_project_state,
        next_semantic_state=next_semantic_state,
        transaction_id=tx,
        evidence_refs=evidence_refs,
        reflow_instant=reflow_instant,
        records=records,
        evaluation_expires_at=evaluation["evaluation_expires_at"],
    )
    return {
        "evaluation": evaluation,
        "decision": decision,
        "next_semantic_state": next_semantic_state,
        "committed_state": committed_state,
        "state_transition_ref": committed_ref,
        "event": lifecycle_event_placeholder,
    }


def _resolve_closed_closure_evaluation(
    store: Any, project_id: str, *, difference_id: str, previous_event_id: str
) -> dict[str, Any]:
    """F7: resolve the Closure Evaluation a Reopen contradicts from the Store's own record.

    *previous_event_id* must resolve to a committed ``difference_lifecycle_event`` that:
    is the exact event this call names (its own content address is checked against
    ``lifecycle_event_id``); belongs to *difference_id*; is itself the ``CLOSED`` head, not
    some earlier or unrelated event; and carries a ``closure_evaluation_ref`` that in turn
    resolves to a committed ``closure_evaluation`` record belonging to the same Difference
    and whose own content address (:func:`~manosube_agent_civilization.reflow.identity.
    closure_evaluation_id`) matches what the event named. Every step fails closed: a caller
    can no longer hand this function an unrelated, forged, or stale Closure Evaluation and
    have it accepted as the one that actually closed the Difference.
    """

    closed_event = store.resolve_record(project_id, "difference_lifecycle_event", previous_event_id)
    if closed_event is None:
        raise ReflowValidationError(
            f"previous_event_id does not resolve to a committed lifecycle event: "
            f"{previous_event_id!r}"
        )
    if closed_event.get("difference_event_id") != lifecycle_event_id(closed_event):
        raise ReflowValidationError(
            "resolved lifecycle event fails its own content address"
        )
    if closed_event["difference_id"] != difference_id:
        raise ReflowValidationError("previous_event_id belongs to a different Difference")
    if closed_event["to_status"] != "CLOSED":
        raise ReflowValidationError(
            "reopen requires the committed CLOSED lifecycle event, not "
            f"{closed_event['to_status']!r}"
        )
    closure_ref = closed_event.get("closure_evaluation_ref")
    if not isinstance(closure_ref, dict) or not closure_ref.get("id"):
        raise ReflowValidationError(
            "the committed CLOSED lifecycle event carries no closure_evaluation_ref"
        )

    old_closure_evaluation = store.resolve_record(project_id, "closure_evaluation", closure_ref["id"])
    if old_closure_evaluation is None:
        raise ReflowValidationError(
            f"closure_evaluation_ref does not resolve to a committed Closure Evaluation: "
            f"{closure_ref['id']!r}"
        )
    if old_closure_evaluation["difference_id"] != difference_id:
        raise ReflowValidationError("resolved Closure Evaluation belongs to a different Difference")
    if closure_evaluation_id(old_closure_evaluation) != closure_ref["id"]:
        raise ReflowValidationError("resolved Closure Evaluation fails its own content address")
    result: dict[str, Any] = old_closure_evaluation
    return result


def reopen(
    store: Any,
    *,
    project_id: str,
    difference: dict[str, Any],
    trigger: str,
    previous_event_id: str,
    event_revision: int,
    next_observation_ref: dict[str, Any],
    observation_refs: list[Any],
    contradiction_evidence_refs: list[Any],
    contradiction_refs: list[Any] | None = None,
    reflow_instant: str,
    expected_state_revision: int | None = None,
    expected_state_fingerprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one Reopen cycle: ``CLOSED -> REOPENED``, re-referencing the old closure.

    Unlike :func:`reflow`, this does not run :func:`~manosube_agent_civilization.reflow.
    closure.evaluate_closure` -- see :mod:`~manosube_agent_civilization.reflow.reopen` for
    why. The old Closure Evaluation is resolved from the Store's own committed lifecycle
    chain (F7), not accepted directly, and the predecessor State is likewise always the
    Store's canonical current one (F1), never a caller-restated body: ``REFLOW_CONTRACT.md``
    section 8's "Reopen preserves old Closure Evaluation/Evidence" means the *old* record
    stays untouched, not that this call may be handed a forged one to reopen against.
    """

    before_project_state = store.load_current(project_id)
    if before_project_state["project_id"] != project_id:
        raise ReflowValidationError("the Store's current State belongs to a different project")
    _check_expected_state(
        before_project_state,
        expected_state_revision=expected_state_revision,
        expected_state_fingerprint=expected_state_fingerprint,
    )

    old_closure_evaluation = _resolve_closed_closure_evaluation(
        store, project_id, difference_id=difference["difference_id"], previous_event_id=previous_event_id
    )

    decision = decide_reopen(old_closure_evaluation, trigger)
    difference_ref = {"kind": "difference", "id": difference["difference_id"]}
    tx = transaction_id(
        project_id=project_id,
        difference_id=difference["difference_id"],
        closure_decision_fingerprint=closure_evaluation_decision_fingerprint(old_closure_evaluation),
        evidence_sufficiency_id=None,
        expected_revision=before_project_state["state_revision"],
        reflow_instant=reflow_instant,
    )
    state_transition_ref = {"kind": "state_transition", "id": tx}

    # F6, applied to Reopen's narrower evidence surface: the only Evidence a Reopen
    # legitimately carries is what names the contradiction, so the committed set is
    # exactly that -- there is no second, independent evidence_refs a caller could
    # otherwise supply out of step with it.
    evidence_refs = list(contradiction_evidence_refs)

    event = mint_transition_event(
        difference=difference,
        current_status="CLOSED",
        previous_event_id=previous_event_id,
        event_revision=event_revision,
        decision=decision,
        evaluation={
            "evaluated_state_revision": before_project_state["state_revision"],
            "evaluated_state_fingerprint": before_project_state["semantic_fingerprint"],
        },
        observation_refs=observation_refs,
        evidence_refs=evidence_refs,
        next_observation_ref=next_observation_ref,
        reopen_trigger=trigger,
        contradiction_evidence_refs=contradiction_evidence_refs,
    )
    lifecycle_event_ref = {"kind": "difference_event", "id": event["difference_event_id"]}

    next_semantic_state = apply_reflow_bookkeeping(
        before_project_state["semantic_state"],
        difference_ref=difference_ref,
        to_status="REOPENED",
        new_evidence_refs=evidence_refs,
        lifecycle_event_ref=lifecycle_event_ref,
        contradiction_refs=contradiction_refs or [],
        transaction_ref=state_transition_ref,
    )

    records: list[tuple[str, str, dict[str, Any]]] = [
        ("difference_lifecycle_event", event["difference_event_id"], event),
    ]

    committed_state, committed_ref = commit_reflow(
        store,
        project_id=project_id,
        before_project_state=before_project_state,
        next_semantic_state=next_semantic_state,
        transaction_id=tx,
        evidence_refs=evidence_refs,
        reflow_instant=reflow_instant,
        records=records,
    )

    return {
        "decision": decision,
        "next_semantic_state": next_semantic_state,
        "committed_state": committed_state,
        "state_transition_ref": committed_ref,
        "event": event,
    }
