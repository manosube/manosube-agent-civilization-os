"""Phase 8 Vertical Proof -- the one public proof entry.

``00_KERNEL/VERTICAL_PROOF_CONTRACT.md`` names this module the Proof Entry: the one function
that drives ``OBJECTIVE -> INITIAL STATE -> OBSERVATION -> OBSERVATION EVIDENCE -> DIFFERENCE
-> AUTHORITY CHECK -> CHANGE -> RE-OBSERVATION -> CHANGE RESULT EVIDENCE -> EVIDENCE
SUFFICIENCY -> CLOSURE EVALUATION -> ATOMIC REFLOW -> NEW STATE -> RECONSTRUCTION`` through
real, public canonical owners only (``PUBLIC_CANONICAL_OWNER_ENTRYPOINTS_ONLY=true``).

Every intermediate canonical record -- the Observation, the Difference, the Authority
Decision, the Change, the two Evidence records, the Evidence Sufficiency Result, the Closure
Evaluation, the lifecycle event, the State transition -- is produced here by calling its own
real producer (:mod:`manosube_agent_civilization.observation`, ``.difference``,
``.authority``, ``.change``, ``.evidence``, ``.reflow``) against the bounded, pinned inputs
``tests/fixtures/vertical_proof.py`` supplies. Nothing here hand-writes one of those records,
and reproduces no owner's own algorithm
(``NO_MANUAL_INTERMEDIATE_CANONICAL_RECORD_CONSTRUCTION=true``).

**Reused Candidate-assembly utilities.** Building a ``CANDIDATE_CLOSURE``-eligible Reflow
request requires the caller to independently verify every mandatory v0.1 Invariant
(``reflow/closure.py``'s own G19) and pre-assemble its own
``candidate_invariant_evaluation_binding``/``candidate_claim_evaluation_binding``/``_event``
records around that real verification -- a design this Kernel's own ``reflow()`` already
places on every caller, not something Phase 8 invents. This module reuses
``tests/reflow_helpers.py``'s existing, generic (fixture-content-agnostic)
``mandatory_invariant_bindings``/``mandatory_invariant_evaluations``/
``mandatory_x003_claim_binding_and_event`` for exactly that assembly, since those functions
themselves call nothing but real owners (:func:`~manosube_agent_civilization.difference.
invariant_verifiers.verify_invariant`, :func:`~manosube_agent_civilization.difference.
completion.build_completion_record`, and the real content-address identity functions) and
carry no Phase 8 (or any other fixture's) business content of their own -- the same, already
13-round-reviewed pattern every accepted Phase 7 ``CANDIDATE_CLOSURE`` integration test in
this repository already depends on. Duplicating that assembly instead of reusing it would be
a second, silently divergent copy of the identical real-owner composition, not independence.

**A genuinely three-Observation route.** ``reflow()``'s own G8 gate refuses a ``CHANGE_BOUND``
closure whose independent re-observation (``reobservation.after_observation_refs``) shares any
Observation identity with the Change-result Evidence's own reproduced lineage
(``after-state Observation overlaps a Change result reference`` -- the Kernel's own
anti-self-closing rule: a Change cannot verify itself). No existing fixture in this repository
threads a real Authority-authorized Change through a real, independent re-observation to a
real ``CLOSED`` Reflow outcome; this module is the first. It therefore performs three,
genuinely separate real Observation Engine calls over the identical bounded fixture inputs:
one ``NOT-READY`` before-observation (grounds the Difference and both Evidence records' own
``before_state``), one ``READY`` post-change observation (grounds Change-result Evidence's own
``after_state``), and one further ``READY`` verification observation, at its own later
observation window and its own ``attempt_id`` (grounds Reflow's own independent
``reobservation``) -- three real, distinct acts of observation over the same real post-change
world, never one Observation record reused across two roles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.fixtures import vertical_proof as fx
from tests.reflow_helpers import (
    mandatory_invariant_bindings,
    mandatory_invariant_evaluations,
    mandatory_x003_claim_binding_and_event,
)
from tests.state_helpers import (
    SCHEMA_ROOT,
    genesis_source_snapshot_records,
    initial_state,
    real_kernel_git_objects,
    real_kernel_source_snapshot,
)

from manosube_agent_civilization.authority import evaluate_authority
from manosube_agent_civilization.change import derive_change
from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.invariant_verifiers import (
    build_invariant_verification_context,
    verify_invariant,
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
from manosube_agent_civilization.reflow.invariant_registry import expected_g19_invariant_ids
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.state.fingerprint import (
    fingerprint_project_state,
    fingerprint_semantic_state,
)
from manosube_agent_civilization.store import FileStateStore

REFLOW_INSTANT = fx.REFLOW_INSTANT


def genesis_semantic_state() -> dict[str, Any]:
    """This proof's own genesis ``semantic_state`` -- built on the identical, already-pinned,
    schema-valid ``initial_state_revision_zero`` contract fixture every other suite in this
    repository already treats as the one canonical genesis-State shape
    (:func:`tests.state_helpers.initial_state`; a real, frozen ``01_SCHEMA/state/project_
    state.schema.json`` conformance case from ``tests/contract/fixtures/schema/valid/cases.
    json``, never business/test-support logic this proof would otherwise have to re-derive
    field-for-field). Only the ``code`` domain is overridden, to the specific ``UNKNOWN``
    starting status this proof's own Candidate later moves to ``KNOWN``."""

    state = initial_state()["semantic_state"]
    state["code"] = {
        "status": "UNKNOWN",
        "claims": {},
        "identity_refs": [],
        "evidence_refs": [],
        "blind_spots": ["not observed"],
    }
    return state


