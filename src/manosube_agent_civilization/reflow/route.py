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

**Provenance by reproduction, restored (Phase 7 structural-review correction, rounds 1-2).**
Neither ``reflow`` nor :func:`reopen` trusts a caller-restated predecessor: the canonical
predecessor State is always obtained from ``store.load_current`` (F1), the Closure
Evaluation's own ``current_state`` is always overridden to that exact loaded State before
it is evaluated (F2), the committed ``evidence_refs`` are always derived from what the
Evaluation itself admitted rather than taken from a second, caller-selected list (F6), and
:func:`reopen` resolves the Closure Evaluation it is reopening from the Store's own
committed lifecycle chain rather than accepting one directly (F7).

**One canonical Difference/lifecycle input (R2-F1).** ``reflow`` takes no separate
``difference``/``current_status`` parameters any more -- there is exactly one Difference
and one current status per call, both read from ``closure_request`` itself, so a Closure
Evaluation computed for Difference A can no longer mint a lifecycle event or bookkeeping
mutation for a different Difference B. ``previous_event_id`` is verified against
``closure_request["difference_event_head_ref"]`` and, wherever it already resolves as a
real committed record, against the Store's own lifecycle chain (matching Difference,
matching ``to_status``, contiguous ``event_revision``); the one case that cannot resolve
from the Store -- the very first Reflow cycle from a Difference's own genesis event -- is
verified against the Difference's own ``genesis_event_ref`` instead.

**Complete reference closure (R2-F3, extended R5-F2).** Every immutable record either
function's committed ``state_transition`` references -- the Closure Evaluation, the minted
lifecycle event (stored under the same ``difference_event`` kind Difference's own reference
vocabulary already uses, not a second, unreachable kind), the Evidence Sufficiency Result,
the validated ``candidate_claim_evaluation_event`` chain and real Completion Record behind
every admitted Claim binding, the real Invariant Evaluation record behind every admitted
Invariant binding, the real ``kernel_source_witness`` record behind the Closure Evaluation's
own ``kernel_source_witness_ref`` (R6-F4 -- the verified Git COMMIT->TREE->PATH->BLOB object
bytes, not only the ``kernel_source_ref_evaluated`` claim, so G19's proof survives a process
restart), the real ``source_snapshot`` record behind every ``source_snapshot_refs`` entry
(R6-F1a -- owned by Observation, :mod:`observation.source_snapshot`), the real Evidence
record behind every ``change_free_verification_evidence_refs`` entry (R6-F1b -- owned by
Evidence, its own new ``CHANGE_FREE_VERIFICATION_EVIDENCE`` position, resolved and persisted
here exactly as Change-result Evidence already was, never produced by Reflow), and every
self-consistent after-state Observation record the reproduction actually consumed -- is
staged and promoted in the *same* atomic Store transaction, whose own manifest membership
now participates in that transaction's replay identity (R2-F3B, see ``store/file_store.py``).
Completion Record and Invariant Evaluation identity/resolution are owned by
:mod:`manosube_agent_civilization.difference.completion`/``.invariant_evaluation``
(R4-F2/R5-F2), not by Reflow -- this module resolves and persists what those owners produce,
it never becomes a second producer. ``terminal_reason_evidence_refs`` (R7-F4, Phase 7
structural-review round 7) is the same reproduce-and-persist treatment now too -- Evidence
remains the sole producer (:func:`~manosube_agent_civilization.evidence.engine.
derive_evidence`), reproduced from ``terminal_reason_evidence_requests`` and re-verified
immediately before *every* commit, not only a ``CLOSED`` one (``CLOSED`` is exactly the
outcome that never carries one).
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.difference.admissibility import require_object
from manosube_agent_civilization.difference.completion import (
    CANDIDATE_COMPLETION_RECORD_KIND,
    build_completion_record,
    resolve_claim_descriptor,
    resolve_completion_record,
)
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.identity import lifecycle_event_id
from manosube_agent_civilization.difference.invariant_evaluation import resolve_invariant_evaluation
from manosube_agent_civilization.difference.invariant_verifiers import (
    build_invariant_verification_context,
)
from manosube_agent_civilization.evidence.engine import derive_evidence
from manosube_agent_civilization.evidence.errors import EvidenceError
from manosube_agent_civilization.evidence.sufficiency import evaluate_sufficiency
from manosube_agent_civilization.observation.errors import ObservationError
from manosube_agent_civilization.observation.identity import observation_identity
from manosube_agent_civilization.observation.source_snapshot import resolve_source_snapshot

