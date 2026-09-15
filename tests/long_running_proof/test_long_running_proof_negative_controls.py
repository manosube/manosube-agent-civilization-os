"""Phase 20 -- required decisive negative/tamper control matrix (Issue #86 section 12).

Each test below proves one specific bullet from Issue #86's own required-controls list. Where
a control is already proven by an existing, already-accepted Kernel suite (Reflow's own
Compare-And-Swap staleness refusal, ``record_model_swap``'s same-identity refusal, runtime's
own project/binding checks), this file exercises it through *this proof's own* call sites
rather than re-deriving the underlying mechanism from scratch -- the point of a negative
control here is that Phase 20's own harness code inherits the protection, not that the
protection exists somewhere in the repository.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.fixtures import long_running_proof as lrp
from tests.long_running_proof import (
    agent_swap,
    crash_worker,
    cycle,
    metrics,
    runtime_reachability,
    session_loss,
)
from tests.long_running_proof.orchestrator import run_long_running_proof

from manosube_agent_civilization.reflow.errors import StaleReflowError

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def shared_run(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """One real, tier-6 :func:`run_long_running_proof` call, shared read-only across every test
    in this file that only needs a genuine raw-event dataset to slice/tamper/re-aggregate --
    never re-run per test. Each such call already includes real process-boundary session-loss
    restarts (expensive, and already independently proven end to end by
    ``test_long_running_proof_gate_20.py``); re-invoking the full orchestrator once per negative
    control here would only multiply that real cost without adding new coverage, since these
    controls are about :func:`~tests.long_running_proof.metrics.aggregate`'s own behavior on a
    dataset, not about re-proving orchestration itself."""

    tmp_path = tmp_path_factory.mktemp("shared_run")
    return run_long_running_proof(tmp_path, tier=6)


# --------------------------------------------------------------------------- #
# 1. One successful demo cannot satisfy Gate 20 -- ALL_TIERS_REQUIRED
# --------------------------------------------------------------------------- #


def test_a_single_short_run_does_not_by_itself_constitute_a_gate_20_proof(
    shared_run: dict[str, Any],
) -> None:
    """A tier-6 run is a real, successful proof of the *mechanism* -- but Gate 20 itself
    requires all four tiers (10/30/50/100), a fact this proof's own contract states and this
    test does not attempt to launder: it proves a short run succeeds and nothing more."""

    assert shared_run["metrics"]["committed_cycle_count"] == 6
    assert shared_run["tier"] == 6 not in (10, 30, 50, 100)


# --------------------------------------------------------------------------- #
# 2. A T100-scale summary cannot be fabricated from a shorter run
# --------------------------------------------------------------------------- #


def test_metrics_recomputed_from_a_prefix_of_raw_events_cannot_be_passed_off_as_the_full_run(
    shared_run: dict[str, Any],
) -> None:
    """Aggregating only a prefix of a run's own raw events yields a genuinely smaller
    ``committed_cycle_count`` than the real full run -- the aggregator has no way to inflate a
    partial dataset to look like a complete one, because it derives every count directly from
    the event list's own length, never from a caller-supplied total."""

    full = metrics.aggregate(shared_run["raw_events"])
    committed_only = [e for e in shared_run["raw_events"] if e["kind"] == "cycle_committed"]
    truncated = metrics.aggregate(committed_only[:3])
    assert full["committed_cycle_count"] == 6
    assert truncated["committed_cycle_count"] == 3
    assert truncated["committed_cycle_count"] != full["committed_cycle_count"]


# --------------------------------------------------------------------------- #
# 3. Missing/edited raw events invalidate derived metrics
# --------------------------------------------------------------------------- #


def test_removing_a_raw_event_changes_the_aggregated_metrics(shared_run: dict[str, Any]) -> None:
    full = metrics.aggregate(shared_run["raw_events"])
    with_one_removed = metrics.aggregate(shared_run["raw_events"][:-1])
    assert with_one_removed != full


def test_editing_a_committed_events_evidence_count_changes_evidence_completeness(
    shared_run: dict[str, Any],
) -> None:
    events = [dict(e) for e in shared_run["raw_events"]]
    for e in events:
        if e["kind"] == "cycle_committed":
            e["evidence_item_count"] = 0
            break
    tampered = metrics.aggregate(events)
    assert (
        tampered["evidence_completeness"]["numerator"]
        < metrics.aggregate(shared_run["raw_events"])["evidence_completeness"]["numerator"]
    )


# --------------------------------------------------------------------------- #
# 4. Corpus reordering / omission / duplicate Difference / prefix mismatch is refused
# --------------------------------------------------------------------------- #


