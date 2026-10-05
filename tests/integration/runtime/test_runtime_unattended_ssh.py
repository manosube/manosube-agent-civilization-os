"""Issue #105: the grant-gated ``PREAUTHORIZED_UNATTENDED_SSH`` path, end to end.

:mod:`~manosube_agent_civilization.runtime.transport_control`'s own pure-function proofs (what a
grant is, what it permits, when it expires, what it must authentically bind) live in
``tests/unit/runtime/test_runtime_transport_control.py``. This file is the zero-call, real-route
proof that module's own docstring promises: a genuinely signed grant's gate sits *in front of*
the real :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target`, not beside
it or after it -- a request this module refuses never reaches
:class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter`, and therefore never
spawns a process, at all. Since PR #108 Structural Review Round 1 (F1), that gate additionally
sits inside ``SshRuntimeAdapter`` itself -- its own construction *is* the grant check, so no
caller can reach the real subprocess by skipping ``transport_control`` and constructing the
adapter directly either (see ``test_direct_adapter_construction_is_the_identical_gate`` below).

The one positive path through this file (a genuinely signed, ratified,
``PREAUTHORIZED_UNATTENDED_SSH``-permitting grant) still runs with the adapter's own bounded-
subprocess helper mocked, for the identical reason ``test_runtime_transport_independence.py``
discloses: no ``ssh``/``sshd`` binary is available in this environment, and provisioning one
would itself be a machine/service modification outside this delivery's authorized scope. The
real local-SSH-fixture vertical proof, and the real unattended-dispatch-against-a-real-target
proof, are both reported **pending** in this delivery's own evidence -- never claimed here, and
this package's own unattended SSH path is never actually launched against anything from this
test file or any other in this delivery.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from unittest.mock import patch

import pytest
from tests.fixtures.runtime_world import (
    DEFAULT_DEPLOYMENT_CONFIG_FINGERPRINT,
    bound,
    commit_target_identity,
    runtime_observation_grant_for,
    ssh_boundary_for,
)

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.adapter import (
    CapturedProbeReportRuntimeAdapter,
    SshRuntimeAdapter,
)
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.route import observe_runtime_target
from manosube_agent_civilization.runtime.transport_control import (
    compute_runtime_observation_operation_id,
    resolve_bounded_actions_fallback,
    select_transport,
)
from manosube_agent_civilization.runtime.types import SSH_PROBE_SCRIPT_SHA256

_DEPLOYMENT_FINGERPRINT = "sha256:" + "d" * 64
_NOW = "2026-06-01T00:00:00Z"

#: This repository's own real, shipped probe script -- the exact file SR4-F4's own tests below
#: copy into an isolated directory and invoke as a real subprocess, never a reimplementation or
#: a mock of its own logic (PR #108 Structural Review Round 4).
_PROBE_SCRIPT_SOURCE = (
    Path(__file__).resolve().parents[3] / "scripts" / "runtime_observation_probe.py"
)

#: Likewise for the CLI script the SR4-F1/F3 wiring tests below exercise as a real
#: subprocess, never only the library functions it calls.
_TRANSPORT_SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "runtime_observation_transport.py"
)


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store, ctx = bound(tmp_path)
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    target_identity = commit_target_identity(
        store,
        ctx["project_id"],
        ctx["project_binding_id"],
        dict(boot_context.human_authority_ref),
        deployment_fingerprint=_DEPLOYMENT_FINGERPRINT,
    )
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "target_identity": target_identity,
    }


def _grant_for(world: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    return runtime_observation_grant_for(
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        permitted_fields=overrides.pop("permitted_fields", ["hostname"]),
        deployment_fingerprint=overrides.pop("deployment_fingerprint", _DEPLOYMENT_FINGERPRINT),
        **overrides,
    )


def _boundary_matching(grant: dict[str, Any]) -> dict[str, Any]:
    """An SSH Boundary naming the identical endpoint the grant itself scopes -- a grant and the
    Boundary it gates describe one target's own transport, never two independently chosen
    ones."""

    return ssh_boundary_for(
        host=grant["host"],
        port=grant["port"],
        user=grant["user"],
        probe_identity=grant["probe_identity"],
        permitted_fields=list(grant["permitted_fields"]),
        issued_at=_NOW,
        expires_at="2026-06-01T01:00:00Z",
    )


def _mocked_probe_stdout(**overrides: Any) -> bytes:
    report = {
        "ok": True,
        "fields": {"hostname": "vps1"},
        "deployment_identity": _DEPLOYMENT_FINGERPRINT,
        "reason": None,
        "probe_script_sha256": SSH_PROBE_SCRIPT_SHA256,
        "deployment_config_fingerprint": DEFAULT_DEPLOYMENT_CONFIG_FINGERPRINT,
    }
    report.update(overrides)
    return (json.dumps(report) + "\n").encode("utf-8")


def test_a_ratified_grant_reaches_a_real_observed_outcome_through_the_identical_route(
    _world: dict[str, Any],
) -> None:
    """The one positive path: ``select_transport`` admits ``PREAUTHORIZED_UNATTENDED_SSH``
    because the grant names it, ``SshRuntimeAdapter`` construction independently re-verifies
    the identical grant, and the identical canonical
    :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` -- not a second,
    unattended-only route -- carries out the observation."""

    grant = _grant_for(_world)
    transport = select_transport(
        actions_status="UNAVAILABLE",
        requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
    )
    assert transport == "PREAUTHORIZED_UNATTENDED_SSH"

    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        # PR #108 Structural Review Round 4, SR4-F2: live re-verification now also checks the
        # trusted clock against this attempt's own Boundary window, so a deterministic test
        # must inject a clock stub matching its own fixed Boundary rather than rely on the
        # real system clock (which, run on any day outside this fixture's own narrow window,
        # would otherwise refuse this positive-path control for an unrelated reason).
        now_fn=lambda: _NOW,
    )
    with patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run:
        mock_run.return_value = (_mocked_probe_stdout(), b"", 0)
        outcome = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=_world["target_identity"],
            boundary=_boundary_matching(grant),
            adapter=adapter,
            observed_at=_NOW,
        )
    assert mock_run.call_count == 1
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"] == {"hostname": "vps1"}
    assert outcome["receipt"].status == "VERIFIED"


def test_direct_adapter_construction_is_the_identical_gate(_world: dict[str, Any]) -> None:
    """PR #108 SR1 F1: the first delivery's own gap -- constructing
    ``SshRuntimeAdapter`` directly, bypassing ``transport_control.select_transport``
    entirely, must refuse exactly as the recommended flow does when the grant is wrong, with
    zero subprocess calls. There is no executable path around this gate."""

    grant = _grant_for(_world, permitted_transports=["MANUAL_SSH"])
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        SshRuntimeAdapter(
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )
    assert mock_run.call_count == 0


def test_a_forged_grant_is_refused_by_the_adapter_itself_with_zero_subprocess_calls(
    _world: dict[str, Any],
) -> None:
    """The exact first-delivery defect, proved at the adapter's own construction boundary: a
    self-asserted ``decision_status: RATIFIED`` with a fabricated signature is never enough."""

    grant = _grant_for(_world)
    grant = dict(grant)
    grant["signature"] = {"algorithm": "ed25519", "key_id": "FORGED", "value": "ab" * 64}
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        SshRuntimeAdapter(
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )
    assert mock_run.call_count == 0


def test_a_grant_for_a_different_target_is_refused_at_observe_time_with_zero_subprocess_calls(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR1 F1: a grant that is genuinely signed, current, and permits
    ``PREAUTHORIZED_UNATTENDED_SSH`` -- but was issued for a *different* deployment target --
    must still be refused the moment it is matched against the real attempt, inside
    ``observe()``, before any subprocess is spawned."""

    grant = _grant_for(_world, deployment_id="some-other-service")
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
    )
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=_world["target_identity"],
            boundary=_boundary_matching(grant),
            adapter=adapter,
            observed_at=_NOW,
        )
    assert mock_run.call_count == 0


def test_no_grant_at_all_is_refused_before_any_transport_is_even_chosen(
    _world: dict[str, Any],
) -> None:
    with pytest.raises(RuntimeRequirementError):
        select_transport(
            actions_status="UNAVAILABLE",
            requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
            grant=None,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )


def test_an_expired_grant_is_refused_with_zero_adapter_calls(_world: dict[str, Any]) -> None:
    grant = _grant_for(
        _world,
        issued_at="2025-01-01T00:00:00Z",
        expires_at="2025-02-01T00:00:00Z",
    )
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        select_transport(
            actions_status="UNAVAILABLE",
            requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )
    assert mock_run.call_count == 0


def test_a_grant_that_does_not_permit_unattended_ssh_is_refused_with_zero_adapter_calls(
    _world: dict[str, Any],
) -> None:
    """A grant ratified only for ``MANUAL_SSH`` -- a Human copy/pasting a command -- must never
    be treated as also permitting the unattended mode merely because it is otherwise valid and
    names the identical target. Tool availability and grant scope are two different questions,
    and this is the one this module exists to keep separate."""

    grant = _grant_for(_world, permitted_transports=["MANUAL_SSH"])
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        select_transport(
            actions_status="UNAVAILABLE",
            requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )
    assert mock_run.call_count == 0


def test_actions_being_unavailable_never_by_itself_escalates_to_unattended_ssh(
    _world: dict[str, Any],
) -> None:
    """Design requirement 6 (tool availability must not create Authority), proved at this
    file's own end-to-end level: even a grant that *does* permit
    ``PREAUTHORIZED_UNATTENDED_SSH`` is never automatically selected just because Actions is
    unavailable -- an explicit ``requested_transport`` is required, or the call is refused."""

    grant = _grant_for(_world)
    with patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run:
        for status in ("UNAVAILABLE", "UNKNOWN"):
            with pytest.raises(RuntimeRequirementError):
                select_transport(
                    actions_status=status,
                    requested_transport=None,
                    grant=grant,
                    store=_world["store"],
                    project_id=_world["project_id"],
                    project_binding_id=_world["project_binding_id"],
                    now=_NOW,
                )
    assert mock_run.call_count == 0


def test_observe_revalidates_the_grant_live_rather_than_trusting_construction_time(
    _world: dict[str, Any],
) -> None:
    """PR #108 Structural Review Round 2, SR2-F2 (trusted clock corrected by Round 3,
    SR3-F2): a grant genuinely valid at *construction* time, but no longer within its own
    validity window by the actual instant of this exact attempt, must be refused inside
    ``observe()`` itself -- never admitted merely because construction's own check happened to
    pass once, earlier, against a different instant. The live instant here is an explicitly
    injected, deterministic trusted-clock stub (SR3-F2's own ``now_fn``) -- never the
    Boundary's own ``time_window.issued_at``, which the prior round used and which SR3-F2 found
    a caller could trivially backdate."""

    grant = _grant_for(
        _world, issued_at="2026-01-01T00:00:00Z", expires_at="2026-02-01T00:00:00Z"
    )
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now="2026-01-15T00:00:00Z",
        now_fn=lambda: "2026-07-01T00:00:00Z",
    )
    # SR3-F2 also now binds the Boundary's own window inside the grant's own window, so a
    # stale-clock control must declare a Boundary window that is *itself* still comfortably
    # inside the grant's own (otherwise that structural check -- proved separately below --
    # would refuse first, for a different reason than the one this test is about).
    stale_boundary = ssh_boundary_for(
        host=grant["host"],
        port=grant["port"],
        user=grant["user"],
        probe_identity=grant["probe_identity"],
        permitted_fields=list(grant["permitted_fields"]),
        issued_at="2026-01-20T00:00:00Z",
        expires_at="2026-01-20T01:00:00Z",
    )
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        adapter.observe(target_identity=_world["target_identity"], boundary=stale_boundary)
    assert mock_run.call_count == 0


def test_observe_trusted_clock_is_never_fooled_by_a_backdated_boundary_timestamp(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR3-F2's own decisive case, reproducing the review's exact reported shape: a
    grant valid Jan 1 - Feb 1, a Boundary whose own ``time_window`` names an issued_at that
    *looks* like it is still comfortably inside that window -- but the trusted clock (not the
    Boundary) is what decides whether the grant is still current, and it reports an instant
    well past the grant's own expiry."""

    grant = _grant_for(
        _world, issued_at="2026-01-01T00:00:00Z", expires_at="2026-02-01T00:00:00Z"
    )
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now="2026-01-15T00:00:00Z",
        now_fn=lambda: "2026-10-01T00:00:00Z",
    )
    boundary = ssh_boundary_for(
        host=grant["host"],
        port=grant["port"],
        user=grant["user"],
        probe_identity=grant["probe_identity"],
        permitted_fields=list(grant["permitted_fields"]),
        issued_at="2026-01-20T00:00:00Z",
        expires_at="2026-01-20T01:00:00Z",
    )
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        adapter.observe(target_identity=_world["target_identity"], boundary=boundary)
    assert mock_run.call_count == 0


def test_observe_succeeds_when_the_injected_trusted_clock_is_within_the_grants_own_window(
    _world: dict[str, Any],
) -> None:
    """The positive sibling of SR3-F2's own correction: a deterministic trusted-clock stub
    that genuinely falls inside the grant's own window still reaches ``OBSERVED`` -- this
    round's own correction refuses a stale clock, never a valid one."""

    grant = _grant_for(_world)
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        # Inside both the grant's own wide (Jan-Dec) window and (SR4-F2) the Boundary's own
        # narrower one-hour window _boundary_matching(grant) declares.
        now_fn=lambda: "2026-06-01T00:30:00Z",
    )
    with patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run:
        mock_run.return_value = (_mocked_probe_stdout(), b"", 0)
        outcome = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=_world["target_identity"],
            boundary=_boundary_matching(grant),
            adapter=adapter,
            observed_at=_NOW,
        )
    assert mock_run.call_count == 1
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"


def test_observe_refuses_a_boundary_window_wider_than_the_grants_own_window(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR3-F2: the Boundary's own declared window must be bound inside the grant's
    own authorized window, structurally -- a Boundary that independently declares a wider
    window than the grant ever signed is refused with zero subprocess calls, regardless of
    what the trusted clock itself reports."""

    grant = _grant_for(
        _world, issued_at="2026-01-01T00:00:00Z", expires_at="2026-02-01T00:00:00Z"
    )
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now="2026-01-15T00:00:00Z",
        now_fn=lambda: "2026-01-15T00:00:00Z",
    )
    wide_boundary = ssh_boundary_for(
        host=grant["host"],
        port=grant["port"],
        user=grant["user"],
        probe_identity=grant["probe_identity"],
        permitted_fields=list(grant["permitted_fields"]),
        issued_at="2025-01-01T00:00:00Z",
        expires_at="2027-01-01T00:00:00Z",
    )
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        adapter.observe(target_identity=_world["target_identity"], boundary=wide_boundary)
    assert mock_run.call_count == 0


def test_observe_refuses_when_the_live_clock_is_outside_the_boundary_but_inside_the_grant(
    _world: dict[str, Any],
) -> None:
    """PR #108 Structural Review Round 4, SR4-F2's own reproduced counterexample, end to end:
    a grant valid January 1 through December 31 (so the trusted-clock-vs-grant check and the
    structural Boundary-subset-of-Grant check, SR3-F2, both admit it) and a Boundary valid
    only January 1 through January 2. A trusted clock reading October is inside the grant's own
    wide window but far outside the Boundary's own narrow one -- this must still refuse, with
    zero subprocess calls, even though every other check before it passed."""

    grant = _grant_for(
        _world, issued_at="2026-01-01T00:00:00Z", expires_at="2026-12-31T23:59:59Z"
    )
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now="2026-01-15T00:00:00Z",
        now_fn=lambda: "2026-10-04T00:00:00Z",
    )
    narrow_boundary = ssh_boundary_for(
        host=grant["host"],
        port=grant["port"],
        user=grant["user"],
        probe_identity=grant["probe_identity"],
        permitted_fields=list(grant["permitted_fields"]),
        issued_at="2026-01-01T00:00:00Z",
        expires_at="2026-01-02T00:00:00Z",
    )
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        adapter.observe(target_identity=_world["target_identity"], boundary=narrow_boundary)
    assert mock_run.call_count == 0


def test_observe_performs_a_fresh_live_reverification_not_merely_the_cached_construction_check(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR2-F2: ``observe()`` must itself call through to a fresh ``boot_project``
    restoration -- the identical primitive construction already called once -- rather than
    reusing whatever that earlier call already proved. Mocking ``boot_project`` (wrapped, so
    it still behaves identically) and asserting it is invoked again by ``observe()`` alone is
    the structural proof that this round's own correction is a live re-check, not a comment."""

    grant = _grant_for(_world)
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    with (
        patch(
            "manosube_agent_civilization.runtime.transport_control.boot_project",
            wraps=boot_project,
        ) as mock_boot,
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
    ):
        mock_run.return_value = (_mocked_probe_stdout(), b"", 0)
        adapter.observe(
            target_identity=_world["target_identity"], boundary=_boundary_matching(grant)
        )
    assert mock_boot.call_count > 0


def test_observe_refuses_a_boundary_whose_timeout_exceeds_the_grants_own_signed_ceiling(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR2-F2: ``boundary.timeout_seconds`` is bound to the grant's own signed
    ``max_timeout_seconds`` ceiling, re-checked live at the attempt -- a Boundary alone can
    never make an unattended probe wait longer than the Human Authority actually approved."""

    grant = _grant_for(_world, max_timeout_seconds=5)
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
    )
    boundary = ssh_boundary_for(
        host=grant["host"],
        port=grant["port"],
        user=grant["user"],
        probe_identity=grant["probe_identity"],
        permitted_fields=list(grant["permitted_fields"]),
        issued_at=_NOW,
        expires_at="2026-06-01T01:00:00Z",
        timeout_seconds=3600,
    )
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        adapter.observe(target_identity=_world["target_identity"], boundary=boundary)
    assert mock_run.call_count == 0


def test_observe_refuses_a_target_whose_deployment_fingerprint_has_rotated(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR2-F2: a grant issued against one claimed ``deployment_fingerprint`` must
    never be reused once the target's own real declared identity has rotated to a new one --
    even though every stable coordinate (provider/deployment_id/instance_identity) still
    matches."""

    grant = _grant_for(_world)
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
    )
    rotated_target_identity = dict(_world["target_identity"])
    rotated_target_identity["deployment_fingerprint"] = "sha256:" + "e" * 64
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        adapter.observe(
            target_identity=rotated_target_identity, boundary=_boundary_matching(grant)
        )
    assert mock_run.call_count == 0


def test_adapter_constructed_for_github_actions_requires_the_grant_to_permit_that_transport(
    _world: dict[str, Any],
) -> None:
    """PR #108 Structural Review Round 2, SR2-F1: ``SshRuntimeAdapter`` now executes for
    either of its two own executable transports, and requires the grant to explicitly permit
    *that exact one* -- a grant permitting only ``PREAUTHORIZED_UNATTENDED_SSH`` (never
    ``GITHUB_ACTIONS``) must refuse construction for the Actions case, with zero subprocess
    calls, even though it would construct perfectly well for the unattended case."""

    grant = _grant_for(_world, permitted_transports=["PREAUTHORIZED_UNATTENDED_SSH"])
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        SshRuntimeAdapter(
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
            transport="GITHUB_ACTIONS",
        )
    assert mock_run.call_count == 0

    # The identical grant genuinely constructs fine for the transport it actually permits.
    SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        transport="PREAUTHORIZED_UNATTENDED_SSH",
    )


def test_adapter_executes_the_real_observation_under_the_github_actions_transport(
    _world: dict[str, Any],
) -> None:
    """The positive sibling: a grant that explicitly permits ``GITHUB_ACTIONS`` genuinely
    reaches ``OBSERVED`` through this identical adapter -- never a second, parallel
    implementation for that transport."""

    grant = _grant_for(_world, permitted_transports=["GITHUB_ACTIONS"])
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        transport="GITHUB_ACTIONS",
        now_fn=lambda: _NOW,
    )
    with patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run:
        mock_run.return_value = (_mocked_probe_stdout(), b"", 0)
        outcome = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=_world["target_identity"],
            boundary=_boundary_matching(grant),
            adapter=adapter,
            observed_at=_NOW,
        )
    assert mock_run.call_count == 1
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"


def test_adapter_refuses_construction_for_manual_ssh(_world: dict[str, Any]) -> None:
    """``MANUAL_SSH``'s whole point is that a Human runs the rendered command themselves --
    this package must never construct a live, executable adapter for it, however the grant
    itself is scoped."""

    grant = _grant_for(
        _world, permitted_transports=["MANUAL_SSH", "PREAUTHORIZED_UNATTENDED_SSH"]
    )
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        SshRuntimeAdapter(
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
            transport="MANUAL_SSH",
        )
    assert mock_run.call_count == 0


def test_a_grant_scoped_to_a_different_project_is_refused_not_merely_the_target_unchecked(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR1 F1 corrects the first delivery's own claim here: a grant naming the wrong
    project is refused by ``require_valid_grant`` itself -- scope binding is not left to
    "a caller is responsible for matching it", it is enforced structurally."""

    grant = runtime_observation_grant_for(
        project_id="some-other-project",
        project_binding_id=_world["project_binding_id"],
        permitted_fields=["hostname"],
    )
    with pytest.raises(RuntimeRequirementError):
        select_transport(
            actions_status="UNAVAILABLE",
            requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )


# ---------------------------------------------------------------------------
# PR #108 Structural Review Round 3, SR3-F3(A): CapturedProbeReportRuntimeAdapter --
# import-output's own captured-transcript replay reaches the identical canonical route,
# the identical grant-scoped validation, and a real envelope/receipt, never a second,
# looser, unbound parser.
# ---------------------------------------------------------------------------


def test_captured_report_adapter_reaches_a_real_observed_outcome_through_the_identical_route(
    _world: dict[str, Any],
) -> None:
    """The positive path: a Human-captured transcript, replayed through
    ``CapturedProbeReportRuntimeAdapter``, reaches a genuine ``OBSERVED`` outcome and a real,
    committed ``runtime_observation_envelope`` -- never a second, parallel return path."""

    grant = _grant_for(_world, permitted_transports=["MANUAL_SSH"])
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=_mocked_probe_stdout(),
        captured_stderr=b"",
        captured_returncode=0,
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=_world["target_identity"],
        boundary=_boundary_matching(grant),
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"] == {"hostname": "vps1"}
    assert outcome["receipt"].status == "VERIFIED"
    resolved = _world["store"].resolve_record(
        _world["project_id"],
        "runtime_observation_envelope",
        outcome["envelope"]["runtime_observation_envelope_id"],
    )
    assert resolved == outcome["envelope"]


def test_captured_report_adapter_refuses_construction_unless_the_grant_permits_manual_ssh(
    _world: dict[str, Any],
) -> None:
    """``CapturedProbeReportRuntimeAdapter`` is hardcoded to exactly ``MANUAL_SSH`` -- a grant
    that never permits it (only the unattended/Actions transports) must refuse construction,
    exactly as ``SshRuntimeAdapter`` itself refuses construction for a transport its own grant
    does not permit."""

    grant = _grant_for(_world, permitted_transports=["PREAUTHORIZED_UNATTENDED_SSH"])
    with pytest.raises(RuntimeRequirementError):
        CapturedProbeReportRuntimeAdapter(
            captured_stdout=_mocked_probe_stdout(),
            captured_stderr=b"",
            captured_returncode=0,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )


def test_captured_report_adapter_refuses_a_lying_excerpt_counter_through_the_real_route(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR3-F3(A)'s own decisive reproduction: a captured report naming an unpermitted
    excerpt field with a self-reported line count that lies about its own real content must
    reach ``MALFORMED`` through the real canonical route -- never an echoed ``ok: true``."""

    grant = _grant_for(
        _world,
        permitted_transports=["MANUAL_SSH"],
        probe_identity="SOURCE_LOG_EXCERPT_BOUNDED",
        permitted_fields=["hostname"],
        max_lines=1,
        max_output_bytes=64,
    )
    lying_stdout = _mocked_probe_stdout(
        fields={
            "hostname": "vps1",
            "source_available": True,
            "source_excerpt": "a\nb\nc",
            "source_line_count": -1,
            "source_excerpt_byte_length": 999,
            "log_available": False,
            "log_excerpt": None,
            "log_line_count": None,
            "log_excerpt_byte_length": None,
        }
    )
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=lying_stdout,
        captured_stderr=b"",
        captured_returncode=0,
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    boundary = ssh_boundary_for(
        host=grant["host"],
        port=grant["port"],
        user=grant["user"],
        probe_identity=grant["probe_identity"],
        permitted_fields=["hostname"],
        issued_at=_NOW,
        expires_at="2026-06-01T01:00:00Z",
    )
    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=_world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] == "MALFORMED"
    assert outcome["envelope"]["observed_fields"] is None


def test_captured_report_adapter_enforces_the_grants_own_max_output_bytes(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR3-F3(A): a captured transcript never goes through
    ``_run_bounded_subprocess`` at all, so the grant's own ``max_output_bytes`` must be
    enforced again, directly, inside the shared classification method -- never silently
    skipped merely because this path never spawned a process to begin with."""

    grant = _grant_for(_world, permitted_transports=["MANUAL_SSH"], max_output_bytes=10)
    oversized_stdout = _mocked_probe_stdout() + b" " * 1000
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=oversized_stdout,
        captured_stderr=b"",
        captured_returncode=0,
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=_world["target_identity"],
        boundary=_boundary_matching(grant),
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] == "MALFORMED"


def test_captured_report_adapter_a_nonzero_exit_code_is_never_observed(
    _world: dict[str, Any],
) -> None:
    """PR #108 Structural Review Round 4, SR4-F3: ``captured_returncode``/``captured_stderr``
    are now required, explicit CLI-supplied facts -- never a silent default of ``0``/``b""``
    standing in for a capture the operator never actually attested. A report left behind by a
    command that genuinely exited nonzero must be refused exactly as a live subprocess result
    with that same exit code already is, never classified as though the command had
    succeeded."""

    grant = _grant_for(_world, permitted_transports=["MANUAL_SSH"])
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=_mocked_probe_stdout(),
        captured_stderr=b"",
        captured_returncode=1,
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=_world["target_identity"],
        boundary=_boundary_matching(grant),
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] == "MALFORMED"


def test_captured_report_adapter_a_permission_denied_exit_is_classified_honestly(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR4-F3's own positive-provenance sibling: an operator who genuinely captured a
    ``255``/"Permission denied" exit from the rendered command gets that honest classification
    back, exactly as a live subprocess result with the identical exit/stderr would."""

    grant = _grant_for(_world, permitted_transports=["MANUAL_SSH"])
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=b"",
        captured_stderr=b"Permission denied (publickey).",
        captured_returncode=255,
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=_world["target_identity"],
        boundary=_boundary_matching(grant),
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] == "PERMISSION_DENIED"


def test_observe_redacts_exactly_the_grants_own_signed_redaction_fields(
    _world: dict[str, Any],
) -> None:
    """PR #108 Structural Review Round 4, SR4-F3: a grant's own signed ``redaction_fields`` is
    what actually controls what gets redacted -- end to end, through the real route, a field
    the grant requires redacted is never persisted in the clear, even though it was genuinely
    observed and reported."""

    grant = _grant_for(
        _world, permitted_fields=["hostname"], redaction_fields=["hostname"]
    )
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    boundary = _boundary_matching(grant)
    boundary["redaction_fields"] = ["hostname"]
    with patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run:
        mock_run.return_value = (_mocked_probe_stdout(), b"", 0)
        outcome = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=_world["target_identity"],
            boundary=boundary,
            adapter=adapter,
            observed_at=_NOW,
        )
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"] == {"hostname": "<REDACTED>"}


def test_observe_refuses_a_boundary_that_redacts_less_than_the_grant_requires(
    _world: dict[str, Any],
) -> None:
    """The decisive SR4-F3 case, end to end: a grant that signs
    ``redaction_fields=["hostname"]`` must refuse an attempt whose own Boundary hardcodes
    ``redaction_fields=[]`` -- with zero subprocess calls, before anything is ever observed."""

    grant = _grant_for(
        _world, permitted_fields=["hostname"], redaction_fields=["hostname"]
    )
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    boundary = _boundary_matching(grant)
    boundary["redaction_fields"] = []
    with (
        patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        adapter.observe(target_identity=_world["target_identity"], boundary=boundary)
    assert mock_run.call_count == 0


# ---------------------------------------------------------------------------
# PR #108 Structural Review Round 4, SR4-F3: the real Evidence handoff, invoked from a genuine
# receipt this file's own real route produced -- never fabricated eligibility, and never
# stopping at the envelope/receipt the way the prior rounds' own claims implied.
# ---------------------------------------------------------------------------


def test_route_runtime_observation_to_evidence_hands_off_a_real_receipt(
    _world: dict[str, Any],
) -> None:
    """A real receipt, produced by this file's own real
    :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` call, reaches a
    genuine Change-Free Verification Evidence record through the existing, unchanged
    :func:`~manosube_agent_civilization.runtime.evidence_handoff.
    route_runtime_observation_to_evidence` -- never a fabricated eligibility or a second,
    parallel Evidence owner. The embedded fixture Observation/Difference request
    (``tests.evidence_helpers``) is rewritten onto this file's own real ``project_id`` so the
    handoff's own project-match check has something genuine to compare against, rather than
    inventing a new Observation pipeline from nothing."""

    import json as _json

    from tests.evidence_helpers import change_free_verification_evidence_request

    from manosube_agent_civilization.runtime import route_runtime_observation_to_evidence

    grant = _grant_for(_world)
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    with patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run:
        mock_run.return_value = (_mocked_probe_stdout(), b"", 0)
        outcome = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=_world["target_identity"],
            boundary=_boundary_matching(grant),
            adapter=adapter,
            observed_at=_NOW,
        )
    assert mock_run.call_count == 1

    raw_request = change_free_verification_evidence_request(provenance=None)
    rewritten = _json.loads(
        _json.dumps(raw_request).replace("PRJ-0001", _world["project_id"])
    )

    evidence = route_runtime_observation_to_evidence(
        _world["store"], outcome["receipt"], _world["project_id"], rewritten
    )
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    assert evidence["target"]["project_id"] == _world["project_id"]
    assert (
        evidence["verification_result_provenance"]["requirement_id"]
        == outcome["envelope"]["runtime_observation_envelope_id"]
    )
    assert (
        evidence["verification_result_provenance"]["observations"]["observation_outcome"]
        == "OBSERVED"
    )


def test_route_runtime_observation_to_evidence_refuses_a_project_mismatched_request(
    _world: dict[str, Any],
) -> None:
    """The existing, unchanged owner's own refusal -- an ``evidence_request`` whose embedded
    Observation names a different project than the real receipt's own never silently succeeds;
    this is the precise bounded status this round's own CLI reports rather than a fabricated
    success."""

    from tests.evidence_helpers import change_free_verification_evidence_request

    from manosube_agent_civilization.runtime import route_runtime_observation_to_evidence
    from manosube_agent_civilization.runtime.errors import RuntimeRequirementError as _RRE

    grant = _grant_for(_world)
    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    with patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run:
        mock_run.return_value = (_mocked_probe_stdout(), b"", 0)
        outcome = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=_world["target_identity"],
            boundary=_boundary_matching(grant),
            adapter=adapter,
            observed_at=_NOW,
        )

    # Deliberately NOT rewritten onto the real project_id -- still names the fixture's own
    # "PRJ-0001", which the real receipt's own project never matches.
    mismatched_request = change_free_verification_evidence_request(provenance=None)
    with pytest.raises(_RRE):
        route_runtime_observation_to_evidence(
            _world["store"], outcome["receipt"], _world["project_id"], mismatched_request
        )


# ---------------------------------------------------------------------------
# PR #108 Structural Review Round 3, SR3-F1: the genuinely independent, bounded controller,
# end to end -- its own decision feeding the identical real route the other transports use.
# ---------------------------------------------------------------------------


def test_controller_fallback_authorized_reaches_a_real_observed_outcome_with_no_human_choice(
    _world: dict[str, Any],
) -> None:
    """The adopted neutral end-to-end proof: Actions never becomes available and the
    controller's own bounded deadline is reached with no decisive answer either -- the grant
    already, explicitly preauthorizes the fallback, so this reaches a genuine ``OBSERVED``
    outcome with zero per-attempt Human transport choice of any kind."""

    grant = _grant_for(_world)
    operation_id = compute_runtime_observation_operation_id(
        grant_id=grant["grant_id"],
        provider=_world["target_identity"]["provider"],
        deployment_id=_world["target_identity"]["deployment_id"],
        instance_identity=_world["target_identity"]["instance_identity"],
        request_id="REQ-1",
    )
    polls = {"count": 0}

    def _dispatch_status_provider(remaining_seconds: float) -> str:
        del remaining_seconds
        polls["count"] += 1
        return "UNKNOWN"

    resolution = resolve_bounded_actions_fallback(
        operation_id=operation_id,
        dispatch_status_provider=_dispatch_status_provider,
        start_deadline_seconds=60.0,
        max_polls=3,
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        sleep_fn=lambda _seconds: None,
    )
    assert resolution.decision == "FALLBACK_AUTHORIZED"
    assert polls["count"] == 3

    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        transport="PREAUTHORIZED_UNATTENDED_SSH",
        now_fn=lambda: _NOW,
    )
    with patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run:
        mock_run.return_value = (_mocked_probe_stdout(), b"", 0)
        outcome = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=_world["target_identity"],
            boundary=_boundary_matching(grant),
            adapter=adapter,
            observed_at=_NOW,
        )
    assert mock_run.call_count == 1
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["receipt"].status == "VERIFIED"


def test_controller_missing_fallback_grant_reaches_zero_target_calls(
    _world: dict[str, Any],
) -> None:
    """The adopted neutral end-to-end proof's other half: a grant that never authorizes
    ``PREAUTHORIZED_UNATTENDED_SSH`` refuses the fallback decision itself -- there is no
    executable path from there to any adapter construction or subprocess call."""

    grant = _grant_for(_world, permitted_transports=["GITHUB_ACTIONS", "MANUAL_SSH"])
    operation_id = compute_runtime_observation_operation_id(
        grant_id=grant["grant_id"],
        provider=_world["target_identity"]["provider"],
        deployment_id=_world["target_identity"]["deployment_id"],
        instance_identity=_world["target_identity"]["instance_identity"],
        request_id="REQ-1",
    )
    with patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run:
        resolution = resolve_bounded_actions_fallback(
            operation_id=operation_id,
            dispatch_status_provider=lambda _remaining_seconds: "UNAVAILABLE",
            start_deadline_seconds=60.0,
            max_polls=3,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
            sleep_fn=lambda _seconds: None,
        )
        assert resolution.decision == "FALLBACK_REFUSED_NO_GRANT"
    assert mock_run.call_count == 0


# ---------------------------------------------------------------------------
# PR #108 Structural Review Round 4, SR4-F4: the real, shipped probe script, run as a real
# subprocess against its own real sibling-file resolution -- never a reimplementation, never
# only the adapter class that happens to parse its output. The SR3 handoff's own clarification
# ("existing authorized runtime test files MUST exercise the relevant scripts via
# importlib/subprocess") is what licenses this section in this already-authorized file.
# ---------------------------------------------------------------------------


def _config_fingerprint(source_excerpt_path: str, log_excerpt_path: str) -> str:
    """The identical digest :func:`scripts.runtime_observation_probe._deployment_config_
    fingerprint` computes -- restated here, over the same two plain strings, rather than
    imported, since this test module exercises the script as a real subprocess, never as an
    importable library."""

    payload = json.dumps(
        {"source_excerpt_path": source_excerpt_path, "log_excerpt_path": log_excerpt_path},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _deployed_probe_script(tmp_path: Path, **sibling_files: str | None) -> Path:
    """Copy this repository's own real, shipped probe script into an isolated directory (never
    the real one on disk, and never executed in place), optionally writing named sibling files
    (``"runtime_observation_probe.config.json"``, ``"runtime_observation_probe.approved_config.
    json"``) alongside it, and return the copied script's own path."""

    deploy_dir = tmp_path / "probe-deploy"
    deploy_dir.mkdir()
    script_path = deploy_dir / "runtime_observation_probe.py"
    shutil.copyfile(_PROBE_SCRIPT_SOURCE, script_path)
    for filename, content in sibling_files.items():
        if content is None:
            continue
        (deploy_dir / filename).write_text(content, encoding="utf-8")
    return script_path


def _run_probe_script(script_path: Path, probe_identity: str, *, timeout: float = 10.0) -> dict[str, Any]:
    result = subprocess.run(  # noqa: S603 -- fixed executable/argv, test-controlled script copy
        [sys.executable, str(script_path), probe_identity],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_probe_script_reports_the_identical_pinned_digest_the_adapter_checks_against(
    tmp_path: Path,
) -> None:
    """The copied script is byte-identical to the one this repository ships and
    ``SshRuntimeAdapter`` pins -- a sanity check that every test below is exercising the real
    artifact, not a stale or edited copy."""

    script_path = _deployed_probe_script(tmp_path)
    report = _run_probe_script(script_path, "OS_HEALTH_SNAPSHOT_BOUNDED")
    assert report["probe_script_sha256"] == SSH_PROBE_SCRIPT_SHA256


def test_probe_script_os_health_identity_bypasses_the_approved_config_gate(
    tmp_path: Path,
) -> None:
    """SR4-F4's own pre-read gate applies to ``SOURCE_LOG_EXCERPT_BOUNDED`` alone --
    ``OS_HEALTH_SNAPSHOT_BOUNDED`` never reads configurable excerpt paths at all, so it must
    succeed with no sibling files of any kind present."""

    script_path = _deployed_probe_script(tmp_path)
    report = _run_probe_script(script_path, "OS_HEALTH_SNAPSHOT_BOUNDED")
    assert report["ok"] is True
    assert report["fields"]["hostname"]


def test_probe_script_succeeds_with_a_genuinely_authorized_configuration(
    tmp_path: Path,
) -> None:
    """The positive path: a sibling path-configuration file and a sibling approved-fingerprint
    file that genuinely names the configuration's own real digest -- the probe reads the real
    configured files and reports their content."""

    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    source_path.write_text("line one\nline two\n", encoding="utf-8")
    log_path.write_text("log line\n", encoding="utf-8")
    fingerprint = _config_fingerprint(str(source_path), str(log_path))
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {"source_excerpt_path": str(source_path), "log_excerpt_path": str(log_path)}
            ),
            "runtime_observation_probe.approved_config.json": json.dumps(
                {"deployment_config_fingerprint": fingerprint}
            ),
        },
    )
    report = _run_probe_script(script_path, "SOURCE_LOG_EXCERPT_BOUNDED")
    assert report["ok"] is True
    assert report["fields"]["source_available"] is True
    assert report["fields"]["source_excerpt"] == "line one\nline two"
    assert report["deployment_config_fingerprint"] == fingerprint


