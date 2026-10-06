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
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
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
from manosube_agent_civilization.runtime.engine import current_utc_instant
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.network import render_ssh_command_argv
from manosube_agent_civilization.runtime.route import observe_runtime_target
from manosube_agent_civilization.runtime.transport_control import (
    compute_runtime_observation_operation_id,
    resolve_bounded_actions_fallback,
    select_transport,
)
from manosube_agent_civilization.runtime.types import (
    SSH_PROBE_LAUNCHER_CODE,
    SSH_PROBE_SCRIPT_SHA256,
)

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


def _load_transport_module() -> Any:
    """Import ``scripts/runtime_observation_transport.py`` as a real module via
    ``importlib`` (the SR3 handoff's own licensed alternative to a real subprocess, used here
    so the SR6-F1 worker-accumulation proof below can inspect this *same test process's* own
    live thread count -- a real subprocess's threads are invisible to this process)."""

    spec = importlib.util.spec_from_file_location(
        "runtime_observation_transport", _TRANSPORT_SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def _world_with_deployment_fingerprint(
    tmp_path: Path, deployment_fingerprint: str
) -> dict[str, Any]:
    """The identical world :func:`_world` builds, parameterized over the target's own
    canonical ``deployment_fingerprint`` (PR #110 Structural Review Round 1, F1 correction,
    2026-10-06) -- used by the real-probe-to-canonical-route completion proofs below, which
    need a target whose declared identity genuinely matches an isolated identity file's own
    content, in the identical canonical ``sha256:<64 hex>`` shape every other fixture in this
    module already uses, never an arbitrary string a declared identity would never actually
    take."""

    store, ctx = bound(tmp_path)
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    target_identity = commit_target_identity(
        store,
        ctx["project_id"],
        ctx["project_binding_id"],
        dict(boot_context.human_authority_ref),
        deployment_fingerprint=deployment_fingerprint,
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
    outcome with zero per-attempt Human transport choice of any kind.

    A deterministic fake ``monotonic_fn`` (PR #108 Structural Review Round 5, SR5-F1) advances
    this call's own clock by a full second on every read, so real elapsed time genuinely
    reaches the declared deadline by the time ``max_polls`` is exhausted -- never the real
    system clock, which an instantly-answering provider would outrun in microseconds, reaching
    the new ``DEADLINE_NOT_YET_REACHED`` decision instead of the ``FALLBACK_AUTHORIZED`` this
    proof is specifically about."""

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

    clock_state = {"t": 0.0}

    def _incrementing_clock() -> float:
        value = clock_state["t"]
        clock_state["t"] += 1.0
        return value

    resolution = resolve_bounded_actions_fallback(
        operation_id=operation_id,
        dispatch_status_provider=_dispatch_status_provider,
        start_deadline_seconds=5.9,
        max_polls=3,
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        sleep_fn=lambda _seconds: None,
        monotonic_fn=_incrementing_clock,
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


_DEFAULT_DEPLOYMENT_IDENTITY_PATH = "/etc/manosube/deployment_fingerprint"


def _config_fingerprint(
    source_excerpt_path: str,
    log_excerpt_path: str,
    deployment_identity_path: str = _DEFAULT_DEPLOYMENT_IDENTITY_PATH,
) -> str:
    """The identical digest :func:`scripts.runtime_observation_probe._deployment_config_
    fingerprint` computes -- restated here, over the same three plain strings (Issue #105
    isolated-deployment-identity correction, 2026-10-06, folded ``deployment_identity_path``
    into this digest alongside the two excerpt paths), rather than imported, since this test
    module exercises the script as a real subprocess, never as an importable library. Callers
    that do not configure ``deployment_identity_path`` in their sibling config omit the third
    argument, which defaults to the script's own shipped default -- the identical fallback
    :data:`scripts.runtime_observation_probe.EFFECTIVE_DEPLOYMENT_IDENTITY_PATH` itself uses."""

    payload = json.dumps(
        {
            "deployment_identity_path": deployment_identity_path,
            "source_excerpt_path": source_excerpt_path,
            "log_excerpt_path": log_excerpt_path,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _deployed_probe_script(tmp_path: Path, **sibling_files: str | None) -> Path:
    """Copy this repository's own real, shipped probe script into an isolated directory (never
    the real one on disk, and never executed in place), optionally writing named sibling files
    (``"runtime_observation_probe.config.json"``) alongside it, and return the copied script's
    own path."""

    deploy_dir = tmp_path / "probe-deploy"
    deploy_dir.mkdir()
    script_path = deploy_dir / "runtime_observation_probe.py"
    shutil.copyfile(_PROBE_SCRIPT_SOURCE, script_path)
    for filename, content in sibling_files.items():
        if content is None:
            continue
        (deploy_dir / filename).write_text(content, encoding="utf-8")
    return script_path


def _run_probe_script(
    script_path: Path, *probe_args: str, timeout: float = 10.0
) -> dict[str, Any]:
    """Run *script_path* as a real subprocess with exactly *probe_args* as its argv -- callers
    pass both the probe identity and (PR #108 Structural Review Round 5, SR5-F2) the second,
    required ``expected_deployment_config_fingerprint`` positional argument explicitly, so a
    test can exercise a missing or malformed one by simply passing fewer/different args, never
    through a sibling file this script no longer reads for that purpose."""

    result = subprocess.run(  # noqa: S603 -- fixed executable/argv, test-controlled script copy
        [sys.executable, str(script_path), *probe_args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _run_probe_script_bytes(
    script_path: Path, *probe_args: str, timeout: float = 10.0
) -> bytes:
    """The identical real subprocess :func:`_run_probe_script` runs, returning the raw,
    undecoded stdout bytes instead of the parsed report (PR #110 Structural Review Round 1,
    F1 correction, 2026-10-06) -- for callers that need to carry the probe's own genuine,
    unmodified output into :class:`~manosube_agent_civilization.runtime.adapter.
    CapturedProbeReportRuntimeAdapter`'s own ``captured_stdout`` exactly as a real Human
    operator's pasted-back transcript would, never a hand-written stand-in for it."""

    result = subprocess.run(  # noqa: S603 -- fixed executable/argv, test-controlled script copy
        [sys.executable, str(script_path), *probe_args],
        capture_output=True,
        timeout=timeout,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


_A_FINGERPRINT_SHAPED_VALUE = "a" * 64


def test_probe_script_reports_the_identical_pinned_digest_the_adapter_checks_against(
    tmp_path: Path,
) -> None:
    """The copied script is byte-identical to the one this repository ships and
    ``SshRuntimeAdapter`` pins -- a sanity check that every test below is exercising the real
    artifact, not a stale or edited copy."""

    script_path = _deployed_probe_script(tmp_path)
    report = _run_probe_script(
        script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", _A_FINGERPRINT_SHAPED_VALUE
    )
    assert report["probe_script_sha256"] == SSH_PROBE_SCRIPT_SHA256


def test_probe_script_os_health_identity_is_gated_by_the_live_fingerprint_too(
    tmp_path: Path,
) -> None:
    """Issue #105 isolated-deployment-identity correction (2026-10-06): before this correction,
    ``OS_HEALTH_SNAPSHOT_BOUNDED`` never read any configurable path, so an arbitrary correctly-
    shaped fingerprint argument always succeeded regardless of its value. Now that
    :data:`scripts.runtime_observation_probe.EFFECTIVE_DEPLOYMENT_IDENTITY_PATH` may itself be
    configured, ``OS_HEALTH_SNAPSHOT_BOUNDED`` is gated identically to
    ``SOURCE_LOG_EXCERPT_BOUNDED``: an arbitrary, correctly-shaped-but-wrong fingerprint is
    refused as ``CONFIG_NOT_AUTHORIZED`` -- never a silent success -- and the genuinely
    matching fingerprint for this deployment's own (here, default/unconfigured) identity path
    succeeds."""

    script_path = _deployed_probe_script(tmp_path)
    wrong_report = _run_probe_script(
        script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", _A_FINGERPRINT_SHAPED_VALUE
    )
    assert wrong_report["ok"] is False
    assert wrong_report["reason"] == "CONFIG_NOT_AUTHORIZED"
    assert wrong_report["deployment_identity"] is None

    genuine_fingerprint = _config_fingerprint(
        "/opt/manosube-runtime-observation/source_excerpt.txt",
        "/var/log/manosube-runtime-observation/observed.log",
    )
    right_report = _run_probe_script(
        script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", genuine_fingerprint
    )
    assert right_report["ok"] is True
    assert right_report["fields"]["hostname"]


def test_probe_script_succeeds_when_the_caller_supplied_fingerprint_genuinely_matches(
    tmp_path: Path,
) -> None:
    """The positive path (PR #108 Structural Review Round 5, SR5-F2): a sibling path-
    configuration file, and a caller-supplied second CLI argument that genuinely equals that
    configuration's own real digest -- exactly what a real, already Grant-verified caller's own
    SSH command (via ``network.render_ssh_command_argv``) would supply. No approval file of any
    kind is read for this purpose any longer."""

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
        },
    )
    report = _run_probe_script(script_path, "SOURCE_LOG_EXCERPT_BOUNDED", fingerprint)
    assert report["ok"] is True
    assert report["fields"]["source_available"] is True
    assert report["fields"]["source_excerpt"] == "line one\nline two"
    assert report["deployment_config_fingerprint"] == fingerprint


def test_probe_script_refuses_before_any_read_when_the_fingerprint_argument_is_entirely_absent(
    tmp_path: Path,
) -> None:
    """PR #108 Structural Review Round 5, SR5-F2's own decisive case: a sibling path-
    configuration file names real, existing files -- so a probe that proceeded to read them
    would succeed -- but the caller supplies no second positional argument at all. The refusal
    must be ``MALFORMED`` (an invocation-shape error ``main`` itself catches before ``run`` is
    ever reached), never ``NOT_FOUND``: the latter would mean this script actually attempted
    the read and then discovered an absence, which this round's own correction refuses to let
    happen either way."""

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
    assert report["reason"] == "MALFORMED"
    assert report["fields"] is None


def test_probe_script_refuses_before_any_read_when_the_fingerprint_argument_is_malshaped(
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
        },
    )
    report = _run_probe_script(script_path, "SOURCE_LOG_EXCERPT_BOUNDED", "not-hex-at-all")
    assert report["ok"] is False
    assert report["reason"] == "MALFORMED"
    assert report["fields"] is None


def test_probe_script_refuses_before_any_read_when_the_supplied_fingerprint_does_not_match(
    tmp_path: Path,
) -> None:
    """The same-name-artifact-replacement scenario the handoff names: the sibling path config
    was changed (or was never the one the caller's live Grant actually names) since the caller
    last verified it -- the computed digest and the caller-supplied one disagree, and the
    probe must refuse rather than read under a stale or mistaken value."""

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
    report = _run_probe_script(
        script_path, "SOURCE_LOG_EXCERPT_BOUNDED", _A_FINGERPRINT_SHAPED_VALUE
    )
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
    process that actually tries to open it for reading. With a caller-supplied fingerprint that
    does not match this deployment's own real configuration, this subprocess must return
    almost immediately; if this script instead attempted the read first, the process would
    hang and this test's own short timeout would fire."""

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
        report = _run_probe_script(
            script_path,
            "SOURCE_LOG_EXCERPT_BOUNDED",
            _A_FINGERPRINT_SHAPED_VALUE,
            timeout=5.0,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            "the probe script did not return within the bounded timeout -- it attempted to "
            "open the unauthorized source path (which blocks forever on an unopened FIFO) "
            "instead of refusing before any read, exactly the regression SR4-F4/SR5-F2 closes"
        )
    assert report["ok"] is False
    assert report["reason"] == "CONFIG_NOT_AUTHORIZED"


def test_probe_script_preserves_the_descriptor_relative_ancestor_symlink_refusal(
    tmp_path: Path,
) -> None:
    """PR #108 Structural Review Round 3, SR3-F3(B)'s own regression, kept as a permanent
    subprocess-level proof now that this file genuinely exercises the script: a configured
    source path reached only through a symlinked *ancestor* directory is still refused, even
    once a genuinely authorized live fingerprint gate (SR5-F2) is satisfied -- the two defenses
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
        },
    )
    report = _run_probe_script(script_path, "SOURCE_LOG_EXCERPT_BOUNDED", fingerprint)
    # The ancestor-symlink refusal makes the source path unavailable (not a hard failure of
    # the whole probe) -- the log excerpt, reached through no symlink, is still reported.
    assert report["ok"] is True
    assert report["fields"]["source_available"] is False
    assert report["fields"]["log_available"] is True


def _launcher_remote_command(
    *,
    expected_probe_script_sha256: str,
    probe_identity: str = "OS_HEALTH_SNAPSHOT_BOUNDED",
    expected_deployment_config_fingerprint: str = _A_FINGERPRINT_SHAPED_VALUE,
) -> str:
    """Return the exact remote-command string :func:`~manosube_agent_civilization.runtime.
    network.render_ssh_command_argv` builds for these fields -- the last argv element, which is
    what a target's own login shell actually receives and parses (PR #108 Structural Review
    Round 6, SR6-F2)."""

    argv = render_ssh_command_argv(
        host="127.0.0.1",
        port=22,
        user="probe",
        probe_identity=probe_identity,
        expected_probe_script_sha256=expected_probe_script_sha256,
        expected_deployment_config_fingerprint=expected_deployment_config_fingerprint,
    )
    return argv[-1]


def _run_remote_command_in(remote_command: str, *, cwd: Path, timeout: float = 10.0) -> dict[str, Any]:
    """Run *remote_command* through a real ``sh -c`` subprocess rooted at *cwd* -- the
    identical interpretation step a target's own sshd-invoked login shell performs on whatever
    string this package's own SSH command actually sends it, without requiring a real `ssh`/
    `sshd` binary (none exists in this delivery's own build environment, disclosed and
    unchanged since Issue #105's own first round)."""

    sh_executable = shutil.which("sh") or "/bin/sh"
    result = subprocess.run(  # noqa: S603 -- fixed, reviewed launcher string; see this function's own docstring
        [sh_executable, "-c", remote_command],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_launcher_succeeds_against_the_genuine_artifact_and_genuine_configuration(
    tmp_path: Path,
) -> None:
    """PR #108 Structural Review Round 6, SR6-F2's own required positive-path proof: the real
    launcher :func:`~manosube_agent_civilization.runtime.network.render_ssh_command_argv`
    builds, run through a real shell against a real, unmodified copy of the shipped probe
    script and a real, matching sibling path configuration, reaches a genuine, successful
    bounded observation -- proving the launcher's own pre-execution artifact check does not
    itself break the legitimate path it is meant to protect."""

    deploy_dir = tmp_path / "probe-deploy"
    deploy_dir.mkdir()
    script_path = deploy_dir / "runtime_observation_probe.py"
    shutil.copyfile(_PROBE_SCRIPT_SOURCE, script_path)
    source_path = deploy_dir / "source_excerpt.txt"
    log_path = deploy_dir / "observed.log"
    source_path.write_text("line one\nline two\n", encoding="utf-8")
    log_path.write_text("log line\n", encoding="utf-8")
    (deploy_dir / "runtime_observation_probe.config.json").write_text(
        json.dumps(
            {"source_excerpt_path": str(source_path), "log_excerpt_path": str(log_path)}
        ),
        encoding="utf-8",
    )
    fingerprint = _config_fingerprint(str(source_path), str(log_path))

    remote_command = _launcher_remote_command(
        expected_probe_script_sha256=SSH_PROBE_SCRIPT_SHA256,
        probe_identity="SOURCE_LOG_EXCERPT_BOUNDED",
        expected_deployment_config_fingerprint=fingerprint,
    )
    report = _run_remote_command_in(remote_command, cwd=deploy_dir)
    assert report["ok"] is True
    assert report["probe_script_sha256"] == SSH_PROBE_SCRIPT_SHA256
    assert report["fields"]["source_available"] is True
    assert report["fields"]["source_excerpt"] == "line one\nline two"
    assert report["deployment_config_fingerprint"] == fingerprint


def test_launcher_refuses_a_byte_different_substitute_script_before_any_execution(
    tmp_path: Path,
) -> None:
    """The mandatory same-name-artifact-replacement proof: a *different* probe script,
    byte-for-byte distinct from the one this repository ships, deployed under the identical
    filename the launcher reads. It leaves its own execution marker as the very first thing it
    would do if it ran -- the launcher must refuse it, via its own freshly recomputed digest
    (never anything the substitute itself claims), BEFORE ``exec()`` is ever reached, so this
    marker must stay absent."""

    deploy_dir = tmp_path / "probe-deploy"
    deploy_dir.mkdir()
    script_path = deploy_dir / "runtime_observation_probe.py"
    shutil.copyfile(_PROBE_SCRIPT_SOURCE, script_path)
    genuine_digest = hashlib.sha256(script_path.read_bytes()).hexdigest()

    marker_path = deploy_dir / "substitute_execution_marker.txt"
    script_path.write_text(
        "import json\n"
        "import sys\n"
        f"open({str(marker_path)!r}, 'w').write('substitute script genuinely ran')\n"
        "json.dump(\n"
        "    {\n"
        "        'ok': True,\n"
        "        'fields': {'hostname': 'substitute'},\n"
        "        'deployment_identity': None,\n"
        "        'reason': None,\n"
        "        'probe_script_sha256': 'f' * 64,\n"
        "        'deployment_config_fingerprint': 'f' * 64,\n"
        "    },\n"
        "    sys.stdout,\n"
        ")\n",
        encoding="utf-8",
    )

    assert not marker_path.exists()
    remote_command = _launcher_remote_command(expected_probe_script_sha256=genuine_digest)
    report = _run_remote_command_in(remote_command, cwd=deploy_dir)
    assert not marker_path.exists()
    assert report["ok"] is False
    assert report["reason"] == "ARTIFACT_NOT_AUTHORIZED"
    assert report["probe_script_sha256"] != genuine_digest


def test_launcher_refuses_a_substitute_that_echoes_the_exact_expected_public_hashes(
    tmp_path: Path,
) -> None:
    """The companion proof the handoff specifically requires: a substitute that *fabricates* a
    self-report naming the exact expected ``probe_script_sha256``/``deployment_config_
    fingerprint`` -- both public values, so copying them is not forgery -- must still be
    refused before execution. The launcher's own check never reads anything the script claims
    about itself; it independently recomputes the digest of the bytes actually on disk, so a
    fabricated self-report inside code that never runs changes nothing."""

    deploy_dir = tmp_path / "probe-deploy"
    deploy_dir.mkdir()
    script_path = deploy_dir / "runtime_observation_probe.py"
    shutil.copyfile(_PROBE_SCRIPT_SOURCE, script_path)
    genuine_digest = hashlib.sha256(script_path.read_bytes()).hexdigest()

    marker_path = deploy_dir / "substitute_execution_marker.txt"
    script_path.write_text(
        "import json\n"
        "import sys\n"
        f"open({str(marker_path)!r}, 'w').write('substitute script genuinely ran')\n"
        "json.dump(\n"
        "    {\n"
        "        'ok': True,\n"
        "        'fields': {'hostname': 'substitute'},\n"
        "        'deployment_identity': None,\n"
        "        'reason': None,\n"
        f"        'probe_script_sha256': {genuine_digest!r},\n"
        "        'deployment_config_fingerprint': "
        f"{_A_FINGERPRINT_SHAPED_VALUE!r},\n"
        "    },\n"
        "    sys.stdout,\n"
        ")\n",
        encoding="utf-8",
    )

    assert not marker_path.exists()
    remote_command = _launcher_remote_command(expected_probe_script_sha256=genuine_digest)
    report = _run_remote_command_in(remote_command, cwd=deploy_dir)
    assert not marker_path.exists()
    assert report["ok"] is False
    assert report["reason"] == "ARTIFACT_NOT_AUTHORIZED"


def test_launcher_code_contains_exactly_one_file_read_closing_the_toctou_window(
) -> None:
    """A structural, static proof standing in for the "no unchecked replacement executes
    between verification and use" control the handoff requires: the whole point of this
    launcher's design is that the digest check and the ``exec()`` both operate on the identical
    in-memory bytes from one single read, so there is no second, later read of the file for an
    attacker to race against. Asserted here directly against the real
    :data:`~manosube_agent_civilization.runtime.types.SSH_PROBE_LAUNCHER_CODE` constant's own
    source, rather than only reasoned about in prose."""

    assert SSH_PROBE_LAUNCHER_CODE.count("open(") == 1
    assert SSH_PROBE_LAUNCHER_CODE.count("compile(") == 1
    assert SSH_PROBE_LAUNCHER_CODE.count("exec(") == 1


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


def test_cli_run_controller_reports_deadline_not_yet_reached_with_zero_target_calls(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    """PR #108 Structural Review Round 4, SR4-F1 (corrected by Round 5, SR5-F1), exercised
    through the real CLI script, against the real system clock (never a fake ``monotonic_fn``,
    unlike the unit-level proofs in ``test_runtime_transport_control.py``): an instantly-
    answering fixture sequence exhausts ``--max-polls`` in a real process in well under a
    second, nowhere near the generous 60-second ``--start-deadline-seconds`` this subcommand
    is given. This must reach the distinct ``DEADLINE_NOT_YET_REACHED`` -- never
    ``FALLBACK_REFUSED_NO_GRANT``, which this test's own prior (pre-SR5-F1) expectation wrongly
    treated as reachable here -- with zero target calls and no claim-state file ever written
    (nothing was genuinely executed to claim)."""

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
        "--fixture-dispatch-status-sequence",
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
    assert out["decision"] == "DEADLINE_NOT_YET_REACHED"
    assert out["executed"] is False
    assert out["final_dispatch_status"] == "UNKNOWN"
    assert out["poll_count"] == 3
    assert out["elapsed_seconds"] < 60
    assert not claim_state_file.exists()

    different_request = _run_transport_cli([*base_args, "--request-id", "REQ-CLI-2"])
    assert different_request["operation_id"] != out["operation_id"]


def test_cli_run_controller_refuses_without_a_permitting_grant_once_the_deadline_genuinely_elapses(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    """The companion real-CLI proof for the genuine deadline-exceeded path: a
    ``--start-deadline-seconds`` of ``0`` means no time budget exists at all, so this
    controller reaches the grant check (and is refused, since this grant never permits
    ``PREAUTHORIZED_UNATTENDED_SSH``) with zero polls -- proving ``DEADLINE_NOT_YET_REACHED``
    is reached only when the deadline genuinely has not yet elapsed, never universally in
    place of ``FALLBACK_REFUSED_NO_GRANT``."""

    grant = _grant_for(_world, permitted_transports=["GITHUB_ACTIONS", "MANUAL_SSH"])
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    target_file = tmp_path / "target_identity.json"
    target_file.write_text(json.dumps(_world["target_identity"]), encoding="utf-8")

    out = _run_transport_cli(
        [
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
            "--fixture-dispatch-status-sequence",
            "UNKNOWN",
            "--start-deadline-seconds",
            "0",
            "--max-polls",
            "3",
            "--request-id",
            "REQ-CLI-ZERO-DEADLINE",
        ]
    )
    assert out["ok"] is True
    assert out["decision"] == "FALLBACK_REFUSED_NO_GRANT"
    assert out["executed"] is False
    assert out["poll_count"] == 0


# ---------------------------------------------------------------------------
# PR #108 Structural Review Round 6, SR6-F1: bounded_dispatch_status_acquisition's removal,
# and --dispatch-status-file's own new request/source/freshness binding, exercised against
# the real module (via importlib, for the thread-count proof below) and the real CLI
# subprocess (for the end-to-end correlation/freshness proofs).
# ---------------------------------------------------------------------------


def test_dispatch_status_file_provider_never_spawns_a_thread_and_never_blocks_on_a_fifo(
    tmp_path: Path,
) -> None:
    """The exact shape the Structural Advisor reproduced against the prior
    ``bounded_dispatch_status_acquisition`` (SR5-F1): twenty repeated reads against a stalled
    source, across several different operation ids (standing in for "successive operations").
    The corrected ``_dispatch_status_file_provider`` spawns no thread at all -- proved here by
    this test process's own live thread count staying exactly flat across every call, never by
    only timing how fast the caller returned."""

    rot = _load_transport_module()
    fifo_path = tmp_path / "dispatch_status_fifo"
    os.mkfifo(fifo_path)

    baseline = threading.active_count()
    started = time.monotonic()
    for index in range(20):
        provider = rot._dispatch_status_file_provider(
            str(fifo_path),
            expected_operation_id=f"OP-{index % 3}",
            expected_source_id="watcher-1",
            max_staleness_seconds=30.0,
            now_fn=lambda: "2026-01-01T00:00:10Z",
        )
        result = provider(5.0)
        assert result == "UNKNOWN"
        assert threading.active_count() == baseline
    elapsed = time.monotonic() - started
    assert elapsed < 2.0
    assert threading.active_count() == baseline


def test_dispatch_status_file_provider_refuses_a_future_dated_fact(tmp_path: Path) -> None:
    """The other half of "stale/future facts => zero SSH" the handoff names explicitly: a
    fact whose own ``observed_at`` is *later* than the trusted clock read for this poll is just
    as untrustworthy as one that is too old -- negative staleness is refused identically to
    positive staleness beyond the bound, never treated as "extra fresh"."""

    rot = _load_transport_module()
    fact_path = tmp_path / "fact.json"
    fact_path.write_text(
        json.dumps(
            {
                "dispatch_status": "UNAVAILABLE",
                "observed_at": "2026-01-01T00:10:00Z",
                "operation_id": "OP-1",
                "source_id": "watcher-1",
            }
        ),
        encoding="utf-8",
    )
    provider = rot._dispatch_status_file_provider(
        str(fact_path),
        expected_operation_id="OP-1",
        expected_source_id="watcher-1",
        max_staleness_seconds=30.0,
        now_fn=lambda: "2026-01-01T00:00:00Z",
    )
    assert provider(5.0) == "UNKNOWN"


def test_dispatch_status_file_provider_reflects_a_genuinely_advancing_trusted_clock(
    tmp_path: Path,
) -> None:
    """PR #108 Structural Review Round 6, SR6-F1's own required proof that freshness is
    re-evaluated fresh at *each* poll, never cached from an earlier one: the identical,
    unchanged fact file is fresh against an injected clock that has not yet advanced past it,
    and becomes stale once that same clock genuinely advances -- across repeated calls to the
    identical provider closure, never a new one constructed per poll."""

    rot = _load_transport_module()
    fact_path = tmp_path / "fact.json"
    fact_path.write_text(
        json.dumps(
            {
                "dispatch_status": "UNAVAILABLE",
                "observed_at": "2026-01-01T00:00:00Z",
                "operation_id": "OP-1",
                "source_id": "watcher-1",
            }
        ),
        encoding="utf-8",
    )
    clock_state = {"now": "2026-01-01T00:00:05Z"}
    provider = rot._dispatch_status_file_provider(
        str(fact_path),
        expected_operation_id="OP-1",
        expected_source_id="watcher-1",
        max_staleness_seconds=30.0,
        now_fn=lambda: clock_state["now"],
    )
    assert provider(5.0) == "UNAVAILABLE"
    clock_state["now"] = "2026-01-01T01:00:00Z"
    assert provider(5.0) == "UNKNOWN"


def _write_dispatch_status_file(
    path: Path,
    *,
    dispatch_status: str = "UNAVAILABLE",
    observed_at: str | None = None,
    operation_id: str,
    source_id: str = "watcher-1",
) -> None:
    """Write a dispatch-status-file fact. *observed_at*, left ``None``, defaults to the real
    current instant (never the fixed ``_NOW`` this module's other grant/boundary fixtures use)
    -- the CLI's own freshness check compares against a fresh real-clock read at poll time
    (PR #108 SR6-F1), so a fact meant to prove the *positive* path must genuinely be fresh by
    that same real clock, not merely close to some other fixture's own fixed instant."""

    path.write_text(
        json.dumps(
            {
                "dispatch_status": dispatch_status,
                "observed_at": observed_at if observed_at is not None else current_utc_instant(),
                "operation_id": operation_id,
                "source_id": source_id,
            }
        ),
        encoding="utf-8",
    )


def test_cli_run_controller_trusts_a_dispatch_status_file_once_correlation_genuinely_matches(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    """The positive path: a dispatch-status-file whose own ``operation_id``/``source_id``
    genuinely match this exact invocation reaches the real controller decision -- a decisive
    ``UNAVAILABLE`` stops polling on the very first read and reaches the (here, refusing)
    grant check, never treated as the ambiguous ``UNKNOWN`` a mismatch would be."""

    grant = _grant_for(_world, permitted_transports=["GITHUB_ACTIONS", "MANUAL_SSH"])
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    target_file = tmp_path / "target_identity.json"
    target_file.write_text(json.dumps(_world["target_identity"]), encoding="utf-8")

    operation_id = compute_runtime_observation_operation_id(
        grant_id=grant["grant_id"],
        provider=_world["target_identity"]["provider"],
        deployment_id=_world["target_identity"]["deployment_id"],
        instance_identity=_world["target_identity"]["instance_identity"],
        request_id="REQ-MATCH",
    )
    fact_file = tmp_path / "dispatch_status.json"
    _write_dispatch_status_file(fact_file, operation_id=operation_id)

    out = _run_transport_cli(
        [
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
            "--dispatch-status-file",
            str(fact_file),
            "--dispatch-status-source-id",
            "watcher-1",
            "--start-deadline-seconds",
            "60",
            "--max-polls",
            "3",
            "--request-id",
            "REQ-MATCH",
        ]
    )
    assert out["ok"] is True
    assert out["decision"] == "FALLBACK_REFUSED_NO_GRANT"
    assert out["executed"] is False
    assert out["final_dispatch_status"] == "UNAVAILABLE"
    assert out["poll_count"] == 1


def test_cli_run_controller_ignores_a_fresh_fact_naming_a_different_operation(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    """PR #108 Structural Review Round 6, SR6-F1's own decisive reproduction: a fresh, honestly
    ``UNAVAILABLE`` record that names a *different* request's own ``operation_id`` must never
    be trusted for this one -- the controller must keep polling (never confirming
    ``UNAVAILABLE``) and, once ``max_polls`` is exhausted with real time still remaining,
    report ``DEADLINE_NOT_YET_REACHED`` with zero target calls, exactly as it would for an
    honestly unknown source."""

    grant = _grant_for(_world, permitted_transports=["GITHUB_ACTIONS", "MANUAL_SSH"])
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    target_file = tmp_path / "target_identity.json"
    target_file.write_text(json.dumps(_world["target_identity"]), encoding="utf-8")

    fact_file = tmp_path / "dispatch_status.json"
    _write_dispatch_status_file(fact_file, operation_id="OTHER_REQUEST")

    out = _run_transport_cli(
        [
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
            "--dispatch-status-file",
            str(fact_file),
            "--dispatch-status-source-id",
            "watcher-1",
            "--start-deadline-seconds",
            "60",
            "--max-polls",
            "3",
            "--request-id",
            "REQ-REAL",
        ]
    )
    assert out["ok"] is True
    assert out["decision"] == "DEADLINE_NOT_YET_REACHED"
    assert out["executed"] is False
    assert out["final_dispatch_status"] == "UNKNOWN"
    assert out["poll_count"] == 3


def test_cli_run_controller_ignores_a_fresh_fact_from_an_undeclared_source(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    """The companion proof for the source half of the same binding: a fact file whose
    ``operation_id`` genuinely matches but whose ``source_id`` does not match the caller's own
    ``--dispatch-status-source-id`` must likewise never be trusted."""

    grant = _grant_for(_world, permitted_transports=["GITHUB_ACTIONS", "MANUAL_SSH"])
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    target_file = tmp_path / "target_identity.json"
    target_file.write_text(json.dumps(_world["target_identity"]), encoding="utf-8")

    operation_id = compute_runtime_observation_operation_id(
        grant_id=grant["grant_id"],
        provider=_world["target_identity"]["provider"],
        deployment_id=_world["target_identity"]["deployment_id"],
        instance_identity=_world["target_identity"]["instance_identity"],
        request_id="REQ-SOURCE-MISMATCH",
    )
    fact_file = tmp_path / "dispatch_status.json"
    _write_dispatch_status_file(
        fact_file, operation_id=operation_id, source_id="some-other-watcher"
    )

    out = _run_transport_cli(
        [
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
            "--dispatch-status-file",
            str(fact_file),
            "--dispatch-status-source-id",
            "watcher-1",
            "--start-deadline-seconds",
            "60",
            "--max-polls",
            "3",
            "--request-id",
            "REQ-SOURCE-MISMATCH",
        ]
    )
    assert out["ok"] is True
    assert out["decision"] == "DEADLINE_NOT_YET_REACHED"
    assert out["executed"] is False
    assert out["final_dispatch_status"] == "UNKNOWN"
    assert out["poll_count"] == 3


def test_cli_run_controller_ignores_a_stale_fact_even_with_genuinely_matching_correlation(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    """Correlation alone is not freshness: a fact file whose ``operation_id``/``source_id``
    genuinely match this invocation, but whose own ``observed_at`` is far older than
    ``--dispatch-status-max-staleness-seconds``, must still be refused as ``UNKNOWN``."""

    grant = _grant_for(_world, permitted_transports=["GITHUB_ACTIONS", "MANUAL_SSH"])
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    target_file = tmp_path / "target_identity.json"
    target_file.write_text(json.dumps(_world["target_identity"]), encoding="utf-8")

    operation_id = compute_runtime_observation_operation_id(
        grant_id=grant["grant_id"],
        provider=_world["target_identity"]["provider"],
        deployment_id=_world["target_identity"]["deployment_id"],
        instance_identity=_world["target_identity"]["instance_identity"],
        request_id="REQ-STALE",
    )
    fact_file = tmp_path / "dispatch_status.json"
    _write_dispatch_status_file(
        fact_file, operation_id=operation_id, observed_at="2020-01-01T00:00:00Z"
    )

    out = _run_transport_cli(
        [
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
            "--dispatch-status-file",
            str(fact_file),
            "--dispatch-status-source-id",
            "watcher-1",
            "--dispatch-status-max-staleness-seconds",
            "30",
            "--start-deadline-seconds",
            "60",
            "--max-polls",
            "3",
            "--request-id",
            "REQ-STALE",
        ]
    )
    assert out["ok"] is True
    assert out["decision"] == "DEADLINE_NOT_YET_REACHED"
    assert out["executed"] is False
    assert out["final_dispatch_status"] == "UNKNOWN"
    assert out["poll_count"] == 3


def test_cli_run_controller_requires_a_declared_source_id_with_dispatch_status_file(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    """Omitting ``--dispatch-status-source-id`` while using ``--dispatch-status-file`` must be
    refused outright, with zero polls and zero target calls -- never silently treated as "no
    source binding required"."""

    grant = _grant_for(_world, permitted_transports=["GITHUB_ACTIONS", "MANUAL_SSH"])
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    target_file = tmp_path / "target_identity.json"
    target_file.write_text(json.dumps(_world["target_identity"]), encoding="utf-8")
    fact_file = tmp_path / "dispatch_status.json"
    _write_dispatch_status_file(fact_file, operation_id="irrelevant")

    out = _run_transport_cli(
        [
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
            "--dispatch-status-file",
            str(fact_file),
            "--start-deadline-seconds",
            "60",
            "--max-polls",
            "3",
            "--request-id",
            "REQ-NO-SOURCE-ID",
        ]
    )
    assert out["ok"] is False
    assert "dispatch-status-source-id" in out["error"]


def test_cli_run_controller_refuses_a_fifo_dispatch_status_file_instead_of_hanging(
    _world: dict[str, Any], tmp_path: Path
) -> None:
    """The real-subprocess companion to the importlib-level thread-count proof above: a
    ``--dispatch-status-file`` pointed at a FIFO nothing ever writes to must never hang this
    subprocess -- every poll refuses promptly as ``UNKNOWN``, and the whole invocation
    completes well within its own bounded timeout."""

    grant = _grant_for(_world, permitted_transports=["GITHUB_ACTIONS", "MANUAL_SSH"])
    grant_file = tmp_path / "grant.json"
    grant_file.write_text(json.dumps(grant), encoding="utf-8")
    target_file = tmp_path / "target_identity.json"
    target_file.write_text(json.dumps(_world["target_identity"]), encoding="utf-8")
    fifo_path = tmp_path / "dispatch_status_fifo"
    os.mkfifo(fifo_path)

    started = time.monotonic()
    out = _run_transport_cli(
        [
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
            "--dispatch-status-file",
            str(fifo_path),
            "--dispatch-status-source-id",
            "watcher-1",
            "--start-deadline-seconds",
            "60",
            "--max-polls",
            "3",
            "--request-id",
            "REQ-FIFO",
        ],
        timeout=10.0,
    )
    elapsed = time.monotonic() - started
    assert out["ok"] is True
    assert out["decision"] == "DEADLINE_NOT_YET_REACHED"
    assert out["final_dispatch_status"] == "UNKNOWN"
    assert out["poll_count"] == 3
    assert elapsed < 5.0


# ---------------------------------------------------------------------------
# Issue #105 isolated-deployment-identity correction (2026-10-06): the real target proof-
# blocker (comment 6006404738 on Issue #105) was that ``DEPLOYMENT_IDENTITY_PATH`` was fixed
# and unreadable on SHUKOU's own real target, with no sibling-config override -- so
# ``_read_deployment_identity`` always returned ``None`` and the canonical route's identity-
# mismatch check could never positively attest a null identity against a non-null declared
# target. This section proves the isolated fix end to end, as a real subprocess against the
# real shipped script: a configurable identity path, folded into the identical signed
# ``deployment_config_fingerprint`` the two excerpt paths already used, gated before any
# configured-path read for *both* pinned probe identities, with the old two-path grants
# correctly refused (never retroactively rebound) and symlink/ancestor defenses intact.
# ---------------------------------------------------------------------------


def test_probe_script_reports_a_configured_isolated_identity_with_a_genuinely_matching_grant(
    tmp_path: Path,
) -> None:
    """The positive isolated-identity path this correction exists to unblock: a sibling config
    naming an isolated ``deployment_identity_path`` (never a system-identity-file write -- a
    plain file in this test's own isolated directory), and a caller-supplied fingerprint that
    genuinely equals this deployment's own three-path digest, reports that identity for *both*
    pinned probe identities."""

    identity_path = tmp_path / "isolated_deployment_identity.txt"
    identity_path.write_text("isolated-proof-identity-001\n", encoding="utf-8")
    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    source_path.write_text("line one\nline two\n", encoding="utf-8")
    log_path.write_text("log line\n", encoding="utf-8")
    fingerprint = _config_fingerprint(
        str(source_path), str(log_path), str(identity_path)
    )
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {
                    "deployment_identity_path": str(identity_path),
                    "source_excerpt_path": str(source_path),
                    "log_excerpt_path": str(log_path),
                }
            ),
        },
    )

    health_report = _run_probe_script(script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", fingerprint)
    assert health_report["ok"] is True
    assert health_report["deployment_identity"] == "isolated-proof-identity-001"

    excerpt_report = _run_probe_script(
        script_path, "SOURCE_LOG_EXCERPT_BOUNDED", fingerprint
    )
    assert excerpt_report["ok"] is True
    assert excerpt_report["deployment_identity"] == "isolated-proof-identity-001"
    assert excerpt_report["fields"]["source_available"] is True


def test_probe_script_omitted_identity_path_config_falls_back_to_the_shipped_default(
    tmp_path: Path,
) -> None:
    """An operator who does not need an isolated identity override simply omits
    ``deployment_identity_path`` from the sibling config -- the identical fallback-to-default
    discipline :data:`scripts.runtime_observation_probe.SOURCE_EXCERPT_PATH`/
    :data:`~scripts.runtime_observation_probe.LOG_EXCERPT_PATH` already keep, and the caller's
    fingerprint computed with the default-path three-argument shape still matches.

    PR #110 Structural Review Round 1, F1 correction (2026-10-06): the prior version of this
    test also asserted ``report["deployment_identity"] is None``, which silently assumed the
    real shipped default path (``/etc/manosube/deployment_fingerprint``) is absent on whatever
    host runs this suite -- true in this delivery's own sandbox, but never proved, and false on
    a privileged runner that genuinely has a file there. That assertion is removed; the actual
    fallback fact this test proves is that the probe's own live-computed fingerprint, with the
    key omitted, equals the identical digest this file's own :func:`_config_fingerprint` helper
    computes with its own default third argument -- the acceptance below (``ok: true``) is
    that proof, and it holds regardless of what (if anything) exists at the real default path.
    """

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
        },
    )

    report = _run_probe_script(script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", fingerprint)
    assert report["ok"] is True


def test_probe_script_absent_empty_or_unreadable_identity_path_reports_none_never_fabricated(
    tmp_path: Path,
) -> None:
    """The real-target failure mode this correction fixes at its root: a configured identity
    path this script cannot turn into a genuine value must still report
    ``deployment_identity: null``, honestly, rather than raising or fabricating a value -- the
    identical contract :func:`scripts.runtime_observation_probe._read_deployment_identity`
    already keeps for its prior, fixed path, now proven for a configured one too, and (PR #110
    Structural Review Round 1, F1 correction, 2026-10-06) across three independently caused
    failure shapes, not only "does not exist":

    - *absent* -- the path names a file that genuinely does not exist;
    - *empty* -- the path exists and opens cleanly, but its own content is the empty string
      (``_read_deployment_identity``'s own ``value or None`` must treat that identically to a
      read failure, never report an empty-string identity);
    - *unreadable* -- the path exists but cannot be read *as a file* at all. A real target's
      own permission bits are not a reliable way to force this deterministically in a test that
      may itself run privileged (root bypasses ordinary permission bits entirely), so this uses
      a directory in the identity path's own place instead: opening a directory for reading
      always raises ``IsADirectoryError`` (an ``OSError`` subclass), regardless of the caller's
      privilege level, giving every test runner the identical, deterministic "cannot be read as
      a file" failure the real unreadable-file case this correction exists to fix would also
      produce.
    """

    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    source_path.write_text("line one\nline two\n", encoding="utf-8")
    log_path.write_text("log line\n", encoding="utf-8")

    absent_identity_path = tmp_path / "does-not-exist" / "identity.txt"
    empty_identity_path = tmp_path / "empty-identity.txt"
    empty_identity_path.write_text("", encoding="utf-8")
    unreadable_identity_path = tmp_path / "unreadable-identity-is-a-directory"
    unreadable_identity_path.mkdir()

    for identity_path in (absent_identity_path, empty_identity_path, unreadable_identity_path):
        fingerprint = _config_fingerprint(str(source_path), str(log_path), str(identity_path))
        deploy_root = tmp_path / f"deploy-{identity_path.name}"
        deploy_root.mkdir()
        script_path = _deployed_probe_script(
            deploy_root,
            **{
                "runtime_observation_probe.config.json": json.dumps(
                    {
                        "deployment_identity_path": str(identity_path),
                        "source_excerpt_path": str(source_path),
                        "log_excerpt_path": str(log_path),
                    }
                ),
            },
        )
        report = _run_probe_script(script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", fingerprint)
        assert report["ok"] is True, identity_path
        assert report["deployment_identity"] is None, identity_path


def test_probe_script_a_changed_identity_path_changes_the_deployment_config_fingerprint(
    tmp_path: Path,
) -> None:
    """The decisive binding property: two sibling configs differing *only* in
    ``deployment_identity_path`` must compute different ``deployment_config_fingerprint``
    values -- never silently treated as equivalent configurations -- so a grant authorized
    against one identity path can never be replayed against a deployment that reads a
    different one.

    PR #110 Structural Review Round 1, F1 correction (2026-10-06): the prior version of this
    test only ever compared two calls to this file's own :func:`_config_fingerprint` replica --
    it never invoked the actual shipped probe at all, so it could not have caught a real
    divergence between that replica and :func:`scripts.runtime_observation_probe.
    _deployment_config_fingerprint`'s own real implementation. This version deploys the real
    script twice, each beside a sibling config differing only in ``deployment_identity_path``,
    and compares the two *self-reported* ``deployment_config_fingerprint`` values the real
    probe subprocess actually computed -- proving the live binding property over the real
    artifact, not over this test file's own model of it."""

    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    source_path.write_text("line one\nline two\n", encoding="utf-8")
    log_path.write_text("log line\n", encoding="utf-8")

    first_identity_path = tmp_path / "identity-a.txt"
    second_identity_path = tmp_path / "identity-b.txt"

    first_deploy_root = tmp_path / "deploy-a"
    first_deploy_root.mkdir()
    first_fingerprint = _config_fingerprint(
        str(source_path), str(log_path), str(first_identity_path)
    )
    first_script_path = _deployed_probe_script(
        first_deploy_root,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {
                    "deployment_identity_path": str(first_identity_path),
                    "source_excerpt_path": str(source_path),
                    "log_excerpt_path": str(log_path),
                }
            ),
        },
    )
    first_report = _run_probe_script(
        first_script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", first_fingerprint
    )
    assert first_report["ok"] is True
    assert first_report["deployment_config_fingerprint"] == first_fingerprint

    second_deploy_root = tmp_path / "deploy-b"
    second_deploy_root.mkdir()
    second_fingerprint = _config_fingerprint(
        str(source_path), str(log_path), str(second_identity_path)
    )
    second_script_path = _deployed_probe_script(
        second_deploy_root,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {
                    "deployment_identity_path": str(second_identity_path),
                    "source_excerpt_path": str(source_path),
                    "log_excerpt_path": str(log_path),
                }
            ),
        },
    )
    second_report = _run_probe_script(
        second_script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", second_fingerprint
    )
    assert second_report["ok"] is True
    assert second_report["deployment_config_fingerprint"] == second_fingerprint

    assert first_report["deployment_config_fingerprint"] != second_report["deployment_config_fingerprint"]


def test_probe_script_zero_configured_file_reads_on_mismatch_for_both_profiles(
    tmp_path: Path,
) -> None:
    """PR #110 Structural Review Round 1, F1's own strongest-available instrumentation ask:
    prove that on a mismatched commitment, this script never opens *any* of the three
    configured paths -- identity, source, or log alike -- for *either* pinned probe identity.
    Re-uses the identical FIFO technique
    ``test_probe_script_refusal_genuinely_precedes_any_attempt_to_open_the_source_path`` already
    establishes for the source path alone: a named pipe nothing ever writes to blocks forever
    on any process that actually opens it for reading, so a probe that incorrectly attempted
    any of these reads before its own authorization gate would hang and this test's own short
    timeout would fire. All three configured paths are FIFOs here, not just one, so a probe
    that read any single one of them -- not merely the source path the existing test already
    covers -- would be caught."""

    identity_fifo = tmp_path / "identity_fifo"
    source_fifo = tmp_path / "source_fifo"
    log_fifo = tmp_path / "log_fifo"
    os.mkfifo(identity_fifo)
    os.mkfifo(source_fifo)
    os.mkfifo(log_fifo)
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {
                    "deployment_identity_path": str(identity_fifo),
                    "source_excerpt_path": str(source_fifo),
                    "log_excerpt_path": str(log_fifo),
                }
            ),
        },
    )
    for probe_identity in ("OS_HEALTH_SNAPSHOT_BOUNDED", "SOURCE_LOG_EXCERPT_BOUNDED"):
        try:
            report = _run_probe_script(
                script_path,
                probe_identity,
                _A_FINGERPRINT_SHAPED_VALUE,
                timeout=5.0,
            )
        except subprocess.TimeoutExpired:
            pytest.fail(
                f"{probe_identity} did not return within the bounded timeout -- it attempted "
                "to open a configured path (identity/source/log, each an unopened FIFO that "
                "blocks forever) instead of refusing before any read"
            )
        assert report["ok"] is False, probe_identity
        assert report["reason"] == "CONFIG_NOT_AUTHORIZED", probe_identity
        assert report["deployment_identity"] is None, probe_identity


