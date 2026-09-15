"""Phase 20 Long-Running Project Proof -- the repeatable, cycle-indexed natural-route
composer, generalizing Phase 8's one-shot ``tests/natural_cycle/proof.py`` to a sequence of
``OBJECTIVE -> STATE -> OBSERVATION -> DIFFERENCE -> AUTHORITY -> CHANGE -> RE-OBSERVATION ->
EVIDENCE -> SUFFICIENCY -> CLOSURE EVALUATION -> ATOMIC REFLOW -> NEW STATE`` cycles run against
one, long-running Project's Store, each cycle's own ``current_state`` derived from the previous
cycle's real, committed Reflow result -- never re-derived by this module and never held only in
memory across cycle boundaries (:func:`run_one_cycle` always re-reads its own predecessor State
the identical way ``reflow()`` itself does, through the Store).

Every intermediate canonical record is produced here by calling its own real, public producer,
exactly as ``tests/natural_cycle/proof.py``'s own module docstring explains for the one-cycle
case (``PUBLIC_CANONICAL_OWNER_ENTRYPOINTS_ONLY=true``,
``NO_MANUAL_INTERMEDIATE_CANONICAL_RECORD_CONSTRUCTION=true``). This module intentionally
duplicates that module's structure rather than importing/parametrizing it directly -- Phase 8's
own fixture module explains why phase fixture worlds stay independent
(``PHASE_8_FIXTURE_BINDING_NE_PHASE_20_FIXTURE_BINDING=true``), and the corresponding harness
code follows the identical convention.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from tests.fixtures import long_running_proof as lrp
from tests.reflow_helpers import mandatory_x003_claim_binding_and_event
from tests.state_helpers import (
    SCHEMA_ROOT,
    genesis_source_snapshot_records,
    initial_state,
    real_kernel_git_objects,
)

from manosube_agent_civilization.authority import evaluate_authority
from manosube_agent_civilization.change import derive_change
from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.invariant_evaluation import (
    build_invariant_evaluation,
    invariant_evaluation_fingerprint,
)
from manosube_agent_civilization.difference.invariant_verifiers import (
    build_invariant_verification_context,
)
from manosube_agent_civilization.evidence.engine import derive_evidence
from manosube_agent_civilization.evidence.levels import (
    COMPLETION_SEMANTICS_BLOB_SHA,
    COMPLETION_SEMANTICS_PATH,
)
from manosube_agent_civilization.evidence.sufficiency import (
    evaluate_sufficiency,
    evidence_level_scale_digest,
)
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.reflow.closure import REQUEST_KEYS, build_after_state_candidate
from manosube_agent_civilization.reflow.invariant_registry import (
    V0_1_INVARIANT_DEFINITION_DIGESTS,
    candidate_invariant_evaluation_binding_id,
    expected_g19_invariant_ids,
)
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.state.fingerprint import (
    fingerprint_project_state,
    fingerprint_semantic_state,
)
from manosube_agent_civilization.store import FileStateStore

REFLOW_INSTANT = lrp.REFLOW_INSTANT


def build_store(tmp_path: Path) -> FileStateStore:
    """A real :class:`FileStateStore`, rooted outside the repository working tree."""

    return FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)


def genesis_semantic_state() -> dict[str, Any]:
    """The one long-running Project's own genesis ``semantic_state`` -- built on the identical,
    already-pinned, schema-valid ``initial_state_revision_zero`` contract fixture every other
    suite in this repository treats as the one canonical genesis-State shape (exactly the
    pattern Phase 8's own ``genesis_semantic_state`` uses). Only the ``code`` domain is
    overridden; its ``claims`` grows by exactly one key per committed cycle."""

    state: dict[str, Any] = initial_state()["semantic_state"]
    state["code"] = {
        "status": "UNKNOWN",
        "claims": {},
        "identity_refs": [],
        "evidence_refs": [],
        "blind_spots": ["not observed"],
    }
    return state


def next_semantic_state(current_semantic_state: dict[str, Any], k: int) -> dict[str, Any]:
    """Cycle *k*'s own real content difference: marker *k* moves to ``READY`` -- a genuine,
    additive change to the previous cycle's own committed content, never a reversion of an
    earlier cycle's claim."""

    state = deepcopy(current_semantic_state)
    state["code"]["status"] = "KNOWN"
    state["code"]["claims"][lrp.claim_key(k)] = "READY"
    return state


def genesis_project_state() -> dict[str, Any]:
    state = initial_state()
    state["project_id"] = lrp.PROJECT_ID
    state["objective_revision_id"] = lrp.OBJECTIVE_REVISION_ID
    state["semantic_state"] = genesis_semantic_state()
    state["semantic_fingerprint"] = fingerprint_project_state(
        state, schema_root=SCHEMA_ROOT
    ).as_dict()
    return state


def initialize_genesis(store: FileStateStore) -> dict[str, Any]:
    genesis = genesis_project_state()
    genesis_records: list[tuple[str, str, Mapping[str, Any]]] = [
        (kind, record_id, body)
        for kind, record_id, body in genesis_source_snapshot_records(genesis)
    ]
    store.initialize(lrp.PROJECT_ID, genesis, records=genesis_records)
    current: dict[str, Any] = store.load_current(lrp.PROJECT_ID)
    return current


def observe_before(k: int, current_state: dict[str, Any]) -> dict[str, Any]:
    """The before-Observation/Evidence two-pass fixed point for cycle *k* (P8-R1-F1/P8-R2-F1
    pattern, generalized): a provisional, placeholder-seeded request derives the real
    Observation Evidence id, then the corrected request -- carrying that real id -- is what
    this function hands back to the caller."""

    provisional_request = lrp.before_observation_request(
        k,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    provisional_bundle = observe(provisional_request)

    provisional_difference_request = lrp.derivation_request(
        k,
        observation_bundle=provisional_bundle,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    provisional_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": lrp.EVIDENCE_RECORDED_AT,
        "observation_request": provisional_request,
        "difference_request": provisional_difference_request,
        "change_request": None,
        "post_change_observation_request": None,
        "verification_observation_request": None,
        "verification_result_provenance": None,
        "artifact_references": [dict(lrp.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    provisional_evidence = derive_evidence(provisional_evidence_request)

    request = lrp.before_observation_request(
        k,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        ref={"kind": "observation_evidence", "id": provisional_evidence["evidence_id"]},
    )
    bundle = observe(request)
    assert (
        bundle["observations"][-1]["observation_id"]
        == provisional_bundle["observations"][-1]["observation_id"]
    )

    difference_request = lrp.derivation_request(
        k,
        observation_bundle=bundle,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    observation_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": lrp.EVIDENCE_RECORDED_AT,
        "observation_request": request,
        "difference_request": difference_request,
        "change_request": None,
        "post_change_observation_request": None,
        "verification_observation_request": None,
        "verification_result_provenance": None,
        "artifact_references": [dict(lrp.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    observation_evidence = derive_evidence(observation_evidence_request)
    if observation_evidence["evidence_id"] != provisional_evidence["evidence_id"]:
        raise AssertionError(
            f"cycle {k}: before-Observation Evidence fixed point did not converge: "
            f"{observation_evidence['evidence_id']!r} != {provisional_evidence['evidence_id']!r}"
        )

    return {
        "request": request,
        "bundle": bundle,
        "observation_evidence_request": observation_evidence_request,
        "observation_evidence": observation_evidence,
    }


def derive_difference(
    k: int, current_state: dict[str, Any], before: dict[str, Any]
) -> dict[str, Any]:
    request = lrp.derivation_request(
        k,
        observation_bundle=before["bundle"],
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    result = derive_differences(request)
    return {"request": request, "result": result, "difference": result["differences"][0]}


def check_authority(k: int, difference: dict[str, Any]) -> dict[str, Any]:
    request: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": difference["project_id"],
        "difference": difference,
        "requested_action": lrp.requested_action(k),
        "requested_scope": lrp.action_scope(),
        "current_state_revision": difference["observed_state_revision"],
        "current_state_fingerprint": difference["observed_state_fingerprint"],
        "authority_rules": [lrp.authority_rule(project_id=difference["project_id"])],
        "prohibitions": [],
        "approvals": [],
        "evaluation_time": lrp.AUTHORITY_EVALUATION_TIME,
    }
    decision = evaluate_authority(request)
    return {"request": request, "decision": decision}


def derive_the_change(authority: dict[str, Any]) -> dict[str, Any]:
    request: dict[str, Any] = {
        "schema_version": "0.1",
        "authority_request": authority["request"],
        "authority_decision": authority["decision"],
    }
    change = derive_change(request)
    return {"request": request, "change": change}


def observe_change_result(
    k: int,
    current_state: dict[str, Any],
    before: dict[str, Any],
    change: dict[str, Any],
) -> dict[str, Any]:
    difference_request = lrp.derivation_request(
        k,
        observation_bundle=before["bundle"],
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )

    provisional_request = lrp.change_result_observation_request(
        k,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    provisional_bundle = observe(provisional_request)
    provisional_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": lrp.EVIDENCE_RECORDED_AT,
        "observation_request": before["request"],
        "difference_request": difference_request,
        "change_request": change["request"],
        "post_change_observation_request": provisional_request,
        "verification_observation_request": None,
        "verification_result_provenance": None,
        "artifact_references": [dict(lrp.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    provisional_evidence = derive_evidence(provisional_evidence_request)

    request = lrp.change_result_observation_request(
        k,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        ref={"kind": "observation_evidence", "id": provisional_evidence["evidence_id"]},
    )
    bundle = observe(request)
    assert (
        bundle["observations"][-1]["observation_id"]
        == provisional_bundle["observations"][-1]["observation_id"]
    )

    return {
        "request": request,
        "bundle": bundle,
        "difference_request": difference_request,
        "_seed_evidence_id": provisional_evidence["evidence_id"],
    }


def observe_verification(
    k: int, current_state: dict[str, Any], before: dict[str, Any]
) -> dict[str, Any]:
    difference_request = lrp.derivation_request(
        k,
        observation_bundle=before["bundle"],
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )

    provisional_request = lrp.verification_observation_request(
        k,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    provisional_bundle = observe(provisional_request)
    provisional_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": lrp.EVIDENCE_RECORDED_AT,
        "observation_request": before["request"],
        "difference_request": difference_request,
        "change_request": None,
        "post_change_observation_request": None,
        "verification_observation_request": provisional_request,
        "verification_result_provenance": lrp.VERIFICATION_RESULT_PROVENANCE,
        "artifact_references": [dict(lrp.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    provisional_evidence = derive_evidence(provisional_evidence_request)

    request = lrp.verification_observation_request(
        k,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        ref={"kind": "observation_evidence", "id": provisional_evidence["evidence_id"]},
    )
    bundle = observe(request)
    assert (
        bundle["observations"][-1]["observation_id"]
        == provisional_bundle["observations"][-1]["observation_id"]
    )

    verification_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": lrp.EVIDENCE_RECORDED_AT,
        "observation_request": before["request"],
        "difference_request": difference_request,
        "change_request": None,
        "post_change_observation_request": None,
        "verification_observation_request": request,
        "verification_result_provenance": lrp.VERIFICATION_RESULT_PROVENANCE,
        "artifact_references": [dict(lrp.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    verification_evidence = derive_evidence(verification_evidence_request)
    if verification_evidence["evidence_id"] != provisional_evidence["evidence_id"]:
        raise AssertionError(
            f"cycle {k}: verification-Observation Evidence fixed point did not converge: "
            f"{verification_evidence['evidence_id']!r} != {provisional_evidence['evidence_id']!r}"
        )

    return {
        "request": request,
        "bundle": bundle,
        "verification_evidence_request": verification_evidence_request,
        "verification_evidence": verification_evidence,
    }


def derive_the_change_result_evidence(
    k: int,
    current_state: dict[str, Any],
    before: dict[str, Any],
    change: dict[str, Any],
    change_result: dict[str, Any],
) -> dict[str, Any]:
    difference_request = change_result.get("difference_request") or lrp.derivation_request(
        k,
        observation_bundle=before["bundle"],
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    change_result_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": lrp.EVIDENCE_RECORDED_AT,
        "observation_request": before["request"],
        "difference_request": difference_request,
        "change_request": change["request"],
        "post_change_observation_request": change_result["request"],
        "verification_observation_request": None,
        "verification_result_provenance": None,
        "artifact_references": [dict(lrp.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    change_result_evidence = derive_evidence(change_result_evidence_request)
    seed_evidence_id = change_result.get("_seed_evidence_id")
    if seed_evidence_id is not None and change_result_evidence["evidence_id"] != seed_evidence_id:
        raise AssertionError(
            f"cycle {k}: Change-result Evidence fixed point did not converge: "
            f"{change_result_evidence['evidence_id']!r} != {seed_evidence_id!r}"
        )
    return {
        "difference_request": difference_request,
        "change_result_evidence_request": change_result_evidence_request,
        "change_result_evidence": change_result_evidence,
    }


def evaluate_the_sufficiency(
    difference: dict[str, Any],
    policy: dict[str, Any],
    *,
    observation_evidence_request: dict[str, Any],
    change_result_evidence_request: dict[str, Any],
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "schema_version": "0.1",
        "difference_ref": {"kind": "difference", "id": difference["difference_id"]},
        "closure_policy": policy,
        "evidence_level_scale_ref": {
            "kind": "evidence_level_scale_source",
            "path": COMPLETION_SEMANTICS_PATH,
            "blob_sha": COMPLETION_SEMANTICS_BLOB_SHA,
            "evidence_level_scale_sha256": evidence_level_scale_digest(),
        },
        "evidence_requests": [observation_evidence_request, change_result_evidence_request],
        "evaluation_instant": lrp.SUFFICIENCY_EVALUATED_AT,
    }
    wrapper = evaluate_sufficiency(request)
    return {
        "request": request,
        "wrapper": wrapper,
        "result": wrapper["evidence_sufficiency_result"],
    }


def invariant_bindings_and_evaluations(
    k: int,
    difference_id: str,
    current_state: dict[str, Any],
    *,
    after_state_candidate: dict[str, Any],
    verification_context: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bindings: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    for invariant_id in sorted(expected_g19_invariant_ids()):
        evaluation_id = (
            "INV-EVAL-"
            + hashlib.sha256(f"long_running_proof:{k}:{difference_id}:{invariant_id}".encode())
            .hexdigest()
            .upper()
        )
        record = build_invariant_evaluation(
            invariant_id,
            verification_context,
            evaluation_id=evaluation_id,
            subject_ref={"kind": "difference", "id": difference_id},
            state_revision=current_state["revision"],
            state_fingerprint=current_state["fingerprint"],
            candidate_id=after_state_candidate["candidate_id"],
            candidate_semantic_fingerprint=after_state_candidate["semantic_fingerprint"],
            evaluated_at=lrp.SUFFICIENCY_EVALUATED_AT,
            evaluator_capability="reflow.closure",
            authority_ref=None,
        )
        evaluations.append(record)
        binding: dict[str, Any] = {
            "kind": "candidate_invariant_evaluation_binding",
            "candidate_id": after_state_candidate["candidate_id"],
            "candidate_semantic_fingerprint": after_state_candidate["semantic_fingerprint"],
            "base_state_ref": {
                "kind": "state",
                "revision": current_state["revision"],
                "fingerprint": current_state["fingerprint"],
            },
            "invariant_ref": {"kind": "kernel_invariant", "id": invariant_id},
            "invariant_definition_ref": {
                "repository": "manosube/manosube-agent-civilization-os",
                "path": "00_KERNEL/KERNEL_INVARIANTS.md",
                "invariant_definition_sha256": (
                    "sha256:" + V0_1_INVARIANT_DEFINITION_DIGESTS[invariant_id]
                ),
            },
            "invariant_evaluation_ref": {
                "kind": "invariant_evaluation",
                "id": record["evaluation_id"],
            },
            "evaluation_record_fingerprint": invariant_evaluation_fingerprint(record),
            "evaluation_result": record["status"],
            "evaluation_evidence_refs": {
                "collection_kind": "UNORDERED_SET",
                "members": list(record["evidence_refs"]["members"]),
            },
            "evaluated_at": record["evaluated_at"],
        }
        binding["binding_id"] = candidate_invariant_evaluation_binding_id(binding)
        bindings.append(binding)
    return bindings, evaluations


def assemble_one_cycle(
    store: FileStateStore,
    *,
    k: int,
    committed_state: dict[str, Any],
) -> dict[str, Any]:
    """Build every real intermediate record and the exact ``reflow()`` call arguments for
    cycle *k*, given the Store's own real current committed State (``committed_state``, as
    :meth:`FileStateStore.load_current`/``read_current_consistent`` or a prior cycle's own
    ``reflow_result["committed_state"]`` returns it) -- without calling ``reflow()`` itself,
    so a required negative/interruption-route test can mutate exactly one already-real input
    and call ``reflow()`` directly."""

    before = observe_before(k, committed_state)
    diff = derive_difference(k, committed_state, before)
    difference = diff["difference"]
    policy = lrp.closure_policy(difference["difference_id"], predicate=lrp.predicate_id(k))

    authority = check_authority(k, difference)
    change = derive_the_change(authority)

    change_result_obs = observe_change_result(k, committed_state, before, change)
    verification_obs = observe_verification(k, committed_state, before)

    change_result_evidence_bundle = derive_the_change_result_evidence(
        k, committed_state, before, change, change_result_obs
    )
    sufficiency = evaluate_the_sufficiency(
        difference,
        policy,
        observation_evidence_request=before["observation_evidence_request"],
        change_result_evidence_request=change_result_evidence_bundle[
            "change_result_evidence_request"
        ],
    )

    verification_difference_request = lrp.derivation_request(
        k,
        observation_bundle=verification_obs["bundle"],
        fingerprint=committed_state["semantic_fingerprint"],
        state_revision=committed_state["state_revision"],
        snapshot_ref=lrp.AFTER_SNAPSHOT_REF,
    )
    verification_observation_id = verification_obs["bundle"]["observations"][0]["observation_id"]

    kernel_source_ref, kernel_source_witness = real_kernel_git_objects()
    after_semantic_state = next_semantic_state(committed_state["semantic_state"], k)
    after_fingerprint = fingerprint_semantic_state(after_semantic_state).as_dict()
    current_state = {
        "revision": committed_state["state_revision"],
        "fingerprint": committed_state["semantic_fingerprint"],
    }
    change_ref = {"kind": "change", "id": change["change"]["change_id"]}
    after_state_candidate = build_after_state_candidate(
        current_state=current_state,
        kernel_source_ref=kernel_source_ref,
        semantic_state=after_semantic_state,
        semantic_fingerprint=after_fingerprint,
        source_snapshot_refs=[lrp.AFTER_SNAPSHOT_REF],
        producing_change_refs=[change_ref],
    )
    verification_context = build_invariant_verification_context(
        policy=policy,
        difference=difference,
        current_state=current_state,
        after_state_candidate=after_state_candidate,
        resolution_mode="CHANGE_BOUND",
        change_result_evidence=[change_result_evidence_bundle["change_result_evidence"]],
        change_free_evidence=[],
        after_observation_ids={verification_observation_id},
        source_snapshot_refs=[lrp.AFTER_SNAPSHOT_REF],
        source_snapshots=[lrp.AFTER_SOURCE_SNAPSHOT],
        sufficiency=sufficiency["result"],
        material_contradictions=[],
        blocking_contradictions=[],
        proposed_terminal_status="CLOSED",
        evaluated_at=lrp.SUFFICIENCY_EVALUATED_AT,
        request_contract_keys=REQUEST_KEYS,
    )
    invariant_bindings, invariant_evaluations = invariant_bindings_and_evaluations(
        k,
        difference["difference_id"],
        current_state,
        after_state_candidate=after_state_candidate,
        verification_context=verification_context,
    )
    invariant_evaluation_refs = [
        binding["invariant_evaluation_ref"] for binding in invariant_bindings
    ]
    claim_binding, claim_event = mandatory_x003_claim_binding_and_event(
        difference,
        current_state,
        invariant_evaluation_refs=invariant_evaluation_refs,
        material_contradiction_refs=[],
        after_state_candidate=after_state_candidate,
    )

    closure_request: dict[str, Any] = {
        "difference": difference,
        "current_status": "VERIFYING",
        "policy": policy,
        "difference_event_head_ref": dict(difference["genesis_event_ref"]),
        "current_state": current_state,
        "objective_revision_id": lrp.OBJECTIVE_REVISION_ID,
        "objective_revision": lrp.objective_revision(),
        "kernel_source_ref": kernel_source_ref,
        "base_kernel_source_ref": kernel_source_ref,
        "kernel_source_witness": kernel_source_witness,
        "resolution_mode": "CHANGE_BOUND",
        "change_refs": [change_ref],
        "change_result_evidence_refs": [
            {
                "kind": "observation_evidence",
                "id": change_result_evidence_bundle["change_result_evidence"]["evidence_id"],
            }
        ],
        "change_result_evidence_requests": [
            change_result_evidence_bundle["change_result_evidence_request"]
        ],
        "change_free_verification_evidence_refs": [],
        "change_free_verification_evidence_requests": [],
        "reobservation": {
            "derivation_request": verification_difference_request,
            "after_observation_refs": [{"kind": "observation", "id": verification_observation_id}],
        },
        "evidence_sufficiency_request": sufficiency["request"],
        "after_state_semantic_state": after_semantic_state,
        "source_snapshot_refs": [lrp.AFTER_SNAPSHOT_REF],
        "source_snapshots": [lrp.AFTER_SOURCE_SNAPSHOT],
        "producing_change_refs": [change_ref],
        "candidate_invariant_evaluation_bindings": invariant_bindings,
        "candidate_claim_evaluation_bindings": [claim_binding],
        "candidate_claim_evaluation_events": [claim_event],
        "invariant_evaluations": invariant_evaluations,
        "material_contradictions": [],
        "terminal_reason_evidence_refs": [],
        "terminal_reason_evidence_requests": [],
        "proposed_terminal_status": "CLOSED",
        "evaluated_at": lrp.SUFFICIENCY_EVALUATED_AT,
    }

    reflow_kwargs: dict[str, Any] = {
        "project_id": lrp.PROJECT_ID,
        "closure_request": closure_request,
        "previous_event_id": difference["genesis_event_ref"]["id"],
        "event_revision": 1,
        "observation_refs": [{"kind": "observation", "id": verification_observation_id}],
        "reflow_instant": REFLOW_INSTANT,
        "expected_state_revision": committed_state["state_revision"],
        "expected_state_fingerprint": committed_state["semantic_fingerprint"],
        "authority_ref": {
            "kind": "authority_decision",
            "id": authority["decision"]["authority_decision_id"],
        },
        "change_refs": [change_ref],
        "provenance_only_evidence_requests": [verification_obs["verification_evidence_request"]],
        "auxiliary_source_snapshots": [lrp.BEFORE_SOURCE_SNAPSHOT],
        "genesis_lifecycle_event": next(
            event
            for event in diff["result"]["events"]
            if event["difference_event_id"] == difference["genesis_event_ref"]["id"]
        ),
    }

    return {
        "k": k,
        "before": before,
        "difference": difference,
        "authority": authority,
        "change": change,
        "change_ref": change_ref,
        "change_result_observation": change_result_obs,
        "verification_observation": verification_obs,
        "verification_observation_id": verification_observation_id,
        "evidence": change_result_evidence_bundle,
        "sufficiency": sufficiency,
        "policy": policy,
        "closure_request": closure_request,
        "reflow_kwargs": reflow_kwargs,
    }


def run_one_cycle(
    store: FileStateStore,
    *,
    k: int,
    committed_state: dict[str, Any],
) -> dict[str, Any]:
    """Run cycle *k* to completion against *store*, given the Store's own real current
    committed State. Returns the assembly, the real ``reflow()`` result, and an identity
    ledger entry -- the caller threads ``reflow_result["committed_state"]`` into the next
    cycle's own ``committed_state`` argument (or re-reads it fresh from the Store, e.g. after
    a real process-boundary restart -- see :mod:`tests.long_running_proof.session_loss`)."""

    assembly = assemble_one_cycle(store, k=k, committed_state=committed_state)
    result = reflow(store, **assembly["reflow_kwargs"])
    return {
        "assembly": assembly,
        "reflow_result": result,
        "identity": {
            "cycle": k,
            "difference_id": assembly["difference"]["difference_id"],
            "authority_decision_id": assembly["authority"]["decision"]["authority_decision_id"],
            "change_id": assembly["change"]["change"]["change_id"],
            "evidence_sufficiency_id": assembly["sufficiency"]["result"]["evidence_sufficiency_id"],
            "closure_evaluation_id": result["evaluation"]["closure_evaluation_id"],
            "difference_lifecycle_event_id": result["event"]["difference_event_id"],
            "state_transition_ref": result["state_transition_ref"],
            "final_state_revision": result["committed_state"]["state_revision"],
            "final_state_fingerprint": result["committed_state"]["semantic_fingerprint"],
        },
    }