def test_probe_script_refuses_before_any_read_when_approved_config_is_entirely_absent(
    tmp_path: Path,
) -> None:
    """PR #108 Structural Review Round 4, SR4-F4's own decisive case: a sibling path-
    configuration file names real, existing files -- so a probe that proceeded to read them
    would succeed -- but no ``runtime_observation_probe.approved_config.json`` exists at all.
    The refusal must be ``CONFIG_NOT_AUTHORIZED``, never ``NOT_FOUND``: the latter would mean
    this script actually attempted the read and then discovered an absence, which is exactly
    what this round's own correction refuses to let happen."""

    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    source_path.write_text("should never be read", encoding="utf-8")
    log_path.write_text("should never be read either", encoding="utf-8")
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {"source_excerpt_path": str(source_path), "log_excerpt_path": str(log_path)}
            ),
        },
    )
    report = _run_probe_script(script_path, "SOURCE_LOG_EXCERPT_BOUNDED")
    assert report["ok"] is False
    assert report["reason"] == "CONFIG_NOT_AUTHORIZED"
    assert report["fields"] is None


def test_probe_script_refuses_before_any_read_when_approved_config_is_malformed(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    source_path.write_text("should never be read", encoding="utf-8")
    log_path.write_text("should never be read either", encoding="utf-8")
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {"source_excerpt_path": str(source_path), "log_excerpt_path": str(log_path)}
            ),
            "runtime_observation_probe.approved_config.json": "{not valid json",
        },
    )
    report = _run_probe_script(script_path, "SOURCE_LOG_EXCERPT_BOUNDED")
    assert report["ok"] is False
    assert report["reason"] == "CONFIG_NOT_AUTHORIZED"
    assert report["fields"] is None