def test_probe_script_refuses_an_old_two_path_grant_against_the_new_three_path_fingerprint(
    tmp_path: Path,
) -> None:
    """The disclosed breaking migration (obligation E -- no retroactive rebinding): a
    fingerprint computed the *old* way, over only ``source_excerpt_path``/``log_excerpt_path``
    (exactly what a grant signed before this correction would carry), no longer equals this
    deployment's own current three-path digest, and is refused as ``CONFIG_NOT_AUTHORIZED``
    before any configured path -- identity, source, or log alike -- is ever read, for *both*
    pinned probe identities. Such a grant must be freshly re-issued, never silently honored."""

    identity_path = tmp_path / "isolated_deployment_identity.txt"
    identity_path.write_text("must never be read\n", encoding="utf-8")
    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    source_path.write_text("must never be read either", encoding="utf-8")
    log_path.write_text("nor this", encoding="utf-8")

    stale_two_path_payload = json.dumps(
        {"source_excerpt_path": str(source_path), "log_excerpt_path": str(log_path)},
        sort_keys=True,
        separators=(",", ":"),
    )
    stale_fingerprint = hashlib.sha256(stale_two_path_payload.encode("utf-8")).hexdigest()

    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {
                    "deployment_identity_path": str(identity_path),
                    "source_excerpt_path": str(source_path),
                    "log_excerpt_path": str(log_path),
                }
            ),
        },
    )

    for probe_identity in ("OS_HEALTH_SNAPSHOT_BOUNDED", "SOURCE_LOG_EXCERPT_BOUNDED"):
        report = _run_probe_script(script_path, probe_identity, stale_fingerprint)
        assert report["ok"] is False
        assert report["reason"] == "CONFIG_NOT_AUTHORIZED"
        assert report["deployment_identity"] is None