from .bookkeeping import apply_reflow_bookkeeping
from .claims import resolve_claim_binding
from .closure import evaluate_closure
from .commit import commit_reflow
from .engine import decide_transition
from .errors import ReflowValidationError, StaleReflowError
from .git_witness import build_kernel_source_witness_record, verify_kernel_source_witness
from .identity import closure_evaluation_decision_fingerprint, closure_evaluation_id, transaction_id
from .invariant_registry import KERNEL_INVARIANTS_BLOB_SHA, KERNEL_INVARIANTS_PATH
from .lifecycle import mint_transition_event
from .reopen import decide_reopen

#: The reference kind Difference's own vocabulary uses for a lifecycle event everywhere it
#: is named (``genesis_event_ref``, ``difference_event_head_ref``, ``derived_from_event_ref``,
#: ...) -- see ``difference/graph.py``'s ``"difference_event": "events"`` mapping. R2-F3:
#: this is also the Store manifest's storage kind now, so a reference this vertical
#: publishes always resolves under the exact kind it was published as.
LIFECYCLE_EVENT_KIND = "difference_event"


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


def _verify_lifecycle_ground_truth(
    store: Any,
    project_id: str,
    *,
    difference: dict[str, Any],
    current_status: str,
    previous_event_id: str,
    event_revision: int,
) -> None:
    """R2-F1: resolve/verify lifecycle ground truth from the canonical Store-owned chain.

    *previous_event_id* is expected to name a committed ``difference_event`` record. When
    it does, that record's own ``difference_id``, ``to_status`` and ``event_revision`` are
    checked against this call's inputs -- a caller cannot mint the next lifecycle event
    against a status or a Difference the actual committed chain disagrees with. The one
    case with nothing yet committed through Reflow's manifest -- the very first cycle from
    a Difference's own genesis event -- is instead checked against the Difference's own
    ``genesis_event_ref`` and ``event_revision == 1``.
    """

    resolved = store.resolve_record(project_id, LIFECYCLE_EVENT_KIND, previous_event_id)
    if resolved is not None:
        if resolved["difference_id"] != difference["difference_id"]:
            raise ReflowValidationError("previous_event_id belongs to a different Difference")
        if resolved["to_status"] != current_status:
            raise ReflowValidationError(
                "previous_event_id's committed to_status does not match current_status: "
                f"{resolved['to_status']!r} != {current_status!r}"
            )
        if resolved["event_revision"] + 1 != event_revision:
            raise ReflowValidationError(
                "event_revision is not contiguous with the resolved predecessor: "
                f"{resolved['event_revision']} + 1 != {event_revision}"
            )
        return

    genesis_ref = difference.get("genesis_event_ref") or {}
    if previous_event_id != genesis_ref.get("id"):
        raise ReflowValidationError(
            "previous_event_id does not resolve to a committed lifecycle event and is not "
            "the Difference's own genesis event"
        )
    if current_status != "VERIFYING":
        raise ReflowValidationError(
            "the first Reflow cycle from genesis requires current_status VERIFYING, not "
            f"{current_status!r}"
        )
    if event_revision != 1:
        raise ReflowValidationError(
            f"the first Reflow cycle from genesis must be event_revision 1, not {event_revision!r}"
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


def _self_consistent_after_observations(closure_request: dict[str, Any]) -> list[dict[str, Any]]:
    """R2-F3: the real, self-consistent after-state Observation records the reobservation
    derivation request actually carries -- reproduced by recomputing each one's own content
    address (:func:`~manosube_agent_civilization.observation.identity.observation_identity`),
    never trusted as a caller-supplied body. A record that fails its own identity check is
    silently excluded, not persisted -- the same "reproduce, don't trust" boundary R2-F4
    applies inside the evaluator applies here to what this vertical is willing to store.
    """

    reobservation = closure_request.get("reobservation")
    if not isinstance(reobservation, dict):
        return []
    request = reobservation.get("derivation_request")
    bindings = request.get("bindings") if isinstance(request, dict) else None
    if not isinstance(bindings, list) or not bindings:
        return []
    bundle = bindings[0].get("observation_bundle") if isinstance(bindings[0], dict) else None
    observations = bundle.get("observations") if isinstance(bundle, dict) else None
    if not isinstance(observations, list):
        return []
    verified: list[dict[str, Any]] = []
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        identity = observation.get("observation_id")
        if isinstance(identity, str) and identity and identity == observation_identity(observation):
            verified.append(observation)
    return verified


def _reproduced_evidence_for_context(closure_request: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(change_result_evidence, change_free_evidence)`` reproduced fresh from
    *closure_request*'s own requests -- R7-F1: the same real Evidence
    :func:`~manosube_agent_civilization.difference.invariant_verifiers.
    build_invariant_verification_context` binds an invariant-verification *context* to,
    reproduced here rather than trusted from *evaluation*'s own already-computed refs, the
    same pin-and-prove discipline every other admitted reference in this module follows. A
    request that no longer reproduces is not raised here: the caller's own reference-closure
    checks already reflect that failure, and an empty list for this one context field is a
    real answer -- there is no Evidence to bind the invariant check to.
    """

    change_result_evidence: list[dict[str, Any]] = []
    for item in closure_request.get("change_result_evidence_requests") or []:
        try:
            change_result_evidence.append(derive_evidence(item))
        except EvidenceError:
            return [], []
    change_free_evidence: list[dict[str, Any]] = []
    for item in closure_request.get("change_free_verification_evidence_requests") or []:
        try:
            change_free_evidence.append(derive_evidence(item))
        except EvidenceError:
            return [], []
    return change_result_evidence, change_free_evidence


def _invariant_verification_context(
    evaluation: dict[str, Any],
    closure_request: dict[str, Any],
    policy: dict[str, Any],
    sufficiency: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the same *context* :func:`~manosube_agent_civilization.reflow.closure.
    evaluate_closure`'s own G19 call built, from data this module already independently
    resolves at preflight/persistence time -- R7-F1's "G19とatomic preflightは同じcanonical
    resolver/verifierを使用する" requirement, applied to the context those two calls share.
    """

    difference = closure_request.get("difference") or {}
    change_result_evidence, change_free_evidence = _reproduced_evidence_for_context(closure_request)
    material_contradictions = closure_request.get("material_contradictions") or []
    blocking_contradictions = [
        item for item in material_contradictions if item.get("impact") == "MATERIAL"
    ]
    return build_invariant_verification_context(
        policy=policy,
        difference=difference,
        current_state={
            "revision": evaluation["evaluated_state_revision"],
            "fingerprint": evaluation["evaluated_state_fingerprint"],
        },
        after_state_candidate=evaluation.get("after_state_candidate"),
        resolution_mode=evaluation.get("resolution_mode"),
        change_result_evidence=change_result_evidence,
        change_free_evidence=change_free_evidence,
        after_observation_ids={
            ref["id"] for ref in evaluation.get("after_observation_refs") or [] if ref.get("id")
        },
        source_snapshot_refs=closure_request.get("source_snapshot_refs") or [],
        source_snapshots=closure_request.get("source_snapshots") or [],
        sufficiency=sufficiency,
        material_contradictions=material_contradictions,
        blocking_contradictions=blocking_contradictions,
    )


def _preflight_reresolve_closure(
    evaluation: dict[str, Any],
    closure_request: dict[str, Any],
    policy: dict[str, Any],
    sufficiency: dict[str, Any] | None,
) -> None:
    """R5-F4: ``ATOMIC_PREFLIGHT_FULL_RERESOLUTION_REQUIRED`` -- immediately before the
    commit that actually promotes a CLOSED Difference, every admitted binding's underlying
    record is re-resolved one more time from the same caller-supplied pools G19/G21 already
    verified, and the Git provenance witness is re-verified -- never merely reused from
    ``evaluate_closure``'s own already-computed result. Mirrors F5/G18's own
    ``evaluation_expires_at`` recheck in spirit: a real re-derivation immediately before
    commit, not a cached decision trusted across time.

    Raises :class:`StaleReflowError` on any mismatch -- a CLOSED Difference is never
    promoted on a preflight failure. Only called for a CLOSED outcome: a non-CLOSED result
    never claims any of these records are valid in the first place, so there is nothing to
    reconfirm.
    """

    claim_bindings = evaluation.get("candidate_claim_evaluation_bindings") or []
    invariant_bindings = evaluation.get("candidate_invariant_evaluation_bindings") or []
    invariant_evaluation_pool = closure_request.get("invariant_evaluations") or []
    claim_events = closure_request.get("candidate_claim_evaluation_events") or []
    invariant_evaluation_refs = [binding["invariant_evaluation_ref"] for binding in invariant_bindings]
    material_contradiction_refs = evaluation.get("contradiction_refs") or []
    observed_state_ref = {
        "kind": "state",
        "revision": evaluation["evaluated_state_revision"],
        "fingerprint": evaluation["evaluated_state_fingerprint"],
    }

    after_state_candidate = evaluation.get("after_state_candidate")
    verification_context = _invariant_verification_context(
        evaluation, closure_request, policy, sufficiency
    )
    for binding in invariant_bindings:
        if after_state_candidate is None:
            raise StaleReflowError(
                "atomic preflight: candidate_invariant_evaluation_bindings requires a real "
                "after_state_candidate"
            )
        try:
            resolve_invariant_evaluation(
                binding,
                invariant_evaluation_pool,
                base_state_ref=binding["base_state_ref"],
                after_state_candidate=after_state_candidate,
                verification_context=verification_context,
            )
        except DifferenceError as error:
            raise StaleReflowError(
                f"atomic preflight: invariant_evaluation_ref for "
                f"{binding['invariant_ref']['id']} no longer resolves: {error}"
            ) from error

    for binding in claim_bindings:
        claim_id = binding["required_claim_ref"]["id"]
        if after_state_candidate is None:
            raise StaleReflowError(
                "atomic preflight: candidate_claim_evaluation_bindings requires a real "
                "after_state_candidate"
            )
        try:
            resolve_claim_binding(
                claim_events,
                binding,
                difference_id=evaluation["difference_id"],
                after_state_candidate=after_state_candidate,
            )
        except ReflowValidationError as error:
            raise StaleReflowError(
                f"atomic preflight: claim evaluation series for {claim_id} no longer "
                f"reconstructs: {error}"
            ) from error
        try:
            resolve_completion_record(
                binding,
                policy=policy,
                observed_state_ref=observed_state_ref,
                evaluated_state_revision=evaluation["evaluated_state_revision"],
                evaluated_state_fingerprint=evaluation["evaluated_state_fingerprint"],
                invariant_evaluation_refs=invariant_evaluation_refs,
                material_contradiction_refs=material_contradiction_refs,
            )
        except DifferenceError as error:
            raise StaleReflowError(
                f"atomic preflight: completion_record_ref for {claim_id} no longer "
                f"resolves: {error}"
            ) from error

    # R6-F4: also re-verified whenever the Closure Evaluation itself carries a
    # kernel_source_witness_ref -- not only when invariant_bindings happens to be
    # non-empty -- so the persisted record's own claim is re-proven immediately before
    # commit exactly like every other admitted reference here.
    if invariant_bindings or evaluation.get("kernel_source_witness_ref"):
        kernel_source_ref = closure_request.get("kernel_source_ref")
        kernel_source_witness = closure_request.get("kernel_source_witness")
        commit_sha = kernel_source_ref.get("commit_sha") if isinstance(kernel_source_ref, dict) else None
        tree_sha = kernel_source_ref.get("tree_sha") if isinstance(kernel_source_ref, dict) else None
        if not isinstance(kernel_source_witness, dict) or not isinstance(commit_sha, str) or not isinstance(
            tree_sha, str
        ):
            raise StaleReflowError(
                "atomic preflight: kernel_source_ref/kernel_source_witness no longer present"
            )
        try:
            verify_kernel_source_witness(
                witness=kernel_source_witness,
                expected_commit_sha=commit_sha,
                expected_tree_sha=tree_sha,
                expected_blob_sha=KERNEL_INVARIANTS_BLOB_SHA,
                path=KERNEL_INVARIANTS_PATH,
            )
        except ReflowValidationError as error:
            raise StaleReflowError(
                f"atomic preflight: kernel_source_witness no longer verifies: {error}"
            ) from error

    # R6-F1a: every declared source_snapshot_refs entry is re-resolved against the real,
    # content-addressed source_snapshot pool immediately before commit too -- not only at
    # evaluation time -- so a Candidate cannot be promoted on a snapshot binding that has
    # since gone stale.
    source_snapshot_pool = closure_request.get("source_snapshots") or []
    for ref in closure_request.get("source_snapshot_refs") or []:
        try:
            resolve_source_snapshot(ref, source_snapshot_pool)
        except ObservationError as error:
            raise StaleReflowError(
                f"atomic preflight: source_snapshot for {ref.get('id')!r} no longer resolves: "
                f"{error}"
            ) from error

    # R6-F2: Evidence is one of the eight items SHUKOU's Round 6 adoption names the atomic
    # preflight must re-verify -- re-reproduced fresh from closure_request's own requests,
    # exactly like G8 itself, rather than trusted from evaluation's already-computed refs.
    # Set equality (not one-directional membership) so an emptied requests list against a
    # still-declared refs list is caught too, not silently skipped.
    change_result_pool_ids: set[str] = set()
    for item in closure_request.get("change_result_evidence_requests") or []:
        try:
            change_result_pool_ids.add(derive_evidence(item)["evidence_id"])
        except EvidenceError as error:
            raise StaleReflowError(
                f"atomic preflight: change_result_evidence_requests no longer reproduces: {error}"
            ) from error
    declared_change_result_ids = {
        ref.get("id") for ref in closure_request.get("change_result_evidence_refs") or []
    }
    if change_result_pool_ids != declared_change_result_ids:
        raise StaleReflowError(
            "atomic preflight: change_result_evidence_refs no longer matches the reproduced "
            "change-result Evidence"
        )

    change_free_pool_ids: set[str] = set()
    for item in closure_request.get("change_free_verification_evidence_requests") or []:
        try:
            change_free_pool_ids.add(derive_evidence(item)["evidence_id"])
        except EvidenceError as error:
            raise StaleReflowError(
                "atomic preflight: change_free_verification_evidence_requests no longer "
                f"reproduces: {error}"
            ) from error
    declared_change_free_ids = {
        ref.get("id")
        for ref in closure_request.get("change_free_verification_evidence_refs") or []
    }
    if change_free_pool_ids != declared_change_free_ids:
        raise StaleReflowError(
            "atomic preflight: change_free_verification_evidence_refs no longer matches the "
            "reproduced change-free verification Evidence"
        )


def _preflight_reresolve_terminal_reason_evidence(
    evaluation: dict[str, Any], closure_request: dict[str, Any]
) -> None:
    """R7-F4: re-reproduce every declared ``terminal_reason_evidence_refs`` entry immediately
    before commit -- called for *every* Reflow outcome, not only ``CLOSED``, since a
    BLOCKED/RETAINED/STALE/NOT_SATISFIED/CONTRADICTED result is exactly where this reference
    kind is ever non-empty (``evaluate_closure`` never lets a ``CLOSED`` evaluation carry
    one). Set equality, matching every other Evidence re-verification here: an emptied
    ``terminal_reason_evidence_requests`` against a still-declared ``terminal_reason_evidence_
    refs`` is refused, not silently skipped.
    """

    declared_ids = {
        ref.get("id")
        for ref in evaluation.get("terminal_reason_evidence_refs") or []
        if isinstance(ref, dict)
    }
    if not declared_ids:
        return
    reproduced_ids: set[str] = set()
    for item in closure_request.get("terminal_reason_evidence_requests") or []:
        try:
            reproduced_ids.add(derive_evidence(item)["evidence_id"])
        except EvidenceError as error:
            raise StaleReflowError(
                f"atomic preflight: terminal_reason_evidence_requests no longer reproduces: {error}"
            ) from error
    if reproduced_ids != declared_ids:
        raise StaleReflowError(
            "atomic preflight: terminal_reason_evidence_refs no longer matches the "
            "reproduced terminal reason Evidence"
        )


def _admitted_records(
    evaluation: dict[str, Any],
    lifecycle_event: dict[str, Any],
    closure_request: dict[str, Any],
    sufficiency: dict[str, Any] | None,
    *,
    policy: dict[str, Any],
    reflow_transition_ref: dict[str, Any] | None,
) -> list[tuple[str, str, dict[str, Any]]]:
    """R2-F3/R5-F2: every immutable record this transition's commit must make
    reference-resolvable.

    Always included: the Closure Evaluation, the minted lifecycle event (under
    :data:`LIFECYCLE_EVENT_KIND`, matching the kind every reference to it is published
    under), and the real Evidence Sufficiency Result the same ``evidence_sufficiency_request``
    reproduces. Reproduced wherever this vertical can derive a real record rather than only
    a bare reference: admitted Evidence (the Evidence Sufficiency request's own
    ``evidence_requests``, and, for a CHANGE_BOUND resolution,
    ``change_result_evidence_requests``); the complete validated
    ``candidate_claim_evaluation_event`` chain behind every admitted Claim binding; the real
    Completion Record and Invariant Evaluation record behind every admitted binding (R5-F2 --
    Difference-owned producers now exist for both, see ``difference/completion.py``/
    ``difference/invariant_evaluation.py``); the real ``kernel_source_witness`` record behind
    ``evaluation["kernel_source_witness_ref"]`` when set (R6-F4 -- re-verified fresh from
    *closure_request* rather than trusted from *evaluation*, matching the pin-and-prove
    pattern every other record here already follows); the real ``source_snapshot`` record
    behind every ``source_snapshot_refs`` entry (R6-F1a, Observation-owned); the real
    Evidence record behind every ``change_free_verification_evidence_refs`` entry (R6-F1b,
    reproduced through :func:`~manosube_agent_civilization.evidence.engine.derive_evidence`
    exactly like ``change_result_evidence_requests`` above -- Evidence stays the sole
    producer); every self-consistent after-state Observation record the reproduction
    actually consumed; and the real Evidence record behind every ``terminal_reason_evidence_
    refs`` entry (R7-F4, reproduced through :func:`derive_evidence` from
    ``terminal_reason_evidence_requests`` exactly like Change-result Evidence above).

    *reflow_transition_ref* is the real ``state_transition`` reference this transition
    commits under when *decision*'s ``to_status`` is ``CLOSED`` (``None`` otherwise) -- the
    same value already threaded into *lifecycle_event*'s own field, computed once, before
    any commit, and reused here so the persisted Completion Record's own post-commit lineage
    field is set at construction, never as a second write after the fact.
    """

    records: dict[tuple[str, str], dict[str, Any]] = {
        ("closure_evaluation", evaluation["closure_evaluation_id"]): evaluation,
        (LIFECYCLE_EVENT_KIND, lifecycle_event["difference_event_id"]): lifecycle_event,
    }
    if sufficiency is not None:
        records[("evidence_sufficiency_result", sufficiency["evidence_sufficiency_id"])] = sufficiency

    sufficiency_request = closure_request.get("evidence_sufficiency_request")
    if isinstance(sufficiency_request, dict):
        for item in sufficiency_request.get("evidence_requests") or []:
            record = derive_evidence(item)
            records[("observation_evidence", record["evidence_id"])] = record
    for item in closure_request.get("change_result_evidence_requests") or []:
        record = derive_evidence(item)
        records[("observation_evidence", record["evidence_id"])] = record
    # R6-F1b: the same reproduce-and-persist treatment for CHANGE_FREE's own Evidence
    # position -- Evidence remains the sole producer (:func:`derive_evidence`); Reflow only
    # resolves and persists what that owner produces, exactly as for Change-result Evidence
    # above.
    for item in closure_request.get("change_free_verification_evidence_requests") or []:
        record = derive_evidence(item)
        records[("observation_evidence", record["evidence_id"])] = record
    # R7-F4: the same reproduce-and-persist treatment for terminal_reason_evidence_refs --
    # Evidence remains the sole producer; Reflow only resolves and persists what that owner
    # produces, so BLOCKED/RETAINED/STALE/NOT_SATISFIED/CONTRADICTED terminal reasons carry
    # a real, resolvable body too, not only a reference that stays permanently opaque.
    for item in closure_request.get("terminal_reason_evidence_requests") or []:
        record = derive_evidence(item)
        records[("observation_evidence", record["evidence_id"])] = record

    # R6-F1a: every declared source_snapshot_refs entry resolves against Observation's own
    # real, content-addressed source_snapshot record (:mod:`observation.source_snapshot`) --
    # re-verified fresh from closure_request rather than trusted from evaluate_closure's
    # already-computed result (pin-and-prove, matching every other record here). A ref this
    # Evaluation already required to resolve (or the Closure Evaluation could not have
    # reached this far) that fails to resolve again here is skipped, not raised: nothing new
    # to persist for a reference the atomic preflight will itself refuse to promote.
    source_snapshot_pool = closure_request.get("source_snapshots") or []
    for ref in closure_request.get("source_snapshot_refs") or []:
        try:
            record = resolve_source_snapshot(ref, source_snapshot_pool)
        except ObservationError:
            continue
        records[("source_snapshot", record["source_snapshot_id"])] = record

    for observation in _self_consistent_after_observations(closure_request):
        records[("observation", observation["observation_id"])] = observation

    # R6-F4: the Closure Evaluation's own kernel_source_witness_ref, when set, names a real
    # kernel_source_witness record -- the verified Git COMMIT->TREE->PATH->BLOB object bytes,
    # not only the {commit_sha, tree_sha} claim -- persisted here so G19's proof survives a
    # process restart (before this, only the claim was ever committed; the witness bytes
    # existed solely as an ephemeral request field). Re-verified fresh from closure_request
    # rather than trusted from evaluation's own already-computed result (pin-and-prove); a
    # failure here can only mean the request changed between evaluation and persistence
    # within this same call, so nothing is persisted rather than a stale claim risked.
    kernel_source_witness_ref = evaluation.get("kernel_source_witness_ref")
    if isinstance(kernel_source_witness_ref, dict):
        kernel_source_ref = closure_request.get("kernel_source_ref")
        kernel_source_witness = closure_request.get("kernel_source_witness")
        commit_sha = kernel_source_ref.get("commit_sha") if isinstance(kernel_source_ref, dict) else None
        tree_sha = kernel_source_ref.get("tree_sha") if isinstance(kernel_source_ref, dict) else None
        if isinstance(kernel_source_witness, dict) and isinstance(commit_sha, str) and isinstance(
            tree_sha, str
        ):
            try:
                verify_kernel_source_witness(
                    witness=kernel_source_witness,
                    expected_commit_sha=commit_sha,
                    expected_tree_sha=tree_sha,
                    expected_blob_sha=KERNEL_INVARIANTS_BLOB_SHA,
                    path=KERNEL_INVARIANTS_PATH,
                )
            except ReflowValidationError:
                pass
            else:
                witness_record = build_kernel_source_witness_record(
                    commit_sha=commit_sha,
                    tree_sha=tree_sha,
                    blob_sha=KERNEL_INVARIANTS_BLOB_SHA,
                    path=KERNEL_INVARIANTS_PATH,
                    witness=kernel_source_witness,
                )
                # The record just rebuilt here must be the exact same one
                # evaluate_closure's own kernel_source_witness_ref already named -- a
                # mismatch means the two independent computations disagree (they never
                # should, from the same verified inputs), so nothing is persisted rather
                # than a record under a different id than the one the Evaluation refers to.
                if witness_record["kernel_source_witness_id"] == kernel_source_witness_ref.get("id"):
                    records[
                        ("kernel_source_witness", witness_record["kernel_source_witness_id"])
                    ] = witness_record

    invariant_evaluation_pool = closure_request.get("invariant_evaluations") or []
    after_state_candidate_for_invariants = evaluation.get("after_state_candidate")
    invariant_verification_context = _invariant_verification_context(
        evaluation, closure_request, policy, sufficiency
    )
    for binding in evaluation.get("candidate_invariant_evaluation_bindings") or []:
        if after_state_candidate_for_invariants is None:
            # Already reflected as a G19 gate failure; nothing new to persist for a
            # binding this Evaluation admits with no real Candidate to bind it to.
            continue
        try:
            record = resolve_invariant_evaluation(
                binding,
                invariant_evaluation_pool,
                base_state_ref=binding["base_state_ref"],
                after_state_candidate=after_state_candidate_for_invariants,
                verification_context=invariant_verification_context,
            )
        except DifferenceError:
            # Already reflected as a G19 gate failure; nothing new to persist for an
            # unresolved binding.
            continue
        records[("invariant_evaluation", record["evaluation_id"])] = record

    invariant_evaluation_refs = [
        binding["invariant_evaluation_ref"]
        for binding in evaluation.get("candidate_invariant_evaluation_bindings") or []
    ]
    material_contradiction_refs = evaluation.get("contradiction_refs") or []
    observed_state_ref = {
        "kind": "state",
        "revision": evaluation["evaluated_state_revision"],
        "fingerprint": evaluation["evaluated_state_fingerprint"],
    }
    claim_events = closure_request.get("candidate_claim_evaluation_events") or []
    after_state_candidate_for_claims = evaluation.get("after_state_candidate")
    for binding in evaluation.get("candidate_claim_evaluation_bindings") or []:
        if after_state_candidate_for_claims is None:
            # Already reflected as a G21 gate failure; nothing new to persist for a
            # binding this Evaluation admits with no real Candidate to bind it to.
            continue
        try:
            chain = resolve_claim_binding(
                claim_events,
                binding,
                difference_id=evaluation["difference_id"],
                after_state_candidate=after_state_candidate_for_claims,
            )
        except ReflowValidationError:
            # Already reflected as a G21 gate failure (or this Evaluation never reached a
            # state where the chain matters); nothing new to persist for an unresolved
            # binding.
            continue
        for event in chain:
            records[("candidate_claim_evaluation_event", event["event_id"])] = event
        try:
            claim_descriptor = resolve_claim_descriptor(binding["required_claim_ref"], policy)
            completion_record = build_completion_record(
                claim_descriptor=claim_descriptor,
                policy_ref=binding["policy_ref"],
                observed_state_ref=observed_state_ref,
                evaluated_state_revision=evaluation["evaluated_state_revision"],
                evaluated_state_fingerprint=evaluation["evaluated_state_fingerprint"],
                evaluation_status=binding["evaluation_status"],
                evaluated_at=binding["evaluated_at"],
                required_evidence_refs=list(binding["evaluation_evidence_refs"].get("members", [])),
                invariant_evaluation_refs=invariant_evaluation_refs,
                material_contradiction_refs=material_contradiction_refs,
                reflow_transition_ref=reflow_transition_ref,
            )
        except (DifferenceError, KeyError):
            # Already reflected as a G21 gate failure; nothing new to persist for an
            # unresolved binding.
            continue
        if binding["completion_record_ref"].get("id") != completion_record["completion_id"]:
            # Already reflected as a G21 gate failure -- the binding's own ref never
            # resolved to this record in the first place.
            continue
        records[(CANDIDATE_COMPLETION_RECORD_KIND, completion_record["completion_id"])] = completion_record

    return [(kind, record_id, body) for (kind, record_id), body in sorted(records.items())]


def reflow(
    store: Any,
    *,
    project_id: str,
    closure_request: dict[str, Any],
    previous_event_id: str,
    event_revision: int,
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
    evaluate_closure`'s own request, and is now also this call's *sole* source of the
    Difference and the current status (R2-F1) -- ``current_state`` is still always
    overridden here (F2) to the canonical predecessor State this function itself loads
    from *store* (F1). *evidence_refs* is not a caller parameter: it is derived (F6) from
    what the Evaluation itself admits. Returns ``{"evaluation", "decision",
    "next_semantic_state", "committed_state", "state_transition_ref", "event"}``.
    """

    before_project_state = store.load_current(project_id)
    if before_project_state["project_id"] != project_id:
        raise ReflowValidationError("the Store's current State belongs to a different project")
    _check_expected_state(
        before_project_state,
        expected_state_revision=expected_state_revision,
        expected_state_fingerprint=expected_state_fingerprint,
    )

    difference = closure_request.get("difference")
    if not isinstance(difference, dict):
        raise ReflowValidationError("closure_request.difference must be an object")
    current_status = closure_request.get("current_status")
    if not isinstance(current_status, str) or not current_status:
        raise ReflowValidationError("closure_request.current_status must be a non-empty string")
    head_ref = closure_request.get("difference_event_head_ref") or {}
    if head_ref.get("id") != previous_event_id:
        raise ReflowValidationError(
            "closure_request.difference_event_head_ref does not match previous_event_id"
        )
    _verify_lifecycle_ground_truth(
        store,
        project_id,
        difference=difference,
        current_status=current_status,
        previous_event_id=previous_event_id,
        event_revision=event_revision,
    )

    closure_request = dict(closure_request)
    closure_request["current_state"] = {
        "revision": before_project_state["state_revision"],
        "fingerprint": before_project_state["semantic_fingerprint"],
    }
    # R7-F3: G3 binds this Evaluation to the exact Objective the canonical current State is
    # itself bound to -- the Store's own committed objective_revision_id, never a caller
    # restatement of it.
    closure_request["objective_revision_id"] = before_project_state["objective_revision_id"]

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
        "kind": LIFECYCLE_EVENT_KIND,
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

    policy = require_object(closure_request["policy"], "closure_request.policy")
    # R7-F4: terminal reason Evidence is re-verified immediately before commit for *every*
    # outcome -- it is CLOSED evaluations that never carry one, not the reverse.
    _preflight_reresolve_terminal_reason_evidence(evaluation, closure_request)
    if decision["to_status"] == "CLOSED":
        _preflight_reresolve_closure(evaluation, closure_request, policy, sufficiency)

    records = _admitted_records(
        evaluation,
        lifecycle_event_placeholder,
        closure_request,
        sufficiency,
        policy=policy,
        reflow_transition_ref=state_transition_ref if decision["to_status"] == "CLOSED" else None,
    )

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
        mandatory_invariant_bindings=evaluation["candidate_invariant_evaluation_bindings"],
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
    store: Any, project_id: str, *, difference_id: str, previous_event_id: str, event_revision: int
) -> dict[str, Any]:
    """F7/R2-F1: resolve the Closure Evaluation a Reopen contradicts from the Store's own
    record, and verify the lifecycle ground truth Reopen's own mint depends on.

    *previous_event_id* must resolve to a committed :data:`LIFECYCLE_EVENT_KIND` record
    that: is the exact event this call names (its own content address is checked against
    ``lifecycle_event_id``); belongs to *difference_id*; is itself the ``CLOSED`` head, not
    some earlier or unrelated event; is contiguous with *event_revision*; and carries a
    ``closure_evaluation_ref`` that in turn resolves to a committed ``closure_evaluation``
    record belonging to the same Difference and whose own content address
    (:func:`~manosube_agent_civilization.reflow.identity.closure_evaluation_id`) matches
    what the event named. Every step fails closed: a caller can no longer hand this
    function an unrelated, forged, or stale Closure Evaluation and have it accepted as the
    one that actually closed the Difference.
    """

    closed_event = store.resolve_record(project_id, LIFECYCLE_EVENT_KIND, previous_event_id)
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
    if closed_event["event_revision"] + 1 != event_revision:
        raise ReflowValidationError(
            "event_revision is not contiguous with the resolved CLOSED predecessor: "
            f"{closed_event['event_revision']} + 1 != {event_revision}"
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
    stays untouched, not that this call may be handed a forged one to reopen against. Reopen
    has no separate ``closure_request`` to cross-check its own ``difference`` against, so its
    R2-F1 guarantee is the same one F7 already gave it: the Difference this call names must
    be the exact Difference the resolved, committed CLOSED lifecycle event belongs to.
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
        store,
        project_id,
        difference_id=difference["difference_id"],
        previous_event_id=previous_event_id,
        event_revision=event_revision,
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
    lifecycle_event_ref = {"kind": LIFECYCLE_EVENT_KIND, "id": event["difference_event_id"]}

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
        (LIFECYCLE_EVENT_KIND, event["difference_event_id"], event),
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
