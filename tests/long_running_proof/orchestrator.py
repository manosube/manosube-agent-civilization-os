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

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from tests.fixtures import long_running_proof as lrp

from . import agent_swap, cycle, metrics, runtime_reachability, session_loss

#: Session-loss real process-boundary restarts are injected after these 0-indexed cycle
#: numbers complete (clamped to the actual tier length) -- at least 2 distinct positions for
#: any tier >= 4, spread across the run rather than clustered at one point.
SESSION_LOSS_BOUNDARY_FRACTIONS = (0.25, 0.5, 0.75)


def _cycle_clock(k: int) -> tuple[str, str]:
    """Deterministic, monotonically advancing wall-clock stand-ins for cycle *k*'s own
    ``started_at``/``closed_at`` raw-event timestamps -- fixture-owned, not a real time.Time()
    read, so the metric dataset stays reproducible run to run."""

    base = datetime(2026, 9, 15, 15, 0, 0, tzinfo=UTC) + timedelta(minutes=2 * k)
    started = base.strftime("%Y-%m-%dT%H:%M:%SZ")
    closed = (base + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return started, closed


def run_sequential_differences(
    store: Any, *, tier: int, session_loss_boundaries: set[int] | None = None
) -> dict[str, Any]:
    """Run cycles ``0..tier-1`` sequentially against *store*, injecting a real process-boundary
    restart after each cycle index named in *session_loss_boundaries* (default: computed from
    :data:`SESSION_LOSS_BOUNDARY_FRACTIONS`). Returns the raw events produced and the final
    committed State."""

    if session_loss_boundaries is None:
        session_loss_boundaries = {
            min(tier - 1, max(0, int(tier * f) - 1)) for f in SESSION_LOSS_BOUNDARY_FRACTIONS if tier * f >= 1
        }

    raw_events: list[dict[str, Any]] = []
    committed_state = cycle.initialize_genesis(store)

    for k in range(tier):
        started_at, closed_at = _cycle_clock(k)
        result = cycle.run_one_cycle(store, k=k, committed_state=committed_state)
        committed_state = result["reflow_result"]["committed_state"]
        raw_events.append(
            metrics.cycle_committed_event(
                k=k,
                difference_id=result["identity"]["difference_id"],
                state_revision=result["identity"]["final_state_revision"],
                evidence_item_count=2,
                evidence_required_count=2,
                started_at=started_at,
                closed_at=closed_at,
            )
        )

        if k in session_loss_boundaries and k < tier - 1:
            pre_revision = committed_state["state_revision"]
            reconstructed = session_loss.restart_and_reconstruct_state(store.root, lrp.PROJECT_ID)
            recovered = reconstructed["state_revision"] == pre_revision
            raw_events.append(
                metrics.session_loss_boundary_event(
                    after_cycle=k,
                    pre_restart_revision=pre_revision,
                    post_restart_revision=reconstructed["state_revision"],
                    recovered=recovered,
                )
            )
            if not recovered:
                raise AssertionError(
                    f"session-loss boundary after cycle {k}: real process restart reconstructed "
                    f"revision {reconstructed['state_revision']!r}, expected {pre_revision!r}"
                )
            # The next cycle resumes from the subprocess's own reconstruction alone -- never
            # from any object the parent process still happens to hold.
            committed_state = reconstructed

    return {"raw_events": raw_events, "final_committed_state": committed_state}


def run_agent_swap_slice(tmp_path: Path, *, project_id: str) -> list[dict[str, Any]]:
    world = agent_swap.build_agent_swap_world(tmp_path, project_id=project_id)
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


def run_runtime_reachability_slice(tmp_path: Path) -> list[dict[str, Any]]:
    world = runtime_reachability.build_runtime_reachability_world(tmp_path)
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
    identity swap slice, and one runtime-reachability measurement slice, then deterministically
    aggregate every raw event into the required metric dataset.

    ``tier`` must be one of the four required values (10, 30, 50, 100) for a genuine Gate 20
    run; smaller values are accepted for fast, non-Gate-20 smoke verification only."""

    store = cycle.build_store(tmp_path / "sequential_differences")
    sequential = run_sequential_differences(store, tier=tier)

    raw_events: list[dict[str, Any]] = list(sequential["raw_events"])
    raw_events += run_agent_swap_slice(tmp_path, project_id=f"PRJ-P20-SWAP-{tier:04d}")
    raw_events += run_runtime_reachability_slice(tmp_path)

    return {
        "tier": tier,
        "raw_events": raw_events,
        "final_committed_state": sequential["final_committed_state"],
        "metrics": metrics.aggregate(raw_events),
        "store_root": str(store.root),
    }
