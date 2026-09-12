"""Phase 19 (Issue #77) shared Multi-Agent Dynamic Execution test world.

Reuses :mod:`tests.fixtures.model_runtime_world` directly for everything Phase 16 already
provides (a bound project, a committed Model Execution Boundary, a genuinely Ed25519-signed
Model Execution Grant, the canonical Change-Free Verification Evidence request shape) rather
than duplicating any of it -- this module adds exactly one thing that world does not offer:
a real, schema-valid, content-addressed Difference whose own ``risk_class`` is caller-chosen,
built through the identical real Observation Engine + Difference producer pipeline
:func:`tests.fixtures.model_runtime_world.difference_for` already uses, never hand-written.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from tests.difference_helpers import (
    PREDICATE_ID,
    PROJECT_ID as DIFFERENCE_HELPERS_PROJECT_ID,
    derivation_request,
    negative_claim,
    objective_revision as difference_objective_revision,
    observation_request,
    observation_scope,
    raw_fact,
    state_fingerprint,
)
from tests.fixtures.model_runtime_world import (
    PERMITTED_CANDIDATE_FIELDS,
    PROJECT_ID,
    REQUIRED_CAPABILITY,
    SECOND_PROJECT_ID,
    _rebind,
    bind_into,
    commit_boundary,
    commit_grant,
    commit_records,
    evidence_request_for,
    human_authority_signing_key,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.identity import difference_id as compute_difference_id
from manosube_agent_civilization.model_runtime.types import MODEL_ADAPTER_OUTCOMES
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.store import FileStateStore

DIFFERENCE_RECORD_KIND = "difference"

#: The exact four-member Difference schema enum, restated here (never imported from
#: ``manosube_agent_civilization.multi_agent.selection`` -- a test fixture reusing the very
#: mapping it exists to exercise would make the mapping's own correctness untestable).
RISK_CLASSES: tuple[str, ...] = ("LOW", "MODERATE", "HIGH", "CRITICAL")


def evidence_observation_request_for(
    project_id: str, *, fact_value: str = "NOT-READY"
) -> dict[str, Any]:
    request = observation_request(
        observation_scope(),
        [raw_fact(value=fact_value)],
        state_fingerprint(),
        negative_claims=[negative_claim("NO_RESULT")],
    )
    return cast("dict[str, Any]", _rebind(request, DIFFERENCE_HELPERS_PROJECT_ID, project_id))


def difference_for(
    project_id: str, *, risk_class: str = "LOW", fact_value: str = "NOT-READY"
) -> dict[str, Any]:
    """One real, schema-valid, content-addressed Difference bound to *project_id*, with its
    own ``risk_class`` set to the caller's choice -- built through the identical real
    Observation Engine and public Difference producer
    :func:`tests.fixtures.model_runtime_world.difference_for` itself uses, the only addition
    being the ``risk_class`` override on the derivation request before the real producer runs.
    """

    if risk_class not in RISK_CLASSES:
        raise ValueError(f"risk_class must be one of {RISK_CLASSES!r}: {risk_class!r}")
    fingerprint = state_fingerprint()
    scope = observation_scope()
    bundle = observe(evidence_observation_request_for(project_id, fact_value=fact_value))
    request = derivation_request(
        difference_objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": bundle,
            }
        ],
        fingerprint,
    )
    request = _rebind(request, DIFFERENCE_HELPERS_PROJECT_ID, project_id)
    request["risk_class"] = risk_class
    difference: dict[str, Any] = dict(derive_differences(request)["differences"][0])
    difference["project_id"] = project_id
    difference["difference_id"] = compute_difference_id(difference)
    if difference["risk_class"] != risk_class:
        raise AssertionError(
            f"the real Difference producer did not honour the requested risk_class: "
            f"{difference['risk_class']!r} != {risk_class!r}"
        )
    return difference


def commit_difference(
    store: FileStateStore,
    project_id: str,
    *,
    risk_class: str = "LOW",
    fact_value: str = "NOT-READY",
    transaction_id: str = "TX-MULTI-AGENT-DIFFERENCE-0001",
) -> tuple[dict[str, str], dict[str, Any]]:
    """Commit one real Difference with the given ``risk_class`` and return ``(ref,
    difference)``."""

    difference = difference_for(project_id, risk_class=risk_class, fact_value=fact_value)
    commit_records(
        store,
        project_id,
        store.load_current(project_id),
        transaction_id,
        [(DIFFERENCE_RECORD_KIND, difference["difference_id"], difference)],
    )
    return {"kind": DIFFERENCE_RECORD_KIND, "id": difference["difference_id"]}, difference


def authorized_world(
    tmp_path: Path,
    *,
    risk_class: str = "LOW",
    subdir: str = "backend",
    project_id: str = PROJECT_ID,
) -> dict[str, Any]:
    """One real Store with one bound project, one committed Difference of the given
    ``risk_class``, one committed Model Execution Boundary, and one committed, genuinely
    signed Model Execution Grant -- everything
    :func:`~manosube_agent_civilization.multi_agent.open_dynamic_execution_plan` needs, and
    nothing it does not."""

    store = FileStateStore(tmp_path / subdir, schema_root=SCHEMA_ROOT)
    ctx = bind_into(store, project_id=project_id)
    difference_ref, difference = commit_difference(store, ctx["project_id"], risk_class=risk_class)
    boundary_ref, boundary = commit_boundary(store, ctx["project_id"], ctx["project_binding_id"])
    grant_ref, grant = commit_grant(store, ctx["project_id"], difference_ref, boundary_ref)
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "human_authority_ref": ctx["human_authority_ref"],
        "human_authority_signing_key": human_authority_signing_key(),
        "difference_ref": difference_ref,
        "difference": difference,
        "boundary_ref": boundary_ref,
        "boundary": boundary,
        "grant_ref": grant_ref,
        "grant": grant,
    }


def open_plan_kwargs(
    world: Mapping[str, Any],
    *,
    adapter_identity: Mapping[str, Any] | None = None,
    opened_at: str = "2026-09-11T01:00:00Z",
    expires_at: str = "2026-09-11T02:00:00Z",
) -> dict[str, Any]:
    """Every keyword :func:`~manosube_agent_civilization.multi_agent.open_dynamic_execution_plan`
    needs for one real, successful open -- deep-copied so a caller may mutate one field for a
    negative control without perturbing *world*."""

    return deepcopy(
        {
            "project_id": world["project_id"],
            "project_binding_id": world["project_binding_id"],
            "difference_ref": world["difference_ref"],
            "boundary_ref": world["boundary_ref"],
            "model_execution_grant_refs": [world["grant_ref"]],
            "adapter_identity": dict(
                adapter_identity or {"adapter": "fake_model_adapter", "version": "0.1"}
            ),
            "opened_at": opened_at,
            "expires_at": expires_at,
        }
    )


# --------------------------------------------------------------------------- #
# Test-double Model Adapters this package's own V5/V6 proofs need
# --------------------------------------------------------------------------- #


class SeededMultiAgentAdapter:
    """A controlled, in-memory, fully deterministic
    :class:`~manosube_agent_civilization.model_runtime.types.ModelAdapter` that reports a
    fixed, caller-declared candidate every time it is called -- the identical
    ``FakeModelAdapter`` shape Phase 16's own fixture layer already establishes, restated here
    (never imported) for this package's own decoupled test world."""

    def __init__(
        self,
        *,
        adapter_identity: Mapping[str, Any] | None = None,
        candidate_fields: Mapping[str, Any] | None = None,
        candidate_kind: str = "OBSERVATION_CANDIDATE",
        adapter_outcome: str = "CANDIDATE",
    ) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "fake_model_adapter", "version": "0.1"}
        )
        self._candidate_fields = dict(candidate_fields or {"summary": "seeded"})
        self._candidate_kind = candidate_kind
        self._adapter_outcome = adapter_outcome
        self.execute_call_count = 0

    def execute(self, *, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.execute_call_count += 1
        if self._adapter_outcome not in MODEL_ADAPTER_OUTCOMES:
            raise ValueError(f"not an adapter-reportable outcome: {self._adapter_outcome!r}")
        if self._adapter_outcome != "CANDIDATE":
            return {
                "adapter_outcome": self._adapter_outcome,
                "candidate_kind": None,
                "candidate_fields": None,
            }
        permitted = list(request["boundary"]["permitted_candidate_fields"])
        candidate_fields = {
            field: self._candidate_fields[field]
            for field in permitted
            if field in self._candidate_fields
        }
        return {
            "adapter_outcome": "CANDIDATE",
            "candidate_kind": self._candidate_kind,
            "candidate_fields": candidate_fields,
        }


class StateRecordingMultiAgentAdapter:
    """A controlled adapter, structurally identical to :class:`SeededMultiAgentAdapter`, that
    additionally appends the exact ``state_revision``/``semantic_fingerprint`` pair its own real
    ``request`` carried onto a caller-supplied shared list -- Structural Review Round 3's own
    P19-R3-F1 required proof that every real adapter request in one plan consumed one actual
    common snapshot, observed from the adapter's own side of the boundary rather than only
    inferred from this package's own bookkeeping metadata or the committed Envelope."""

    def __init__(
        self,
        *,
        observed: list[dict[str, Any]],
        candidate_fields: Mapping[str, Any] | None = None,
    ) -> None:
        self.adapter_identity: Mapping[str, Any] = {
            "adapter": "fake_model_adapter",
            "version": "0.1",
        }
        self._candidate_fields = dict(candidate_fields or {"summary": "seeded"})
        self._observed = observed
        self.execute_call_count = 0

    def execute(self, *, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.execute_call_count += 1
        self._observed.append(
            {
                "state_revision": request["state_revision"],
                "semantic_fingerprint": dict(request["semantic_fingerprint"]),
            }
        )
        permitted = list(request["boundary"]["permitted_candidate_fields"])
        candidate_fields = {
            field: self._candidate_fields[field]
            for field in permitted
            if field in self._candidate_fields
        }
        return {
            "adapter_outcome": "CANDIDATE",
            "candidate_kind": "OBSERVATION_CANDIDATE",
            "candidate_fields": candidate_fields,
        }


class CrashingMultiAgentAdapter:
    """A controlled adapter that raises a genuinely unexpected (non-``ModelRuntimeError``)
    exception from ``execute()`` -- the V6 coordinator-crash simulation's own subject. Never
    raised as a typed, honestly-reported adapter outcome (see
    :class:`~manosube_agent_civilization.model_runtime.types.ModelAdapter`'s own protocol
    docstring: an adapter must never raise for an *ordinary* operational failure) -- this
    represents the strictly stronger case of an infrastructure fault the adapter itself could
    not have reported as a typed outcome at all.
    """

    def __init__(self, *, adapter_identity: Mapping[str, Any] | None = None) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "fake_model_adapter", "version": "0.1"}
        )
        self.execute_call_count = 0

    def execute(self, *, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.execute_call_count += 1
        raise RuntimeError("simulated coordinator/infrastructure crash")


class HangingMultiAgentAdapter:
    """A controlled adapter whose ``execute()`` blocks for a caller-declared, real wall-clock
    duration before ever returning -- Structural Review Round 3's own P19-R3-F4 required proof
    subject: a genuinely hanging adapter, never a simulated timeout. The duration is chosen by
    each test to exceed its own plan's ``per_slot_timeout_seconds`` so the real bounded-call
    enforcement (``route.py``'s own ``ThreadPoolExecutor`` + ``future.result(timeout=...)``) is
    what ends the call, never this adapter returning early on its own."""

    def __init__(
        self, *, sleep_seconds: float, adapter_identity: Mapping[str, Any] | None = None
    ) -> None:
        self.adapter_identity: Mapping[str, Any] = dict(
            adapter_identity or {"adapter": "fake_model_adapter", "version": "0.1"}
        )
        self._sleep_seconds = sleep_seconds
        self.execute_call_count = 0

    def execute(self, *, request: Mapping[str, Any]) -> Mapping[str, Any]:
        import time

        self.execute_call_count += 1
        time.sleep(self._sleep_seconds)
        permitted = list(request["boundary"]["permitted_candidate_fields"])
        return {
            "adapter_outcome": "CANDIDATE",
            "candidate_kind": "OBSERVATION_CANDIDATE",
            "candidate_fields": dict.fromkeys(permitted, "late"),
        }


__all__ = [
    "PERMITTED_CANDIDATE_FIELDS",
    "PROJECT_ID",
    "REQUIRED_CAPABILITY",
    "RISK_CLASSES",
    "SECOND_PROJECT_ID",
    "CrashingMultiAgentAdapter",
    "HangingMultiAgentAdapter",
    "SeededMultiAgentAdapter",
    "StateRecordingMultiAgentAdapter",
    "authorized_world",
    "bind_into",
    "commit_boundary",
    "commit_difference",
    "commit_grant",
    "commit_records",
    "difference_for",
    "evidence_request_for",
    "open_plan_kwargs",
]