def after_semantic_state() -> dict[str, Any]:
    """The one real content difference this proof's Candidate claims: the ``code`` domain's
    own ``status`` moves ``UNKNOWN -> KNOWN`` -- nothing else changes."""

    state = genesis_semantic_state()
    state["code"] = {
        "status": "KNOWN",
        "claims": {"vertical_proof_target": "READY"},
        "identity_refs": [],
        "evidence_refs": [],
        "blind_spots": [],
    }
    return state


def genesis_project_state() -> dict[str, Any]:
    """This proof's own, real genesis ``project_state`` -- revision 0, built on the identical
    pinned contract fixture :func:`genesis_semantic_state` explains, overridden only to this
    proof's own dedicated ``project_id``/``objective_revision_id`` and this proof's own
    ``code``-domain starting content, then re-fingerprinted for real
    (R9-F2's own ``GENESIS_KERNEL_PROVENANCE_REQUIRED=true`` real Kernel Source Snapshot
    provenance is already the pinned fixture's own, unmodified by this override)."""

    state = initial_state()
    state["project_id"] = fx.PROJECT_ID
    state["objective_revision_id"] = fx.OBJECTIVE_REVISION_ID
    state["semantic_state"] = genesis_semantic_state()
    state["semantic_fingerprint"] = fingerprint_project_state(
        state, schema_root=SCHEMA_ROOT
    ).as_dict()
    return state


