"""PR #90 Round 6 -- the ``MANOSUBE_PRESENT`` condition composer for the two-task real-Agent
corpus (``examples/comparative_benchmark/real_agent_corpus/TASK_CORPUS.md``).

Adapted from ``tests/long_running_proof/cycle.py`` (Phase 20's own repeated-cycle natural-route
composer), kept as its own independent module rather than importing/parametrizing either
``tests/long_running_proof/cycle.py`` or ``tests/natural_cycle/proof.py`` directly -- the same
``PHASE_8_FIXTURE_BINDING_NE_PHASE_20_FIXTURE_BINDING=true`` convention both of those modules'
own docstrings already establish for keeping each phase/round's composer independently kept.

The one deliberate, load-bearing structural difference from both predecessors: between the
Change record's derivation and the post-change Observation, this composer calls a caller-
supplied ``perform_real_change`` callback -- the real Agent action itself (the identical write
this corpus's ``MANOSUBE_ABSENT`` condition already performed directly, per ``RAW_EVENTS.md``)
-- and only *then* takes the post-change Observation, of the real, now-changed bytes on disk.
Every intermediate canonical record downstream of that point is still produced only by calling
its own real, public producer (``NO_MANUAL_INTERMEDIATE_CANONICAL_RECORD_CONSTRUCTION=true``);
what is new here is *what the Observation reads*, not how the Observation, Difference,
Authority Decision, Change, Evidence, Sufficiency, or Reflow records are derived.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
from typing import Any

from tests.fixtures import comparative_benchmark_real_agent as ra
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


def _offset(instant: str, *, seconds: int) -> str:
    """*instant* shifted by *seconds* -- G8's own anti-self-closing check requires the
    Change-result Observation and the independent verification Observation to be
    genuinely distinct real acts of observation, not the identical Observation content
    reused in two roles (exactly the three-genuinely-separate-Observation-calls
    discipline ``tests/natural_cycle/proof.py``'s own module docstring documents)."""

    parsed = datetime.fromisoformat(instant.replace("Z", "+00:00"))
    shifted = parsed + timedelta(seconds=seconds)
    return shifted.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_store(tmp_path: Path) -> FileStateStore:
    return FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)


def genesis_semantic_state() -> dict[str, Any]:
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
    state = deepcopy(current_semantic_state)
    state["code"]["status"] = "KNOWN"
    state["code"]["claims"][ra.claim_key(k)] = "READY"
    return state


def genesis_project_state() -> dict[str, Any]:
    state = initial_state()
    state["project_id"] = ra.PROJECT_ID
    state["objective_revision_id"] = ra.OBJECTIVE_REVISION_ID
    state["semantic_state"] = genesis_semantic_state()
    state["semantic_fingerprint"] = fingerprint_project_state(
        state, schema_root=SCHEMA_ROOT
    ).as_dict()
    return state


def bind_genesis(store: FileStateStore) -> dict[str, Any]:
    from manosube_agent_civilization.binding.route import bind_project

    genesis = genesis_project_state()
    genesis_records = list(genesis_source_snapshot_records(genesis))
    kwargs = ra.bind_project_kwargs(genesis)
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records, schema_root=SCHEMA_ROOT
    )
    return {
        "project_binding_id": result["project_binding_id"],
        "committed_state": result["committed_state"],
    }


def initialize_genesis(store: FileStateStore) -> dict[str, Any]:
    committed_state: dict[str, Any] = bind_genesis(store)["committed_state"]
    return committed_state


