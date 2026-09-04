"""Shared fixtures for Reflow's Closure Evaluation producer tests.

Every Difference, Closure Policy and Evidence Sufficiency request here is exactly the
Phase 4/6 fixture family in ``tests/difference_helpers.py`` and ``tests/evidence_helpers.py``
-- nothing is hand-built that those public predecessor routes already produce.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    objective_revision,
    observation_scope,
    semantic_state,
    state_fingerprint,
)
from tests.evidence_helpers import (
    AFTER_REVISION,
    after_observation_request,
    closure_policy,
    evidenced_difference,
    sufficiency_request,
)
from tests.state_helpers import SCHEMA_ROOT, initial_state

from manosube_agent_civilization.evidence.engine import derive_evidence
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.reflow.claims import (
    candidate_claim_evaluation_event_id,
    candidate_claim_evaluation_series_id,
)
from manosube_agent_civilization.reflow.closure import MANDATORY_X003_CLAIM_REF
from manosube_agent_civilization.reflow.identity import material_contradiction_id
from manosube_agent_civilization.reflow.invariant_registry import (
    V0_1_INVARIANT_DEFINITION_DIGESTS,
    candidate_invariant_evaluation_binding_id,
    expected_g19_invariant_ids,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

GIT_TREE_REF: dict[str, Any] = {
    "kind": "git_tree",
    "repository": "manosube/manosube-agent-civilization-os",
    "commit_sha": "a" * 40,
    "tree_sha": "b" * 40,
}

EVALUATED_AT = "2026-08-30T11:05:00Z"


def _advanced_project_state(
    state: dict[str, Any], *, next_semantic_state: dict[str, Any] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(successor_project_state, state_transition_event)`` one revision forward."""

    successor = deepcopy(state)
    successor["state_revision"] = state["state_revision"] + 1
    successor["previous_state_fingerprint"] = state["semantic_fingerprint"]
    tx = f"TX-ADVANCE-{successor['state_revision']:04d}"
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": tx}
    if next_semantic_state is not None:
        successor["semantic_state"] = next_semantic_state
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1", "transaction_id": tx, "event_type": "TRANSITION",
        "project_id": successor["project_id"], "from_revision": state["state_revision"],
        "to_revision": successor["state_revision"], "before_fingerprint": state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"], "after_state": successor,
        "evidence_refs": [], "committed_at": "2026-08-30T09:00:00Z",
    }
    return successor, event


def store_ready_for_closure(
    store: FileStateStore, *, genesis: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Initialize *store* (from *genesis*, defaulting to ``initial_state()``) and advance
    it to a real, committed State at ``AFTER_REVISION``.

    F1/F2 now bind a Closure Evaluation's ``current_state`` to the Store's own canonical
    State rather than a caller-asserted one, so a candidate-closure test needs a real Store
    lineage that actually reaches at least ``AFTER_REVISION`` (G5's revision floor is the
    only thing any gate checks about it) -- not a hand-asserted stand-in. Every
    intermediate revision is a real committed ``state_transition``.
    """

    if genesis is None:
        genesis = initial_state()
    genesis = deepcopy(genesis)
    genesis["semantic_fingerprint"] = fingerprint_project_state(
        genesis, schema_root=SCHEMA_ROOT
    ).as_dict()
    store.initialize(genesis["project_id"], genesis)

    current = genesis
    for step in range(1, AFTER_REVISION + 1):
        # Mutated in place (never swapped wholesale) so callers who seeded *genesis* with
        # their own bookkeeping (e.g. a pre-existing `open_differences` entry) keep it
        # across every advanced revision, exactly as a real Reflow bookkeeping mutation
        # would.
        next_semantic = deepcopy(current["semantic_state"])
        if step == AFTER_REVISION:
            next_semantic["code"]["status"] = "KNOWN"
        successor, event = _advanced_project_state(current, next_semantic_state=next_semantic)
        store.commit(
            successor["project_id"],
            current["state_revision"],
            current["semantic_fingerprint"],
            successor,
            event,
        )
        current = successor
    return current


def fixture_difference() -> dict[str, Any]:
    """The canonical NOT-READY Difference every closure test evaluates against."""

    return evidenced_difference()


def fixture_policy(difference: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return closure_policy(difference["difference_id"], **kwargs)


def satisfied_reobservation(
    difference: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return ``(derivation_request, after_observation_ref, later_state_fingerprint)``.

    The re-observation is a real, independent Observation run through the public
    Observation Engine (``after_observation_request`` -> ``observe``), re-derived through
    the real ``derive_differences`` producer -- never a hand-written "satisfied" record.
    """

    after_bundle = observe(after_observation_request())
    observation_ref = {
        "kind": "observation",
        "id": after_bundle["observations"][0]["observation_id"],
    }
    later_fingerprint = state_fingerprint("KNOWN")
    request = derivation_request(
        objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": observation_scope(),
                "observation_bundle": after_bundle,
            }
        ],
        later_fingerprint,
        AFTER_REVISION,
    )
    return request, observation_ref, later_fingerprint