def test_probe_script_refuses_before_any_read_when_the_approved_digest_does_not_match(
    tmp_path: Path,
) -> None:
    """The same-name-artifact-replacement scenario the handoff names: the sibling path config
    was changed (or was never the one approved) since the approval file was written -- the
    computed digest and the approved one disagree, and the probe must refuse rather than read
    under the stale approval."""

    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    source_path.write_text("should never be read", encoding="utf-8")
    log_path.write_text("should never be read either", encoding="utf-8")
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {"source_excerpt_path": str(source_path), "log_excerpt_path": str(log_path)}
            ),
            "runtime_observation_probe.approved_config.json": json.dumps(
                {"deployment_config_fingerprint": "f" * 64}
            ),
        },
    )
    report = _run_probe_script(script_path, "SOURCE_LOG_EXCERPT_BOUNDED")
    assert report["ok"] is False
    assert report["reason"] == "CONFIG_NOT_AUTHORIZED"
    assert report["fields"] is None


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="requires a POSIX mkfifo")
def test_probe_script_refusal_genuinely_precedes_any_attempt_to_open_the_source_path(
    tmp_path: Path,
) -> None:
    """The strongest available proof that this round's own authorization check runs *before*
    any read is attempted, not merely that the final report happens to say so: the configured
    ``source_excerpt_path`` is a named pipe nothing ever writes to, which blocks forever on any
    process that actually tries to open it for reading. With no approved-config file at all,
    this subprocess must return almost immediately; if this script instead attempted the read
    first, the process would hang and this test's own short timeout would fire."""

    fifo_path = tmp_path / "source_excerpt_fifo"
    os.mkfifo(fifo_path)
    log_path = tmp_path / "observed.log"
    log_path.write_text("should never be read either", encoding="utf-8")
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {"source_excerpt_path": str(fifo_path), "log_excerpt_path": str(log_path)}
            ),
        },
    )
    try:
        report = _run_probe_script(script_path, "SOURCE_LOG_EXCERPT_BOUNDED", timeout=5.0)
    except subprocess.TimeoutExpired:
        pytest.fail(
            "the probe script did not return within the bounded timeout -- it attempted to "
            "open the unauthorized source path (which blocks forever on an unopened FIFO) "
            "instead of refusing before any read, exactly the regression SR4-F4 closes"
        )
    assert report["ok"] is False
    assert report["reason"] == "CONFIG_NOT_AUTHORIZED"


