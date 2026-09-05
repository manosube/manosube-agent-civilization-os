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
    REAL_SNAPSHOT_RECORD,
    REAL_SNAPSHOT_REF,
    derivation_request,
    objective_revision,
    observation_request,
    observation_scope,
    raw_fact,
    semantic_state,
    state_fingerprint,
)
from tests.evidence_helpers import (
    AFTER_REVISION,
    after_observation_request,
    before_observation_request,
    change_free_verification_evidence_request,
    closure_policy,
    difference_request,
    evidenced_difference,
    observation_evidence_request,
    sufficiency_request,
)
from tests.state_helpers import (
    SCHEMA_ROOT,
    genesis_source_snapshot_records,
    initial_state,
    real_kernel_git_objects,
    real_kernel_source_snapshot,
)

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.completion import (
    CANDIDATE_COMPLETION_RECORD_KIND,
    MANDATORY_X003_CLAIM_DESCRIPTOR,
    build_completion_record,
    completion_record_fingerprint,
)
from manosube_agent_civilization.difference.invariant_evaluation import (
    invariant_evaluation_fingerprint,
)
from manosube_agent_civilization.difference.invariant_verifiers import (
    build_invariant_verification_context,
    verification_stage_and_method,
    verify_invariant,
)
from manosube_agent_civilization.evidence.engine import derive_evidence
from manosube_agent_civilization.evidence.sufficiency import evaluate_sufficiency
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.reflow.claims import (
    candidate_claim_evaluation_binding_id,
    candidate_claim_evaluation_event_id,
    candidate_claim_evaluation_series_id,
)
from manosube_agent_civilization.reflow.closure import (
    MANDATORY_X003_CLAIM_REF,
    REQUEST_KEYS,
    build_after_state_candidate,
)
from manosube_agent_civilization.reflow.identity import material_contradiction_id
from manosube_agent_civilization.reflow.invariant_registry import (
    V0_1_INVARIANT_DEFINITION_DIGESTS,
    candidate_invariant_evaluation_binding_id,
    expected_g19_invariant_ids,
)
from manosube_agent_civilization.state.fingerprint import (
    fingerprint_project_state,
    fingerprint_semantic_state,
)
from manosube_agent_civilization.store import FileStateStore

GIT_TREE_REF: dict[str, Any] = {
    "kind": "git_tree",
    "repository": "manosube/manosube-agent-civilization-os",
    "commit_sha": "a" * 40,
    "tree_sha": "b" * 40,
}

EVALUATED_AT = "2026-08-30T11:05:00Z"


