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

import json
from pathlib import Path
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
        now_fn=lambda: "2026-06-15T00:00:00Z",
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
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
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
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
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
    )
    polls = {"count": 0}

    def _dispatch_status_provider() -> str:
        polls["count"] += 1
        return "UNKNOWN"

    decision = resolve_bounded_actions_fallback(
        operation_id=operation_id,
        dispatch_status_provider=_dispatch_status_provider,
        max_polls=3,
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        sleep_fn=lambda _seconds: None,
    )
    assert decision == "FALLBACK_AUTHORIZED"
    assert polls["count"] == 3

    adapter = SshRuntimeAdapter(
        grant=grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
        transport="PREAUTHORIZED_UNATTENDED_SSH",
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
    )
    with patch("manosube_agent_civilization.runtime.adapter._run_bounded_subprocess") as mock_run:
        decision = resolve_bounded_actions_fallback(
            operation_id=operation_id,
            dispatch_status_provider=lambda: "UNAVAILABLE",
            max_polls=3,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
            sleep_fn=lambda _seconds: None,
        )
        assert decision == "FALLBACK_REFUSED_NO_GRANT"
    assert mock_run.call_count == 0
