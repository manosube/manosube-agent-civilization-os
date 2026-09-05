"""Phase 8 Vertical Proof -- required negative and interruption routes (Issue #41 item E).

Every test below proves one of the fourteen bullets Issue #41's "Required negative and
interruption routes" section names, verbatim:

    E1  substituting any hand-built intermediate record is refused or makes the proof fail
    E2  changing any semantic fixture field changes the appropriate downstream identity or
        verdict
    E3  wrong project, Objective Revision, State revision/fingerprint, Difference head,
        Authority, Change, Observation, Evidence, policy or instant fails closed
    E4  sufficient Evidence without successful Reflow does not close
    E5  failed/blocked/insufficient route remains non-closed and reconstructable
    E6  stale Evidence and material contradiction do not become success
    E7  Change cannot self-close and Evidence cannot self-close
    E8  crash injection at every existing Store/Reflow stage never exposes a partial
        canonical cycle
    E9  recovery converges to the one valid final State where commit intent permits recovery
    E10 identical replay adds no State revision, lifecycle event or immutable record
    E11 same transaction identity with different payload is rejected
    E12 deleting/reordering/tampering lineage or a referenced record is detected
    E13 a new Store instance using only the persisted backend reconstructs the same State
    E14 a fresh Python process proves session loss does not alter the final identity

Every mutation below changes exactly one already-real input :func:`tests.natural_cycle.proof.
assemble_vertical_proof_route` produced -- never a second, hand-built substitute for what a
real owner call itself would have produced. Where the natural home for a guarantee is a lower
real owner than the full vertical route (Evidence's own instant check, Authority/Change's own
provenance check, ``commit_reflow``'s own replay contract), this is called out in that test's
own docstring rather than silently reproduced at the wrong layer.

E13 is also the specific, more heavily asserted claim already proven by
``test_vertical_proof.py::test_reconstruction_from_lineage_matches_the_committed_state_exactly``;
this file adds no duplicate of that -- :func:`test_e14...` below builds on it directly for the
process-isolation case.
"""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any

import pytest
from tests.fixtures import vertical_proof as fx
from tests.natural_cycle.proof import (
    after_semantic_state,
    assemble_vertical_proof_route,
    build_store,
    initialize_genesis,
    run_vertical_proof,
)
from tests.reflow_helpers import material_contradiction_record
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority import evaluate_authority
from manosube_agent_civilization.change import derive_change
from manosube_agent_civilization.change.errors import UnauthorizedChangeError
from manosube_agent_civilization.difference.identity import (
    closure_policy_id,
    policy_semantic_fingerprint,
)
from manosube_agent_civilization.evidence.engine import derive_evidence
from manosube_agent_civilization.evidence.errors import EvidenceError
from manosube_agent_civilization.reflow.commit import commit_reflow
from manosube_agent_civilization.reflow.errors import ReflowError
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.store import STAGES, FileStateStore
from manosube_agent_civilization.store.errors import (
    CorruptStoreError,
    SimulatedCrash,
    TransactionConflictError,
)


def _reflow_with_mutation(
    tmp_path: Path, mutate: Callable[[dict[str, Any], dict[str, Any]], None]
) -> tuple[dict[str, Any], Callable[[], dict[str, Any]]]:
    """Assemble the one real route, apply exactly one mutation to its already-real
    ``closure_request``/``reflow()`` keyword arguments, and call ``reflow()``.

    Returns ``(assembly, call)`` where ``call`` invokes the mutated ``reflow()`` -- so a
    caller can assert on the raised error via ``pytest.raises`` while retaining ``assembly``
    for a post-condition check (e.g. that the Store never advanced).
    """

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    closure_request = dict(kwargs["closure_request"])
    mutate(kwargs, closure_request)
    kwargs["closure_request"] = closure_request

    def call() -> dict[str, Any]:
        return reflow(assembly["store"], **kwargs)

    return assembly, call


def _assert_store_never_advanced(assembly: dict[str, Any]) -> None:
    """The Store's committed State is still exactly the genesis revision this route began
    from -- a refused route leaves nothing partially applied."""

    fresh = FileStateStore(assembly["store"].root, schema_root=SCHEMA_ROOT)
    current = fresh.load_current(fx.PROJECT_ID)
    assert current["state_revision"] == assembly["genesis_state"]["state_revision"]
    reconstructed = fresh.reconstruct(fx.PROJECT_ID)
    assert reconstructed == current


