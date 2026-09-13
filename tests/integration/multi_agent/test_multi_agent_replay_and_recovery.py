"""Phase 19 (Issue #77) V6: replay/concurrency/crash/release matrix.

Exact replay, conflicting replay, duplicate coordinator, partial execution, coordinator
crash, release visibility, recovery, and no leaked Agent.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.fixtures.multi_agent_world import (
    CrashingMultiAgentAdapter,
    HangingMultiAgentAdapter,
    SeededMultiAgentAdapter,
    authorized_world,
    open_plan_kwargs,
)

from manosube_agent_civilization.agent_runtime import TemporaryAgent, start_temporary_agent
import manosube_agent_civilization.model_runtime.route as model_runtime_route_module
from manosube_agent_civilization.multi_agent import (
    execute_dynamic_execution_plan,
    open_dynamic_execution_plan,
)
from manosube_agent_civilization.multi_agent.errors import MultiAgentReplayConflictError
import manosube_agent_civilization.multi_agent.route as route_module


def _coordinator(world: dict[str, Any]) -> Any:
    return start_temporary_agent(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
    )


def _open(world: dict[str, Any]) -> dict[str, Any]:
    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(world["store"], coordinator, **open_plan_kwargs(world))
    coordinator.release()
    return opened


def _execute(
    world: dict[str, Any], plan_ref: dict[str, Any], factory: Any, executed_at: str
) -> dict[str, Any]:
    coordinator = _coordinator(world)
    result = execute_dynamic_execution_plan(
        world["store"],
        coordinator,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        plan_ref=plan_ref,
        model_adapter_factory=factory,
        executed_at=executed_at,
    )
    coordinator.release()
    return result


def test_exact_replay_reuses_every_slot_output_with_zero_new_adapter_calls(tmp_path: Any) -> None:
    world = authorized_world(tmp_path, risk_class="HIGH")
    opened = _open(world)
    adapters = [SeededMultiAgentAdapter(candidate_fields={"summary": "same"}) for _ in range(2)]

    adapter_iterator = iter(adapters)
    first = _execute(
        world, opened["plan_ref"], lambda: next(adapter_iterator), "2026-09-11T01:30:00Z"
    )
    assert all(adapter.execute_call_count == 1 for adapter in adapters)

    # Replay: a fresh execute call over the identical plan_ref must resolve the identical
    # slot_outputs/release_receipts/conflict_set/aggregation_input, and must never touch the
    # adapters at all -- a factory that raises proves it was never even called.
    def _forbidden_factory() -> Any:
        raise AssertionError("adapter_factory must not be called on a genuine replay")

    second = _execute(world, opened["plan_ref"], _forbidden_factory, "2026-09-11T01:30:00Z")

    assert [so["multi_agent_slot_output_id"] for so in first["slot_outputs"]] == [
        so["multi_agent_slot_output_id"] for so in second["slot_outputs"]
    ]
    assert (
        first["conflict_set"]["multi_agent_conflict_set_id"]
        == second["conflict_set"]["multi_agent_conflict_set_id"]
    )
    assert (
        first["aggregation_input"]["multi_agent_evidence_aggregation_input_id"]
        == second["aggregation_input"]["multi_agent_evidence_aggregation_input_id"]
    )


def test_conflicting_reuse_of_an_attempt_identity_refuses(tmp_path: Any) -> None:
    """Simulates an attacker (or a genuine bug) able to write Store records directly:
    planting a *different-content* ``multi_agent_slot_output`` at the identical attempt
    identity a real attempt already occupies must refuse, never silently overwrite or
    coexist."""

    world = authorized_world(tmp_path, risk_class="LOW")
    opened = _open(world)
    executed = _execute(
        world, opened["plan_ref"], lambda: SeededMultiAgentAdapter(), "2026-09-11T01:30:00Z"
    )
    real_slot_output = executed["slot_outputs"][0]

    tampered = dict(real_slot_output)
    tampered["outcome"] = "REFUSED"
    tampered["result_fingerprint"] = None
    tampered["outcome_detail"] = "planted by an attacker"
    # The narrow id is unchanged (it excludes outcome by design); recompute the fingerprint so
    # the planted record is at least internally self-consistent -- the point is that the
    # *content* genuinely differs from what is already committed at this exact Store key.
    from manosube_agent_civilization.multi_agent.identity import (
        multi_agent_slot_output_semantic_fingerprint,
    )

    tampered["multi_agent_slot_output_semantic_fingerprint"] = (
        multi_agent_slot_output_semantic_fingerprint(tampered)
    )

    store = world["store"]
    fresh = route_module._fresh_execution_contract(
        store, project_id=world["project_id"], project_binding_id=world["project_binding_id"]
    )
    with pytest.raises(MultiAgentReplayConflictError):
        route_module._commit(
            store,
            world["project_id"],
            [("multi_agent_slot_output", tampered["multi_agent_slot_output_id"], tampered)],
            committed_at="2026-09-11T01:35:00Z",
            project_binding_id=world["project_binding_id"],
            expected_authority=fresh,
            transaction_prefix="TX-MULTI-AGENT-TAMPER",
            transaction_key="0001",
        )


class _ReleaseCountingAgentProxy(TemporaryAgent):
    """Wraps a real, live Temporary Agent and counts ``.release()`` calls -- used to prove no
    Agent this package constructs is ever leaked, even when the code between construction and
    release raises."""

    def __init__(self, real_agent: TemporaryAgent, counters: dict[str, int]) -> None:
        self._real = real_agent
        self._counters = counters

    @property
    def boot_context(self) -> Any:
        return self._real.boot_context

    def release(self) -> None:
        self._counters["released"] += 1
        self._real.release()


def test_partial_execution_coordinator_crash_and_recovery_leak_no_agent(
    tmp_path: Any, monkeypatch: Any
) -> None:
    """Structural Review Round 4, P19-R4-F2's own required proof (rewritten from this test's
    pre-Round-4 shape): a genuinely unexpected, non-``ModelRuntimeError`` adapter crash --
    exactly this test's own ``CrashingMultiAgentAdapter`` -- is no longer allowed to propagate
    out of the whole orchestration call uncaught (Round 3's own explicit, deliberate design
    choice, now reversed). It is instead caught by :func:`_execute_one_slot`'s own broadened
    ``except Exception`` and durably terminalized: this call returns normally, with a typed
    ``UNAVAILABLE`` outcome and a resolved ``RELEASED`` release receipt for the crashed slot, no
    Agent left unaccounted for, and no attempt-envelope claim (there is no real Envelope this
    attempt could ever truthfully name). Because that terminal pair is now genuinely committed,
    replaying the identical ``plan_ref`` afterward reuses it verbatim -- P19-R4-F2's own
    ``replay must not ambiguously repeat a terminal attempt`` requirement -- never invoking the
    adapter a second time for that same, now-permanently-UNAVAILABLE attempt.
    """

    world = authorized_world(tmp_path, risk_class="HIGH")
    opened = _open(world)

    counters = {"constructed": 0, "released": 0}
    real_start_temporary_agent = start_temporary_agent

    def _counting_start_temporary_agent(*args: Any, **kwargs: Any) -> TemporaryAgent:
        real_agent = real_start_temporary_agent(*args, **kwargs)
        counters["constructed"] += 1
        return _ReleaseCountingAgentProxy(real_agent, counters)

    monkeypatch.setattr(route_module, "start_temporary_agent", _counting_start_temporary_agent)

    working_adapter = SeededMultiAgentAdapter(candidate_fields={"summary": "ok"})
    crashing_adapter = CrashingMultiAgentAdapter()
    factory_calls = iter([working_adapter, crashing_adapter])

    executed = _execute(
        world, opened["plan_ref"], lambda: next(factory_calls), "2026-09-11T01:30:00Z"
    )

    # No Agent this package constructed is ever leaked, even for the slot whose own adapter call
    # crashed with a genuinely unexpected exception.
    assert counters["constructed"] == counters["released"]
    assert counters["constructed"] >= 2

    assert crashing_adapter.execute_call_count == 1
    assert executed["slot_outputs"][0]["outcome"] == "CANDIDATE_ACCEPTED"
    slot1_output = executed["slot_outputs"][1]
    assert slot1_output["outcome"] == "UNAVAILABLE"
    assert slot1_output["model_execution_envelope_ref"] is None
    assert slot1_output["result_fingerprint"] is None
    assert executed["release_receipts"][1]["release_status"] == "RELEASED"

    store = world["store"]
    assert (
        route_module.resolve_and_verify_committed_slot_output(  # type: ignore[attr-defined]
            store,
            world["project_id"],
            route_module.compute_slot_output_id(  # type: ignore[attr-defined]
                project_id=world["project_id"], plan_ref=opened["plan_ref"], slot_index=1
            ),
        )
        is not None
    )
    # No claim is committed for a crashed attempt: no real Envelope was ever derived to name.
    assert (
        _record_kind_count(store, world["project_id"], "multi_agent_slot_attempt_envelope_claim")
        == 1
    )

    monkeypatch.undo()

    # Replay: a fresh call over the identical plan_ref reuses BOTH slots verbatim -- slot 1's own
    # crash is now a genuine terminal attempt, not a recoverable gap, so the adapter is never
    # reached again for it.
    recovering_adapter = SeededMultiAgentAdapter(candidate_fields={"summary": "ok"})
    recovered = _execute(
        world, opened["plan_ref"], iter([recovering_adapter]).__next__, "2026-09-11T01:45:00Z"
    )
    assert working_adapter.execute_call_count == 1
    assert crashing_adapter.execute_call_count == 1
    assert recovering_adapter.execute_call_count == 0
    assert len(recovered["slot_outputs"]) == 2
    assert recovered["slot_outputs"][0]["outcome"] == "CANDIDATE_ACCEPTED"
    assert recovered["slot_outputs"][1]["outcome"] == "UNAVAILABLE"
    assert all(receipt["release_status"] == "RELEASED" for receipt in recovered["release_receipts"])


def test_p19_r1_f2_a_crash_between_slot_output_derivation_and_commit_leaves_neither_record(
    tmp_path: Any, monkeypatch: Any
) -> None:
    """Structural Review Round 1, P19-R1-F2, refined by Round 3's own P19-R3-F3: reproduces the
    exact crash point the review found -- previously, the slot's own attempt output was
    committed in its own transaction *before* the release receipt was even derived, so a crash
    right there left a committed slot output with no release receipt, and every later replay
    call raised ``MultiAgentRequirementError`` forever. The slot output and release receipt are
    still committed together in one atomic transaction: injecting a crash before that single
    commit call is reached (inside the release receipt's own derivation) still leaves *neither*
    of those two records committed.

    Round 3's own P19-R3-F3 adds a durable envelope claim record, committed right after the
    real adapter call itself succeeds -- strictly *before* this test's own crash point. So this
    exact crash no longer loses the real adapter work it already paid for: recovery must resolve
    the already-committed claim, reuse its already-committed Model Execution Envelope, and reach
    the identical terminal outcome *without* invoking the adapter a second time. That is
    precisely P19-R3-F3's own required proof, ``RECOVERY_DUPLICATE_ADAPTER_CALL_COUNT=0``.
    """

    world = authorized_world(tmp_path, risk_class="LOW")
    opened = _open(world)

    real_derive = route_module.derive_multi_agent_agent_release_receipt

    def _crashing_derive(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("simulated crash before the atomic slot-complete commit")

    monkeypatch.setattr(route_module, "derive_multi_agent_agent_release_receipt", _crashing_derive)

    crashing_adapter = SeededMultiAgentAdapter(candidate_fields={"summary": "ok"})
    with pytest.raises(
        RuntimeError, match="simulated crash before the atomic slot-complete commit"
    ):
        _execute(
            world,
            opened["plan_ref"],
            lambda: crashing_adapter,
            "2026-09-11T01:30:00Z",
        )
    assert crashing_adapter.execute_call_count == 1

    store = world["store"]
    slot_output_id = route_module.compute_slot_output_id(  # type: ignore[attr-defined]
        project_id=world["project_id"], plan_ref=opened["plan_ref"], slot_index=0
    )
    assert (
        store.resolve_record(world["project_id"], "multi_agent_slot_output", slot_output_id) is None
    )
    assert _record_kind_count(store, world["project_id"], "multi_agent_agent_release_receipt") == 0
    # The real adapter call already committed its own Model Execution Envelope and this Round
    # 3 envelope claim durably -- both survive the crash, since both commit strictly before the
    # crash point this test injects.
    assert (
        _record_kind_count(store, world["project_id"], "multi_agent_slot_attempt_envelope_claim")
        == 1
    )

    monkeypatch.setattr(route_module, "derive_multi_agent_agent_release_receipt", real_derive)

    # Recovery: the envelope claim committed by the crashed attempt is resolved and reused -- the
    # adapter is never called a second time for the same slot attempt.
    recovering_adapter = SeededMultiAgentAdapter(candidate_fields={"summary": "ok"})
    recovered = _execute(
        world, opened["plan_ref"], lambda: recovering_adapter, "2026-09-11T01:45:00Z"
    )
    assert recovering_adapter.execute_call_count == 0
    assert len(recovered["slot_outputs"]) == 1
    assert recovered["slot_outputs"][0]["outcome"] == "CANDIDATE_ACCEPTED"
    assert recovered["release_receipts"][0]["release_status"] == "RELEASED"


def _record_kind_count(store: Any, project_id: str, kind: str) -> int:
    directory = store.root / "projects" / project_id / "records" / kind
    if not directory.exists():
        return 0
    return len(list(directory.glob("*.json")))


def test_release_incompleteness_blocks_aggregation_and_therefore_clean_completion(
    tmp_path: Any, monkeypatch: Any
) -> None:
    """P19-C8: a plan cannot claim clean terminal completion while any Agent's own release
    remains unaccounted for.

    Two independent gates are proved: (1) the engine itself refuses to *construct* an
    aggregation input from a non-``RELEASED`` release receipt at all (proved directly at the
    engine layer by ``test_aggregation_input_refuses_when_any_release_receipt_is_not_released``
    in the unit suite -- genuinely unreachable end to end here, since a differently-valued
    release receipt can never be committed at an already-occupied natural key, P19-C9's own
    conflicting-reuse refusal, and ``agent_runtime``'s own ``release()`` cannot itself fail);
    and (2) the Evidence hand-off *independently re-verifies* every release receipt itself
    rather than trusting the aggregation input's own history -- proved here by monkeypatching
    the one resolver it calls to honestly return a tampered, ``RELEASE_FAILED`` copy (standing
    in for a resolver bug or a future storage layer that could return one), without ever
    writing a genuinely divergent record to the real Store (which the Store's own cross-
    claimant integrity check would itself catch as corruption, a stronger and separate
    guarantee -- not the one this test targets).
    """

    world = authorized_world(tmp_path, risk_class="LOW")
    opened = _open(world)
    executed = _execute(
        world, opened["plan_ref"], lambda: SeededMultiAgentAdapter(), "2026-09-11T01:30:00Z"
    )
    release_receipt = executed["release_receipts"][0]
    assert release_receipt["release_status"] == "RELEASED"

    tampered = dict(release_receipt)
    tampered["release_status"] = "RELEASE_FAILED"

    real_resolver = route_module.resolve_and_verify_committed_release_receipt

    def _tampering_resolver(store_arg: Any, project_id_arg: str, release_receipt_id: str) -> Any:
        resolved = real_resolver(store_arg, project_id_arg, release_receipt_id)
        if (
            resolved is not None
            and resolved["multi_agent_agent_release_receipt_id"]
            == tampered["multi_agent_agent_release_receipt_id"]
        ):
            return tampered
        return resolved

    monkeypatch.setattr(
        route_module, "resolve_and_verify_committed_release_receipt", _tampering_resolver
    )

    from tests.fixtures.multi_agent_world import evidence_request_for

    from manosube_agent_civilization.multi_agent import route_orchestration_to_evidence
    from manosube_agent_civilization.multi_agent.errors import MultiAgentReleaseIncompleteError

    coordinator = _coordinator(world)
    with pytest.raises(MultiAgentReleaseIncompleteError):
        route_orchestration_to_evidence(
            world["store"],
            coordinator,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            plan_ref=opened["plan_ref"],
            evidence_request_template=evidence_request_for(world["project_id"], provenance=None),
            completed_at="2026-09-11T01:40:00Z",
        )
    coordinator.release()


def test_p19_r3_f4_a_genuinely_hanging_adapter_is_bounded_by_the_plans_own_real_timeout(
    tmp_path: Any,
) -> None:
    """Structural Review Round 3, P19-R3-F4's own required proof: a genuinely hanging adapter
    (a real ``time.sleep()`` far longer than the plan's own ``per_slot_timeout_seconds``, never
    a simulated timeout) is bounded by this package's own real, runtime-enforced per-slot call
    budget. The call returns promptly -- long before the adapter itself ever would -- with a
    typed ``TIMEOUT`` outcome, no Envelope reference, and a release receipt that still resolves
    to ``RELEASED`` (the constructed slot Agent is never leaked even though its own adapter call
    never returned in time).
    """

    import time

    world = authorized_world(tmp_path, risk_class="LOW")

    # A same-shaped baseline call (identical plan/world setup, an ordinary fast adapter) first,
    # to measure this environment's own real Store I/O overhead for one full execute call --
    # this file-backed Store's own commit latency varies by host, so the decisive comparison
    # below is relative to that measured baseline, never a hardcoded absolute wall-clock bound.
    baseline_coordinator = _coordinator(world)
    baseline_opened = open_dynamic_execution_plan(
        world["store"], baseline_coordinator, **open_plan_kwargs(world)
    )
    baseline_coordinator.release()
    baseline_started_at = time.monotonic()
    _execute(
        world,
        baseline_opened["plan_ref"],
        lambda: SeededMultiAgentAdapter(candidate_fields={"summary": "ok"}),
        "2026-09-11T01:15:00Z",
    )
    baseline_elapsed = time.monotonic() - baseline_started_at

    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(
        world["store"],
        coordinator,
        **open_plan_kwargs(world),
        per_slot_timeout_seconds=1,
    )
    coordinator.release()
    assert opened["plan"]["execution_bounds"]["per_slot_timeout_seconds"] == 1

    sleep_seconds = 20.0
    hanging_adapter = HangingMultiAgentAdapter(sleep_seconds=sleep_seconds)
    started_at = time.monotonic()
    executed = _execute(world, opened["plan_ref"], lambda: hanging_adapter, "2026-09-11T01:30:00Z")
    elapsed = time.monotonic() - started_at

    # HANGING_ADAPTER_BOUNDED_TERMINATION=true: this call returned within a small, environment-
    # scaled margin over the baseline call's own overhead plus the plan's own 1-second bound --
    # nowhere near the adapter's own real 20-second sleep, which this assertion would fail hard
    # against if the bounded call had actually waited for it.
    assert elapsed < baseline_elapsed + 10.0
    assert elapsed < sleep_seconds
    assert hanging_adapter.execute_call_count == 1

    # TIMEOUT_OR_CANCELLATION_TYPED_OUTCOME=true, DEADLINE_CROSSED_DURING_EXECUTION_CLEAN_
    # SUCCESS=false: a typed TIMEOUT outcome, never a fabricated success, and no Envelope this
    # attempt could ever truthfully name.
    slot_output = executed["slot_outputs"][0]
    assert slot_output["outcome"] == "TIMEOUT"
    assert slot_output["result_fingerprint"] is None
    assert slot_output["model_execution_envelope_ref"] is None

    # TIMEOUT_OR_CANCELLATION_RELEASE_RECEIPT_RESOLVES=true: the constructed slot Agent this
    # attempt built is still accounted for as released, never left open just because its own
    # adapter call ran past the bound.
    release_receipt = executed["release_receipts"][0]
    assert release_receipt["release_status"] == "RELEASED"


def test_p19_r4_f1_a_late_returning_adapter_call_never_commits_after_this_call_gave_up(
    tmp_path: Any,
) -> None:
    """Structural Review Round 4, P19-R4-F1's own required proof.

    ``executor.shutdown(wait=False)`` never stops or kills the abandoned background thread --
    it only stops this call's own waiting on it -- so a genuinely late-returning adapter call
    could, before this fix, still go on to commit a real Envelope and attempt-claim well after
    this function had already given up and recorded a typed ``TIMEOUT`` outcome. This proof lets
    that abandoned worker actually finish (a real wait past its own sleep duration, never a
    mock or a monkeypatched clock), then inspects the Store directly and proves every late write
    that attempt could have made is durably absent: no committed attempt-claim exists under this
    attempt's own deterministic claim key, and the Store's own committed State revision -- which
    only ever advances via a real commit -- is unchanged from immediately after the bounded call
    itself already returned.
    """

    import time

    from manosube_agent_civilization.multi_agent.route import (
        compute_slot_attempt_envelope_claim_id,
        resolve_and_verify_committed_slot_attempt_envelope_claim,
    )

    world = authorized_world(tmp_path, risk_class="LOW")

    coordinator = _coordinator(world)
    opened = open_dynamic_execution_plan(
        world["store"],
        coordinator,
        **open_plan_kwargs(world),
        per_slot_timeout_seconds=1,
    )
    coordinator.release()

    sleep_seconds = 3.0
    hanging_adapter = HangingMultiAgentAdapter(sleep_seconds=sleep_seconds)
    executed = _execute(world, opened["plan_ref"], lambda: hanging_adapter, "2026-09-11T01:30:00Z")

    slot_output = executed["slot_outputs"][0]
    assert slot_output["outcome"] == "TIMEOUT"
    assert slot_output["model_execution_envelope_ref"] is None

    claim_key = compute_slot_attempt_envelope_claim_id(
        project_id=world["project_id"], plan_ref=dict(opened["plan_ref"]), slot_index=0
    )
    assert (
        resolve_and_verify_committed_slot_attempt_envelope_claim(
            world["store"], world["project_id"], claim_key
        )
        is None
    )
    state_revision_immediately_after_timeout = world["store"].load_current(world["project_id"])[
        "state_revision"
    ]

    # A real wait, strictly longer than the hanging adapter's own real sleep, for the abandoned
    # background worker to actually finish and reach this route's own cancellation check.
    time.sleep(sleep_seconds + 5.0)
    assert hanging_adapter.execute_call_count == 1

    # LATE_WRITE_COUNT=0: neither the attempt-claim nor any State-revision advance exists after
    # the abandoned worker's own real completion -- this call's own typed TIMEOUT, recorded
    # while the caller had already moved on, was never silently overwritten by a late success.
    assert (
        resolve_and_verify_committed_slot_attempt_envelope_claim(
            world["store"], world["project_id"], claim_key
        )
        is None
    )
    assert (
        world["store"].load_current(world["project_id"])["state_revision"]
        == state_revision_immediately_after_timeout
    )


def test_p19_r5_f1_the_worker_already_won_the_gate_is_never_overridden_by_a_false_timeout(
    tmp_path: Any, monkeypatch: Any
) -> None:
    """Structural Review Round 5, P19-R5-F1's own required decisive test: pause the worker
    thread *after* it has already won this attempt's own terminal-decision gate (its own real
    adapter call already succeeded, and its own ``cancellation_check`` already observed it is
    the winner) but strictly *before* the physical Envelope+claim commit, then let the plan's
    own real ``per_slot_timeout_seconds`` genuinely elapse while it stays paused there. Round
    4's own design would have let the coordinator declare a contradictory TIMEOUT right there
    (the worker's own earlier, independent ``cancellation_check()`` call could not know the
    coordinator was about to give up); this test proves that no longer happens -- the
    coordinator's own bounded wait times out, but it recognizes the gate is already won and
    blocks for the worker's own real, already-decided result instead of publishing a false
    terminal fact for an attempt that actually completed. The pause point is a real
    synchronization barrier (:class:`threading.Event`), never a sleep-based race -- this
    ordering is structural under every interleaving, not a fluke of timing, and this is proved
    by repeating the identical deterministic scenario several times, each against its own fresh
    plan.
    """

    import threading
    import time

    world = authorized_world(tmp_path, risk_class="LOW")

    # A same-shaped baseline call (identical plan/world setup, an ordinary fast adapter, no
    # pausing) first, to measure this environment's own real Store I/O + adapter-call overhead
    # for one full, un-paused attempt -- this file-backed Store's own commit latency varies by
    # host, so this decisive test's own per_slot_timeout_seconds below is set relative to that
    # measured baseline, never a hardcoded absolute wall-clock bound. Too tight a bound here would
    # let the coordinator's own bounded wait race the worker to its *own* cancellation_check call
    # (a different, already-proven race) instead of the one this test exists to prove: the
    # coordinator's timeout firing *after* the worker already won the gate.
    baseline_coordinator = _coordinator(world)
    baseline_opened = open_dynamic_execution_plan(
        world["store"], baseline_coordinator, **open_plan_kwargs(world)
    )
    baseline_coordinator.release()
    baseline_started_at = time.monotonic()
    _execute(
        world,
        baseline_opened["plan_ref"],
        lambda: SeededMultiAgentAdapter(candidate_fields={"summary": "baseline"}),
        "2026-09-11T01:10:00Z",
    )
    baseline_elapsed = time.monotonic() - baseline_started_at
    # Canonical State's own v0.1 encoding admits only a whole number of seconds here (Structural
    # Review Round 3, P19-R3-F4) -- rounded up, never truncated down below the measured margin.
    per_slot_timeout_seconds = int(max(5.0, baseline_elapsed * 5.0 + 5.0)) + 1

    for iteration in range(3):
        coordinator = _coordinator(world)
        opened = open_dynamic_execution_plan(
            world["store"],
            coordinator,
            **open_plan_kwargs(world),
            per_slot_timeout_seconds=per_slot_timeout_seconds,
        )
        coordinator.release()

        reached_commit = threading.Event()
        release_commit = threading.Event()
        real_commit = model_runtime_route_module._commit

        # Every loop-scoped name this closure reads is bound as its own default argument
        # (evaluated once, immediately, at this exact iteration's own function-definition point)
        # rather than read from the enclosing loop's own rebindable variable -- this is a real
        # concurrency proof, so it must never depend on which iteration's own name a late call
        # happens to still see.
        def _pausing_commit(
            *args: Any,
            _reached_commit: threading.Event = reached_commit,
            _release_commit: threading.Event = release_commit,
            _real_commit: Any = real_commit,
            **kwargs: Any,
        ) -> Any:
            _reached_commit.set()
            # A real synchronization barrier, not a sleep: this call blocks here,
            # deterministically, until the test itself releases it -- well past the plan's own
            # per_slot_timeout_seconds, guaranteeing the coordinator's own bounded wait times out
            # while this attempt already holds the gate, every single time this runs.
            _release_commit.wait(timeout=60)
            return _real_commit(*args, **kwargs)

        monkeypatch.setattr(model_runtime_route_module, "_commit", _pausing_commit)

        adapter = SeededMultiAgentAdapter(
            candidate_fields={"summary": f"worker-wins-the-race-{iteration}"}
        )
        result_holder: dict[str, Any] = {}

        def _run(
            _opened: dict[str, Any] = opened,
            _adapter: Any = adapter,
            _result_holder: dict[str, Any] = result_holder,
        ) -> None:
            _result_holder["executed"] = _execute(
                world, _opened["plan_ref"], lambda: _adapter, "2026-09-11T01:30:00Z"
            )

        runner = threading.Thread(target=_run)
        runner.start()
        assert reached_commit.wait(timeout=per_slot_timeout_seconds + 30.0), (
            "worker never reached its own pre-commit checkpoint"
        )
        # The worker is now paused holding the gate -- it already passed cancellation_check --
        # strictly after its own real adapter call already succeeded. Let the plan's own real
        # per_slot_timeout_seconds genuinely elapse while it stays paused right there.
        time.sleep(per_slot_timeout_seconds + 2.0)
        release_commit.set()
        runner.join(timeout=30)
        assert not runner.is_alive()

        monkeypatch.setattr(model_runtime_route_module, "_commit", real_commit)

        executed = result_holder["executed"]
        slot_output = executed["slot_outputs"][0]
        # CHECK_TO_COMMIT_RACE_TERMINAL_WINNER_COUNT=1: the worker's own already-won commit is
        # what this attempt's own terminal outcome reflects -- never a contradictory TIMEOUT,
        # even though the coordinator's own bounded wait for this slot genuinely elapsed while
        # the worker was paused holding the gate.
        assert slot_output["outcome"] == "CANDIDATE_ACCEPTED"
        assert slot_output["model_execution_envelope_ref"] is not None
        assert executed["release_receipts"][0]["release_status"] == "RELEASED"


def test_p19_r6_f1_a_post_commit_acknowledgement_loss_never_publishes_a_false_unavailable(
    tmp_path: Any, monkeypatch: Any
) -> None:
    """Structural Review Round 6, P19-R6-F1's own required decisive test: the exact-head
    counterexample the adoption reproduced was an exception surfacing from
    ``execute_model_work_unit`` strictly *after* its own atomic Envelope+claim commit already
    succeeded -- an acknowledgement-loss between that real commit and this coordinator thread
    observing its return value, never a failure of the adapter or the commit itself. Round 5's
    own broad ``except Exception`` (P19-R4-F2) had no way to distinguish that case from a
    genuine pre-commit failure, so it published a durable ``UNAVAILABLE`` slot output over a
    real, already-committed ``CANDIDATE_ACCEPTED`` Envelope.

    This test injects exactly that: ``execute_model_work_unit`` itself is wrapped so it still
    performs its own real call (the real Envelope+claim commit genuinely happens) but then
    raises before returning to its caller. The fix must recover the real terminal outcome from
    the durably committed claim/Envelope pair -- never publish ``UNAVAILABLE`` -- and a
    subsequent replay call must make zero further adapter calls.
    """

    world = authorized_world(tmp_path, risk_class="LOW")
    opened = _open(world)

    real_execute_model_work_unit = route_module.execute_model_work_unit  # type: ignore[attr-defined]

    def _ack_losing_execute_model_work_unit(*args: Any, **kwargs: Any) -> Any:
        # The real call still runs to completion -- its own atomic Envelope+claim commit
        # genuinely succeeds -- before this wrapper discards its return value and raises,
        # simulating the caller never receiving the acknowledgement of that already-durable
        # commit.
        real_execute_model_work_unit(*args, **kwargs)
        raise RuntimeError("simulated acknowledgement loss after the real commit already succeeded")

    monkeypatch.setattr(
        route_module, "execute_model_work_unit", _ack_losing_execute_model_work_unit
    )

    adapter = SeededMultiAgentAdapter(candidate_fields={"summary": "ack-loss-survives"})
    executed = _execute(world, opened["plan_ref"], lambda: adapter, "2026-09-11T01:30:00Z")

    monkeypatch.setattr(route_module, "execute_model_work_unit", real_execute_model_work_unit)

    # POST_COMMIT_ACK_LOSS_REAL_ENVELOPE_COUNT=1 / POST_COMMIT_ACK_LOSS_REAL_CLAIM_COUNT=1: the
    # real adapter call happened exactly once, and its own real Envelope+claim genuinely
    # committed durably despite the exception this coordinator observed afterward.
    assert adapter.execute_call_count == 1
    assert _record_kind_count(world["store"], world["project_id"], "model_execution_envelope") == 1
    assert (
        _record_kind_count(
            world["store"], world["project_id"], "multi_agent_slot_attempt_envelope_claim"
        )
        == 1
    )

    # POST_COMMIT_ACK_LOSS_PUBLISHED_UNAVAILABLE_COUNT=0 /
    # RECONSTRUCTED_SLOT_OUTCOME_EQUALS_ENVELOPE_OUTCOME=true: the published slot output is the
    # real, durably committed outcome -- never a contradictory UNAVAILABLE fallback -- and it
    # names the real committed Envelope.
    slot_output = executed["slot_outputs"][0]
    assert slot_output["outcome"] == "CANDIDATE_ACCEPTED"
    assert slot_output["model_execution_envelope_ref"] is not None

    # TERMINAL_FACT_COUNT_EXACTLY_ONE=true: exactly one slot output and one release receipt
    # exist for this attempt -- the recovery path derived a single terminal fact, not a second
    # one alongside some other record this exception might otherwise have left behind.
    assert _record_kind_count(world["store"], world["project_id"], "multi_agent_slot_output") == 1
    assert executed["release_receipts"][0]["release_status"] == "RELEASED"

    # REPLAY_DUPLICATE_ADAPTER_CALL_COUNT=0: a fresh call over the identical plan_ref reuses the
    # already-committed slot output verbatim -- the adapter is never reached again.
    def _forbidden_factory() -> Any:
        raise AssertionError("adapter_factory must not be called on a genuine replay")

    replayed = _execute(world, opened["plan_ref"], _forbidden_factory, "2026-09-11T01:45:00Z")
    assert (
        replayed["slot_outputs"][0]["multi_agent_slot_output_id"]
        == slot_output["multi_agent_slot_output_id"]
    )
    assert adapter.execute_call_count == 1
