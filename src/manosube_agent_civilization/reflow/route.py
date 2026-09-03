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
"""

from __future__ import annotations

from typing import Any

from .bookkeeping import apply_reflow_bookkeeping
from .closure import evaluate_closure
from .commit import commit_reflow
from .engine import decide_transition
from .identity import closure_evaluation_decision_fingerprint, transaction_id
from .lifecycle import mint_transition_event


def reflow(
    store: Any,
    *,
    project_id: str,
    difference: dict[str, Any],
    current_status: str,
    previous_event_id: str,
    event_revision: int,
    before_project_state: dict[str, Any],
    closure_request: dict[str, Any],
    observation_refs: list[Any],
    evidence_refs: list[Any],
    reflow_instant: str,
    authority_ref: Any | None = None,
    change_refs: list[Any] | None = None,
    contradiction_refs: list[Any] | None = None,
    blocker_kind: str | None = None,
    blocker_scope: dict[str, Any] | None = None,
    blocker_resolution_condition: dict[str, Any] | None = None,
    next_observation_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one Reflow cycle to completion and return every record it produced.

    *closure_request* is exactly :func:`~manosube_agent_civilization.reflow.closure.
    evaluate_closure`'s own request. *before_project_state* is the canonical
    ``project_state`` :func:`~manosube_agent_civilization.reflow.commit.commit_reflow`
    will Compare-And-Swap against -- its ``semantic_state`` is what
    :func:`~manosube_agent_civilization.reflow.bookkeeping.apply_reflow_bookkeeping`
    mutates. Returns ``{"evaluation", "decision", "next_semantic_state", "committed_state",
    "state_transition_ref", "event"}``.
    """

    evaluation = evaluate_closure(closure_request)
    decision = decide_transition(evaluation, current_status)

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

    committed_state, committed_ref = commit_reflow(
        store,
        project_id=project_id,
        before_project_state=before_project_state,
        next_semantic_state=next_semantic_state,
        transaction_id=tx,
        evidence_refs=evidence_refs,
        reflow_instant=reflow_instant,
    )
    return {
        "evaluation": evaluation,
        "decision": decision,
        "next_semantic_state": next_semantic_state,
        "committed_state": committed_state,
        "state_transition_ref": committed_ref,
        "event": lifecycle_event_placeholder,
    }