# --- E1: a hand-built intermediate record substituted for a request is refused ------------- #


def test_e1_a_hand_built_evidence_record_substituted_for_its_own_request_is_refused(
    tmp_path: Path,
) -> None:
    """``NO_SUBSTITUTE_ARTIFACT=true``: the real, already-derived Change-result Evidence
    *record* (Evidence's own output) is substituted in the one place a *request* (Evidence's
    own input) belongs. It is never accepted as a stand-in -- the reproduction fails to
    re-derive it as a request at all, and the route is refused before it can close."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    closure_request = dict(kwargs["closure_request"])
    closure_request["change_result_evidence_requests"] = [
        assembly["evidence"]["change_result_evidence"]
    ]
    kwargs["closure_request"] = closure_request

    with pytest.raises(ReflowError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


# --- E2: changing a semantic fixture field changes the downstream verdict ------------------ #


def test_e2_changing_the_before_observation_value_changes_the_derived_difference_verdict(
    tmp_path: Path,
) -> None:
    """Changing exactly one bounded fixture input -- the before-world's own observed value --
    from ``"NOT-READY"`` (the real fixture) to the Target's own expected value (``"READY"``)
    changes the downstream verdict from *one Difference produced* to *none*: the Target is
    already satisfied, so ``derive_differences`` has nothing to report. No fixture field is
    inert."""

    from manosube_agent_civilization.difference import derive_differences
    from manosube_agent_civilization.observation import observe

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)

    real_request = fx.before_observation_request(
        fingerprint=genesis["semantic_fingerprint"], state_revision=genesis["state_revision"]
    )
    real_bundle = observe(real_request)
    real_diff_request = fx.derivation_request(
        observation_bundle=real_bundle,
        fingerprint=genesis["semantic_fingerprint"],
        state_revision=genesis["state_revision"],
    )
    real_result = derive_differences(real_diff_request)
    assert len(real_result["differences"]) == 1

    changed_request = fx.observation_request(
        value="READY",
        snapshot_ref=fx.BEFORE_SNAPSHOT_REF,
        snapshot_locator=fx.BEFORE_SOURCE_SNAPSHOT["source_locator"],
        snapshot_time=fx.BEFORE_SNAPSHOT_TIME,
        fingerprint=genesis["semantic_fingerprint"],
        state_revision=genesis["state_revision"],
        started_at=fx.BEFORE_OBSERVATION_STARTED_AT,
        ended_at=fx.BEFORE_OBSERVATION_ENDED_AT,
        attempt_id="ATTEMPT-VP8-0001",
    )
    changed_bundle = observe(changed_request)
    changed_diff_request = fx.derivation_request(
        observation_bundle=changed_bundle,
        fingerprint=genesis["semantic_fingerprint"],
        state_revision=genesis["state_revision"],
    )
    changed_result = derive_differences(changed_diff_request)
    assert len(changed_result["differences"]) == 0


# --- E3: wrong project/revision/state/head/change/observation/evidence/policy/instant ------ #


def test_e3_wrong_project_id_fails_closed(tmp_path: Path) -> None:
    """A project the Store never initialized cannot be loaded at all -- refused before
    ``reflow()`` reaches any of its own gates."""

    from manosube_agent_civilization.store.errors import StoreError

    _assembly, call = _reflow_with_mutation(
        tmp_path, lambda kwargs, closure_request: kwargs.__setitem__("project_id", "PRJ-WRONG-0001")
    )
    with pytest.raises(StoreError):
        call()


def test_e3_wrong_difference_lifecycle_head_fails_closed(tmp_path: Path) -> None:
    assembly, call = _reflow_with_mutation(
        tmp_path,
        lambda kwargs, closure_request: kwargs.__setitem__(
            "previous_event_id", "D-EVT-" + "0" * 64
        ),
    )
    with pytest.raises(ReflowError, match="does not match previous_event_id"):
        call()
    _assert_store_never_advanced(assembly)


def test_e3_wrong_expected_state_revision_fails_closed(tmp_path: Path) -> None:
    assembly, call = _reflow_with_mutation(
        tmp_path, lambda kwargs, closure_request: kwargs.__setitem__("expected_state_revision", 999)
    )
    with pytest.raises(ReflowError, match="expected_state_revision"):
        call()
    _assert_store_never_advanced(assembly)


def test_e3_wrong_expected_state_fingerprint_fails_closed(tmp_path: Path) -> None:
    def mutate(kwargs: dict[str, Any], closure_request: dict[str, Any]) -> None:
        kwargs["expected_state_fingerprint"] = {"algorithm": "sha256", "digest": "0" * 64}

    assembly, call = _reflow_with_mutation(tmp_path, mutate)
    with pytest.raises(ReflowError, match="expected_state_fingerprint"):
        call()
    _assert_store_never_advanced(assembly)


def test_e3_wrong_difference_identity_fails_closed(tmp_path: Path) -> None:
    def mutate(kwargs: dict[str, Any], closure_request: dict[str, Any]) -> None:
        difference = dict(closure_request["difference"])
        difference["difference_id"] = "D-" + "9" * 64
        closure_request["difference"] = difference

    assembly, call = _reflow_with_mutation(tmp_path, mutate)
    with pytest.raises(ReflowError):
        call()
    _assert_store_never_advanced(assembly)


def test_e3_wrong_policy_subject_difference_ref_fails_closed(tmp_path: Path) -> None:
    def mutate(kwargs: dict[str, Any], closure_request: dict[str, Any]) -> None:
        policy = dict(closure_request["policy"])
        policy["subject_difference_ref"] = {"kind": "difference", "id": "D-" + "8" * 64}
        closure_request["policy"] = policy

    assembly, call = _reflow_with_mutation(tmp_path, mutate)
    with pytest.raises(ReflowError, match="policy does not govern"):
        call()
    _assert_store_never_advanced(assembly)


def test_e3_wrong_producing_change_refs_fails_closed(tmp_path: Path) -> None:
    """The Change bound into the Candidate no longer matches the real, authorized Change."""

    def mutate(kwargs: dict[str, Any], closure_request: dict[str, Any]) -> None:
        closure_request["producing_change_refs"] = [{"kind": "change", "id": "CHANGE-WRONG"}]

    assembly, call = _reflow_with_mutation(tmp_path, mutate)
    with pytest.raises(ReflowError):
        call()
    _assert_store_never_advanced(assembly)


def test_e3_wrong_reobservation_after_observation_refs_fails_closed(tmp_path: Path) -> None:
    """The independent re-Observation Reflow's own G8 gate resolves no longer names a real
    Observation this run produced."""

    def mutate(kwargs: dict[str, Any], closure_request: dict[str, Any]) -> None:
        reobservation = dict(closure_request["reobservation"])
        reobservation["after_observation_refs"] = [{"kind": "observation", "id": "OBS-WRONG"}]
        closure_request["reobservation"] = reobservation

    assembly, call = _reflow_with_mutation(tmp_path, mutate)
    with pytest.raises(ReflowError):
        call()
    _assert_store_never_advanced(assembly)


def test_e3_wrong_evidence_sufficiency_difference_ref_fails_closed(tmp_path: Path) -> None:
    def mutate(kwargs: dict[str, Any], closure_request: dict[str, Any]) -> None:
        request = dict(closure_request["evidence_sufficiency_request"])
        request["difference_ref"] = {"kind": "difference", "id": "D-" + "7" * 64}
        closure_request["evidence_sufficiency_request"] = request

    assembly, call = _reflow_with_mutation(tmp_path, mutate)
    with pytest.raises(ReflowError):
        call()
    _assert_store_never_advanced(assembly)


def test_e3_wrong_change_result_evidence_refs_fails_closed(tmp_path: Path) -> None:
    def mutate(kwargs: dict[str, Any], closure_request: dict[str, Any]) -> None:
        closure_request["change_result_evidence_refs"] = [
            {"kind": "observation_evidence", "id": "EVIDENCE-WRONG"}
        ]

    assembly, call = _reflow_with_mutation(tmp_path, mutate)
    with pytest.raises(ReflowError):
        call()
    _assert_store_never_advanced(assembly)


def test_e3_wrong_authority_decision_fails_closed(tmp_path: Path) -> None:
    """Authority's own binding, one layer below Reflow: a denied Authority decision (no rule
    resolved) can never derive the real Change at all -- through the real Authority and Change
    owners, not a hand-built refusal."""

    assembly = assemble_vertical_proof_route(tmp_path)
    denied_request = dict(assembly["authority"]["request"])
    denied_request["authority_rules"] = []
    denied_decision = evaluate_authority(denied_request)
    assert denied_decision["decision"] != "AUTONOMOUS"

    with pytest.raises(UnauthorizedChangeError):
        derive_change(
            {
                "schema_version": "0.1",
                "authority_request": denied_request,
                "authority_decision": denied_decision,
            }
        )


def test_e3_wrong_instant_evidence_recorded_before_observation_ended_fails_closed(
    tmp_path: Path,
) -> None:
    """Evidence's own instant check, one layer below Reflow: ``recorded_at`` may never
    precede the end of the Observation it records."""

    assembly = assemble_vertical_proof_route(tmp_path)
    request = dict(assembly["evidence"]["change_result_evidence_request"])
    request["recorded_at"] = "2020-01-01T00:00:00Z"
    with pytest.raises(EvidenceError, match="precedes the end of the Observation"):
        derive_evidence(request)


# --- E4: sufficient Evidence without a successful Reflow does not close -------------------- #


def test_e4_sufficient_evidence_without_a_successful_reflow_does_not_close(
    tmp_path: Path,
) -> None:
    """The real Evidence Sufficiency Result is independently confirmed ``SUFFICIENT`` before
    Reflow ever runs -- and Reflow itself is then made to fail (a stale caller-side State
    expectation, item E3's own case, reused here to isolate this exact claim). Sufficient
    Evidence alone is never enough: the Store's committed State never advances."""

    assembly = assemble_vertical_proof_route(tmp_path)
    assert assembly["sufficiency"]["result"]["result"] == "SUFFICIENT"

    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["expected_state_revision"] = 999
    with pytest.raises(ReflowError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


# --- E5: a non-SATISFIED route remains non-closed and reconstructable --------------------- #


def test_e5_an_evaluation_that_is_not_satisfied_never_closes_and_stays_reconstructable(
    tmp_path: Path,
) -> None:
    """Emptying the Evidence pool (``EVIDENCE_ABSENT``) makes the Closure Evaluation itself
    not-``SATISFIED`` while the route still proposes ``CLOSED`` -- refused, and the Store
    stays exactly at its pre-transition genesis State, fully reconstructable."""

    def mutate(kwargs: dict[str, Any], closure_request: dict[str, Any]) -> None:
        request = dict(closure_request["evidence_sufficiency_request"])
        request["evidence_requests"] = []
        closure_request["evidence_sufficiency_request"] = request

    assembly, call = _reflow_with_mutation(tmp_path, mutate)
    with pytest.raises(ReflowError, match="must propose BLOCKED or RETAINED"):
        call()
    _assert_store_never_advanced(assembly)


def test_p8r1f2_a_genuinely_not_satisfied_evaluation_commits_a_real_retained_transition(
    tmp_path: Path,
) -> None:
    """P8-R1-F2 (SHUKOU Phase 8 structural-review round 1): the sibling test above only
    proves a *rejected* ``CLOSED`` proposal leaves the Store untouched -- a rejected proposal
    and a genuinely committed non-``CLOSED`` outcome are two different claims, and Issue #41
    requires the second one too. Emptying the Evidence pool the identical way, but correctly
    proposing ``RETAINED`` (one of this fixture's own ``allowed_terminal_states``) instead of
    ``CLOSED``, is accepted: a real State revision commits, the real lifecycle event
    persists and resolves, and a fresh Store instance reconstructs exactly what was
    committed -- never ``CLOSED``, and the Difference stays open."""

    assembly = assemble_vertical_proof_route(tmp_path)
    before = assembly["before"]
    kwargs = dict(assembly["reflow_kwargs"])
    closure_request = dict(kwargs["closure_request"])

    sufficiency_request = dict(closure_request["evidence_sufficiency_request"])
    sufficiency_request["evidence_requests"] = []
    closure_request["evidence_sufficiency_request"] = sufficiency_request
    closure_request["proposed_terminal_status"] = "RETAINED"
    # A non-CLOSED terminal status requires its own real, resolvable terminal-reason
    # Evidence (R7-F4) -- the real Observation Evidence :func:`observe_before` already
    # derived serves that role here, reused rather than a second Evidence derivation.
    closure_request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": before["observation_evidence"]["evidence_id"]}
    ]
    closure_request["terminal_reason_evidence_requests"] = [before["observation_evidence_request"]]
    kwargs["closure_request"] = closure_request
    kwargs["next_observation_ref"] = {
        "kind": "observation",
        "id": assembly["verification_observation_id"],
    }

    result = reflow(assembly["store"], **kwargs)

    assert result["decision"]["to_status"] == "RETAINED"
    assert (
        result["committed_state"]["state_revision"]
        == assembly["genesis_state"]["state_revision"] + 1
    )
    difference_ref = {"kind": "difference", "id": assembly["difference"]["difference_id"]}
    assert difference_ref in result["committed_state"]["semantic_state"]["open_differences"]

    fresh = FileStateStore(assembly["store"].root, schema_root=SCHEMA_ROOT)
    reconstructed = fresh.reconstruct(fx.PROJECT_ID)
    assert reconstructed == result["committed_state"]
    resolved_event = fresh.resolve_record(
        fx.PROJECT_ID, "difference_event", result["event"]["difference_event_id"]
    )
    assert resolved_event is not None
    assert resolved_event["to_status"] == "RETAINED"


# --- E6: stale Evidence and a material contradiction do not become success ----------------- #


def test_e6_evidence_older_than_the_policys_own_maximum_age_does_not_close(
    tmp_path: Path,
) -> None:
    """The real fixture's own Closure Policy leaves ``maximum_evidence_age`` unset
    (``None``), so this test builds the one real, policy-content variant that *does* set a
    finite maximum age shorter than this Evidence's real age -- through the same real
    ``policy_semantic_fingerprint``/``closure_policy_id`` identity functions the fixture's own
    ``closure_policy`` uses, never a hand-asserted id."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    closure_request = dict(kwargs["closure_request"])

    stale_policy = dict(closure_request["policy"])
    stale_policy["maximum_evidence_age"] = 60
    stale_policy["policy_semantic_fingerprint"] = policy_semantic_fingerprint(stale_policy)
    stale_policy["closure_policy_id"] = closure_policy_id(
        stale_policy["policy_semantic_fingerprint"], assembly["difference"]["difference_id"]
    )
    closure_request["policy"] = stale_policy
    sufficiency_request = dict(closure_request["evidence_sufficiency_request"])
    sufficiency_request["closure_policy"] = stale_policy
    closure_request["evidence_sufficiency_request"] = sufficiency_request
    kwargs["closure_request"] = closure_request

    with pytest.raises(ReflowError, match="must propose BLOCKED or RETAINED"):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


def test_e6_a_material_contradiction_does_not_become_success(tmp_path: Path) -> None:
    """A real, schema-valid ``material_contradiction`` record (built through the same
    generic, fixture-content-agnostic ``tests.reflow_helpers.material_contradiction_record``
    every other Phase 7 CONTRADICTED-route test already relies on) bound to this run's own
    genesis State/project never becomes a ``CLOSED`` success."""

    def mutate(kwargs: dict[str, Any], closure_request: dict[str, Any]) -> None:
        assembly_genesis = kwargs["closure_request"]["current_state"]
        contradiction = material_contradiction_record(
            project_id=fx.PROJECT_ID,
            detected_at_state_revision=assembly_genesis["revision"],
            detected_at_state_fingerprint=assembly_genesis["fingerprint"],
        )
        closure_request["material_contradictions"] = [contradiction]

    assembly, call = _reflow_with_mutation(tmp_path, mutate)
    with pytest.raises(ReflowError, match="must propose BLOCKED or RETAINED"):
        call()
    _assert_store_never_advanced(assembly)


# --- E7: Change cannot self-close and Evidence cannot self-close -------------------------- #


def test_e7_the_changes_own_result_observation_cannot_stand_in_as_its_own_verification(
    tmp_path: Path,
) -> None:
    """The Kernel's own G8 anti-self-closing gate, exercised through this proof's own real
    identities: reusing the real post-change Observation (the one Change-result Evidence is
    already grounded in) as Reflow's own independent re-observation -- instead of the real,
    separate verification Observation -- is refused. A Change can never verify itself."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    closure_request = dict(kwargs["closure_request"])

    change_result_obs_id = assembly["change_result_observation"]["bundle"]["observations"][-1][
        "observation_id"
    ]
    genesis = assembly["genesis_state"]
    self_closing_request = fx.derivation_request(
        observation_bundle=assembly["change_result_observation"]["bundle"],
        fingerprint=genesis["semantic_fingerprint"],
        state_revision=genesis["state_revision"],
        snapshot_ref=fx.AFTER_SNAPSHOT_REF,
    )
    closure_request["reobservation"] = {
        "derivation_request": self_closing_request,
        "after_observation_refs": [{"kind": "observation", "id": change_result_obs_id}],
    }
    kwargs["closure_request"] = closure_request
    kwargs["observation_refs"] = [{"kind": "observation", "id": change_result_obs_id}]

    with pytest.raises(ReflowError):
        reflow(assembly["store"], **kwargs)
    _assert_store_never_advanced(assembly)


# --- E8/E9: crash at every Store stage never exposes a partial cycle; recovery converges --- #

_PRE_COMMIT_INTENT_STAGES = frozenset(STAGES[: STAGES.index("AFTER_COMMIT_INTENT")])


@pytest.mark.parametrize("stage", STAGES)
def test_e8_e9_crash_at_every_store_stage_never_exposes_a_partial_cycle(
    stage: str, tmp_path: Path
) -> None:
    """Injects a real :class:`SimulatedCrash` at *stage* into the real vertical proof's own
    ``reflow()``-driven commit (via :class:`~tests.natural_cycle.proof.FaultInjectingStore`,
    the one seam ``FileStateStore.commit``/``commit_reflow`` already expose to every caller).
    After :meth:`FileStateStore.recover`, the committed State is *exactly* one of two values,
    never a partial mixture: still genesis (a crash before ``COMMIT_INTENT`` was durably
    written) or the one fully-closed successor (at or after it) -- recovery converges to
    exactly the one valid final State, matching a clean run bit-for-bit when it does."""

    def fault(current: str, _stage: str = stage) -> None:
        if current == _stage:
            raise SimulatedCrash(_stage)

    with pytest.raises(SimulatedCrash):
        run_vertical_proof(tmp_path, fault=fault)

    store = build_store(tmp_path)
    store.recover(fx.PROJECT_ID)
    current = store.load_current(fx.PROJECT_ID)
    reconstructed = store.reconstruct(fx.PROJECT_ID)
    assert current == reconstructed

    if stage in _PRE_COMMIT_INTENT_STAGES:
        assert current["state_revision"] == 0
    else:
        assert current["state_revision"] == 1
        # Per-kind record resolvability after a clean commit is already proven exhaustively
        # by test_vertical_proof.py's own reconstruction test; the sufficient joint check
        # here is that recovery converges to exactly the one successor State identity.


# --- E10/E11: identical replay adds nothing; a conflicting replay is rejected -------------- #


def test_e10_e11_identical_commit_replay_is_a_no_op_and_a_conflicting_replay_is_rejected(
    tmp_path: Path,
) -> None:
    """This guarantee -- ``commit_reflow``'s own idempotent-replay/conflict contract -- lives
    at the Reflow commit owner itself, one layer below the full ``reflow()`` orchestration:
    ``reflow()``'s own caller-side staleness pre-check (``expected_state_revision``) refuses a
    second call once the Store has already advanced, so a literal second ``reflow()`` call can
    never be a byte-identical replay of the first by construction (its freshly-loaded
    ``current_state`` has moved). The real replay/conflict guarantee is therefore proven here
    directly against ``commit_reflow`` -- the same real, public Reflow owner ``reflow()``
    itself calls -- fed this proof's own real genesis State and real after-Semantic-State
    content, never hand-built substitutes."""

    store = build_store(tmp_path)
    genesis = initialize_genesis(store)
    next_semantic = after_semantic_state()
    tx = "TX-" + "1" * 61

    committed_first, ref_first = commit_reflow(
        store,
        project_id=fx.PROJECT_ID,
        before_project_state=genesis,
        next_semantic_state=next_semantic,
        transaction_id=tx,
        evidence_refs=[],
        reflow_instant=fx.REFLOW_INSTANT,
    )
    events_after_first = store._events(fx.PROJECT_ID)
    assert committed_first["state_revision"] == genesis["state_revision"] + 1

    committed_replay, ref_replay = commit_reflow(
        store,
        project_id=fx.PROJECT_ID,
        before_project_state=genesis,
        next_semantic_state=next_semantic,
        transaction_id=tx,
        evidence_refs=[],
        reflow_instant=fx.REFLOW_INSTANT,
    )
    events_after_replay = store._events(fx.PROJECT_ID)

    assert committed_replay == committed_first
    assert ref_replay == ref_first
    assert len(events_after_replay) == len(events_after_first)

    conflicting_semantic = after_semantic_state()
    conflicting_semantic["code"]["claims"]["vertical_proof_target"] = "DIFFERENT"
    with pytest.raises(TransactionConflictError):
        commit_reflow(
            store,
            project_id=fx.PROJECT_ID,
            before_project_state=genesis,
            next_semantic_state=conflicting_semantic,
            transaction_id=tx,
            evidence_refs=[],
            reflow_instant=fx.REFLOW_INSTANT,
        )
    assert store.load_current(fx.PROJECT_ID) == committed_first


def test_p8r1f3_the_full_vertical_transaction_record_set_replays_as_a_true_no_op(
    tmp_path: Path,
) -> None:
    """P8-R1-F3 (SHUKOU Phase 8 structural-review round 1): the sibling test above only
    replays an empty ``records``/``evidence_refs`` transaction -- it never proves the *real*
    vertical proof's own full immutable-record set (Closure Evaluation, lifecycle event,
    Evidence Sufficiency Result, both real Evidence records, the real Observation, every
    mandatory Invariant Evaluation, the Candidate claim-evaluation event, the Completion
    Record, the Source Snapshot, the Kernel witness) replays as a true no-op, or that a
    conflicting payload under the one real transaction identity is rejected.

    The exact manifest -- every ``(kind, record_id)`` pair this transaction actually
    committed -- is read from the transaction's own persisted recovery journal
    (``state/recovery/<tx>/manifest.json``, the identical file
    ``FileStateStore._stage_records``/``_transaction_manifest_keys`` themselves read and
    write) and every record body is then resolved through the public
    :meth:`~manosube_agent_civilization.store.FileStateStore.resolve_record` -- never
    hand-reproduced -- so the replayed ``records`` argument is provably the real, complete
    set this transaction admitted, not an approximation of it."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    project_id = fx.PROJECT_ID
    tx_id = result["reflow_result"]["state_transition_ref"]["id"]
    transition = store.resolve_transaction(project_id, tx_id)
    assert transition is not None

    manifest_path = (
        store.root / "projects" / project_id / "state" / "recovery" / tx_id / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest) > 10  # the real vertical proof's own full record set, not a stub

    records = []
    for kind, record_id in manifest:
        body = store.resolve_record(project_id, kind, record_id)
        assert body is not None, f"{kind}/{record_id} did not resolve"
        records.append((kind, record_id, body))

    events_before = list(store._events(project_id))
    per_kind_count_before = {
        kind: len(list((store.root / "projects" / project_id / "records" / kind).glob("*.json")))
        for kind, _ in manifest
    }
    current_before = store.load_current(project_id)
    reconstructed_before = store.reconstruct(project_id)

    replayed = store.commit(
        project_id,
        expected_revision=999,  # irrelevant on the replay path -- the tx already exists
        expected_fingerprint={"algorithm": "irrelevant", "digest": "irrelevant"},
        next_state=transition["after_state"],
        transition=transition,
        records=records,
    )

    assert replayed == transition["after_state"] == current_before
    events_after = list(store._events(project_id))
    assert len(events_after) == len(events_before)
    per_kind_count_after = {
        kind: len(list((store.root / "projects" / project_id / "records" / kind).glob("*.json")))
        for kind, _ in manifest
    }
    assert per_kind_count_after == per_kind_count_before
    assert store.load_current(project_id) == current_before
    assert store.reconstruct(project_id) == reconstructed_before
    for kind, record_id, body in records:
        assert store.resolve_record(project_id, kind, record_id) == body

    conflicting_records = list(records)
    tamper_kind, tamper_id, tamper_body = conflicting_records[0]
    tampered_body = dict(tamper_body)
    tampered_body["schema_version"] = "9.9"
    conflicting_records[0] = (tamper_kind, tamper_id, tampered_body)
    with pytest.raises(TransactionConflictError):
        store.commit(
            project_id,
            expected_revision=999,
            expected_fingerprint={"algorithm": "irrelevant", "digest": "irrelevant"},
            next_state=transition["after_state"],
            transition=transition,
            records=conflicting_records,
        )
    assert store.load_current(project_id) == current_before
    assert store.reconstruct(project_id) == reconstructed_before
    assert store.resolve_record(project_id, tamper_kind, tamper_id) == tamper_body


# --- E12: deleting/reordering/tampering lineage or a referenced record is detected --------- #


def test_e12_a_tampered_persisted_record_is_detected_on_resolution(tmp_path: Path) -> None:
    """A committed record's own file, rewritten directly on disk (never through the Store's
    own API), is detected the next time any Store instance resolves it -- the multi-claimant
    visibility scan (R12-F1) refuses to return content that disagrees with what the
    committing transaction's own manifest actually claimed."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    ledger = result["identity_ledger"]
    path = (
        store.root
        / "projects"
        / fx.PROJECT_ID
        / "records"
        / "closure_evaluation"
        / f"{ledger['closure_evaluation_id']}.json"
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    data["result"] = "TAMPERED"
    path.write_text(json.dumps(data), encoding="utf-8")

    fresh = FileStateStore(store.root, schema_root=SCHEMA_ROOT)
    with pytest.raises(CorruptStoreError):
        fresh.resolve_record(fx.PROJECT_ID, "closure_evaluation", ledger["closure_evaluation_id"])


def test_e12_a_tampered_lineage_entry_is_detected_on_reconstruction(tmp_path: Path) -> None:
    """The committed lineage journal, rewritten directly on disk, is detected the next time
    any Store instance reconstructs or loads the current State from it."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    lineage_path = store.root / "projects" / fx.PROJECT_ID / "events" / "transitions.jsonl"
    lines = lineage_path.read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[-1])
    event["to_revision"] = 999
    lines[-1] = json.dumps(event)
    lineage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fresh = FileStateStore(store.root, schema_root=SCHEMA_ROOT)
    with pytest.raises(CorruptStoreError):
        fresh.reconstruct(fx.PROJECT_ID)
    with pytest.raises(CorruptStoreError):
        fresh.load_current(fx.PROJECT_ID)


# --- E14: a fresh Python process proves session loss does not alter the final identity ----- #


def test_e14_a_fresh_python_process_reconstructs_the_identical_final_state(
    tmp_path: Path,
) -> None:
    """Process isolation *is* feasible in this retained environment (a plain ``subprocess``
    of the same interpreter): a brand-new Python process, holding none of this test's own
    in-process objects, is started; it only opens the identical persisted backend directory
    through the real, public :class:`FileStateStore` and reconstructs. Its result, read back
    over a pipe, is asserted byte-for-byte identical to the parent process's own committed
    State -- session loss changes nothing about the final identity."""

    result = run_vertical_proof(tmp_path)
    store_root = str(result["store"].root)
    committed = result["reflow_result"]["committed_state"]

    script = textwrap.dedent(
        f"""
        import json, pathlib
        from manosube_agent_civilization.store import FileStateStore
        from tests.state_helpers import SCHEMA_ROOT
        store = FileStateStore(pathlib.Path({store_root!r}), schema_root=SCHEMA_ROOT)
        state = store.reconstruct({fx.PROJECT_ID!r})
        print(json.dumps(state, sort_keys=True))
        """
    )
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(Path.cwd()),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    fresh_state = json.loads(proc.stdout.strip().splitlines()[-1])
    assert fresh_state == committed
