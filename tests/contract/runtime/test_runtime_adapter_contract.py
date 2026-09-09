"""V2 (Issue #64): controlled Runtime Adapter contract proof.

Proves, through a real ``FileStateStore`` and the real
:func:`~manosube_agent_civilization.runtime.route.observe_runtime_target`, that:

- every one of the eight closed :data:`~manosube_agent_civilization.runtime.types.
  RUNTIME_OBSERVATION_OUTCOMES` is reachable end to end;
- a transport failure (``PERMISSION_DENIED``/``TIMEOUT``/``UNAVAILABLE``/``MALFORMED``) never
  becomes, or is ever confused with, an authoritative ``NOT_FOUND`` absence;
- ``NEGATIVE``/``IDENTITY_MISMATCH`` are *route-level-only* classifications -- a
  :class:`~manosube_agent_civilization.runtime.adapter.FakeRuntimeAdapter` reporting a genuine
  transport-level ``OBSERVED`` is independently reclassified by the route itself, never
  trusted as the adapter's own self-report of either;
- the route fails closed on a malformed/out-of-vocabulary adapter report, and on an adapter
  that declares no readable ``adapter_identity``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pytest
from tests.fixtures.runtime_world import bound, boundary_for, target_identity_for

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.adapter import FakeRuntimeAdapter
from manosube_agent_civilization.runtime.errors import RuntimeAdapterError
from manosube_agent_civilization.runtime.route import observe_runtime_target
from manosube_agent_civilization.runtime.types import (
    RUNTIME_ADAPTER_TRANSPORT_OUTCOMES,
    RUNTIME_OBSERVATION_OUTCOMES,
    RUNTIME_OUTCOME_TO_RECEIPT_STATUS,
)


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store, ctx = bound(tmp_path)
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    target_identity = target_identity_for(ctx["project_binding_id"])
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "human_authority_ref": dict(boot_context.human_authority_ref),
        "target_identity": target_identity,
    }


def _observe(
    world: dict[str, Any], adapter: Any, boundary: dict[str, Any], observed_at: str
) -> dict[str, Any]:
    return observe_runtime_target(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at=observed_at,
    )


def test_runtime_adapter_transport_outcomes_is_a_strict_subset() -> None:
    assert RUNTIME_ADAPTER_TRANSPORT_OUTCOMES < RUNTIME_OBSERVATION_OUTCOMES
    assert "NEGATIVE" not in RUNTIME_ADAPTER_TRANSPORT_OUTCOMES
    assert "IDENTITY_MISMATCH" not in RUNTIME_ADAPTER_TRANSPORT_OUTCOMES
    assert {
        "NEGATIVE",
        "IDENTITY_MISMATCH",
    } == RUNTIME_OBSERVATION_OUTCOMES - RUNTIME_ADAPTER_TRANSPORT_OUTCOMES


@pytest.mark.parametrize(
    "transport_outcome", ["NOT_FOUND", "PERMISSION_DENIED", "TIMEOUT", "UNAVAILABLE", "MALFORMED"]
)
def test_each_transport_level_outcome_is_reachable_and_faithfully_committed(
    _world: dict[str, Any], transport_outcome: str
) -> None:
    adapter = FakeRuntimeAdapter()
    boundary = boundary_for()
    if transport_outcome != "NOT_FOUND":
        adapter.seed_target(
            target_identity=_world["target_identity"],
            fields={"status": "ok"},
            transport_outcome=transport_outcome,
        )
    outcome = _observe(_world, adapter, boundary, "2026-01-01T00:30:00Z")
    assert outcome["envelope"]["observation_outcome"] == transport_outcome
    assert outcome["receipt"].observations["observation_outcome"] == transport_outcome
    assert outcome["receipt"].status == RUNTIME_OUTCOME_TO_RECEIPT_STATUS[transport_outcome]
    # No content is ever committed for a non-OBSERVED outcome.
    assert outcome["envelope"]["observed_fields"] is None
    assert outcome["envelope"]["observed_content_fingerprint"] is None


def test_observed_outcome_is_reachable_and_carries_real_content(_world: dict[str, Any]) -> None:
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=_world["target_identity"], fields={"status": "ok"})
    boundary = boundary_for()
    outcome = _observe(_world, adapter, boundary, "2026-01-01T00:30:00Z")
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"] == {"status": "ok"}
    assert outcome["envelope"]["observed_content_fingerprint"] is not None
    assert outcome["receipt"].status == "VERIFIED"


@pytest.mark.parametrize(
    "transport_outcome", ["PERMISSION_DENIED", "TIMEOUT", "UNAVAILABLE", "MALFORMED"]
)
def test_transport_failure_never_becomes_absence(
    _world: dict[str, Any], transport_outcome: str
) -> None:
    """A transport-level failure must never be committed as, or confused with, the one
    outcome (``NOT_FOUND``) that means a genuine, authoritative absence."""

    adapter = FakeRuntimeAdapter()
    adapter.seed_target(
        target_identity=_world["target_identity"],
        fields={"status": "ok"},
        transport_outcome=transport_outcome,
    )
    outcome = _observe(_world, adapter, boundary_for(), "2026-01-01T00:30:00Z")
    assert outcome["envelope"]["observation_outcome"] != "NOT_FOUND"
    assert outcome["envelope"]["observation_outcome"] == transport_outcome
    # NOT_FOUND/NEGATIVE/IDENTITY_MISMATCH are all classified FAILED; a transport-level
    # failure the adapter itself could not resolve is classified UNAVAILABLE instead --
    # a real caller can tell "confirmed absent/wrong" apart from "could not tell".
    assert outcome["receipt"].status == "UNAVAILABLE"


def test_negative_is_a_route_level_classification_never_trusted_from_the_adapter(
    _world: dict[str, Any],
) -> None:
    """The Fake adapter can only ever report the transport-level truth (``OBSERVED``, content
    included) -- ``NEGATIVE`` is exclusively computed by the route itself, from the Boundary's
    own ``expected_field``/``expected_value`` closure."""

    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=_world["target_identity"], fields={"status": "down"})
    boundary = boundary_for(expected_field="status", expected_value="ok")
    outcome = _observe(_world, adapter, boundary, "2026-01-01T00:30:00Z")
    assert outcome["envelope"]["observation_outcome"] == "NEGATIVE"
    assert outcome["receipt"].status == "FAILED"
    # The content itself is real and was genuinely observed -- NEGATIVE is a semantic
    # judgment about that content, not a transport failure.
    assert outcome["envelope"]["observed_fields"] == {"status": "down"}
    assert outcome["envelope"]["observed_content_fingerprint"] is not None


def test_identity_mismatch_is_a_route_level_classification_never_trusted_from_the_adapter(
    _world: dict[str, Any],
) -> None:
    """A target that genuinely, transport-level answers ``OBSERVED`` but reports an identity
    different from what was declared must never be silently accepted as the declared target --
    computed here, never accepted from the adapter's own claimed match/mismatch (the adapter
    protocol offers no such claim at all)."""

    adapter = FakeRuntimeAdapter()
    adapter.seed_target(
        target_identity=_world["target_identity"],
        fields={"status": "ok"},
        observed_deployment_identity="sha256:" + "f" * 64,
    )
    outcome = _observe(_world, adapter, boundary_for(), "2026-01-01T00:30:00Z")
    assert outcome["envelope"]["observation_outcome"] == "IDENTITY_MISMATCH"
    assert outcome["receipt"].status == "FAILED"


def test_route_refuses_an_out_of_vocabulary_transport_outcome(_world: dict[str, Any]) -> None:
    """Even if a buggy/malicious adapter tried to directly self-report ``NEGATIVE`` or
    ``IDENTITY_MISMATCH`` as its own transport_outcome (never legitimate per the Protocol),
    the route refuses outright rather than accept it as a valid classification."""

    adapter = FakeRuntimeAdapter()
    adapter.force_result(
        {
            "transport_outcome": "NEGATIVE",
            "observed_fields": None,
            "observed_deployment_identity": None,
        }
    )
    with pytest.raises(RuntimeAdapterError):
        _observe(_world, adapter, boundary_for(), "2026-01-01T00:30:00Z")


def test_route_refuses_observed_with_unreadable_observed_fields(_world: dict[str, Any]) -> None:
    adapter = FakeRuntimeAdapter()
    adapter.force_result(
        {
            "transport_outcome": "OBSERVED",
            "observed_fields": None,
            "observed_deployment_identity": "x",
        }
    )
    with pytest.raises(RuntimeAdapterError):
        _observe(_world, adapter, boundary_for(), "2026-01-01T00:30:00Z")


def test_route_refuses_a_non_mapping_adapter_report(_world: dict[str, Any]) -> None:
    class _BadAdapter:
        adapter_identity: ClassVar[dict[str, str]] = {"adapter": "bad", "version": "0.1"}

        def observe(self, *, target_identity: Any, boundary: Any) -> Any:
            return "not-a-mapping"

    with pytest.raises(RuntimeAdapterError):
        _observe(_world, _BadAdapter(), boundary_for(), "2026-01-01T00:30:00Z")


def test_route_refuses_an_adapter_with_no_readable_identity(_world: dict[str, Any]) -> None:
    class _AnonymousAdapter:
        def observe(self, *, target_identity: Any, boundary: Any) -> Any:
            return {
                "transport_outcome": "OBSERVED",
                "observed_fields": {"status": "ok"},
                "observed_deployment_identity": _world["target_identity"]["deployment_fingerprint"],
            }

    with pytest.raises(RuntimeAdapterError):
        _observe(_world, _AnonymousAdapter(), boundary_for(), "2026-01-01T00:30:00Z")