def real_kernel_source_witness() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(kernel_source_ref, kernel_source_witness)`` -- a real, self-consistent Git
    object witness proving ``00_KERNEL/KERNEL_INVARIANTS.md`` is reachable via a genuine
    commit/tree/blob chain (R4-F3). Delegates to :func:`tests.state_helpers.
    real_kernel_git_objects` (R9-F2 factored this construction out to the one place both
    this module and genesis's own ``state_metadata.source_snapshot_refs`` need it, so a
    Candidate's own witness and the base State's own Kernel provenance always name the
    identical commit/tree/blob by construction, never by coincidence).
    """

    return real_kernel_git_objects()


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
        "schema_version": "0.1",
        "transaction_id": tx,
        "event_type": "TRANSITION",
        "project_id": successor["project_id"],
        "from_revision": state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-08-30T09:00:00Z",
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
    # R7-F3: G3 now requires the committed State's own objective_revision_id to exactly
    # match the fixture Difference's objective_revision_ref.id -- the widely-shared
    # ``initial_state_revision_zero`` contract fixture's own value never was designed to
    # correspond to it (nothing checked the two together before this round), so every
    # caller of this reflow-only helper (which always evaluates against
    # ``fixture_difference()``/``evidenced_difference()``) gets it overridden here, rather
    # than mutating the shared contract fixture every other schema test also reads.
    genesis["objective_revision_id"] = objective_revision()["objective_revision_id"]
    genesis["semantic_fingerprint"] = fingerprint_project_state(
        genesis, schema_root=SCHEMA_ROOT
    ).as_dict()
    # R10-F1: genesis's own Kernel Source Snapshot reference must close to a real,
    # Store-adopted record -- never a dangling reference the caller pool merely restates.
    store.initialize(
        genesis["project_id"], genesis, records=genesis_source_snapshot_records(genesis)
    )

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


def fixture_genesis_lifecycle_event(difference: dict[str, Any]) -> dict[str, Any]:
    """P8-R4-F3 (SHUKOU Phase 8 final-closure round 4): the real genesis lifecycle event
    (revision 0) the Difference owner already produced when deriving *difference* --
    re-derived fresh through the identical, deterministic, content-addressed request
    :func:`~tests.evidence_helpers.evidenced_difference` itself uses internally, rather than
    cached or hand-built, so this always reproduces the exact same body `difference`'s own
    ``genesis_event_ref`` names. For a caller that already has *difference* (built via
    :func:`fixture_difference`/:func:`~tests.evidence_helpers.evidenced_difference`) and just
    needs the matching real genesis event to pass as ``reflow()``'s own
    ``genesis_lifecycle_event`` on the very first Reflow cycle for it.
    """

    request = difference_request()
    request["bindings"][0]["observation_bundle"] = observe(before_observation_request())
    result = derive_differences(request)
    return next(
        event
        for event in result["events"]
        if event["difference_event_id"] == difference["genesis_event_ref"]["id"]
    )


def _real_admissible_before_observation() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(observation_request, difference_request)`` for a "before" Observation this
    module admits through ``reflow.route.reflow`` -- built against the real, content-
    addressed ``REAL_SNAPSHOT_REF`` and :func:`fixture_difference`'s own matching scope
    (never the widely-shared, permanently-opaque default ``SNAPSHOT_REF``/scope pair), and
    with a real, resolvable ``observation_evidence_refs`` entry rather than the widely-
    shared, permanently-opaque ``EVID-0001`` placeholder.

    P8-R4 (SHUKOU Phase 8 final-closure round 4): ``observation_evidence_refs`` is excluded
    from an Observation's own content-addressed identity (the same fact ``tests/fixtures/
    vertical_proof.py`` and P8-R1-F1 already rely on) -- confirmed directly here too: a
    provisional Observation is observed first, the real Evidence this same request derives
    from it is computed, and the corrected request -- naming that Evidence's own real id as
    its own ``observation_evidence_refs`` entry -- is what this function returns. Once both
    this Observation and the Evidence request built from it are admitted into the same
    Reflow transaction (as they always are together here), the Observation's own declared
    reference resolves against that same transaction's own manifest -- no second,
    hand-maintained bootstrap record required.
    """

    real_difference_request = difference_request(
        scope=observation_scope(snapshot_refs=[REAL_SNAPSHOT_REF])
    )
    provisional = before_observation_request(snapshot_refs=[REAL_SNAPSHOT_REF])
    provisional_evidence = derive_evidence(
        observation_evidence_request(
            observation=provisional, difference=deepcopy(real_difference_request)
        )
    )
    corrected = before_observation_request(
        snapshot_refs=[REAL_SNAPSHOT_REF],
        observation_evidence_refs=[
            {"kind": "observation_evidence", "id": provisional_evidence["evidence_id"]}
        ],
    )
    return corrected, real_difference_request


