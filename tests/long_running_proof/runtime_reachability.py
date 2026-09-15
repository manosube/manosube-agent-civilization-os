"""Phase 20 -- runtime reachability observation (Issue #86 section 8).

Reuses the existing, already-accepted Runtime Observation Contract (``10_RUNTIME``) exactly as
it stands: :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` against
the fixture/local controlled ``FakeRuntimeAdapter``, never a new production provider or
credential (Issue #86's own Boundary). Runtime reachability is measured, never assumed: this
module distinguishes ``REACHABLE`` (the adapter's own transport-level ``OBSERVED`` outcome),
``UNREACHABLE`` (a real transport failure the adapter honestly reports -- ``TIMEOUT``/
``UNAVAILABLE``), and ``UNKNOWN`` (no target was ever seeded -- the adapter's own honest
``NOT_FOUND``, meaning "no observation was ever made", not "observed absent") as three
genuinely distinct, never-conflated outcomes (``UNREACHABLE_AND_UNKNOWN_RETAINED=true``).

This module never wraps its own calls in ``with_work_time_coordination``: the Work-Time
Transparency ``adapter_kind`` enum is closed at 8 members and does not include Runtime
Observation (confirmed by direct inspection of ``work_time_transparency/types.py`` --
``ADAPTER_KINDS`` has no ``RUNTIME`` entry, and ``observe_runtime_target`` itself never imports
``work_time_transparency``). Minting a new coordination kind, or reusing an unrelated one, would
either require a real Kernel schema/enum change this Issue does not authorize, or would be a
caller lying about what kind of work opened -- so runtime reachability is measured here as
un-coordinated, harness-owned diagnostic scaffolding only, exactly as the Issue's own Boundary
permits ("the harness may orchestrate and measure only").
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.fixtures.runtime_world import bound, boundary_for, commit_target_identity

from manosube_agent_civilization.runtime.adapter import FakeRuntimeAdapter
from manosube_agent_civilization.runtime.route import observe_runtime_target

REACHABLE = "REACHABLE"
UNREACHABLE = "UNREACHABLE"
UNKNOWN = "UNKNOWN"

_OUTCOME_TO_CLASSIFICATION = {
    "OBSERVED": REACHABLE,
    "TIMEOUT": UNREACHABLE,
    "UNAVAILABLE": UNREACHABLE,
    "NOT_FOUND": UNKNOWN,
}


def build_runtime_reachability_world(tmp_path: Path) -> dict[str, Any]:
    """One real, genuinely bound Project plus a real, committed, signed
    ``runtime_deployment_declaration`` anchoring one target -- everything
    ``observe_runtime_target`` needs, reusing the existing V1-V5 Runtime fixture world exactly
    as its own suites already do."""

    store, ctx = bound(tmp_path)
    target_identity = commit_target_identity(
        store,
        ctx["project_id"],
        ctx["project_binding_id"],
        ctx["genesis_state"]["state_metadata"].get("human_authority_ref")
        or {"kind": "human_authority", "id": "AUTH-BIND-0001"},
    )
    boundary = boundary_for(issued_at="2026-09-15T13:00:00Z", expires_at="2026-09-15T18:00:00Z")
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "target_identity": target_identity,
        "boundary": boundary,
    }


def observe_reachability(
    world: dict[str, Any],
    *,
    adapter: FakeRuntimeAdapter,
    observed_at: str,
) -> dict[str, Any]:
    """One real ``observe_runtime_target`` call, returning both the real committed
    Observation Receipt and this module's own reachable/unreachable/unknown classification of
    its transport outcome -- the classification is harness-side bookkeeping only; the
    canonical fact is the receipt itself."""

    outcome = observe_runtime_target(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
        boundary=world["boundary"],
        adapter=adapter,
        observed_at=observed_at,
    )
    transport_outcome = outcome["receipt"].observations["observation_outcome"]
    classification = _OUTCOME_TO_CLASSIFICATION.get(transport_outcome, UNKNOWN)
    return {
        "outcome": outcome,
        "transport_outcome": transport_outcome,
        "classification": classification,
    }


def run_reachability_measurements(world: dict[str, Any]) -> list[dict[str, Any]]:
    """Three genuinely distinct measurements against the identical target: reachable,
    unreachable, and unknown -- proving all three classifications are honestly distinguished
    rather than one silently standing in for another."""

    results = []

    reachable_adapter = FakeRuntimeAdapter()
    reachable_adapter.seed_target(target_identity=world["target_identity"], fields={"status": "ok"})
    results.append(
        observe_reachability(world, adapter=reachable_adapter, observed_at="2026-09-15T14:00:00Z")
    )

    unreachable_adapter = FakeRuntimeAdapter()
    unreachable_adapter.seed_target(
        target_identity=world["target_identity"],
        fields={"status": "ok"},
        transport_outcome="TIMEOUT",
    )
    results.append(
        observe_reachability(world, adapter=unreachable_adapter, observed_at="2026-09-15T14:05:00Z")
    )

    unknown_adapter = FakeRuntimeAdapter()
    results.append(
        observe_reachability(world, adapter=unknown_adapter, observed_at="2026-09-15T14:10:00Z")
    )

    return results