def test_probe_script_preserves_the_descriptor_relative_ancestor_symlink_refusal(
    tmp_path: Path,
) -> None:
    """PR #108 Structural Review Round 3, SR3-F3(B)'s own regression, kept as a permanent
    subprocess-level proof now that this file genuinely exercises the script: a configured
    source path reached only through a symlinked *ancestor* directory is still refused, even
    once a genuinely authorized configuration gate (SR4-F4) is satisfied -- the two defenses
    are independent, and neither substitutes for the other."""

    real_dir = tmp_path / "real-data"
    real_dir.mkdir()
    source_path = real_dir / "source_excerpt.txt"
    source_path.write_text("must not be read through the symlinked ancestor", encoding="utf-8")
    log_path = tmp_path / "observed.log"
    log_path.write_text("log line\n", encoding="utf-8")

    symlinked_ancestor = tmp_path / "symlinked-ancestor"
    symlinked_ancestor.symlink_to(real_dir, target_is_directory=True)
    source_path_via_symlink = symlinked_ancestor / "source_excerpt.txt"

    fingerprint = _config_fingerprint(str(source_path_via_symlink), str(log_path))
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {
                    "source_excerpt_path": str(source_path_via_symlink),
                    "log_excerpt_path": str(log_path),
                }
            ),
            "runtime_observation_probe.approved_config.json": json.dumps(
                {"deployment_config_fingerprint": fingerprint}
            ),
        },
    )
    report = _run_probe_script(script_path, "SOURCE_LOG_EXCERPT_BOUNDED")
    # The ancestor-symlink refusal makes the source path unavailable (not a hard failure of
    # the whole probe) -- the log excerpt, reached through no symlink, is still reported.
    assert report["ok"] is True
    assert report["fields"]["source_available"] is False
    assert report["fields"]["log_available"] is True


