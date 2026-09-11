"""Phase 19 (Issue #77) V6: replay/concurrency/crash/release matrix.

Exact replay, conflicting replay, duplicate coordinator, partial execution, coordinator
crash, release visibility, recovery, and no leaked Agent.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.fixtures.multi_agent_world import (
    CrashingMultiAgentAdapter,
    SeededMultiAgentAdapter,
    authorized_world,
    open_plan_kwargs,
)

from manosube_agent_civilization.agent_runtime import TemporaryAgent, start_temporary_agent
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

    with pytest.raises(RuntimeError, match="simulated coordinator/infrastructure crash"):
        _execute(world, opened["plan_ref"], lambda: next(factory_calls), "2026-09-11T01:30:00Z")

    # Slot 0 completed and was released before the crash on slot 1; slot 1's own Agent (the
    # freshness-check helper aside) was also released in its own finally even though the
    # exception then propagated out of the whole call.
    assert counters["constructed"] == counters["released"]
    assert counters["constructed"] >= 2

    store = world["store"]
    slot0_output = store.resolve_record(
        world["project_id"],
        "multi_agent_slot_output",
        route_module.compute_slot_output_id(  # type: ignore[attr-defined]
            project_id=world["project_id"], plan_ref=opened["plan_ref"], slot_index=0
        ),
    )
    assert slot0_output is not None
    assert slot0_output["outcome"] == "CANDIDATE_ACCEPTED"
    slot1_output = store.resolve_record(
        world["project_id"],
        "multi_agent_slot_output",
        route_module.compute_slot_output_id(  # type: ignore[attr-defined]
            project_id=world["project_id"], plan_ref=opened["plan_ref"], slot_index=1
        ),
    )
    assert slot1_output is None  # the crash happened before slot 1's own attempt was committed

    monkeypatch.undo()

    # Recovery: a fresh call over the identical plan_ref reuses slot 0 untouched (no second
    # adapter call) and completes slot 1 fresh.
    recovering_adapter = SeededMultiAgentAdapter(candidate_fields={"summary": "ok"})
    recovered = _execute(
        world, opened["plan_ref"], iter([recovering_adapter]).__next__, "2026-09-11T01:45:00Z"
    )
    assert working_adapter.execute_call_count == 1
    assert recovering_adapter.execute_call_count == 1
    assert len(recovered["slot_outputs"]) == 2
    assert all(so["outcome"] == "CANDIDATE_ACCEPTED" for so in recovered["slot_outputs"])
    assert all(receipt["release_status"] == "RELEASED" for receipt in recovered["release_receipts"])
    assert recovered["aggregation_input"]["unresolved_capabilities"] == []


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

    import manosube_agent_civilization.multi_agent.evidence_handoff as evidence_handoff_module

    real_resolver = (
        evidence_handoff_module.resolve_and_verify_committed_release_receipt  # type: ignore[attr-defined]
    )

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
        evidence_handoff_module, "resolve_and_verify_committed_release_receipt", _tampering_resolver
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
