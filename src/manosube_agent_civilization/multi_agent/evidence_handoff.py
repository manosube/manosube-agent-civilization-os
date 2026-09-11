"""The one public Multi-Agent-to-Evidence hand-off (Phase 19, Issue #77, P19-C7).

Reuses the existing Model Runtime hand-off
(:func:`~manosube_agent_civilization.model_runtime.evidence_handoff.
route_model_execution_to_evidence`) once per admitted slot output -- never a second Evidence,
Observation, Reflow or Closure owner, and never a Phase-19-invented "verdict" record. This
module never marks anything Evidence-sufficient itself: sufficiency belongs to the existing
Evidence/Independent Verification owners alone (P19-C7's own "not an Evidence verdict").

**Genesis-immutable aggregation input, evidence refs only on the terminal receipt (disclosed
choice).** :func:`~manosube_agent_civilization.multi_agent.route.execute_dynamic_execution_plan`
commits one ``multi_agent_evidence_aggregation_input`` per plan *before* any Evidence hand-off
ever runs -- it is a pure function of the admitted output set, the conflict set, the absent
slots and the release receipts, and carries no Evidence reference of its own. Only this
module's own terminal ``multi_agent_orchestration_receipt`` carries ``evidence_refs``, appended
after the hand-off below actually produces them. This keeps the aggregation input a stable,
content-addressed fact about *what was produced*, independent of *what Evidence eventually made
of it* -- exactly the separation P19-C7 draws between "aggregation input" and "Evidence
verdict".

**A genuinely linked Evidence chain, not N independent records.** Every admitted slot output
for one plan concerns the identical canonical Difference (the plan's own, shared Model Work
Unit binds them all to it) -- so the identical caller-supplied *evidence_request_template* is
reused for every admitted output, varying only ``predecessor_evidence_refs``: the second
admitted output's own request names the first's own Evidence record as its predecessor, the
third names the second's, and so on. N admitted outputs for one plan therefore produce a
genuinely linked chain of N Evidence records, never N unrelated ones and never a single
Phase-19-invented aggregate.

**Reuses ``route.py``'s own private commit/freshness helpers (disclosed exception to this
repository's usual "each module keeps its own private copy" convention).** Model Runtime's own
``evidence_handoff.py`` needed no commit of its own at all -- ``derive_evidence`` itself commits
nothing to Store. This module's own terminal receipt genuinely must be committed, and rather
than duplicate ``route.py``'s Compare-And-Swap retry and authority-freshness machinery a second
time inside the *same* single-owner package, it imports that machinery directly. The usual
convention decouples *independently owned* adapter-layer packages from one another (Model
Runtime from Runtime, Runtime from Projection); it was never a rule against one package's own
two files sharing one one committer.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.agent_runtime import TemporaryAgent
from manosube_agent_civilization.evidence import EVIDENCE_REFERENCE_KIND
from manosube_agent_civilization.model_runtime.evidence_handoff import (
    route_model_execution_to_evidence,
)
from manosube_agent_civilization.model_runtime.route import resolve_and_verify_committed_envelope
from manosube_agent_civilization.model_runtime.types import (
    MODEL_OUTCOME_TO_RECEIPT_STATUS,
    ModelExecutionReceipt,
)

from .engine import (
    derive_multi_agent_orchestration_receipt,
    require_valid_multi_agent_orchestration_receipt,
    require_valid_timestamp,
)
from .errors import (
    MultiAgentRecordIntegrityError,
    MultiAgentReleaseIncompleteError,
    MultiAgentRequirementError,
)
from .identity import (
    multi_agent_conflict_set_id,
    multi_agent_evidence_aggregation_input_id,
    multi_agent_orchestration_receipt_id,
    multi_agent_orchestration_receipt_semantic_fingerprint,
)

# Disclosed intra-package reuse of route.py's own private commit/freshness/validation helpers
# -- see this module's own docstring for why this deliberately departs from this repository's
# usual cross-*package* decoupling convention.
from .route import (
    AGGREGATION_INPUT_RECORD_KIND,
    CONFLICT_SET_RECORD_KIND,
    PLAN_RECORD_KIND,
    _commit,
    _live_contract,
    _require_canonical_identity,
    _require_reference,
    _require_resolved,
    resolve_and_verify_committed_aggregation_input,
    resolve_and_verify_committed_conflict_set,
    resolve_and_verify_committed_plan,
    resolve_and_verify_committed_release_receipt,
    resolve_and_verify_committed_slot_output,
)
from .types import ACCEPTED_SLOT_OUTCOME

ORCHESTRATION_RECEIPT_RECORD_KIND = "multi_agent_orchestration_receipt"


def _plan_keyed_payload(
    schema_version: str, project_id: str, plan_ref: Mapping[str, Any]
) -> dict[str, Any]:
    return {"schema_version": schema_version, "project_id": project_id, "plan_ref": dict(plan_ref)}


def _receipt_from_envelope(envelope: Mapping[str, Any]) -> ModelExecutionReceipt:
    """Rebuild an equivalent, ephemeral :class:`~manosube_agent_civilization.model_runtime.
    types.ModelExecutionReceipt` purely from a real, resolved, integrity-checked Envelope.

    Safe by construction: every field copied here is read straight off the real Envelope the
    existing Model Runtime hand-off itself re-resolves and re-verifies before trusting anything
    -- this is not a second, independent claim about what happened, it is the identical fact,
    restated in the one shape that existing hand-off's own public signature accepts. A
    ``ModelExecutionReceipt`` is documented as ephemeral and never itself Store-committed, so
    rebuilding one here (rather than threading the original in-memory object across what may be
    a wholly separate process/session) is exactly how a genuinely Store-resolution-based,
    replayable hand-off is possible at all.
    """

    outcome = str(envelope["execution_outcome"])
    return ModelExecutionReceipt(
        status=MODEL_OUTCOME_TO_RECEIPT_STATUS[outcome],
        model_execution_envelope_id=str(envelope["model_execution_envelope_id"]),
        project_id=str(envelope["project_id"]),
        model_work_unit_ref=dict(envelope["model_work_unit_ref"]),
        adapter_identity=dict(envelope["adapter_identity"]),
        difference_ref=dict(envelope["difference_ref"]),
        authority_ref=dict(envelope["authority_ref"]),
        boundary_ref=dict(envelope["boundary_ref"]),
        required_capability=str(envelope["required_capability"]),
        evidence_requirements=dict(envelope["evidence_requirements"]),
        human_authority_ref=dict(envelope["human_authority_ref"]),
        input_refs=(dict(envelope["difference_ref"]), dict(envelope["model_work_unit_ref"])),
        observations={
            "execution_outcome": outcome,
            "normalized_candidate_fingerprint": envelope["normalized_candidate_fingerprint"],
            "executed_at": envelope["executed_at"],
        },
    )


def route_orchestration_to_evidence(
    store: Any,
    agent: TemporaryAgent,
    *,
    project_id: str,
    project_binding_id: str,
    plan_ref: Mapping[str, Any],
    evidence_request_template: Mapping[str, Any],
    completed_at: str,
) -> dict[str, Any]:
    """Hand every admitted slot output of one already-executed plan off to the existing
    Evidence owner and commit the terminal Multi-Agent Orchestration Receipt.

    Requires :func:`~manosube_agent_civilization.multi_agent.route.
    execute_dynamic_execution_plan` to have already run for *plan_ref* -- resolves the plan's
    own conflict set and Evidence-aggregation input from the Store (never trusts an in-memory
    copy), refuses if either does not yet exist or if any accounted-for release is not
    ``RELEASED`` (defense in depth: :func:`~manosube_agent_civilization.multi_agent.engine.
    derive_multi_agent_evidence_aggregation_input` already refused to let this state exist, but
    this module never trusts a resolved record's own history without re-checking).

    *evidence_request_template* must already be a real, Change-free,
    ``verification_observation_request``-grounded Evidence request (the identical shape
    :func:`~manosube_agent_civilization.model_runtime.evidence_handoff.
    route_model_execution_to_evidence` itself requires), reused unchanged for every admitted
    output except for its own ``predecessor_evidence_refs``, which this function threads.

    Returns ``{"orchestration_receipt": ..., "orchestration_receipt_ref": ...,
    "evidence_refs": [...]}``.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(completed_at, "completed_at")
    checked_plan_ref = _require_reference(plan_ref, context="plan_ref", kind=PLAN_RECORD_KIND)
    if not isinstance(evidence_request_template, Mapping):
        raise MultiAgentRequirementError(
            f"evidence_request_template must be an explicit mapping: {evidence_request_template!r}"
        )

    _held, fresh = _live_contract(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        require_exact_state=False,
    )

    plan = resolve_and_verify_committed_plan(store, project_id, checked_plan_ref["id"])

    conflict_set_id = multi_agent_conflict_set_id(
        _plan_keyed_payload(plan["schema_version"], project_id, checked_plan_ref)
    )
    conflict_set = resolve_and_verify_committed_conflict_set(store, project_id, conflict_set_id)

    aggregation_input_id = multi_agent_evidence_aggregation_input_id(
        _plan_keyed_payload(plan["schema_version"], project_id, checked_plan_ref)
    )
    aggregation_input = resolve_and_verify_committed_aggregation_input(
        store, project_id, aggregation_input_id
    )
    if aggregation_input["conflict_set_ref"] != {
        "kind": CONFLICT_SET_RECORD_KIND,
        "id": conflict_set_id,
    }:
        raise MultiAgentRequirementError(
            "resolved Evidence aggregation input names a different conflict set than the one "
            "this plan actually produced -- refusing to trust it"
        )

    release_receipt_refs = list(aggregation_input["release_receipt_refs"]["members"])
    unreleased: list[str] = []
    for ref in release_receipt_refs:
        release_receipt = resolve_and_verify_committed_release_receipt(store, project_id, ref["id"])
        if release_receipt is None or release_receipt.get("release_status") != "RELEASED":
            unreleased.append(ref["id"])
    if unreleased:
        raise MultiAgentReleaseIncompleteError(
            f"one or more release receipts this plan's Evidence aggregation input names are "
            f"not RELEASED: {sorted(unreleased)!r} -- refusing to hand any admitted output off "
            "to the existing Evidence owner while any release remains unaccounted for"
        )

    evidence_records: list[dict[str, Any]] = []
    predecessor_ref: dict[str, Any] | None = None
    admitted_refs = sorted(
        aggregation_input["admitted_slot_output_refs"]["members"], key=lambda ref: ref["id"]
    )
    for ref in admitted_refs:
        slot_output = resolve_and_verify_committed_slot_output(store, project_id, ref["id"])
        if slot_output is None:
            raise MultiAgentRequirementError(
                f"aggregation input names an admitted slot output that no longer resolves: "
                f"{ref['id']!r}"
            )
        if (
            slot_output["outcome"] != ACCEPTED_SLOT_OUTCOME
            or slot_output["model_execution_envelope_ref"] is None
        ):
            raise MultiAgentRequirementError(
                f"aggregation input names slot output {ref['id']!r} as admitted, but it is not "
                "a CANDIDATE_ACCEPTED attempt with a real Envelope -- refusing to hand it off"
            )
        envelope = resolve_and_verify_committed_envelope(
            store, project_id, slot_output["model_execution_envelope_ref"]["id"]
        )
        model_execution_receipt = _receipt_from_envelope(envelope)
        request = dict(evidence_request_template)
        request["predecessor_evidence_refs"] = (
            [] if predecessor_ref is None else [dict(predecessor_ref)]
        )
        evidence = route_model_execution_to_evidence(
            store, model_execution_receipt, project_id, request
        )
        evidence_records.append(evidence)
        predecessor_ref = {"kind": EVIDENCE_REFERENCE_KIND, "id": str(evidence["evidence_id"])}

    orchestration_outcome = (
        "COMPLETED_WITH_UNRESOLVED_CAPABILITY"
        if aggregation_input["unresolved_capabilities"]
        else "COMPLETED_ALL_RELEASED"
    )
    evidence_refs = [
        {"kind": EVIDENCE_REFERENCE_KIND, "id": str(record["evidence_id"])}
        for record in evidence_records
    ]

    orchestration_receipt = derive_multi_agent_orchestration_receipt(
        project_id=project_id,
        plan_ref=dict(checked_plan_ref),
        slot_output_refs=list(conflict_set["considered_slot_output_refs"]["members"]),
        release_receipt_refs=release_receipt_refs,
        conflict_set_ref={"kind": CONFLICT_SET_RECORD_KIND, "id": conflict_set_id},
        aggregation_input_ref={
            "kind": AGGREGATION_INPUT_RECORD_KIND,
            "id": aggregation_input_id,
        },
        evidence_refs=evidence_refs,
        orchestration_outcome=orchestration_outcome,
        completed_at=completed_at,
    )
    # Structural Review Round 1, P19-R1-F4: every derived Evidence record is committed here, in
    # the identical single transaction as the terminal receipt that names it -- `derive_evidence`
    # (reached through `route_model_execution_to_evidence` above) is a pure function, exactly
    # like every other `derive_*` engine function in this repository, and persists nothing on its
    # own (the identical discipline :mod:`~manosube_agent_civilization.reflow.route` already
    # follows for its own `derive_evidence` calls, committing each result under the identical
    # ``"observation_evidence"`` kind literal, keyed by its own ``evidence_id``). Before this fix,
    # only the orchestration receipt was ever committed: a caller resolving any of its own
    # ``evidence_refs`` found nothing, because nothing had ever been written. Committing every
    # Evidence record atomically with the receipt that references it is what makes "the
    # orchestration receipt's own evidence_refs all resolve" a fact true from the instant the
    # receipt itself first becomes visible, never a race a later, separate write could still lose.
    _commit(
        store,
        project_id,
        [
            (EVIDENCE_REFERENCE_KIND, str(record["evidence_id"]), record)
            for record in evidence_records
        ]
        + [
            (
                ORCHESTRATION_RECEIPT_RECORD_KIND,
                str(orchestration_receipt["multi_agent_orchestration_receipt_id"]),
                orchestration_receipt,
            )
        ],
        committed_at=completed_at,
        project_binding_id=project_binding_id,
        expected_authority=fresh,
        transaction_prefix="TX-MULTI-AGENT-ORCHESTRATION",
        transaction_key=str(orchestration_receipt["multi_agent_orchestration_receipt_id"]),
    )

    return {
        "orchestration_receipt": orchestration_receipt,
        "orchestration_receipt_ref": {
            "kind": ORCHESTRATION_RECEIPT_RECORD_KIND,
            "id": str(orchestration_receipt["multi_agent_orchestration_receipt_id"]),
        },
        "evidence_refs": evidence_records,
    }


def resolve_and_verify_committed_orchestration_receipt(
    store: Any, project_id: str, orchestration_receipt_id: str
) -> dict[str, Any]:
    """Resolve the real, committed ``multi_agent_orchestration_receipt`` named by
    *orchestration_receipt_id* with the identical three-way canonical admission every record
    this package resolves is held to -- schema-valid, same project, and its own identity *and*
    semantic fingerprint, independently recomputed from its own content, equal to their own
    declared values and (for identity) to the Store lookup key itself.

    Structural Review Round 1, P19-R1-F3: this resolver previously verified only the narrow
    identity, unlike every sibling resolver this module and ``route.py`` already hold every
    other record kind to -- a resolved receipt whose own ``orchestration_outcome`` (or any other
    non-key field) had been altered after commit, with the unchanged narrow id still matching,
    passed here undetected. The semantic fingerprint check below is what a narrow-id check alone
    can never catch, since ``multi_agent_orchestration_receipt_id`` is computed from the plan-
    keyed natural key only (``schema_version``, ``project_id``, ``plan_ref`` -- see
    :mod:`~manosube_agent_civilization.multi_agent.identity`'s own module docstring) and does not
    cover the outcome, references or timing the semantic fingerprint alone addresses.
    """

    resolved = _require_resolved(
        store,
        project_id,
        ORCHESTRATION_RECEIPT_RECORD_KIND,
        {"kind": ORCHESTRATION_RECEIPT_RECORD_KIND, "id": orchestration_receipt_id},
    )
    receipt = require_valid_multi_agent_orchestration_receipt(resolved)
    if receipt.get("project_id") != project_id:
        raise MultiAgentRequirementError(
            f"resolved multi_agent_orchestration_receipt names a different project than the "
            f"one being executed: {receipt.get('project_id')!r} != {project_id!r}"
        )
    declared_id = receipt.get("multi_agent_orchestration_receipt_id")
    recomputed_id = multi_agent_orchestration_receipt_id(receipt)
    if orchestration_receipt_id != declared_id or recomputed_id != declared_id:
        raise MultiAgentRequirementError(
            "resolved multi_agent_orchestration_receipt's own identity does not agree across "
            f"the Store lookup key, its own declared value, and its own recomputed value -- "
            f"lookup={orchestration_receipt_id!r}, declared={declared_id!r}, "
            f"recomputed={recomputed_id!r}"
        )
    if multi_agent_orchestration_receipt_semantic_fingerprint(receipt) != receipt.get(
        "multi_agent_orchestration_receipt_semantic_fingerprint"
    ):
        raise MultiAgentRecordIntegrityError(
            f"resolved multi_agent_orchestration_receipt {orchestration_receipt_id!r} own "
            "recomputed semantic fingerprint does not equal its own declared value -- refusing "
            "to trust any of its fields"
        )
    return receipt


__all__ = ["resolve_and_verify_committed_orchestration_receipt", "route_orchestration_to_evidence"]