def mandatory_x003_claim_binding(
    difference: dict[str, Any],
    current_state: dict[str, Any],
    *,
    evaluation_status: str = "SATISFIED",
    claim_ref: dict[str, str] | None = None,
) -> dict[str, Any]:
    """One conformant ``candidate_claim_evaluation_binding`` for the mandatory X-003 claim."""

    required_claim_ref = claim_ref if claim_ref is not None else MANDATORY_X003_CLAIM_REF
    policy_ref = deepcopy(difference["closure_policy"])
    candidate_id = "STATE-CANDIDATE-" + "1" * 64
    series_id = candidate_claim_evaluation_series_id(
        difference_id=difference["difference_id"],
        policy_ref=policy_ref,
        candidate_id=candidate_id,
        required_claim_ref=required_claim_ref,
    )
    return {
        "kind": "candidate_claim_evaluation_binding",
        "binding_id": "CAND-CLAIM-EVAL-" + "0" * 64,
        "difference_id": difference["difference_id"],
        "policy_ref": policy_ref,
        "candidate_id": candidate_id,
        "candidate_semantic_fingerprint": {
            "profile": "MANOSUBE-STATE-SHA256-0.1",
            "digest": "1" * 64,
        },
        "base_state_ref": {
            "kind": "state",
            "revision": current_state["revision"],
            "fingerprint": current_state["fingerprint"],
        },
        "required_claim_ref": required_claim_ref,
        "evaluation_series_id": series_id,
        "evaluation_head_event_ref": {
            "kind": "candidate_claim_evaluation_event",
            "id": "CAND-CLAIM-EVT-" + "3" * 64,
        },
        "completion_record_ref": {"kind": "completion_record", "id": "CMP-" + "4" * 64},
        "evaluation_record_fingerprint": "sha256:" + "5" * 64,
        "evaluation_status": evaluation_status,
        "evaluation_evidence_refs": {"collection_kind": "UNORDERED_SET", "members": []},
        "evaluated_at": EVALUATED_AT,
    }