def observe_before(
    k: int,
    current_state: dict[str, Any],
    *,
    snapshot: dict[str, Any],
    instant: str,
    evidence_recorded_at: str,
) -> dict[str, Any]:
    provisional_request = ra.before_observation_request(
        k,
        snapshot=snapshot,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        started_at=instant,
        ended_at=instant,
    )
    provisional_bundle = observe(provisional_request)

    provisional_difference_request = ra.derivation_request(
        k,
        observation_bundle=provisional_bundle,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        snapshot_ref_value=ra.snapshot_ref(snapshot),
    )
    provisional_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": evidence_recorded_at,
        "observation_request": provisional_request,
        "difference_request": provisional_difference_request,
        "change_request": None,
        "post_change_observation_request": None,
        "verification_observation_request": None,
        "verification_result_provenance": None,
        "artifact_references": [dict(ra.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    provisional_evidence = derive_evidence(provisional_evidence_request)

    request = ra.before_observation_request(
        k,
        snapshot=snapshot,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        started_at=instant,
        ended_at=instant,
        ref={"kind": "observation_evidence", "id": provisional_evidence["evidence_id"]},
    )
    bundle = observe(request)
    assert (
        bundle["observations"][-1]["observation_id"]
        == provisional_bundle["observations"][-1]["observation_id"]
    )

    difference_request = ra.derivation_request(
        k,
        observation_bundle=bundle,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        snapshot_ref_value=ra.snapshot_ref(snapshot),
    )
    observation_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": evidence_recorded_at,
        "observation_request": request,
        "difference_request": difference_request,
        "change_request": None,
        "post_change_observation_request": None,
        "verification_observation_request": None,
        "verification_result_provenance": None,
        "artifact_references": [dict(ra.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    observation_evidence = derive_evidence(observation_evidence_request)
    if observation_evidence["evidence_id"] != provisional_evidence["evidence_id"]:
        raise AssertionError(
            f"task {k}: before-Observation Evidence fixed point did not converge: "
            f"{observation_evidence['evidence_id']!r} != {provisional_evidence['evidence_id']!r}"
        )

    return {
        "request": request,
        "bundle": bundle,
        "observation_evidence_request": observation_evidence_request,
        "observation_evidence": observation_evidence,
        "snapshot": snapshot,
    }


def derive_difference(
    k: int, current_state: dict[str, Any], before: dict[str, Any]
) -> dict[str, Any]:
    request = ra.derivation_request(
        k,
        observation_bundle=before["bundle"],
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        snapshot_ref_value=ra.snapshot_ref(before["snapshot"]),
    )
    result = derive_differences(request)
    return {"request": request, "result": result, "difference": result["differences"][0]}


def check_authority(k: int, difference: dict[str, Any], *, instant: str) -> dict[str, Any]:
    request: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": difference["project_id"],
        "difference": difference,
        "requested_action": ra.requested_action(k),
        "requested_scope": ra.action_scope(),
        "current_state_revision": difference["observed_state_revision"],
        "current_state_fingerprint": difference["observed_state_fingerprint"],
        "authority_rules": [ra.authority_rule(project_id=difference["project_id"])],
        "prohibitions": [],
        "approvals": [],
        "evaluation_time": instant,
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
    *,
    snapshot: dict[str, Any],
    instant: str,
    evidence_recorded_at: str,
) -> dict[str, Any]:
    difference_request = ra.derivation_request(
        k,
        observation_bundle=before["bundle"],
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        snapshot_ref_value=ra.snapshot_ref(before["snapshot"]),
    )

    provisional_request = ra.change_result_observation_request(
        k,
        snapshot=snapshot,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        started_at=instant,
        ended_at=instant,
    )
    provisional_bundle = observe(provisional_request)
    provisional_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": evidence_recorded_at,
        "observation_request": before["request"],
        "difference_request": difference_request,
        "change_request": change["request"],
        "post_change_observation_request": provisional_request,
        "verification_observation_request": None,
        "verification_result_provenance": None,
        "artifact_references": [dict(ra.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    provisional_evidence = derive_evidence(provisional_evidence_request)

    request = ra.change_result_observation_request(
        k,
        snapshot=snapshot,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        started_at=instant,
        ended_at=instant,
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
        "snapshot": snapshot,
    }


def observe_verification(
    k: int,
    current_state: dict[str, Any],
    before: dict[str, Any],
    *,
    snapshot: dict[str, Any],
    instant: str,
) -> dict[str, Any]:
    difference_request = ra.derivation_request(
        k,
        observation_bundle=before["bundle"],
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        snapshot_ref_value=ra.snapshot_ref(before["snapshot"]),
    )

    provisional_request = ra.verification_observation_request(
        k,
        snapshot=snapshot,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        started_at=instant,
        ended_at=instant,
    )
    provisional_bundle = observe(provisional_request)
    provisional_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": instant,
        "observation_request": before["request"],
        "difference_request": difference_request,
        "change_request": None,
        "post_change_observation_request": None,
        "verification_observation_request": provisional_request,
        "verification_result_provenance": ra.VERIFICATION_RESULT_PROVENANCE,
        "artifact_references": [dict(ra.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    provisional_evidence = derive_evidence(provisional_evidence_request)

    request = ra.verification_observation_request(
        k,
        snapshot=snapshot,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        started_at=instant,
        ended_at=instant,
        ref={"kind": "observation_evidence", "id": provisional_evidence["evidence_id"]},
    )
    bundle = observe(request)
    assert (
        bundle["observations"][-1]["observation_id"]
        == provisional_bundle["observations"][-1]["observation_id"]
    )

    verification_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": instant,
        "observation_request": before["request"],
        "difference_request": difference_request,
        "change_request": None,
        "post_change_observation_request": None,
        "verification_observation_request": request,
        "verification_result_provenance": ra.VERIFICATION_RESULT_PROVENANCE,
        "artifact_references": [dict(ra.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    verification_evidence = derive_evidence(verification_evidence_request)
    if verification_evidence["evidence_id"] != provisional_evidence["evidence_id"]:
        raise AssertionError(
            f"task {k}: verification-Observation Evidence fixed point did not converge: "
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
    *,
    instant: str,
) -> dict[str, Any]:
    difference_request = change_result.get("difference_request") or ra.derivation_request(
        k,
        observation_bundle=before["bundle"],
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
        snapshot_ref_value=ra.snapshot_ref(before["snapshot"]),
    )
    change_result_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": instant,
        "observation_request": before["request"],
        "difference_request": difference_request,
        "change_request": change["request"],
        "post_change_observation_request": change_result["request"],
        "verification_observation_request": None,
        "verification_result_provenance": None,
        "artifact_references": [dict(ra.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    change_result_evidence = derive_evidence(change_result_evidence_request)
    seed_evidence_id = change_result.get("_seed_evidence_id")
    if seed_evidence_id is not None and change_result_evidence["evidence_id"] != seed_evidence_id:
        raise AssertionError(
            f"task {k}: Change-result Evidence fixed point did not converge: "
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
    instant: str,
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
        "evaluation_instant": instant,
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
    instant: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bindings: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    for invariant_id in sorted(expected_g19_invariant_ids()):
        evaluation_id = (
            "INV-EVAL-"
            + hashlib.sha256(f"real_agent_present:{k}:{difference_id}:{invariant_id}".encode())
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
            evaluated_at=instant,
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


def run_one_task(
    store: FileStateStore,
    *,
    k: int,
    committed_state: dict[str, Any],
    perform_real_change: Callable[[], None],
    instant: str,
) -> dict[str, Any]:
    """Run the real Difference -> Authority -> Change -> (real Agent action) ->
    Observation -> Evidence -> Sufficiency -> Reflow cycle for corpus task *k*, given the
    Store's own real current committed State.

    *perform_real_change* is called exactly once, after the Change record is derived and
    before the post-change Observation reads the real world -- it is where the real Agent
    action itself happens (identical to what ``MANOSUBE_ABSENT`` already performed
    directly): this function never simulates, asserts, or pre-computes that side effect
    itself.
    """

    before_instant = _offset(instant, seconds=0)
    authority_instant = _offset(instant, seconds=300)
    change_result_instant = _offset(instant, seconds=900)
    verification_instant = _offset(instant, seconds=1200)
    evidence_instant = _offset(instant, seconds=1500)
    closure_instant = _offset(instant, seconds=1800)

    before_snapshot = ra.status_source_snapshot(captured_at=before_instant)
    before = observe_before(
        k,
        committed_state,
        snapshot=before_snapshot,
        instant=before_instant,
        evidence_recorded_at=evidence_instant,
    )
    diff = derive_difference(k, committed_state, before)
    difference = diff["difference"]
    policy = ra.closure_policy(difference["difference_id"], predicate=ra.predicate_id(k))

    authority = check_authority(k, difference, instant=authority_instant)
    change = derive_the_change(authority)

    # The real Agent action -- the identical write MANOSUBE_ABSENT already performed
    # directly for this same task, per RAW_EVENTS.md -- happens here, for real, only now
    # that a real Authority Decision has authorized it.
    perform_real_change()

    change_result_snapshot = ra.status_source_snapshot(captured_at=change_result_instant)
    change_result_obs = observe_change_result(
        k,
        committed_state,
        before,
        change,
        snapshot=change_result_snapshot,
        instant=change_result_instant,
        evidence_recorded_at=evidence_instant,
    )

    # A genuinely separate, later real observation of the real, now-changed world --
    # never the identical Observation content the Change-result step already produced
    # (G8's anti-self-closing check refuses exactly that reuse).
    after_snapshot = ra.status_source_snapshot(captured_at=verification_instant)
    verification_obs = observe_verification(
        k, committed_state, before, snapshot=after_snapshot, instant=verification_instant
    )

    change_result_evidence_bundle = derive_the_change_result_evidence(
        k, committed_state, before, change, change_result_obs, instant=evidence_instant
    )
    sufficiency = evaluate_the_sufficiency(
        difference,
        policy,
        observation_evidence_request=before["observation_evidence_request"],
        change_result_evidence_request=change_result_evidence_bundle[
            "change_result_evidence_request"
        ],
        instant=evidence_instant,
    )

    verification_difference_request = ra.derivation_request(
        k,
        observation_bundle=verification_obs["bundle"],
        fingerprint=committed_state["semantic_fingerprint"],
        state_revision=committed_state["state_revision"],
        snapshot_ref_value=ra.snapshot_ref(after_snapshot),
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
    after_snapshot_ref = ra.snapshot_ref(after_snapshot)
    after_state_candidate = build_after_state_candidate(
        current_state=current_state,
        kernel_source_ref=kernel_source_ref,
        semantic_state=after_semantic_state,
        semantic_fingerprint=after_fingerprint,
        source_snapshot_refs=[after_snapshot_ref],
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
        source_snapshot_refs=[after_snapshot_ref],
        source_snapshots=[after_snapshot],
        sufficiency=sufficiency["result"],
        material_contradictions=[],
        blocking_contradictions=[],
        proposed_terminal_status="CLOSED",
        evaluated_at=closure_instant,
        request_contract_keys=REQUEST_KEYS,
    )
    invariant_bindings, invariant_evaluations = invariant_bindings_and_evaluations(
        k,
        difference["difference_id"],
        current_state,
        after_state_candidate=after_state_candidate,
        verification_context=verification_context,
        instant=closure_instant,
    )
    invariant_evaluation_refs = [b["invariant_evaluation_ref"] for b in invariant_bindings]
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
        "objective_revision_id": ra.OBJECTIVE_REVISION_ID,
        "objective_revision": ra.objective_revision(),
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
        "source_snapshot_refs": [after_snapshot_ref],
        "source_snapshots": [after_snapshot],
        "producing_change_refs": [change_ref],
        "candidate_invariant_evaluation_bindings": invariant_bindings,
        "candidate_claim_evaluation_bindings": [claim_binding],
        "candidate_claim_evaluation_events": [claim_event],
        "invariant_evaluations": invariant_evaluations,
        "material_contradictions": [],
        "terminal_reason_evidence_refs": [],
        "terminal_reason_evidence_requests": [],
        "proposed_terminal_status": "CLOSED",
        "evaluated_at": closure_instant,
    }

    reflow_kwargs: dict[str, Any] = {
        "project_id": ra.PROJECT_ID,
        "closure_request": closure_request,
        "previous_event_id": difference["genesis_event_ref"]["id"],
        "event_revision": 1,
        "observation_refs": [{"kind": "observation", "id": verification_observation_id}],
        "reflow_instant": closure_instant,
        "expected_state_revision": committed_state["state_revision"],
        "expected_state_fingerprint": committed_state["semantic_fingerprint"],
        "authority_ref": {
            "kind": "authority_decision",
            "id": authority["decision"]["authority_decision_id"],
        },
        "change_refs": [change_ref],
        "provenance_only_evidence_requests": [verification_obs["verification_evidence_request"]],
        "auxiliary_source_snapshots": [before_snapshot, change_result_snapshot],
        "genesis_lifecycle_event": next(
            event
            for event in diff["result"]["events"]
            if event["difference_event_id"] == difference["genesis_event_ref"]["id"]
        ),
    }

    result = reflow(store, **reflow_kwargs)

    return {
        "k": k,
        "before": before,
        "difference": difference,
        "authority": authority,
        "change": change,
        "change_result_observation": change_result_obs,
        "verification_observation": verification_obs,
        "evidence": change_result_evidence_bundle,
        "sufficiency": sufficiency,
        "closure_request": closure_request,
        "reflow_result": result,
        "identity": {
            "task": ra.TASK_KEYS[k],
            "difference_id": difference["difference_id"],
            "authority_decision_id": authority["decision"]["authority_decision_id"],
            "change_id": change["change"]["change_id"],
            "before_source_snapshot_id": before_snapshot["source_snapshot_id"],
            "after_source_snapshot_id": after_snapshot["source_snapshot_id"],
            "evidence_sufficiency_id": sufficiency["result"]["evidence_sufficiency_id"],
            "closure_evaluation_id": result["evaluation"]["closure_evaluation_id"],
            "difference_lifecycle_event_id": result["event"]["difference_event_id"],
            "state_transition_ref": result["state_transition_ref"],
            "final_state_revision": result["committed_state"]["state_revision"],
            "final_state_fingerprint": result["committed_state"]["semantic_fingerprint"],
            "final_terminal_status": result["event"]["to_status"],
        },
    }