def fixture_policy(difference: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return closure_policy(difference["difference_id"], **kwargs)


def real_snapshot_after_observation_request() -> dict[str, Any]:
    """The ``after_observation_request``-shaped request every caller in this module that
    needs the real, content-addressed ``REAL_SNAPSHOT_REF`` (rather than the widely-shared,
    permanently-opaque ``SNAPSHOT_REF``) builds from -- factored out so two independent
    callers building it separately still produce the byte-identical request (and therefore
    the identical Observation record) that :func:`self_closing_change_bound_closure_request`
    depends on for its own self-closing collision to actually collide (R6-F1a)."""

    return observation_request(
        observation_scope(snapshot_refs=[REAL_SNAPSHOT_REF]),
        [raw_fact(value="READY", snapshot_id=REAL_SNAPSHOT_REF["id"])],
        state_fingerprint("KNOWN"),
        AFTER_REVISION,
    )


def satisfied_reobservation(
    difference: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return ``(derivation_request, after_observation_ref, later_state_fingerprint)``.

    The re-observation is a real, independent Observation run through the public
    Observation Engine (``observe``), re-derived through the real ``derive_differences``
    producer -- never a hand-written "satisfied" record.

    R6-F1a: unlike ``tests.evidence_helpers.after_observation_request`` (whose own
    ``source_snapshot_refs`` default is the widely-shared, permanently-opaque
    ``SNAPSHOT_REF``), this Observation is built to report the real, content-addressed
    ``REAL_SNAPSHOT_REF`` -- this function's only two callers both build a Reflow
    ``closure_request`` that now must resolve a real ``source_snapshot`` body for it, not
    only cross-reference its bare id.
    """

    scope = observation_scope(snapshot_refs=[REAL_SNAPSHOT_REF])
    after_bundle = observe(real_snapshot_after_observation_request())
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
                "observation_scope": scope,
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
    invariant_evaluation_refs: list[dict[str, Any]] | None = None,
    material_contradiction_refs: list[dict[str, Any]] | None = None,
    after_state_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One conformant ``candidate_claim_evaluation_binding`` for the mandatory X-003 claim.

    R5-F1: *after_state_candidate*, when supplied, is the real, content-addressed candidate
    (:func:`~manosube_agent_civilization.reflow.closure.build_after_state_candidate`) this
    binding's own ``candidate_id``/``candidate_semantic_fingerprint`` must match for G21 to
    resolve it -- closure.py now verifies both against it, never accepting a caller's bare
    restatement. Left ``None`` (a placeholder id) only for fixtures that never route through
    G21's own candidate check, e.g. this module's ``resolve_claim_binding``-only tests.
    """

    required_claim_ref = claim_ref if claim_ref is not None else MANDATORY_X003_CLAIM_REF
    policy_ref = deepcopy(difference["closure_policy"])
    candidate_id = (
        after_state_candidate["candidate_id"]
        if after_state_candidate is not None
        else "STATE-CANDIDATE-" + "1" * 64
    )
    candidate_semantic_fingerprint = (
        after_state_candidate["semantic_fingerprint"]
        if after_state_candidate is not None
        else {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "1" * 64}
    )
    series_id = candidate_claim_evaluation_series_id(
        difference_id=difference["difference_id"],
        policy_ref=policy_ref,
        candidate_id=candidate_id,
        required_claim_ref=required_claim_ref,
    )
    observed_state_ref = {
        "kind": "state",
        "revision": current_state["revision"],
        "fingerprint": current_state["fingerprint"],
    }
    # R4-F2/R3-F2: the real Completion Record the binding's completion_record_ref must
    # resolve to -- built the same way reflow.closure.resolve_completion_record verifies
    # it, not a fake placeholder id/fingerprint.
    completion_record = build_completion_record(
        claim_descriptor=MANDATORY_X003_CLAIM_DESCRIPTOR,
        policy_ref=policy_ref,
        observed_state_ref=observed_state_ref,
        evaluated_state_revision=current_state["revision"],
        evaluated_state_fingerprint=current_state["fingerprint"],
        evaluation_status=evaluation_status,
        evaluated_at=EVALUATED_AT,
        required_evidence_refs=[],
        invariant_evaluation_refs=invariant_evaluation_refs or [],
        material_contradiction_refs=material_contradiction_refs or [],
    )
    binding = {
        "kind": "candidate_claim_evaluation_binding",
        "difference_id": difference["difference_id"],
        "policy_ref": policy_ref,
        "candidate_id": candidate_id,
        "candidate_semantic_fingerprint": candidate_semantic_fingerprint,
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
        "completion_record_ref": {
            "kind": CANDIDATE_COMPLETION_RECORD_KIND,
            "id": completion_record["completion_id"],
        },
        "evaluation_record_fingerprint": completion_record_fingerprint(completion_record),
        "evaluation_status": evaluation_status,
        "evaluation_evidence_refs": {"collection_kind": "UNORDERED_SET", "members": []},
        "evaluated_at": EVALUATED_AT,
    }
    # R3-F2: binding_id is now checked against its own content-addressed derivation, so
    # it must be computed last, from the assembled closed fields.
    binding["binding_id"] = candidate_claim_evaluation_binding_id(binding)
    return binding


def real_terminal_reason_evidence_request() -> dict[str, Any]:
    """R7-F4: one real ``observation_evidence_request``-shaped request that reproduces the
    exact same Difference :func:`fixture_difference`/:func:`evidenced_difference` derive --
    a real, content-addressed terminal reason Evidence record for the fixture Difference,
    never a bare placeholder id no request backs.
    """

    return observation_evidence_request()


def real_terminal_reason_evidence_fields() -> tuple[dict[str, Any], str]:
    """Return ``(request, evidence_id)`` -- the real
    :func:`real_terminal_reason_evidence_request` paired with the ``evidence_id``
    :func:`~manosube_agent_civilization.evidence.engine.derive_evidence` actually derives
    from it, for the many negative-control tests that need to override
    ``terminal_reason_evidence_refs``/``terminal_reason_evidence_requests`` together to a
    real, self-consistent pair (R7-F4) rather than a bare placeholder id no request backs.
    """

    request = real_terminal_reason_evidence_request()
    return request, derive_evidence(request)["evidence_id"]


def base_closure_request(difference: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """A candidate-free (``TERMINAL_POLICY_ONLY``-shaped) request every test starts from.

    R9-F2: ``kernel_source_ref``/``kernel_source_witness``/``source_snapshots`` now default
    to the same real, self-consistent Kernel Git witness and content-addressed Source
    Snapshot every candidate route already uses (:func:`real_kernel_source_witness`,
    :func:`~tests.state_helpers.real_kernel_source_snapshot`) -- not the bare, unverifiable
    ``GIT_TREE_REF`` placeholder this fixture used before this round. A ``TERMINAL_POLICY_
    ONLY`` cycle commits a real State transition too (R-005) and now gets the identical real
    Kernel-provenance proof a candidate cycle already got (``EVERY_COMMITTED_STATE_KERNEL_
    PROVENANCE_REQUIRED=true``), both at this module's own direct-``evaluate_closure`` level
    (the now-unconditional ``kernel_source_witness_ref`` computation) and, for a caller
    driving this request through ``reflow.route.reflow``, at the Store-derived
    ``_resolve_base_kernel_source_ref`` level -- which requires this same real ``source_
    snapshots``/``kernel_source_witness`` pair to resolve the genesis State's own committed
    ``state_metadata.source_snapshot_refs`` against. ``objective_revision`` is the new field
    R9-F2 also adds: TERMINAL_POLICY_ONLY's own G3 now validates a real Objective Revision
    body here too, not only via a candidate's ``reobservation.derivation_request`` -- the
    identical real fixture (:func:`~tests.difference_helpers.objective_revision`) already
    used to build *difference*'s own ``objective_revision_ref`` in the first place.
    """

    terminal_reason_request = real_terminal_reason_evidence_request()
    terminal_reason_record = derive_evidence(terminal_reason_request)
    kernel_source_ref, kernel_source_witness = real_kernel_source_witness()
    return {
        "difference": difference,
        "current_status": "VERIFYING",
        "policy": policy,
        "difference_event_head_ref": deepcopy(difference["genesis_event_ref"]),
        "current_state": {
            "revision": AFTER_REVISION,
            "fingerprint": state_fingerprint("KNOWN"),
        },
        "objective_revision_id": difference["objective_revision_ref"]["id"],
        "objective_revision": objective_revision(),
        "kernel_source_ref": kernel_source_ref,
        "base_kernel_source_ref": deepcopy(kernel_source_ref),
        "resolution_mode": None,
        "change_refs": [],
        "change_result_evidence_refs": [],
        "change_result_evidence_requests": [],
        "change_free_verification_evidence_refs": [],
        "change_free_verification_evidence_requests": [],
        "reobservation": None,
        "evidence_sufficiency_request": None,
        "after_state_semantic_state": None,
        "source_snapshot_refs": [],
        "source_snapshots": [real_kernel_source_snapshot()],
        "producing_change_refs": [],
        "candidate_invariant_evaluation_bindings": [],
        "candidate_claim_evaluation_bindings": [],
        "candidate_claim_evaluation_events": [],
        "invariant_evaluations": [],
        "kernel_source_witness": kernel_source_witness,
        "material_contradictions": [],
        "terminal_reason_evidence_refs": [
            {"kind": "observation_evidence", "id": terminal_reason_record["evidence_id"]}
        ],
        "terminal_reason_evidence_requests": [terminal_reason_request],
        "proposed_terminal_status": "BLOCKED",
        "evaluated_at": EVALUATED_AT,
    }


def _hex_digest(seed: str) -> str:
    """A deterministic 64-character hex string, for identities a fixture needs but whose
    exact value nothing in this vertical independently verifies (see the module docstring
    on ``reflow/invariant_registry.py``'s named non-claim about per-invariant digests)."""

    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


#: The same placeholder candidate identity :func:`mandatory_invariant_bindings` falls back
#: to when no real *after_state_candidate* is supplied -- a single source of truth so a
#: caller's Invariant Evaluation record pool and its bindings always agree even when neither
#: passes a real Candidate (R6-F3).
_PLACEHOLDER_CANDIDATE_ID = "STATE-CANDIDATE-" + "1" * 64
_PLACEHOLDER_CANDIDATE_SEMANTIC_FINGERPRINT = {
    "profile": "MANOSUBE-STATE-SHA256-0.1",
    "digest": "1" * 64,
}


def mandatory_invariant_evaluation(
    difference_id: str,
    invariant_id: str,
    current_state: dict[str, Any],
    *,
    status: str = "PASS",
    evidence_refs: list[dict[str, str]] | None = None,
    after_state_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One real, schema-valid ``invariant_evaluation`` record for *invariant_id*.

    R8-F1: *evidence_refs* defaults to empty, matching invariant ids
    :mod:`~manosube_agent_civilization.difference.invariant_verifiers`'s own
    ``_EVIDENCE_SOURCE`` does not map. A caller exercising an id that map does cover (through
    :func:`mandatory_invariant_evaluations`) must instead pass the real, independently
    recomputed refs :func:`~manosube_agent_civilization.difference.invariant_verifiers.
    verify_invariant` itself returns for that id -- ``resolve_invariant_evaluation`` now
    fails closed on any declared ``evidence_refs`` that does not match that real
    recomputation.

    R4-F2: ``evaluation_id`` is caller-assigned (no content-address formula exists for it
    in ``CLOSURE_POLICY.md`` -- see ``difference/invariant_evaluation.py``'s module
    docstring), so this fixture assigns the same deterministic value
    :func:`mandatory_invariant_bindings` declares on its own ``invariant_evaluation_ref``.

    R5-F1: ``subject_ref`` is ``{"kind": "difference", "id": difference_id}`` -- the
    ``difference``/``objective_revision``/``state`` set ``difference/graph.py``'s own edge
    table permits for this field (``kernel_invariant``, an earlier round's placeholder, is
    not among them and is rejected by that checker).

    R6-F3: ``candidate_id``/``candidate_semantic_fingerprint`` are set from
    *after_state_candidate*, when supplied, matching :func:`mandatory_invariant_bindings`'s
    identical parameter -- see its docstring for why it defaults to a placeholder rather
    than being required.
    """

    candidate_id = (
        after_state_candidate["candidate_id"]
        if after_state_candidate is not None
        else _PLACEHOLDER_CANDIDATE_ID
    )
    candidate_semantic_fingerprint = (
        after_state_candidate["semantic_fingerprint"]
        if after_state_candidate is not None
        else _PLACEHOLDER_CANDIDATE_SEMANTIC_FINGERPRINT
    )
    verification_stage, method = verification_stage_and_method(invariant_id)
    return {
        "schema_version": "0.1",
        "evaluation_id": "INV-EVAL-" + _hex_digest(f"eval:{invariant_id}").upper(),
        "invariant_id": invariant_id,
        "subject_ref": {"kind": "difference", "id": difference_id},
        "state_revision": current_state["revision"],
        "state_fingerprint": current_state["fingerprint"],
        "candidate_id": candidate_id,
        "candidate_semantic_fingerprint": candidate_semantic_fingerprint,
        "verification_stage": verification_stage,
        "method": method,
        "expected": {"invariant_id": invariant_id, "result": "PASS"},
        "observed": {"invariant_id": invariant_id, "result": status},
        "status": status,
        "evaluated_at": EVALUATED_AT,
        "evaluator_capability": "reflow.closure",
        "authority_ref": None,
        "evidence_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": list(evidence_refs) if evidence_refs else [],
        },
        "remaining_differences": {"collection_kind": "UNORDERED_SET", "members": []},
    }


def mandatory_invariant_evaluations(
    difference_id: str,
    current_state: dict[str, Any],
    *,
    after_state_candidate: dict[str, Any] | None = None,
    verification_results: dict[str, tuple[str, list[dict[str, str]]]] | None = None,
) -> list[dict[str, Any]]:
    """The real Invariant Evaluation record pool matching every binding
    :func:`mandatory_invariant_bindings` builds -- the caller-supplied pool R4-F2's
    ``invariant_evaluations`` closure_request field carries.

    R8-F1: *verification_results*, when supplied, is the real ``{invariant_id: (status,
    evidence_refs)}`` map :func:`~manosube_agent_civilization.difference.invariant_verifiers.
    verify_invariant` itself returned for every mandatory id against this same request's real
    verification context (see :func:`candidate_closure_request`) -- each record's own
    ``status``/``evidence_refs`` are set from that real recomputation rather than a fixed
    ``PASS``/empty default, so a fixture claiming ``CANDIDATE_CLOSURE`` genuinely reproduces
    what the shared resolver will independently verify, not merely what the fixture asserts.
    """

    results = verification_results or {}
    return [
        mandatory_invariant_evaluation(
            difference_id,
            invariant_id,
            current_state,
            status=results[invariant_id][0] if invariant_id in results else "PASS",
            evidence_refs=results[invariant_id][1] if invariant_id in results else None,
            after_state_candidate=after_state_candidate,
        )
        for invariant_id in sorted(expected_g19_invariant_ids())
    ]


def mandatory_invariant_bindings(
    difference_id: str,
    current_state: dict[str, Any],
    *,
    after_state_candidate: dict[str, Any] | None = None,
    verification_results: dict[str, tuple[str, list[dict[str, str]]]] | None = None,
) -> list[dict[str, Any]]:
    """One real ``candidate_invariant_evaluation_binding`` per pinned v0.1 mandatory id.

    G19 now additively requires the whole :func:`expected_g19_invariant_ids` union
    regardless of what a Closure Policy itself declares (see ``reflow/closure.py``), so a
    request that wants ``CANDIDATE_CLOSURE`` to actually reach ``SATISFIED`` must bind all
    of them, not only whatever the Policy names.

    R5-F1: *after_state_candidate*, when supplied, is the real candidate every binding's own
    ``candidate_id``/``candidate_semantic_fingerprint`` is set to match -- see
    :func:`mandatory_x003_claim_binding`'s identical parameter for why it defaults to
    ``None`` (a placeholder id) rather than being required.

    R8-F1: *verification_results*, when supplied, is the same real ``{invariant_id: (status,
    evidence_refs)}`` map :func:`mandatory_invariant_evaluations` takes -- every bound
    invariant's own Invariant Evaluation record (and therefore
    ``evaluation_record_fingerprint``, which is derived from that record) reflects the real
    recomputed ``evidence_refs``, never a fixed empty default. ``evaluation_result`` on the
    binding itself is unconditionally ``"PASS"``: a binding only exists on the golden
    CANDIDATE_CLOSURE path this helper builds, where every mandatory id's real status is
    independently confirmed PASS by :func:`candidate_closure_request` before binding.
    """

    candidate_id = (
        after_state_candidate["candidate_id"]
        if after_state_candidate is not None
        else _PLACEHOLDER_CANDIDATE_ID
    )
    candidate_semantic_fingerprint = (
        after_state_candidate["semantic_fingerprint"]
        if after_state_candidate is not None
        else _PLACEHOLDER_CANDIDATE_SEMANTIC_FINGERPRINT
    )
    results = verification_results or {}
    bindings = []
    for invariant_id in sorted(expected_g19_invariant_ids()):
        record = mandatory_invariant_evaluation(
            difference_id,
            invariant_id,
            current_state,
            status=results[invariant_id][0] if invariant_id in results else "PASS",
            evidence_refs=results[invariant_id][1] if invariant_id in results else None,
            after_state_candidate=after_state_candidate,
        )
        binding = {
            "kind": "candidate_invariant_evaluation_binding",
            "candidate_id": candidate_id,
            "candidate_semantic_fingerprint": candidate_semantic_fingerprint,
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
                "invariant_definition_sha256": "sha256:"
                + V0_1_INVARIANT_DEFINITION_DIGESTS[invariant_id],
            },
            "invariant_evaluation_ref": {
                "kind": "invariant_evaluation",
                "id": record["evaluation_id"],
            },
            # R4-F2: the real fingerprint of the matching Invariant Evaluation record
            # (mandatory_invariant_evaluations), not a fake placeholder -- G19 now
            # resolves and recomputes it.
            "evaluation_record_fingerprint": invariant_evaluation_fingerprint(record),
            "evaluation_result": "PASS",
            "evaluation_evidence_refs": {
                "collection_kind": "UNORDERED_SET",
                "members": list(record["evidence_refs"]["members"]),
            },
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
    invariant_evaluation_refs: list[dict[str, Any]] | None = None,
    material_contradiction_refs: list[dict[str, Any]] | None = None,
    after_state_candidate: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """A real ``(binding, event)`` pair whose head reference actually agrees."""

    binding = mandatory_x003_claim_binding(
        difference,
        current_state,
        evaluation_status=evaluation_status,
        claim_ref=claim_ref,
        invariant_evaluation_refs=invariant_evaluation_refs,
        material_contradiction_refs=material_contradiction_refs,
        after_state_candidate=after_state_candidate,
    )
    event = mandatory_x003_claim_event(binding, difference, evaluation_status=evaluation_status)
    binding = dict(binding)
    binding["evaluation_head_event_ref"] = {
        "kind": "candidate_claim_evaluation_event",
        "id": event["event_id"],
    }
    # R3-F2: binding_id must be recomputed after evaluation_head_event_ref is finalized --
    # it is part of the same closed-field hash.
    binding["binding_id"] = candidate_claim_evaluation_binding_id(binding)
    return binding, event


def candidate_closure_request(
    difference: dict[str, Any],
    policy: dict[str, Any],
    *,
    current_state: dict[str, Any] | None = None,
    material_contradictions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """A fully wired ``CANDIDATE_CLOSURE``-eligible request: every gate should PASS.

    *current_state* defaults to a fixture-computed value, for tests that call
    ``evaluate_closure`` directly. A caller driving this through
    ``reflow.route.reflow`` must instead pass the *real* Store-derived
    ``{"revision", "fingerprint"}`` it expects to be loaded and substituted (F2) --
    G21's own base-State binding check (R2-F8) requires every claim binding's
    ``base_state_ref`` to equal the State the Evaluation is actually bound to, and that
    can only be known in advance for a real Store by asking it.

    *material_contradictions* defaults to none. R4-F2 requires the mandatory X-003
    claim binding's Completion Record to already carry the same ``material_contradiction_refs``
    ``evaluate_closure`` itself derives from this same list (``reflow/closure.py``'s
    ``contradiction_refs``, every recorded contradiction regardless of ``impact`` -- not only
    the ``MATERIAL`` ones that block) -- so a caller who wants a non-empty
    ``material_contradictions`` list and a still-``SATISFIED`` result (e.g. a non-material
    contradiction) must pass the records here rather than mutate the returned request's
    ``material_contradictions`` key afterwards, or G21 fails to resolve the binding's stale
    Completion Record.
    """

    reobservation_request, after_ref, later_fingerprint = satisfied_reobservation(difference)
    if current_state is None:
        current_state = {"revision": AFTER_REVISION, "fingerprint": later_fingerprint}
    material_contradictions = material_contradictions or []
    contradiction_refs = [
        {"kind": "material_contradiction", "id": item["material_contradiction_id"]}
        for item in material_contradictions
    ]
    request = base_closure_request(difference, policy)
    kernel_source_ref, kernel_source_witness = real_kernel_source_witness()
    after_semantic_state = semantic_state("KNOWN")
    source_snapshot_refs = [deepcopy(REAL_SNAPSHOT_REF)]
    # R5-F1: the real after_state_candidate every binding this request builds must match --
    # built from exactly the same inputs evaluate_closure itself uses to build its own,
    # so the two are the same content-addressed candidate.
    after_state_candidate = build_after_state_candidate(
        current_state=current_state,
        kernel_source_ref=kernel_source_ref,
        semantic_state=after_semantic_state,
        semantic_fingerprint=fingerprint_semantic_state(after_semantic_state).as_dict(),
        source_snapshot_refs=source_snapshot_refs,
        producing_change_refs=[],
    )
    # R6-F1b: a real, schema-valid change_free_verification_evidence record -- Evidence's
    # own defaults deterministically re-derive the exact same Difference `difference` is
    # (both are `evidenced_difference()`), so this Evidence's difference_ref binds to
    # exactly the Difference this closure_request is for, by construction.
    #
    # P8-R4 (SHUKOU Phase 8 final-closure round 4): its own verification Observation is
    # built with the real, content-addressed ``REAL_SNAPSHOT_REF`` (not the widely-shared,
    # permanently-opaque default ``SNAPSHOT_REF``) -- P8-R3-F1 already admits this
    # Observation into the Store (as the change-free Evidence's own named verification
    # Observation), and the unconditional Reference Closure invariant (P8-R4-F1) now
    # requires its declared ``source_snapshot_refs`` to actually resolve before commit.
    change_free_before_observation, change_free_difference_request = (
        _real_admissible_before_observation()
    )
    change_free_evidence_request = change_free_verification_evidence_request(
        observation=change_free_before_observation,
        difference=deepcopy(change_free_difference_request),
        verification_observation=after_observation_request(snapshot_refs=[REAL_SNAPSHOT_REF]),
    )
    change_free_evidence_record = derive_evidence(change_free_evidence_request)
    # R8-F1: the real Sufficiency result this request's own `evidence_sufficiency_request`
    # will independently re-derive at evaluation time -- `evaluate_sufficiency` is a pure
    # function of its request, so computing it here reproduces exactly what
    # `evaluate_closure` computes internally, not a fixture guess.
    evidence_sufficiency_request = sufficiency_request(
        difference_id=difference["difference_id"], policy=policy
    )
    sufficiency_wrapper = evaluate_sufficiency(evidence_sufficiency_request)
    sufficiency = sufficiency_wrapper["evidence_sufficiency_result"]
    blocking_contradictions = [
        item for item in material_contradictions if item.get("impact") == "MATERIAL"
    ]
    verification_context = build_invariant_verification_context(
        policy=policy,
        difference=difference,
        current_state=current_state,
        after_state_candidate=after_state_candidate,
        resolution_mode="CHANGE_FREE",
        change_result_evidence=[],
        change_free_evidence=[change_free_evidence_record],
        after_observation_ids={after_ref["id"]},
        source_snapshot_refs=source_snapshot_refs,
        source_snapshots=[deepcopy(REAL_SNAPSHOT_RECORD)],
        sufficiency=sufficiency,
        material_contradictions=material_contradictions,
        blocking_contradictions=blocking_contradictions,
        proposed_terminal_status="CLOSED",
        evaluated_at=EVALUATED_AT,
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
        material_contradiction_refs=contradiction_refs,
        after_state_candidate=after_state_candidate,
    )
    request.update(
        {
            "current_state": current_state,
            "kernel_source_ref": kernel_source_ref,
            "base_kernel_source_ref": kernel_source_ref,
            "kernel_source_witness": kernel_source_witness,
            "material_contradictions": material_contradictions,
            "resolution_mode": "CHANGE_FREE",
            "change_free_verification_evidence_refs": [
                {"kind": "observation_evidence", "id": change_free_evidence_record["evidence_id"]}
            ],
            "change_free_verification_evidence_requests": [change_free_evidence_request],
            "reobservation": {
                "derivation_request": reobservation_request,
                "after_observation_refs": [after_ref],
            },
            "evidence_sufficiency_request": evidence_sufficiency_request,
            "after_state_semantic_state": after_semantic_state,
            "source_snapshot_refs": source_snapshot_refs,
            # R9-F2: the real Kernel Source Snapshot is appended (never replaces index 0,
            # REAL_SNAPSHOT_RECORD, which several negative controls tamper with by position)
            # so `reflow.route.reflow`'s own base-Kernel-provenance resolution can also
            # resolve it from this same pool.
            "source_snapshots": [deepcopy(REAL_SNAPSHOT_RECORD), real_kernel_source_snapshot()],
            "candidate_invariant_evaluation_bindings": invariant_bindings,
            "invariant_evaluations": invariant_evaluations,
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
    # R6-F1a: the post-change Observation must be built from the exact same request
    # satisfied_reobservation's own real_snapshot_after_observation_request() uses -- the
    # self-closing collision this fixture exists to prove only actually collides when both
    # sides are the same Observation, and that Observation must resolve a real
    # source_snapshot body now that G8 requires one.
    cr_evidence_request = change_result_evidence_request(
        change_request=change_req,
        post_change_observation=real_snapshot_after_observation_request(),
    )
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
            "source_snapshot_refs": [deepcopy(REAL_SNAPSHOT_REF)],
            "source_snapshots": [deepcopy(REAL_SNAPSHOT_RECORD), real_kernel_source_snapshot()],
            "producing_change_refs": [{"kind": "change", "id": change_record["change_id"]}],
            "candidate_invariant_evaluation_bindings": mandatory_invariant_bindings(
                difference["difference_id"], current_state
            ),
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