def base_closure_request(
    difference: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    """A candidate-free (``TERMINAL_POLICY_ONLY``-shaped) request every test starts from."""

    return {
        "difference": difference,
        "current_status": "VERIFYING",
        "policy": policy,
        "difference_event_head_ref": deepcopy(difference["genesis_event_ref"]),
        "current_state": {
            "revision": AFTER_REVISION,
            "fingerprint": state_fingerprint("KNOWN"),
        },
        "kernel_source_ref": deepcopy(GIT_TREE_REF),
        "base_kernel_source_ref": deepcopy(GIT_TREE_REF),
        "resolution_mode": None,
        "change_refs": [],
        "change_result_evidence_refs": [],
        "change_result_evidence_requests": [],
        "change_free_verification_evidence_refs": [],
        "reobservation": None,
        "evidence_sufficiency_request": None,
        "after_state_semantic_state": None,
        "source_snapshot_refs": [],
        "producing_change_refs": [],
        "candidate_invariant_evaluation_bindings": [],
        "candidate_claim_evaluation_bindings": [],
        "candidate_claim_evaluation_events": [],
        "material_contradictions": [],
        "terminal_reason_evidence_refs": [
            {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
        ],
        "proposed_terminal_status": "BLOCKED",
        "evaluated_at": EVALUATED_AT,
    }


def _hex_digest(seed: str) -> str:
    """A deterministic 64-character hex string, for identities a fixture needs but whose
    exact value nothing in this vertical independently verifies (see the module docstring
    on ``reflow/invariant_registry.py``'s named non-claim about per-invariant digests)."""

    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def mandatory_invariant_bindings(current_state: dict[str, Any]) -> list[dict[str, Any]]:
    """One real ``candidate_invariant_evaluation_binding`` per pinned v0.1 mandatory id.

    G19 now additively requires the whole :func:`expected_g19_invariant_ids` union
    regardless of what a Closure Policy itself declares (see ``reflow/closure.py``), so a
    request that wants ``CANDIDATE_CLOSURE`` to actually reach ``SATISFIED`` must bind all
    of them, not only whatever the Policy names.
    """

    bindings = []
    for invariant_id in sorted(expected_g19_invariant_ids()):
        binding = {
            "kind": "candidate_invariant_evaluation_binding",
            "candidate_id": "STATE-CANDIDATE-" + "1" * 64,
            "candidate_semantic_fingerprint": {
                "profile": "MANOSUBE-STATE-SHA256-0.1",
                "digest": "1" * 64,
            },
            "base_state_ref": {
                "kind": "state",
                "revision": current_state["revision"],
                "fingerprint": current_state["fingerprint"],
            },
            "invariant_ref": {"kind": "kernel_invariant", "id": invariant_id},
            "invariant_definition_ref": {
                "repository": "manosube/manosube-agent-civilization-os",
                "path": "00_KERNEL/KERNEL_INVARIANTS.md",
                # R2-G19: the real pinned per-invariant definition digest, not a fake
                # placeholder -- closure.py's G19 now requires an exact match against
                # invariant_registry.expected_g19_invariant_entries().
                "invariant_definition_sha256": "sha256:" + V0_1_INVARIANT_DEFINITION_DIGESTS[invariant_id],
            },
            "invariant_evaluation_ref": {
                "kind": "invariant_evaluation",
                "id": "INV-EVAL-" + _hex_digest(f"eval:{invariant_id}").upper(),
            },
            "evaluation_record_fingerprint": "sha256:" + _hex_digest(f"record:{invariant_id}"),
            "evaluation_result": "PASS",
            "evaluation_evidence_refs": {"collection_kind": "UNORDERED_SET", "members": []},
            "evaluated_at": EVALUATED_AT,
        }
        # R2-G19: binding_id is now checked against its own content-addressed derivation,
        # so the fixture must compute the real value rather than a placeholder.
        binding["binding_id"] = candidate_invariant_evaluation_binding_id(binding)
        bindings.append(binding)
    return bindings


def mandatory_x003_claim_event(
    binding: dict[str, Any], difference: dict[str, Any], *, evaluation_status: str
) -> dict[str, Any]:
    """The one real ``candidate_claim_evaluation_event`` (revision 0) *binding* declares."""

    event: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "candidate_claim_evaluation_event",
        "event_id": "",
        "evaluation_series_id": binding["evaluation_series_id"],
        "event_revision": 0,
        "predecessor_event_ref": None,
        "difference_id": difference["difference_id"],
        "policy_ref": deepcopy(binding["policy_ref"]),
        "candidate_id": binding["candidate_id"],
        "required_claim_ref": deepcopy(binding["required_claim_ref"]),
        "completion_record_ref": deepcopy(binding["completion_record_ref"]),
        "completion_record_fingerprint": binding["evaluation_record_fingerprint"],
        "evaluation_status": evaluation_status,
        "recorded_at": binding["evaluated_at"],
    }
    event["event_id"] = candidate_claim_evaluation_event_id(event)
    return event


def mandatory_x003_claim_binding_and_event(
    difference: dict[str, Any],
    current_state: dict[str, Any],
    *,
    evaluation_status: str = "SATISFIED",
    claim_ref: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """A real ``(binding, event)`` pair whose head reference actually agrees."""

    binding = mandatory_x003_claim_binding(
        difference, current_state, evaluation_status=evaluation_status, claim_ref=claim_ref
    )
    event = mandatory_x003_claim_event(binding, difference, evaluation_status=evaluation_status)
    binding = dict(binding)
    binding["evaluation_head_event_ref"] = {
        "kind": "candidate_claim_evaluation_event",
        "id": event["event_id"],
    }
    return binding, event


def candidate_closure_request(
    difference: dict[str, Any], policy: dict[str, Any], *, current_state: dict[str, Any] | None = None
) -> dict[str, Any]:
    """A fully wired ``CANDIDATE_CLOSURE``-eligible request: every gate should PASS.

    *current_state* defaults to a fixture-computed value, for tests that call
    ``evaluate_closure`` directly. A caller driving this through
    ``reflow.route.reflow`` must instead pass the *real* Store-derived
    ``{"revision", "fingerprint"}`` it expects to be loaded and substituted (F2) --
    G21's own base-State binding check (R2-F8) requires every claim binding's
    ``base_state_ref`` to equal the State the Evaluation is actually bound to, and that
    can only be known in advance for a real Store by asking it.
    """

    reobservation_request, after_ref, later_fingerprint = satisfied_reobservation(difference)
    if current_state is None:
        current_state = {"revision": AFTER_REVISION, "fingerprint": later_fingerprint}
    request = base_closure_request(difference, policy)
    claim_binding, claim_event = mandatory_x003_claim_binding_and_event(difference, current_state)
    request.update(
        {
            "current_state": current_state,
            "resolution_mode": "CHANGE_FREE",
            "change_free_verification_evidence_refs": [
                {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64}
            ],
            "reobservation": {
                "derivation_request": reobservation_request,
                "after_observation_refs": [after_ref],
            },
            "evidence_sufficiency_request": sufficiency_request(
                difference_id=difference["difference_id"], policy=policy
            ),
            "after_state_semantic_state": semantic_state("KNOWN"),
            "source_snapshot_refs": [{"kind": "source_snapshot", "id": "SNAP-0001"}],
            "candidate_invariant_evaluation_bindings": mandatory_invariant_bindings(current_state),
            "candidate_claim_evaluation_bindings": [claim_binding],
            "candidate_claim_evaluation_events": [claim_event],
            "terminal_reason_evidence_refs": [],
            "proposed_terminal_status": "CLOSED",
        }
    )
    return request


def self_closing_change_bound_closure_request(
    difference: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    """A CHANGE_BOUND request whose Change-result Evidence and independent re-observation
    are, by construction, the *same* Observation (F4/G8's injected-violation control).

    Both ``satisfied_reobservation`` and ``evidence_helpers.change_result_evidence_request``
    default their post-change Observation to the identical ``after_observation_request()``
    -- so building both from those same defaults is not a coincidence, it is the exact
    self-closing collision G8 exists to refuse: a Change's own executed-result Evidence
    standing in as the independent re-observation that is supposed to verify it.
    """

    from tests.evidence_helpers import change_result_evidence_request, real_change_request

    from manosube_agent_civilization.change import derive_change

    change_req = real_change_request()
    change_record = derive_change(change_req)
    cr_evidence_request = change_result_evidence_request(change_request=change_req)
    cr_evidence_record = derive_evidence(cr_evidence_request)

    reobservation_request, after_ref, later_fingerprint = satisfied_reobservation(difference)
    current_state = {"revision": AFTER_REVISION, "fingerprint": later_fingerprint}
    request = base_closure_request(difference, policy)
    claim_binding, claim_event = mandatory_x003_claim_binding_and_event(difference, current_state)
    request.update(
        {
            "current_state": current_state,
            "resolution_mode": "CHANGE_BOUND",
            "change_refs": [{"kind": "change", "id": change_record["change_id"]}],
            "change_result_evidence_refs": [
                {"kind": "observation_evidence", "id": cr_evidence_record["evidence_id"]}
            ],
            "change_result_evidence_requests": [cr_evidence_request],
            "reobservation": {
                "derivation_request": reobservation_request,
                "after_observation_refs": [after_ref],
            },
            "evidence_sufficiency_request": sufficiency_request(
                difference_id=difference["difference_id"],
                policy=policy,
                evidence_requests=[cr_evidence_request],
            ),
            "after_state_semantic_state": semantic_state("KNOWN"),
            "source_snapshot_refs": [{"kind": "source_snapshot", "id": "SNAP-0001"}],
            "producing_change_refs": [{"kind": "change", "id": change_record["change_id"]}],
            "candidate_invariant_evaluation_bindings": mandatory_invariant_bindings(current_state),
            "candidate_claim_evaluation_bindings": [claim_binding],
            "candidate_claim_evaluation_events": [claim_event],
            "terminal_reason_evidence_refs": [],
            "proposed_terminal_status": "CLOSED",
        }
    )
    return request


def material_contradiction_record(
    *,
    impact: str = "MATERIAL",
    project_id: str = "PRJ-0001",
    detected_at_state_revision: int = AFTER_REVISION,
    detected_at_state_fingerprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One schema-valid ``material_contradiction`` record, addressed by its own identity."""

    record: dict[str, Any] = {
        "schema_version": "0.1",
        "material_contradiction_id": "",
        "project_id": project_id,
        "contradiction_kind": "EVIDENCE_EVIDENCE",
        "subject_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": [
                {"kind": "observation_evidence", "id": "EVIDENCE-" + "1" * 64},
                {"kind": "observation_evidence", "id": "EVIDENCE-" + "2" * 64},
            ],
        },
        "impact": impact,
        "reason": "two Observation Evidence records disagree on the same Target subject",
        "detected_at_state_revision": detected_at_state_revision,
        "detected_at_state_fingerprint": (
            detected_at_state_fingerprint
            if detected_at_state_fingerprint is not None
            else state_fingerprint("KNOWN")
        ),
        "material_contradiction_semantic_fingerprint": "sha256:" + "3" * 64,
    }
    record["material_contradiction_id"] = material_contradiction_id(record)
    return record