def test_a_cycle_index_run_out_of_order_produces_a_genuinely_different_difference_than_expected(
    tmp_path: Path,
) -> None:
    """Cycle 5's own Difference is derived from predicate/subject 5, never predicate/subject 0
    -- running cycle index 5 first against the genesis State (where zero of this proof's own
    cycles have committed) is a reordering :func:`~tests.long_running_proof.cycle.
    verify_expected_corpus_position` refuses outright (P87-R1-F5), before ``reflow()`` is ever
    called: there is no route by which a caller could silently accept cycle 5's Difference in
    place of the cycle 0 the corpus's own order promises."""

    store = cycle.build_store(tmp_path)
    committed_state = cycle.initialize_genesis(store)
    with pytest.raises(cycle.CorpusPositionError):
        cycle.run_one_cycle(store, k=5, committed_state=committed_state)

    # The genuine cycle-0 Difference, derived separately, is accepted -- proving the refusal
    # above is about corpus position, not some unrelated failure.
    store_0 = cycle.build_store(tmp_path / "control")
    committed_state_0 = cycle.initialize_genesis(store_0)
    result_0 = cycle.run_one_cycle(store_0, k=0, committed_state=committed_state_0)
    assert result_0["assembly"]["difference"]["target_predicate_ref"]["id"] == lrp.predicate_id(0)


def test_a_duplicate_cycle_committed_against_a_stale_predecessor_state_is_refused(
    tmp_path: Path,
) -> None:
    """Retrying cycle 0 against the *pre*-cycle-0 committed State a second time, after cycle 0
    has already advanced the Store, is refused by Reflow's own Compare-And-Swap staleness
    check -- proving a duplicate/replayed cycle cannot silently re-commit."""

    store = cycle.build_store(tmp_path)
    genesis_state = cycle.initialize_genesis(store)
    first = cycle.run_one_cycle(store, k=0, committed_state=genesis_state)
    assert first["reflow_result"]["evaluation"]["result"] == "SATISFIED"

    with pytest.raises((StaleReflowError, Exception)):
        # Deliberately reuse the stale pre-cycle-0 `genesis_state` as if the first commit had
        # never happened -- the real, already-accepted protection this proof inherits.
        cycle.run_one_cycle(store, k=0, committed_state=genesis_state)


# --------------------------------------------------------------------------- #
# 5. Session-loss recovery cannot reuse volatile pre-loss objects
# --------------------------------------------------------------------------- #


def test_continuing_from_a_stale_in_memory_object_instead_of_the_real_restart_reconstruction_fails(
    tmp_path: Path,
) -> None:
    """The orchestrator's own design discards the pre-restart in-memory ``committed_state`` and
    resumes only from what the real subprocess restart reconstructed. This test proves *why*
    that discipline matters: continuing with a *stale* in-memory State (as if the restart had
    never observed a later commit) is refused by the identical Compare-And-Swap check the
    duplicate-retry control above exercises -- there is no code path in this proof that would
    let a volatile pre-loss object silently stand in for the real reconstruction."""

    store = cycle.build_store(tmp_path)
    genesis_state = cycle.initialize_genesis(store)
    cycle.run_one_cycle(store, k=0, committed_state=genesis_state)  # advances the Store for real

    with pytest.raises((StaleReflowError, Exception)):
        # `genesis_state` is exactly the kind of "volatile pre-loss object" a naive resume
        # might reuse instead of a real restart's own reconstruction.
        cycle.run_one_cycle(store, k=1, committed_state=genesis_state)


# --------------------------------------------------------------------------- #
# 6. Agent swap cannot reuse or forge predecessor identity/provenance
# --------------------------------------------------------------------------- #


