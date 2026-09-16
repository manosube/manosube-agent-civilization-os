"""Phase 20 -- runtime reachability observation (Issue #86 section 8).

Reuses the existing, already-accepted Runtime Observation Contract (``10_RUNTIME``) exactly as
it stands: :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` against
the fixture/local controlled ``FakeRuntimeAdapter``, never a new production provider or
credential (Issue #86's own Boundary). Runtime reachability is measured, never assumed:
:func:`classify_transport_outcome` is a total, fail-closed function over the Runtime package's
own complete, closed eight-member ``RUNTIME_OBSERVATION_OUTCOMES`` vocabulary (P87-R1-F6) --
every member is mapped explicitly, the map's completeness against that vocabulary is asserted
at import time, and any value outside it raises :class:`UnmappedRuntimeOutcomeError` rather
than silently defaulting. ``REACHABLE`` covers every outcome meaning a real response was
obtained (``OBSERVED``/``NEGATIVE``/``IDENTITY_MISMATCH``); ``UNREACHABLE`` covers every real
transport-level failure to obtain one (``TIMEOUT``/``UNAVAILABLE``/``MALFORMED``/
``PERMISSION_DENIED``); ``UNKNOWN`` is reserved for ``NOT_FOUND`` alone (no observation was ever
made against a seeded target) -- three genuinely distinct, never-conflated categories
(``UNREACHABLE_AND_UNKNOWN_RETAINED=true``).

This module itself performs no ``with_work_time_coordination`` call of its own (P87-R1-F7):
the production long-running-proof entrypoint (:func:`~tests.long_running_proof.orchestrator.
run_long_running_proof`) is the one caller that opens the single, real ``LONG_RUNNING_PROOF``
coordination for the whole run, and verifies (via :func:`~manosube_agent_civilization.
work_time_transparency.adapters.verify_joined_coordination`) that this module's own slice
executes strictly inside that already-open outer work unit before ever calling
:func:`run_reachability_measurements` -- a caller-supplied 9th adapter_kind (``types.py`` +
schema enum, both amended for this correction) and the identical, already-accepted join
primitive Model Runtime itself uses for its own nested Work Units, never a caller-forged
coordination context."""

from __future__ import annotations

from typing import Any

from tests.fixtures.runtime_world import boundary_for, commit_target_identity

from manosube_agent_civilization.runtime.adapter import FakeRuntimeAdapter
from manosube_agent_civilization.runtime.route import observe_runtime_target
from manosube_agent_civilization.runtime.types import RUNTIME_OBSERVATION_OUTCOMES
from manosube_agent_civilization.store import FileStateStore

REACHABLE = "REACHABLE"
UNREACHABLE = "UNREACHABLE"
UNKNOWN = "UNKNOWN"


class UnmappedRuntimeOutcomeError(RuntimeError):
    """Raised by :func:`classify_transport_outcome` when a receipt's own
    ``observation_outcome`` is not one of :data:`~manosube_agent_civilization.runtime.types.
    RUNTIME_OBSERVATION_OUTCOMES`'s eight closed members -- this harness-side classifier fails
    closed on any value it cannot place (P87-R1-F6), never silently folding an unrecognized
    future outcome into ``UNKNOWN`` the way a bare ``dict.get(outcome, UNKNOWN)`` would."""


#: The complete, explicit map of every one of the Runtime package's own eight closed
#: ``observation_outcome`` values to exactly one of this proof's three required reachability
#: categories (Issue #86 section 8) -- covers :data:`RUNTIME_OBSERVATION_OUTCOMES` exhaustively
#: (asserted at import time below), so ``classify_transport_outcome`` never needs a default.
#: ``OBSERVED``/``NEGATIVE``/``IDENTITY_MISMATCH`` all mean a real response was obtained from
#: the target (the route reached it and got back content, even if that content was a negative
#: fact or failed the route's own independent identity re-verification) -- ``REACHABLE``.
#: ``NOT_FOUND`` means no observation was ever attempted against a seeded target -- ``UNKNOWN``,
#: kept distinct from every transport-failure outcome. ``TIMEOUT``/``UNAVAILABLE``/``MALFORMED``/
#: ``PERMISSION_DENIED`` are all real transport-level failures to obtain a usable signal --
#: ``UNREACHABLE``, never folded into ``UNKNOWN``.
_OUTCOME_TO_CLASSIFICATION: dict[str, str] = {
    "OBSERVED": REACHABLE,
    "NEGATIVE": REACHABLE,
    "IDENTITY_MISMATCH": REACHABLE,
    "NOT_FOUND": UNKNOWN,
    "TIMEOUT": UNREACHABLE,
    "UNAVAILABLE": UNREACHABLE,
    "MALFORMED": UNREACHABLE,
    "PERMISSION_DENIED": UNREACHABLE,
}
if set(_OUTCOME_TO_CLASSIFICATION) != RUNTIME_OBSERVATION_OUTCOMES:
    raise AssertionError(
        "_OUTCOME_TO_CLASSIFICATION has drifted from RUNTIME_OBSERVATION_OUTCOMES: "
        f"missing={RUNTIME_OBSERVATION_OUTCOMES - set(_OUTCOME_TO_CLASSIFICATION)!r} "
        f"extra={set(_OUTCOME_TO_CLASSIFICATION) - RUNTIME_OBSERVATION_OUTCOMES!r}"
    )


def classify_transport_outcome(outcome: str) -> str:
    """The one, total, fail-closed classifier: refuses (never defaults to ``UNKNOWN``) any
    ``outcome`` outside the closed vocabulary this module's own map covers."""

    if outcome not in _OUTCOME_TO_CLASSIFICATION:
        raise UnmappedRuntimeOutcomeError(
            f"runtime observation_outcome {outcome!r} is not one of the closed "
            f"RUNTIME_OBSERVATION_OUTCOMES this classifier maps: "
            f"{sorted(_OUTCOME_TO_CLASSIFICATION)!r}"
        )
    return _OUTCOME_TO_CLASSIFICATION[outcome]


def build_runtime_reachability_world(
    store: FileStateStore,
    *,
    project_id: str,
    project_binding_id: str,
    human_authority_ref: dict[str, Any],
) -> dict[str, Any]:
    """A real, committed, signed ``runtime_deployment_declaration`` anchoring one target,
    committed into *store*'s own already-real Project Binding (P87-R1-F4) -- the identical
    shape ``observe_runtime_target`` needs, but bound into the long-running cycle sequence's
    own Store/Project/Binding rather than a second, unrelated fixture world, so the runtime-
    reachability slice shares the exact ``project_binding_id`` and lineage every cycle
    Difference/Reflow commit also advances."""

    target_identity = commit_target_identity(
        store, project_id, project_binding_id, human_authority_ref
    )
    boundary = boundary_for(issued_at="2026-09-15T13:00:00Z", expires_at="2026-09-15T18:00:00Z")
    return {
        "store": store,
        "project_id": project_id,
        "project_binding_id": project_binding_id,
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
    classification = classify_transport_outcome(transport_outcome)
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