def test_probe_script_refuses_the_configured_identity_path_through_a_symlinked_ancestor(
    tmp_path: Path,
) -> None:
    """PR #108 Structural Review Round 3, SR3-F3(B)'s own descriptor-relative ancestor-symlink
    refusal, proven for the identity path too: a genuinely authorized, genuinely matching
    fingerprint does not override the independent symlinked-ancestor defense
    :func:`scripts.runtime_observation_probe._open_bounded_strict` already enforces for every
    configured path alike."""

    real_dir = tmp_path / "real-identity-dir"
    real_dir.mkdir()
    real_identity_path = real_dir / "identity.txt"
    real_identity_path.write_text("must not be read through the symlinked ancestor", encoding="utf-8")

    symlinked_ancestor = tmp_path / "symlinked-ancestor"
    symlinked_ancestor.symlink_to(real_dir, target_is_directory=True)
    identity_path_via_symlink = symlinked_ancestor / "identity.txt"

    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    source_path.write_text("line one\nline two\n", encoding="utf-8")
    log_path.write_text("log line\n", encoding="utf-8")
    fingerprint = _config_fingerprint(
        str(source_path), str(log_path), str(identity_path_via_symlink)
    )
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {
                    "deployment_identity_path": str(identity_path_via_symlink),
                    "source_excerpt_path": str(source_path),
                    "log_excerpt_path": str(log_path),
                }
            ),
        },
    )

    report = _run_probe_script(script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", fingerprint)
    assert report["ok"] is True
    assert report["deployment_identity"] is None


# ---------------------------------------------------------------------------
# PR #110 Structural Review Round 1, F1 (2026-10-06): the required completion proof the
# isolated-deployment-identity correction's own adopted handoff asked for and the prior round's
# tests stopped short of -- a report produced by the *real*, shipped probe subprocess, over an
# isolated configured identity path, carried through the real canonical
# :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` and
# :func:`~manosube_agent_civilization.runtime.evidence_handoff.
# route_runtime_observation_to_evidence`, using a genuinely signed grant and a genuinely
# Store-committed target identity -- never a hand-written ``_mocked_probe_stdout()`` stand-in,
# and never stopping at the probe's own bare JSON report the way the prior round's tests did.
# ``CapturedProbeReportRuntimeAdapter`` (PR #108 Structural Review Round 3, SR3-F3(A)) is the
# existing, unchanged, already-authorized route for exactly this: a real captured transcript,
# classified through the identical grant-scoped validation a live SSH subprocess result is,
# with zero new persistence/Authority/Evidence owner introduced.
# ---------------------------------------------------------------------------


def test_real_probe_report_over_an_isolated_identity_reaches_observed_verified_and_evidence(
    tmp_path: Path,
) -> None:
    """The positive completion proof, end to end: a canonical-format isolated identity value
    (the identical ``sha256:<64 hex>`` shape every other fixture in this module already uses,
    never the prior round's own "isolated-proof-identity-001") is written to a neutral identity
    file; the real, shipped probe script is run as a real subprocess against a sibling config
    naming that file plus neutral source/log files; its own genuine stdout bytes -- never
    rewritten or hand-constructed -- are carried through ``CapturedProbeReportRuntimeAdapter``
    into the real :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target`,
    against a target whose own committed ``deployment_fingerprint`` genuinely equals that same
    identity value and a genuinely Ed25519-signed grant whose own ``deployment_fingerprint``/
    ``deployment_config_fingerprint`` match it too; and the resulting real receipt is hand
    ed to the real, unchanged :func:`~manosube_agent_civilization.runtime.
    route_runtime_observation_to_evidence`. Every reference/fingerprint/provenance value
    asserted below is read back from what those real, existing functions actually returned,
    never asserted as a precondition of the test's own setup."""

    import json as _json

    from tests.evidence_helpers import change_free_verification_evidence_request

    from manosube_agent_civilization.runtime import route_runtime_observation_to_evidence

    identity_value = "sha256:" + hashlib.sha256(b"pr110-sr1-f1-isolated-identity-proof").hexdigest()
    world = _world_with_deployment_fingerprint(tmp_path, identity_value)

    identity_path = tmp_path / "isolated_deployment_identity.txt"
    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    identity_path.write_text(identity_value, encoding="utf-8")
    source_path.write_text("line one\nline two\n", encoding="utf-8")
    log_path.write_text("log line\n", encoding="utf-8")
    fingerprint = _config_fingerprint(str(source_path), str(log_path), str(identity_path))
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {
                    "deployment_identity_path": str(identity_path),
                    "source_excerpt_path": str(source_path),
                    "log_excerpt_path": str(log_path),
                }
            ),
        },
    )
    real_stdout = _run_probe_script_bytes(script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", fingerprint)
    # Sanity: the genuine report this real subprocess produced actually carries the identity
    # and fingerprint this test's own assertions below depend on -- never assumed blind.
    parsed_report = json.loads(real_stdout.decode("utf-8").strip().splitlines()[-1])
    assert parsed_report["ok"] is True
    assert parsed_report["deployment_identity"] == identity_value
    assert parsed_report["deployment_config_fingerprint"] == fingerprint

    grant = runtime_observation_grant_for(
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        deployment_fingerprint=identity_value,
        deployment_config_fingerprint=fingerprint,
        probe_identity="OS_HEALTH_SNAPSHOT_BOUNDED",
        permitted_fields=["hostname"],
        permitted_transports=["MANUAL_SSH"],
    )
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=real_stdout,
        captured_stderr=b"",
        captured_returncode=0,
        grant=grant,
        store=world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
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
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    # The real host's own hostname (never "vps1" -- that is only the other, hand-written
    # ``_mocked_probe_stdout()`` fixture's stand-in value), read back from the identical real
    # report this test already parsed above to confirm its own setup.
    assert outcome["envelope"]["observed_fields"] == {"hostname": parsed_report["fields"]["hostname"]}
    assert outcome["receipt"].status == "VERIFIED"

    raw_request = change_free_verification_evidence_request(provenance=None)
    rewritten = _json.loads(_json.dumps(raw_request).replace("PRJ-0001", world["project_id"]))
    evidence = route_runtime_observation_to_evidence(
        world["store"], outcome["receipt"], world["project_id"], rewritten
    )
    # What the Evidence handoff actually returns, read back and compared against the real
    # envelope/receipt this test's own route call produced -- never asserted independently of
    # them. This is a *derived* Evidence record the existing, unchanged handoff route returns;
    # it is not, on this call alone, asserted to have additionally been committed to the Store
    # as its own canonical record -- that is `route_runtime_observation_to_evidence`'s own,
    # unchanged, pre-existing responsibility, exercised identically to every other call site in
    # this file, not a new persistence path this correction adds.
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    assert evidence["target"]["project_id"] == world["project_id"]
    assert (
        evidence["verification_result_provenance"]["requirement_id"]
        == outcome["envelope"]["runtime_observation_envelope_id"]
    )
    assert (
        evidence["verification_result_provenance"]["observations"]["observation_outcome"]
        == "OBSERVED"
    )


def test_real_probe_report_over_an_isolated_identity_reaches_observed_for_excerpt_profile_too(
    tmp_path: Path,
) -> None:
    """The identical positive proof, for ``SOURCE_LOG_EXCERPT_BOUNDED`` -- the other pinned
    probe identity this correction's own pre-read gate now covers identically to
    ``OS_HEALTH_SNAPSHOT_BOUNDED`` -- reaching the real canonical route with genuine excerpt
    fields alongside the genuine isolated identity, never only the simpler health profile."""

    identity_value = "sha256:" + hashlib.sha256(b"pr110-sr1-f1-excerpt-profile-proof").hexdigest()
    world = _world_with_deployment_fingerprint(tmp_path, identity_value)

    identity_path = tmp_path / "isolated_deployment_identity.txt"
    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    identity_path.write_text(identity_value, encoding="utf-8")
    source_path.write_text("line one\nline two\n", encoding="utf-8")
    log_path.write_text("log line\n", encoding="utf-8")
    fingerprint = _config_fingerprint(str(source_path), str(log_path), str(identity_path))
    script_path = _deployed_probe_script(
        tmp_path,
        **{
            "runtime_observation_probe.config.json": json.dumps(
                {
                    "deployment_identity_path": str(identity_path),
                    "source_excerpt_path": str(source_path),
                    "log_excerpt_path": str(log_path),
                }
            ),
        },
    )
    real_stdout = _run_probe_script_bytes(
        script_path, "SOURCE_LOG_EXCERPT_BOUNDED", fingerprint
    )

    grant = runtime_observation_grant_for(
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        deployment_fingerprint=identity_value,
        deployment_config_fingerprint=fingerprint,
        probe_identity="SOURCE_LOG_EXCERPT_BOUNDED",
        permitted_fields=["source_excerpt", "source_available"],
        permitted_transports=["MANUAL_SSH"],
    )
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=real_stdout,
        captured_stderr=b"",
        captured_returncode=0,
        grant=grant,
        store=world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    boundary = ssh_boundary_for(
        host=grant["host"],
        port=grant["port"],
        user=grant["user"],
        probe_identity=grant["probe_identity"],
        permitted_fields=["source_excerpt", "source_available"],
        issued_at=_NOW,
        expires_at="2026-06-01T01:00:00Z",
    )
    outcome = observe_runtime_target(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"]["source_excerpt"] == "line one\nline two"
    assert outcome["receipt"].status == "VERIFIED"


# ---------------------------------------------------------------------------
# PR #110 Structural Review Round 1, F1: the required canonical-route negative controls --
# absent, empty, unreadable, and genuinely wrong identity must each reach the real
# ``observe_runtime_target`` route and settle at ``IDENTITY_MISMATCH``/``FAILED``, never at a
# fabricated ``VERIFIED`` receipt.
# ---------------------------------------------------------------------------


def test_real_probe_identity_failure_modes_never_reach_verified_through_the_canonical_route(
    tmp_path: Path,
) -> None:
    """Four independently caused identity failures -- absent, empty, unreadable (a directory in
    the identity path's own place; see ``test_probe_script_absent_empty_or_unreadable_identity_
    path_reports_none_never_fabricated`` for why this is the deterministic, privilege-
    independent proxy this file already uses for "unreadable"), and a genuinely wrong value --
    each produced by a real probe subprocess run and carried through the real canonical route
    against a target whose own declared identity is a *different*, specific canonical value.
    None may ever settle at ``OBSERVED``/``VERIFIED``; the route's own, unchanged identity-
    mismatch comparison in ``route.py`` is what is being proved here, not reimplemented."""

    declared_identity = "sha256:" + hashlib.sha256(b"pr110-sr1-f1-declared-target").hexdigest()
    wrong_identity = "sha256:" + hashlib.sha256(b"pr110-sr1-f1-wrong-identity").hexdigest()
    world = _world_with_deployment_fingerprint(tmp_path, declared_identity)

    source_path = tmp_path / "source_excerpt.txt"
    log_path = tmp_path / "observed.log"
    source_path.write_text("line one\nline two\n", encoding="utf-8")
    log_path.write_text("log line\n", encoding="utf-8")

    absent_identity_path = tmp_path / "does-not-exist" / "identity.txt"
    empty_identity_path = tmp_path / "empty-identity.txt"
    empty_identity_path.write_text("", encoding="utf-8")
    unreadable_identity_path = tmp_path / "unreadable-identity-is-a-directory"
    unreadable_identity_path.mkdir()
    wrong_identity_path = tmp_path / "wrong-identity.txt"
    wrong_identity_path.write_text(wrong_identity, encoding="utf-8")

    for case_name, identity_path in (
        ("absent", absent_identity_path),
        ("empty", empty_identity_path),
        ("unreadable", unreadable_identity_path),
        ("wrong", wrong_identity_path),
    ):
        fingerprint = _config_fingerprint(str(source_path), str(log_path), str(identity_path))
        deploy_root = tmp_path / f"deploy-{case_name}"
        deploy_root.mkdir()
        script_path = _deployed_probe_script(
            deploy_root,
            **{
                "runtime_observation_probe.config.json": json.dumps(
                    {
                        "deployment_identity_path": str(identity_path),
                        "source_excerpt_path": str(source_path),
                        "log_excerpt_path": str(log_path),
                    }
                ),
            },
        )
        real_stdout = _run_probe_script_bytes(
            script_path, "OS_HEALTH_SNAPSHOT_BOUNDED", fingerprint
        )

        grant = runtime_observation_grant_for(
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            deployment_fingerprint=declared_identity,
            deployment_config_fingerprint=fingerprint,
            probe_identity="OS_HEALTH_SNAPSHOT_BOUNDED",
            permitted_fields=["hostname"],
            permitted_transports=["MANUAL_SSH"],
        )
        adapter = CapturedProbeReportRuntimeAdapter(
            captured_stdout=real_stdout,
            captured_stderr=b"",
            captured_returncode=0,
            grant=grant,
            store=world["store"],
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
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
            world["store"],
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            target_identity=world["target_identity"],
            boundary=boundary,
            adapter=adapter,
            observed_at=_NOW,
        )
        assert outcome["envelope"]["observation_outcome"] == "IDENTITY_MISMATCH", case_name
        assert outcome["receipt"].status == "FAILED", case_name