# ---------------------------------------------------------------------------
# PR #108 Structural Review Round 4, SR4-F1/F3: the real CLI script, run as a real
# subprocess against a real, Boot-bound on-disk Store -- "test actual CLI wiring, not only
# the adapter class", exactly as the handoff requires.
# ---------------------------------------------------------------------------


def _run_transport_cli(args: list[str], *, timeout: float = 30.0) -> dict[str, Any]:
    result = subprocess.run(  # noqa: S603 -- fixed executable/argv, test-controlled args
        [sys.executable, str(_TRANSPORT_SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    assert result.returncode in (0, 1), result.stderr
    return json.loads(result.stdout)


def test_cli_import_output_wires_captured_provenance_and_redaction_through_the_real_route(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    """PR #108 Structural Review Round 4, SR4-F2/F3, exercised through the real CLI script
    (never only ``CapturedProbeReportRuntimeAdapter`` directly): ``--captured-at`` becomes the
    real Envelope's own ``observed_at``, ``--captured-exit-code`` is required and genuinely
    threaded through to the adapter, and the grant's own signed ``redaction_fields`` -- never a
    hardcoded ``[]`` -- is what the real, committed Envelope's own ``observed_fields`` actually
    redacts."""

    grant = _grant_for(
        _world, permitted_transports=["MANUAL_SSH"], redaction_fields=["hostname"]
    )
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    target_file = tmp_path / "target_identity.json"
    target_file.write_text(json.dumps(_world["target_identity"]), encoding="utf-8")
    report_file = tmp_path / "report.json"
    report_file.write_bytes(_mocked_probe_stdout())

    out = _run_transport_cli(
        [
            "import-output",
            "--report-file",
            str(report_file),
            "--grant-file",
            str(grant_file),
            "--target-identity-file",
            str(target_file),
            "--store-root",
            str(_world["store"].root),
            "--schema-root",
            str(_world["store"].schema_root),
            "--project-id",
            _world["project_id"],
            "--project-binding-id",
            _world["project_binding_id"],
            "--permitted-fields",
            ",".join(grant["permitted_fields"]),
            "--now",
            _NOW,
            "--captured-at",
            _NOW,
            "--captured-exit-code",
            "0",
        ]
    )
    assert out["ok"] is True
    assert out["observation_outcome"] == "OBSERVED"
    assert out["observed_fields"] == {"hostname": "<REDACTED>"}
    assert out["evidence_handoff"] == {"status": "NOT_REQUESTED"}

    resolved = _world["store"].resolve_record(
        _world["project_id"], "runtime_observation_envelope", out["envelope_id"]
    )
    assert resolved["observed_at"] == _NOW


def test_cli_import_output_requires_an_explicit_captured_exit_code(tmp_path: Path) -> None:
    """PR #108 SR4-F3: argparse itself refuses to run without ``--captured-exit-code`` --
    there is no silent default standing in for a capture the operator never attested."""

    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(_TRANSPORT_SCRIPT),
            "import-output",
            "--report-file",
            str(tmp_path / "report.json"),
            "--grant-file",
            str(tmp_path / "grant.json"),
            "--target-identity-file",
            str(tmp_path / "target_identity.json"),
            "--store-root",
            str(tmp_path / "backend"),
            "--schema-root",
            str(tmp_path / "schema"),
            "--project-id",
            "PRJ-X",
            "--project-binding-id",
            "PROJBIND-X",
            "--permitted-fields",
            "hostname",
            "--now",
            _NOW,
            "--captured-at",
            _NOW,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "--captured-exit-code" in result.stderr


def test_cli_run_controller_reports_the_real_elapsed_time_bound_with_zero_target_calls(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    """PR #108 Structural Review Round 4, SR4-F1, exercised through the real CLI script:
    ``--start-deadline-seconds``/``--max-polls``/``--request-id`` all genuinely reach
    :func:`~manosube_agent_civilization.runtime.transport_control.
    resolve_bounded_actions_fallback`, and a grant that never permits
    ``PREAUTHORIZED_UNATTENDED_SSH`` reaches ``FALLBACK_REFUSED_NO_GRANT`` with zero target
    calls and no claim-state file ever written (nothing was genuinely executed to claim)."""

    grant = _grant_for(_world, permitted_transports=["GITHUB_ACTIONS", "MANUAL_SSH"])
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    target_file = tmp_path / "target_identity.json"
    target_file.write_text(json.dumps(_world["target_identity"]), encoding="utf-8")
    claim_state_file = tmp_path / "claim_state.json"

    base_args = [
        "run-controller",
        "--grant-file",
        str(grant_file),
        "--target-identity-file",
        str(target_file),
        "--store-root",
        str(_world["store"].root),
        "--schema-root",
        str(_world["store"].schema_root),
        "--project-id",
        _world["project_id"],
        "--project-binding-id",
        _world["project_binding_id"],
        "--permitted-fields",
        "hostname",
        "--now",
        _NOW,
        "--dispatch-status-sequence",
        "UNKNOWN,UNKNOWN,UNKNOWN",
        "--start-deadline-seconds",
        "60",
        "--max-polls",
        "3",
        "--claim-state-file",
        str(claim_state_file),
    ]

    out = _run_transport_cli([*base_args, "--request-id", "REQ-CLI-1"])
    assert out["ok"] is True
    assert out["decision"] == "FALLBACK_REFUSED_NO_GRANT"
    assert out["executed"] is False
    assert out["final_dispatch_status"] == "UNKNOWN"
    assert out["poll_count"] == 3
    assert not claim_state_file.exists()

    different_request = _run_transport_cli([*base_args, "--request-id", "REQ-CLI-2"])
    assert different_request["operation_id"] != out["operation_id"]