class FaultInjectingStore(FileStateStore):
    """A thin, non-canonical test seam: forwards every call unchanged to the real
    :class:`FileStateStore`, except that ``commit`` (and only ``commit``) receives the
    caller's own ``fault`` hook -- the identical, real, public crash-injection parameter
    ``FileStateStore.commit`` (and :func:`~manosube_agent_civilization.reflow.commit.
    commit_reflow`) already exposes to every caller. ``reflow()`` itself never accepts a
    ``fault`` parameter (production callers must never be able to inject one), so this is the
    one seam a repository-resident crash test can use to exercise a *real* ``reflow()``-driven
    commit's own crash/recovery behavior without reproducing any of ``reflow()``'s internal
    algorithm and without a second Store implementation: this class mints no record, decides
    nothing, and owns no State of its own -- it is the identical, one canonical
    ``FileStateStore``, called through.
    """

    def __init__(self, *args: Any, fault: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._vp8_fault = fault

    def commit(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        # ``commit_reflow`` always passes its own ``fault`` keyword explicitly (``None`` when
        # the caller supplied none) -- ``setdefault`` would never override an explicit
        # ``None``, so this seam must replace the keyword outright, not merely fill it in.
        kwargs["fault"] = self._vp8_fault
        return super().commit(*args, **kwargs)


def build_store(tmp_path: Path, *, fault: Any = None) -> FileStateStore:
    """A real :class:`FileStateStore`, rooted outside the repository working tree (item D.1)."""

    if fault is None:
        return FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    return FaultInjectingStore(tmp_path / "backend", schema_root=SCHEMA_ROOT, fault=fault)


def initialize_genesis(store: FileStateStore) -> dict[str, Any]:
    """Item D.1: the real genesis State, its own real Kernel Source Snapshot record
    resolvable through the Store from the very first call."""

    genesis = genesis_project_state()
    store.initialize(fx.PROJECT_ID, genesis, records=genesis_source_snapshot_records(genesis))
    current: dict[str, Any] = store.load_current(fx.PROJECT_ID)
    return current


def observe_before(current_state: dict[str, Any]) -> dict[str, Any]:
    """Item D.2: the real before-Observation, through the real Observation owner."""

    request = fx.before_observation_request(
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    return {"request": request, "bundle": observe(request)}


def derive_difference(current_state: dict[str, Any], before: dict[str, Any]) -> dict[str, Any]:
    """Item D.3: the real Difference, through the real Difference owner."""

    request = fx.derivation_request(
        observation_bundle=before["bundle"],
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    result = derive_differences(request)
    return {"request": request, "result": result, "difference": result["differences"][0]}


def check_authority(difference: dict[str, Any]) -> dict[str, Any]:
    """Item D.4: the real Authority check, through the real Authority owner."""

    request: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": difference["project_id"],
        "difference": difference,
        "requested_action": fx.requested_action(),
        "requested_scope": fx.action_scope(),
        "current_state_revision": difference["observed_state_revision"],
        "current_state_fingerprint": difference["observed_state_fingerprint"],
        "authority_rules": [fx.authority_rule(project_id=difference["project_id"])],
        "prohibitions": [],
        "approvals": [],
        "evaluation_time": fx.AUTHORITY_EVALUATION_TIME,
    }
    decision = evaluate_authority(request)
    return {"request": request, "decision": decision}


def derive_the_change(authority: dict[str, Any]) -> dict[str, Any]:
    """Item D.5: the real Change, through the real Change owner."""

    request: dict[str, Any] = {
        "schema_version": "0.1",
        "authority_request": authority["request"],
        "authority_decision": authority["decision"],
    }
    change = derive_change(request)
    return {"request": request, "change": change}


def observe_change_result(current_state: dict[str, Any]) -> dict[str, Any]:
    """Item D.6 (first half): the real post-change Observation Change-result Evidence binds
    to."""

    request = fx.change_result_observation_request(
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    return {"request": request, "bundle": observe(request)}


def observe_verification(current_state: dict[str, Any]) -> dict[str, Any]:
    """Item D.6 (second half): the real, independent re-observation Reflow's own G8 gate
    verifies -- a genuinely separate Observation from :func:`observe_change_result`."""

    request = fx.verification_observation_request(
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    return {"request": request, "bundle": observe(request)}


def derive_the_evidence(
    current_state: dict[str, Any],
    before: dict[str, Any],
    change: dict[str, Any],
    change_result: dict[str, Any],
) -> dict[str, Any]:
    """Item D.7: the real Observation Evidence and Change-result Evidence, through the real
    Evidence owner."""

    difference_request = fx.derivation_request(
        observation_bundle=None,
        fingerprint=current_state["semantic_fingerprint"],
        state_revision=current_state["state_revision"],
    )
    observation_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": fx.EVIDENCE_RECORDED_AT,
        "observation_request": before["request"],
        "difference_request": difference_request,
        "change_request": None,
        "post_change_observation_request": None,
        "verification_observation_request": None,
        "artifact_references": [dict(fx.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    observation_evidence = derive_evidence(observation_evidence_request)

    change_result_evidence_request: dict[str, Any] = {
        "schema_version": "0.1",
        "recorded_at": fx.EVIDENCE_RECORDED_AT,
        "observation_request": before["request"],
        "difference_request": difference_request,
        "change_request": change["request"],
        "post_change_observation_request": change_result["request"],
        "verification_observation_request": None,
        "artifact_references": [dict(fx.ARTIFACT)],
        "predecessor_evidence_refs": [],
        "remaining_difference_refs": [],
    }
    change_result_evidence = derive_evidence(change_result_evidence_request)
    return {
        "difference_request": difference_request,
        "observation_evidence_request": observation_evidence_request,
        "observation_evidence": observation_evidence,
        "change_result_evidence_request": change_result_evidence_request,
        "change_result_evidence": change_result_evidence,
    }


def evaluate_the_sufficiency(
    difference: dict[str, Any], policy: dict[str, Any], evidence: dict[str, Any]
) -> dict[str, Any]:
    """Item D.8: the real Evidence Sufficiency, through the real Sufficiency owner."""

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
        "evidence_requests": [
            evidence["observation_evidence_request"],
            evidence["change_result_evidence_request"],
        ],
        "evaluation_instant": fx.SUFFICIENCY_EVALUATED_AT,
    }
    wrapper = evaluate_sufficiency(request)
    return {
        "request": request,
        "wrapper": wrapper,
        "result": wrapper["evidence_sufficiency_result"],
    }


def assemble_vertical_proof_route(tmp_path: Path, *, fault: Any = None) -> dict[str, Any]:
    """Build every real intermediate record and the exact ``reflow()`` call arguments for
    the one successful route, *without* calling ``reflow()`` itself.

    This is the identical assembly :func:`run_vertical_proof` runs, extracted so a required
    negative/interruption-route test (Issue #41 item E) can mutate exactly one already-real
    input -- a single field of ``closure_request``, or one keyword ``reflow()`` itself takes
    -- and then call ``reflow()`` directly, rather than a second, hand-duplicated assembly
    that could silently drift from the one real route this module proves.
    """

    store = build_store(tmp_path, fault=fault)
    genesis_state = initialize_genesis(store)

    before = observe_before(genesis_state)
    diff = derive_difference(genesis_state, before)
    difference = diff["difference"]
    policy = fx.closure_policy(difference["difference_id"])

    authority = check_authority(difference)
    change = derive_the_change(authority)

    change_result_obs = observe_change_result(genesis_state)
    verification_obs = observe_verification(genesis_state)

    evidence = derive_the_evidence(genesis_state, before, change, change_result_obs)
    sufficiency = evaluate_the_sufficiency(difference, policy, evidence)

    verification_difference_request = fx.derivation_request(
        observation_bundle=verification_obs["bundle"],
        fingerprint=genesis_state["semantic_fingerprint"],
        state_revision=genesis_state["state_revision"],
        snapshot_ref=fx.AFTER_SNAPSHOT_REF,
    )
    verification_observation_id = verification_obs["bundle"]["observations"][0]["observation_id"]

    kernel_source_ref, kernel_source_witness = real_kernel_git_objects()
    kernel_snapshot = real_kernel_source_snapshot()
    after_state = after_semantic_state()
    after_fingerprint = fingerprint_semantic_state(after_state).as_dict()
    current_state = {
        "revision": genesis_state["state_revision"],
        "fingerprint": genesis_state["semantic_fingerprint"],
    }
    change_ref = {"kind": "change", "id": change["change"]["change_id"]}
    after_state_candidate = build_after_state_candidate(
        current_state=current_state,
        kernel_source_ref=kernel_source_ref,
        semantic_state=after_state,
        semantic_fingerprint=after_fingerprint,
        source_snapshot_refs=[fx.AFTER_SNAPSHOT_REF],
        producing_change_refs=[change_ref],
    )
    blocking_contradictions: list[dict[str, Any]] = []
    verification_context = build_invariant_verification_context(
        policy=policy,
        difference=difference,
        current_state=current_state,
        after_state_candidate=after_state_candidate,
        resolution_mode="CHANGE_BOUND",
        change_result_evidence=[evidence["change_result_evidence"]],
        change_free_evidence=[],
        after_observation_ids={verification_observation_id},
        source_snapshot_refs=[fx.AFTER_SNAPSHOT_REF],
        source_snapshots=[fx.AFTER_SOURCE_SNAPSHOT],
        sufficiency=sufficiency["result"],
        material_contradictions=[],
        blocking_contradictions=blocking_contradictions,
        proposed_terminal_status="CLOSED",
        evaluated_at=fx.SUFFICIENCY_EVALUATED_AT,
        request_contract_keys=REQUEST_KEYS,
    )
    verification_results = {
        invariant_id: verify_invariant(invariant_id, verification_context)
        for invariant_id in expected_g19_invariant_ids()
    }
    invariant_bindings = mandatory_invariant_bindings(
        difference["difference_id"],
        current_state,
        after_state_candidate=after_state_candidate,
        verification_results=verification_results,
    )
    invariant_evaluations = mandatory_invariant_evaluations(
        difference["difference_id"],
        current_state,
        after_state_candidate=after_state_candidate,
        verification_results=verification_results,
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
        "objective_revision_id": fx.OBJECTIVE_REVISION_ID,
        "objective_revision": fx.objective_revision(),
        "kernel_source_ref": kernel_source_ref,
        "base_kernel_source_ref": kernel_source_ref,
        "kernel_source_witness": kernel_source_witness,
        "resolution_mode": "CHANGE_BOUND",
        "change_refs": [change_ref],
        "change_result_evidence_refs": [
            {
                "kind": "observation_evidence",
                "id": evidence["change_result_evidence"]["evidence_id"],
            }
        ],
        "change_result_evidence_requests": [evidence["change_result_evidence_request"]],
        "change_free_verification_evidence_refs": [],
        "change_free_verification_evidence_requests": [],
        "reobservation": {
            "derivation_request": verification_difference_request,
            "after_observation_refs": [{"kind": "observation", "id": verification_observation_id}],
        },
        "evidence_sufficiency_request": sufficiency["request"],
        "after_state_semantic_state": after_state,
        "source_snapshot_refs": [fx.AFTER_SNAPSHOT_REF],
        "source_snapshots": [fx.AFTER_SOURCE_SNAPSHOT, kernel_snapshot],
        "producing_change_refs": [change_ref],
        "candidate_invariant_evaluation_bindings": invariant_bindings,
        "candidate_claim_evaluation_bindings": [claim_binding],
        "candidate_claim_evaluation_events": [claim_event],
        "invariant_evaluations": invariant_evaluations,
        "material_contradictions": [],
        "terminal_reason_evidence_refs": [],
        "terminal_reason_evidence_requests": [],
        "proposed_terminal_status": "CLOSED",
        "evaluated_at": fx.SUFFICIENCY_EVALUATED_AT,
    }

    reflow_kwargs: dict[str, Any] = {
        "project_id": fx.PROJECT_ID,
        "closure_request": closure_request,
        "previous_event_id": difference["genesis_event_ref"]["id"],
        "event_revision": 1,
        "observation_refs": [{"kind": "observation", "id": verification_observation_id}],
        "reflow_instant": REFLOW_INSTANT,
        "expected_state_revision": genesis_state["state_revision"],
        "expected_state_fingerprint": genesis_state["semantic_fingerprint"],
        "authority_ref": {
            "kind": "authority_decision",
            "id": authority["decision"]["authority_decision_id"],
        },
        "change_refs": [change_ref],
    }

    return {
        "store": store,
        "genesis_state": genesis_state,
        "before": before,
        "difference": difference,
        "authority": authority,
        "change": change,
        "change_ref": change_ref,
        "change_result_observation": change_result_obs,
        "verification_observation": verification_obs,
        "verification_observation_id": verification_observation_id,
        "evidence": evidence,
        "sufficiency": sufficiency,
        "policy": policy,
        "closure_request": closure_request,
        "reflow_kwargs": reflow_kwargs,
    }


def run_vertical_proof(tmp_path: Path, *, fault: Any = None) -> dict[str, Any]:
    """Items D.1-D.14: run the full natural cycle exactly once and return every named
    identity plus the constructed request/record pool, so a caller can assert the identity
    ledger (``00_KERNEL/VERTICAL_PROOF_CONTRACT.md``) without re-deriving any of it.

    Raises whatever the real owner it calls raises -- a caller wanting a *refused* route
    (a required negative/interruption route) calls :func:`assemble_vertical_proof_route`
    directly, mutates exactly the one input the route names, and calls ``reflow()`` itself.
    """

    assembly = assemble_vertical_proof_route(tmp_path, fault=fault)
    store = assembly["store"]
    genesis_state = assembly["genesis_state"]
    before = assembly["before"]
    difference = assembly["difference"]
    authority = assembly["authority"]
    change = assembly["change"]
    change_result_obs = assembly["change_result_observation"]
    verification_obs = assembly["verification_observation"]
    verification_observation_id = assembly["verification_observation_id"]
    evidence = assembly["evidence"]
    sufficiency = assembly["sufficiency"]
    closure_request = assembly["closure_request"]

    result = reflow(store, **assembly["reflow_kwargs"])

    reconstructed = FileStateStore(store.root, schema_root=SCHEMA_ROOT).reconstruct(fx.PROJECT_ID)

    return {
        "store": store,
        "genesis_state": genesis_state,
        "before": before,
        "difference": difference,
        "authority": authority,
        "change": change,
        "change_result_observation": change_result_obs,
        "verification_observation": verification_obs,
        "evidence": evidence,
        "sufficiency": sufficiency,
        "closure_request": closure_request,
        "reflow_result": result,
        "reconstructed_state": reconstructed,
        "identity_ledger": {
            "objective_revision_id": fx.OBJECTIVE_REVISION_ID,
            "initial_state_revision": genesis_state["state_revision"],
            "initial_state_fingerprint": genesis_state["semantic_fingerprint"],
            "before_observation_id": before["bundle"]["observations"][-1]["observation_id"],
            "difference_id": difference["difference_id"],
            "difference_lifecycle_head_ref": dict(difference["genesis_event_ref"]),
            "authority_decision_id": authority["decision"]["authority_decision_id"],
            "change_id": change["change"]["change_id"],
            "change_result_observation_id": change_result_obs["bundle"]["observations"][-1][
                "observation_id"
            ],
            "verification_observation_id": verification_observation_id,
            "observation_evidence_id": evidence["observation_evidence"]["evidence_id"],
            "change_result_evidence_id": evidence["change_result_evidence"]["evidence_id"],
            "evidence_sufficiency_id": sufficiency["result"]["evidence_sufficiency_id"],
            "closure_evaluation_id": result["evaluation"]["closure_evaluation_id"],
            "difference_lifecycle_event_id": result["event"]["difference_event_id"],
            "state_transition_ref": result["state_transition_ref"],
            "final_state_revision": result["committed_state"]["state_revision"],
            "final_state_fingerprint": result["committed_state"]["semantic_fingerprint"],
            "final_lineage_head_ref": result["committed_state"]["lineage_head_ref"],
        },
    }
