"""P15-R1-F6: deployed identity verification is no longer circular.

Structural Review Round 1 found that ``target_identity["deployment_fingerprint"]`` was an
arbitrary caller string and ``observed_deployment_identity`` was read straight out of the
target's own HTTP response -- so the route's comparison of the two proved only that *the
endpoint echoed the expected string*, which anyone controlling both the target declaration and
the responding endpoint can arrange trivially. That is not independent verification.

The declared side is now anchored: ``target_identity`` carries a required
``deployment_declaration_ref``, which must resolve to a genuinely committed, content-addressed,
Human-Authority-declared ``runtime_deployment_declaration`` whose own independently recomputed
identity matches, and which independently restates every one of this target's identifying
fields. Only then does the existing observed-vs-declared comparison run, unchanged.

Classification, disclosed: every refusal in this file is a
:class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` with **zero
commits**, never an ``IDENTITY_MISMATCH`` observation outcome. ``IDENTITY_MISMATCH`` is a
statement about what a genuinely reached target reported; here nothing has been reached at all,
because the *request itself* is not anchored -- so there is no observation to classify, and
none is committed.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.runtime_world import (
    DEFAULT_DEPLOYMENT_FINGERPRINT,
    DEPLOYMENT_DECLARATION_RECORD_KIND,
    bound,
    boundary_for,
    commit_deployment_declaration,
    commit_records,
    commit_target_identity,
    deployment_declaration_for,
    target_identity_for,
)

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.adapter import FakeRuntimeAdapter
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.route import observe_runtime_target

_SPOOFED_FINGERPRINT = "sha256:" + "5" * 64


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store, ctx = bound(tmp_path)
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "human_authority_ref": dict(boot_context.human_authority_ref),
    }


def _observe(
    world: dict[str, Any], target_identity: dict[str, Any], adapter: Any
) -> dict[str, Any]:
    return observe_runtime_target(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=target_identity,
        boundary=boundary_for(),
        adapter=adapter,
        observed_at="2026-01-01T00:30:00Z",
    )


def _envelope_count(world: dict[str, Any]) -> int:
    directory = (
        Path(world["store"].root)
        / "projects"
        / world["project_id"]
        / "records"
        / "runtime_observation_envelope"
    )
    return len(list(directory.iterdir())) if directory.is_dir() else 0


def _seeded(target_identity: dict[str, Any], **kwargs: Any) -> FakeRuntimeAdapter:
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=target_identity, fields={"status": "ok"}, **kwargs)
    return adapter


# ---------------------------------------------------------------------------
# The anchored happy path
# ---------------------------------------------------------------------------


def test_a_target_anchored_to_a_genuinely_committed_declaration_is_observed(
    _world: dict[str, Any],
) -> None:
    target_identity = commit_target_identity(
        _world["store"],
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
    )
    outcome = _observe(_world, target_identity, _seeded(target_identity))
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert (
        outcome["envelope"]["target_identity"]["deployment_declaration_ref"]["kind"]
        == DEPLOYMENT_DECLARATION_RECORD_KIND
    )


def test_an_anchored_target_whose_endpoint_reports_a_different_identity_is_still_a_mismatch(
    _world: dict[str, Any],
) -> None:
    """Anchoring the *declared* side does not weaken the existing observed-vs-declared check --
    a genuinely reached target reporting some other identity is still ``IDENTITY_MISMATCH``,
    exactly as before."""

    target_identity = commit_target_identity(
        _world["store"],
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
    )
    adapter = _seeded(target_identity, observed_deployment_identity="sha256:" + "f" * 64)
    outcome = _observe(_world, target_identity, adapter)
    assert outcome["envelope"]["observation_outcome"] == "IDENTITY_MISMATCH"


# ---------------------------------------------------------------------------
# The spoofing control
# ---------------------------------------------------------------------------


def test_a_caller_selected_fingerprint_with_no_committed_declaration_is_refused(
    _world: dict[str, Any],
) -> None:
    """The exact finding: a caller controls both the declaration and the endpoint, and makes
    them agree on a fingerprint that has no canonical record behind it at all. Before this
    correction that produced a perfectly ``OBSERVED`` Envelope."""

    target_identity = target_identity_for(
        _world["project_binding_id"],
        deployment_declaration_ref={
            "kind": DEPLOYMENT_DECLARATION_RECORD_KIND,
            "id": "RUNTIME-DEPLOYMENT-DECLARATION-" + "0" * 64,
        },
        deployment_fingerprint=_SPOOFED_FINGERPRINT,
    )
    adapter = _seeded(target_identity)  # the endpoint happily echoes the spoofed fingerprint
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, target_identity, adapter)
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


def test_a_declared_fingerprint_diverging_from_its_own_committed_declaration_is_refused(
    _world: dict[str, Any],
) -> None:
    """A genuinely committed declaration exists, and the endpoint agrees with the caller -- but
    the caller's claimed fingerprint is not the one the canonical record actually declares."""

    declaration = deployment_declaration_for(
        _world["project_id"], _world["project_binding_id"], _world["human_authority_ref"]
    )
    ref = commit_deployment_declaration(_world["store"], _world["project_id"], declaration)
    target_identity = target_identity_for(
        _world["project_binding_id"],
        deployment_declaration_ref=ref,
        deployment_fingerprint=_SPOOFED_FINGERPRINT,
    )
    adapter = _seeded(target_identity)
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, target_identity, adapter)
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