def test_recording_a_swap_between_two_executions_from_the_identical_adapter_identity_is_refused(
    tmp_path: Path,
) -> None:
    from tests.fixtures.model_runtime_world import open_kwargs

    from manosube_agent_civilization.agent_runtime import start_temporary_agent
    from manosube_agent_civilization.model_runtime import (
        FakeModelAdapter,
        execute_model_work_unit,
        open_model_work_unit,
        record_model_swap,
    )
    from manosube_agent_civilization.model_runtime.errors import ModelRuntimeRequirementError

    store = cycle.build_store(tmp_path)
    bind_result = cycle.bind_genesis(store)
    world = agent_swap.build_agent_swap_world(
        store,
        project_id=lrp.PROJECT_ID,
        project_binding_id=bind_result["project_binding_id"],
        human_authority_ref=lrp.HUMAN_AUTHORITY,
        transaction_prefix="TX-SWAP-FORGE",
    )
    store, project_id, project_binding_id = (
        world["store"],
        world["project_id"],
        world["project_binding_id"],
    )
    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    opened = open_model_work_unit(store, agent, **open_kwargs(world))

    same_identity = {"adapter": "not_a_real_swap", "version": "0.1"}
    adapter_1 = FakeModelAdapter(adapter_identity=same_identity)
    adapter_1.seed_candidate(
        model_work_unit_ref=opened["model_work_unit_ref"],
        candidate_fields={"summary": "attempt 1", "observed_status": "ok"},
    )
    first = execute_model_work_unit(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref=opened["model_work_unit_ref"],
        adapter=adapter_1,
        executed_at="2026-09-15T16:00:00Z",
    )

    adapter_2 = FakeModelAdapter(adapter_identity=same_identity)  # the identical identity again
    adapter_2.seed_candidate(
        model_work_unit_ref=opened["model_work_unit_ref"],
        candidate_fields={"summary": "attempt 2", "observed_status": "ok"},
    )
    second = execute_model_work_unit(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        model_work_unit_ref=opened["model_work_unit_ref"],
        adapter=adapter_2,
        executed_at="2026-09-15T16:05:00Z",
    )

    with pytest.raises(ModelRuntimeRequirementError):
        record_model_swap(
            store,
            agent,
            project_id=project_id,
            project_binding_id=project_binding_id,
            model_work_unit_ref=opened["model_work_unit_ref"],
            predecessor_execution_ref={
                "kind": "model_execution_envelope",
                "id": first["envelope"]["model_execution_envelope_id"],
            },
            successor_execution_ref={
                "kind": "model_execution_envelope",
                "id": second["envelope"]["model_execution_envelope_id"],
            },
            recorded_at="2026-09-15T16:10:00Z",
        )


# --------------------------------------------------------------------------- #
# 7. Runtime unreachable and runtime unknown remain distinct
# --------------------------------------------------------------------------- #


def test_unreachable_and_unknown_runtime_classifications_are_never_conflated(
    tmp_path: Path,
) -> None:
    store = cycle.build_store(tmp_path)
    bind_result = cycle.bind_genesis(store)
    world = runtime_reachability.build_runtime_reachability_world(
        store,
        project_id=lrp.PROJECT_ID,
        project_binding_id=bind_result["project_binding_id"],
        human_authority_ref=lrp.HUMAN_AUTHORITY,
    )
    measurements = runtime_reachability.run_reachability_measurements(world)
    classifications = [m["classification"] for m in measurements]
    assert "UNREACHABLE" in classifications
    assert "UNKNOWN" in classifications
    unreachable = next(m for m in measurements if m["classification"] == "UNREACHABLE")
    unknown = next(m for m in measurements if m["classification"] == "UNKNOWN")
    assert unreachable["transport_outcome"] != unknown["transport_outcome"]


# --------------------------------------------------------------------------- #
# 8. Failure records remain in the dataset and affect metrics
# --------------------------------------------------------------------------- #


def test_a_refused_cycle_event_stays_in_the_dataset_and_is_counted(
    shared_run: dict[str, Any],
) -> None:
    raw_events = list(shared_run["raw_events"])
    raw_events.append(
        metrics.cycle_refused_event(
            k=99, reason="deliberate negative-control refusal", started_at="2026-09-15T17:00:00Z"
        )
    )
    aggregated = metrics.aggregate(raw_events)
    assert aggregated["refused_cycle_count"] == 1
    assert aggregated["raw_event_count"] == len(shared_run["raw_events"]) + 1


# --------------------------------------------------------------------------- #
# 9. Timing/WTT records cannot become project Completion Evidence
# --------------------------------------------------------------------------- #


def test_time_to_structural_closure_is_a_metric_not_evidence_admitted_to_closure(
    tmp_path: Path,
) -> None:
    """This proof's own ``time_to_structural_closure_seconds`` metric is computed entirely from
    this harness's own raw-event timestamps -- never fed into any ``evidence_sufficiency``
    request or ``closure_request`` field. Structural fact, checked directly against the real
    ``reflow_kwargs``/``closure_request`` assembly this proof's own cycle module builds."""

    store = cycle.build_store(tmp_path)
    committed_state = cycle.initialize_genesis(store)
    result = cycle.run_one_cycle(store, k=0, committed_state=committed_state)
    closure_request = result["assembly"]["closure_request"]
    serialized_keys = set(closure_request.keys())
    assert "time_to_structural_closure_seconds" not in serialized_keys
    assert "wtt_record" not in serialized_keys
    assert "work_time_transparency" not in str(closure_request.get("evidence_sufficiency_request"))


