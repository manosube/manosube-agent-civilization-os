"""Phase 20 -- the top-level long-running proof orchestrator (Issue #86).

Composes the four proven mechanisms (:mod:`tests.long_running_proof.cycle`,
:mod:`tests.long_running_proof.session_loss`, :mod:`tests.long_running_proof.agent_swap`,
:mod:`tests.long_running_proof.runtime_reachability`) into one run, parametrized only by
*tier* -- the exact same deterministic corpus (:mod:`tests.fixtures.long_running_proof`) sliced
to its first *tier* entries, so T10/T30/T50/T100 are literal prefixes of one corpus by
construction, never four independently generated or shuffled runs
(``TIER_PREFIX_RELATION_REQUIRED=true``).

This module owns no Canonical State, Authority, Evidence, Reflow, or Completion decision of its
own (``HARNESS_OWNS_CANONICAL_STATE=false`` et al., Issue #86 section 11) -- it only calls the
existing natural-route modules above, in order, and records what happened as raw events for
:mod:`tests.long_running_proof.metrics` to aggregate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tests.fixtures import long_running_proof as lrp

from manosube_agent_civilization.reflow.errors import StaleReflowError
from manosube_agent_civilization.work_time_transparency.adapters import (
    ProgressReporter,
    verify_joined_coordination,
    with_work_time_coordination,
)

from . import agent_swap, crash_worker, cycle, metrics, runtime_reachability, session_loss

#: The one Work-Time Transparency adapter_kind SHUKOU's P87-R1-F7 correction authorized
#: (``types.py``/schema both amended) for this exact production long-running-proof entrypoint.
ADAPTER_KIND = "LONG_RUNNING_PROOF"
WORK_UNIT_REF_KIND = "long_running_proof_run"

#: A real, genuine mid-cycle crash-and-recover (P87-R1-F1/F2, :mod:`tests.long_running_proof.
#: crash_worker`) is injected -- in place of that cycle's own normal :func:`attempt_cycle` --
#: at these 0-indexed cycle positions (clamped to the actual tier length), one position per
#: :data:`crash_worker.BOUNDARIES` member, round-robin, so a Gate 20 tier run exercises every
#: one of the four named boundaries at least once, spread across the run rather than clustered
#: at one point.
SESSION_LOSS_BOUNDARY_FRACTIONS = (0.2, 0.4, 0.6, 0.8)


def _observed_now() -> str:
    """The one real wall-clock read this proof's own metric dataset uses for cycle
    ``started_at``/``closed_at`` (P87-R1-F9) -- genuinely non-deterministic observation time,
    deliberately never the corpus's own deterministic identity (``predicate_id``/``subject``/
    ``REFLOW_INSTANT``, all of which stay fixed regardless of how long a cycle actually took,
    including any real failure/restart/retry time a session-loss boundary injected)."""

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def attempt_cycle(store: Any, *, k: int, committed_state: dict[str, Any]) -> dict[str, Any]:
    """Run cycle *k* through the real orchestrated route, returning a real, durable raw event
    either way (P87-R1-F3): a ``cycle_committed`` event on success, or -- if
    :func:`~tests.long_running_proof.cycle.run_one_cycle` itself refuses (a real
    :class:`~tests.long_running_proof.cycle.CorpusPositionError` or Reflow's own
    ``StaleReflowError``) -- a real ``cycle_refused`` event captured from that actual refusal,
    never a synthetic dict a caller hand-authors after the fact. *committed_state* is returned
    unchanged on refusal (``NO_STATE_ADVANCE_ON_ORDERING_REFUSAL=true``)."""

    started_at = _observed_now()
    try:
        result = cycle.run_one_cycle(store, k=k, committed_state=committed_state)
    except (cycle.CorpusPositionError, StaleReflowError) as exc:
        return {
            "outcome": "refused",
            "event": metrics.cycle_refused_event(k=k, reason=str(exc), started_at=started_at),
            "committed_state": committed_state,
        }
    closed_at = _observed_now()
    return {
        "outcome": "committed",
        "event": metrics.cycle_committed_event(
            k=k,
            difference_id=result["identity"]["difference_id"],
            state_revision=result["identity"]["final_state_revision"],
            evidence_item_count=2,
            evidence_required_count=2,
            started_at=started_at,
            closed_at=closed_at,
        ),
        "committed_state": result["reflow_result"]["committed_state"],
        "result": result,
    }


def run_agent_swap_slice(
    store: Any, *, project_id: str, project_binding_id: str, transaction_prefix: str
) -> list[dict[str, Any]]:
    world = agent_swap.build_agent_swap_world(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        human_authority_ref=lrp.HUMAN_AUTHORITY,
        transaction_prefix=transaction_prefix,
    )
    result = agent_swap.run_agent_swap_sequence(world)
    raw_events: list[dict[str, Any]] = []
    for i, receipt in enumerate(result["swap_receipts"]):
        raw_events.append(
            metrics.agent_swap_event(
                swap_index=i,
                predecessor_identity=dict(receipt["predecessor_adapter_identity"]),
                successor_identity=dict(receipt["successor_adapter_identity"]),
                succeeded=True,
            )
        )
    if result["swap_count"] < 3 or result["distinct_identity_count"] < 2:
        raise AssertionError(
            f"agent-swap slice under-delivered: swap_count={result['swap_count']} "
            f"distinct_identity_count={result['distinct_identity_count']}"
        )
    return raw_events


def run_runtime_reachability_slice(
    store: Any, *, project_id: str, project_binding_id: str
) -> list[dict[str, Any]]:
    world = runtime_reachability.build_runtime_reachability_world(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        human_authority_ref=lrp.HUMAN_AUTHORITY,
    )
    measurements = runtime_reachability.run_reachability_measurements(world)
    return [
        metrics.runtime_observation_event(
            classification=m["classification"], transport_outcome=m["transport_outcome"]
        )
        for m in measurements
    ]


def run_long_running_proof(tmp_path: Path, *, tier: int) -> dict[str, Any]:
    """The one Gate 20 proof entry point: run *tier* sequential Differences (with real
    process-boundary session-loss recovery injected along the way), one real agent/runtime-
    identity swap slice, and one runtime-reachability measurement slice -- all three bound into
    the exact same Store/``project_id``/``project_binding_id`` and interleaved at declared
    positions within the tier run (P87-R1-F4), the whole run WTT-coordinated under one real
    ``LONG_RUNNING_PROOF`` work unit (P87-R1-F7) -- then deterministically aggregate every raw
    event into the required metric dataset.

    ``tier`` must be one of the four required values (10, 30, 50, 100) for a genuine Gate 20
    run; smaller values are accepted for fast, non-Gate-20 smoke verification only."""

    store = cycle.build_store(tmp_path / "sequential_differences")
    bind_result = cycle.bind_genesis(store)
    project_binding_id = bind_result["project_binding_id"]

    #: Declared interleave positions within the tier run: the Agent-swap slice runs after the
    #: cycle at roughly 1/3 through, the runtime-reachability slice after roughly 2/3 through --
    #: both genuinely inside the same sequential run, sharing its own advancing state_revision,
    #: never a separate post-hoc call against an unrelated store.
    swap_after_cycle = max(0, tier // 3 - 1)
    runtime_after_cycle = max(swap_after_cycle + 1, (2 * tier) // 3 - 1)

    work_unit_ref = {"kind": WORK_UNIT_REF_KIND, "id": f"WORK-UNIT-LRP-T{tier:04d}"}

    def _perform(reporter: ProgressReporter) -> dict[str, Any]:
        verify_joined_coordination(
            store,
            reporter,
            project_id=lrp.PROJECT_ID,
            project_binding_id=project_binding_id,
            expected_adapter_kind=ADAPTER_KIND,
            expected_work_unit_ref=work_unit_ref,
        )

        boundary_positions = sorted(
            {
                min(tier - 1, max(0, int(tier * f) - 1))
                for f in SESSION_LOSS_BOUNDARY_FRACTIONS
                if tier * f >= 1
            }
        )
        boundary_for_position = {
            pos: crash_worker.BOUNDARIES[i % len(crash_worker.BOUNDARIES)]
            for i, pos in enumerate(boundary_positions)
        }

        raw_events: list[dict[str, Any]] = []
        committed_state = bind_result["committed_state"]

        for k in range(tier):
            if k in boundary_for_position:
                boundary = boundary_for_position[k]
                pre_revision = committed_state["state_revision"]
                started_at = _observed_now()
                crash_result = session_loss.crash_mid_cycle_and_recover(
                    store.root, project_id=lrp.PROJECT_ID, k=k, boundary=boundary
                )
                closed_at = _observed_now()
                committed_state = crash_result["committed_state"]
                identity = crash_result["identity"]
                raw_events.append(
                    metrics.session_loss_boundary_event(
                        after_cycle=k,
                        boundary=boundary,
                        pre_restart_revision=pre_revision,
                        post_restart_revision=committed_state["state_revision"],
                        recovered=True,
                    )
                )
                raw_events.append(
                    metrics.cycle_committed_event(
                        k=k,
                        difference_id=identity["difference_id"],
                        state_revision=identity["final_state_revision"],
                        evidence_item_count=2,
                        evidence_required_count=2,
                        started_at=started_at,
                        closed_at=closed_at,
                    )
                )
            else:
                attempt = attempt_cycle(store, k=k, committed_state=committed_state)
                raw_events.append(attempt["event"])
                if attempt["outcome"] == "refused":
                    raise AssertionError(
                        f"cycle {k}: real orchestrated route refused during the positive "
                        f"Gate 20 route -- {attempt['event']['reason']}"
                    )
                committed_state = attempt["committed_state"]

            if k == swap_after_cycle:
                raw_events += run_agent_swap_slice(
                    store,
                    project_id=lrp.PROJECT_ID,
                    project_binding_id=project_binding_id,
                    transaction_prefix=f"TX-LRP-T{tier:04d}-SWAP",
                )
                reporter.report(
                    position_kind="WORK_RUNNING",
                    current_position=f"agent-swap slice complete after cycle {k}",
                    next_progress_update_due_minutes=10,
                    remaining_duration_unknown=True,
                )
                committed_state = store.load_current(lrp.PROJECT_ID)

            if k == runtime_after_cycle:
                raw_events += run_runtime_reachability_slice(
                    store, project_id=lrp.PROJECT_ID, project_binding_id=project_binding_id
                )
                reporter.report(
                    position_kind="WORK_RUNNING",
                    current_position=f"runtime-reachability slice complete after cycle {k}",
                    next_progress_update_due_minutes=10,
                    remaining_duration_unknown=True,
                )
                committed_state = store.load_current(lrp.PROJECT_ID)

        return {"raw_events": raw_events, "final_committed_state": committed_state}

    _open_record, _terminal_record, sequential = with_work_time_coordination(
        store,
        project_id=lrp.PROJECT_ID,
        project_binding_id=project_binding_id,
        adapter_kind=ADAPTER_KIND,
        work_unit_ref=work_unit_ref,
        estimated_duration_lower_minutes=5,
        estimated_duration_upper_minutes=60,
        estimate_confidence="LOW",
        major_steps=[
            "sequential difference cycles",
            "agent-swap slice",
            "runtime-reachability slice",
            "session-loss recovery boundaries",
        ],
        next_progress_update_due_minutes=10,
        variability_factors="tier size, crash-injection retry rounds",
        perform=_perform,
    )

    raw_events = sequential["raw_events"]

    return {
        "tier": tier,
        "raw_events": raw_events,
        "final_committed_state": sequential["final_committed_state"],
        "metrics": metrics.aggregate(raw_events),
        "store_root": str(store.root),
        "project_binding_id": project_binding_id,
    }