# ---------------------------------------------------------------------------
# The replay control
# ---------------------------------------------------------------------------


def test_a_declaration_for_one_target_may_not_anchor_a_different_target(
    _world: dict[str, Any],
) -> None:
    """Target A's own legitimately committed declaration, presented alongside Target B's
    provider/deployment/instance fields. Every field the declaration restates is compared, so a
    valid declaration cannot be replayed as the anchor for anything but its own target."""

    declaration_a = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        provider="local",
        deployment_id="widget-service",
        instance_identity="widget-service-1",
    )
    ref_a = commit_deployment_declaration(_world["store"], _world["project_id"], declaration_a)

    target_b = target_identity_for(
        _world["project_binding_id"],
        deployment_declaration_ref=ref_a,
        provider="local",
        deployment_id="billing-service",
        instance_identity="billing-service-9",
        deployment_fingerprint=DEFAULT_DEPLOYMENT_FINGERPRINT,
    )
    adapter = _seeded(target_b)
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, target_b, adapter)
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


def test_a_declaration_bound_to_a_different_project_binding_is_refused(
    _world: dict[str, Any],
) -> None:
    """The declaration is committed in this project's own Store and is internally valid, but
    binds a different Project Binding than the target claims."""

    declaration = deployment_declaration_for(
        _world["project_id"], "PROJBIND-SOMEWHERE-ELSE", _world["human_authority_ref"]
    )
    ref = commit_deployment_declaration(_world["store"], _world["project_id"], declaration)
    target_identity = target_identity_for(
        _world["project_binding_id"], deployment_declaration_ref=ref
    )
    adapter = _seeded(target_identity)
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, target_identity, adapter)
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


# ---------------------------------------------------------------------------
# The tamper control
# ---------------------------------------------------------------------------


def test_a_committed_declaration_whose_own_identity_does_not_reproduce_is_refused(
    _world: dict[str, Any],
) -> None:
    """A declaration committed directly (a hypothetical bug or an attacker able to write
    records) whose declared content does not reproduce its own content address is refused, the
    identical ``_resolve_*``-with-identity-reverification discipline ``bootstrap.py`` already
    applies to grants and declarations."""

    declaration = deployment_declaration_for(
        _world["project_id"], _world["project_binding_id"], _world["human_authority_ref"]
    )
    forged = deepcopy(declaration)
    forged["deployment_fingerprint"] = _SPOOFED_FINGERPRINT  # id/fingerprint now stale
    commit_records(
        _world["store"],
        _world["project_id"],
        _world["store"].load_current(_world["project_id"]),
        "TX-RUNTIME-FORGED-DEPLOYMENT-DECLARATION",
        [
            (
                DEPLOYMENT_DECLARATION_RECORD_KIND,
                forged["runtime_deployment_declaration_id"],
                forged,
            )
        ],
    )
    target_identity = target_identity_for(
        _world["project_binding_id"],
        deployment_declaration_ref={
            "kind": DEPLOYMENT_DECLARATION_RECORD_KIND,
            "id": forged["runtime_deployment_declaration_id"],
        },
        deployment_fingerprint=_SPOOFED_FINGERPRINT,
    )
    adapter = _seeded(target_identity)
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, target_identity, adapter)
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


def test_a_declaration_committed_under_another_project_never_anchors_this_one(
    tmp_path: Path,
) -> None:
    """A genuinely legitimate declaration from an entirely separate Store simply never resolves
    here -- the reference is resolved exclusively within the Store being observed."""

    store_a, ctx_a = bound(tmp_path / "world-a")
    store_b, ctx_b = bound(tmp_path / "world-b")
    boot_b = boot_project(
        store_b, project_id=ctx_b["project_id"], project_binding_id=ctx_b["project_binding_id"]
    )
    declaration_b = deployment_declaration_for(
        ctx_b["project_id"], ctx_b["project_binding_id"], dict(boot_b.human_authority_ref)
    )
    ref_b = commit_deployment_declaration(store_b, ctx_b["project_id"], declaration_b)

    target_identity = target_identity_for(
        ctx_a["project_binding_id"], deployment_declaration_ref=ref_b
    )
    adapter = _seeded(target_identity)
    with pytest.raises(RuntimeRequirementError):
        observe_runtime_target(
            store_a,
            project_id=ctx_a["project_id"],
            project_binding_id=ctx_a["project_binding_id"],
            target_identity=target_identity,
            boundary=boundary_for(),
            adapter=adapter,
            observed_at="2026-01-01T00:30:00Z",
        )
    assert adapter.observe_call_count == 0