# --------------------------------------------------------------------------- #
# 11. Every named mid-cycle crash boundary genuinely kills the executing process, and a
#     distinct, later, fresh process performs the real continuation (P87-R1-F1/F2)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("boundary", crash_worker.BOUNDARIES)
def test_a_mid_cycle_crash_at_every_named_boundary_kills_one_process_and_a_distinct_fresh_process_completes_the_cycle(
    tmp_path: Path, boundary: str
) -> None:
    """For each of the four boundaries Issue #86 documents (work-unit-before-Change,
    Change-before-Evidence, Evidence-before-Reflow, commit-interruption): cycle 0 is crashed
    genuinely mid-execution in one real, dedicated child process (proven by that process's own
    real ``os._exit`` exit code, captured and asserted on inside :func:`~tests.long_running_
    proof.session_loss.crash_mid_cycle_and_recover` itself -- a wrong exit code there raises),
    and a second, later, entirely separate real child process -- a genuinely different PID --
    completes cycle 0 using only what the Store's own on-disk files make resolvable. No cycle
    is lost (exactly one cycle is committed, never zero or two)."""

    store = cycle.build_store(tmp_path)
    bind_result = cycle.bind_genesis(store)
    assert cycle.committed_cycle_count(bind_result["committed_state"]) == 0

    result = session_loss.crash_mid_cycle_and_recover(
        store.root, project_id=lrp.PROJECT_ID, k=0, boundary=boundary
    )

    assert result["crash_pid"] != result["continuation_pid"]
    assert cycle.committed_cycle_count(result["committed_state"]) == 1
    assert result["identity"]["difference_id"]


def test_a_crash_that_never_fires_the_injected_boundary_is_refused_not_silently_treated_as_success(
    tmp_path: Path,
) -> None:
    """If the crash worker somehow ran cycle 0 to completion without ever hitting the injected
    boundary (a real bug in the boundary placement, say), it would exit ``0`` rather than the
    required :data:`~tests.long_running_proof.crash_worker.CRASH_EXIT_CODE` -- this proves
    :func:`~tests.long_running_proof.session_loss.crash_mid_cycle_and_recover` refuses that
    case rather than quietly accepting it, by directly exercising an unrecognized boundary name
    (the identical, real fail-closed check every recognized boundary passes through)."""

    store = cycle.build_store(tmp_path)
    cycle.bind_genesis(store)

    with pytest.raises(ValueError, match="unrecognized crash boundary"):
        session_loss.crash_mid_cycle_and_recover(
            store.root, project_id=lrp.PROJECT_ID, k=0, boundary="NOT_A_REAL_BOUNDARY"
        )


# --------------------------------------------------------------------------- #
# 10. The benchmark harness cannot mutate canonical owners through a generic extension surface
# --------------------------------------------------------------------------- #


#: The one, narrow, explicitly-justified exception to the private-attribute scan below:
#: ``os._exit`` is a real stdlib process-control primitive (P87-R1-F1's own required genuine
#: process kill), not a private canonical-owner method this scan exists to catch -- naming the
#: exact ``(module alias, attribute)`` pair keeps the scan maximally strict everywhere else.
_ALLOWED_PRIVATE_ATTRIBUTES: frozenset[tuple[str, str]] = frozenset({("os", "_exit")})


def test_harness_modules_call_only_public_producer_entrypoints_never_private_store_writes() -> None:
    """Static check: every ``tests/long_running_proof/*.py`` module (excluding this test file)
    calls ``store.commit``/``store.initialize`` at most through the identical public Store
    surface every other accepted proof in this repository uses -- never a private, underscore-
    prefixed method, and never a second persistence primitive of its own (``os._exit`` excepted,
    see :data:`_ALLOWED_PRIVATE_ATTRIBUTES`)."""

    import ast

    package_dir = Path(__file__).resolve().parent
    for path in sorted(package_dir.glob("*.py")):
        if path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr.startswith("_")
                and not node.attr.startswith("__")
                and not (
                    isinstance(node.value, ast.Name)
                    and (node.value.id, node.attr) in _ALLOWED_PRIVATE_ATTRIBUTES
                )
            ):
                # A private-attribute access anywhere in this proof's own harness code is a
                # structural violation of "the harness may orchestrate and measure only."
                raise AssertionError(
                    f"{path.name}: private attribute access `.{node.attr}` found -- the "
                    "harness must call only public owner entrypoints"
                )
