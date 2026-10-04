"""Issue #105: the grant-gated ``PREAUTHORIZED_UNATTENDED_SSH`` path, end to end.

:mod:`~manosube_agent_civilization.runtime.transport_control`'s own pure-function proofs (what a
grant is, what it permits, when it expires) live in ``tests/unit/runtime/
test_runtime_transport_control.py``. This file is the zero-call, real-route proof that module's
own docstring promises: a Human-ratified grant's gate sits genuinely *in front of* the real
:func:`~manosube_agent_civilization.runtime.route.observe_runtime_target`, not beside it or
after it -- a request this module refuses never reaches
:class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter`, and therefore never
spawns a process, at all.

The one positive path through this file (a valid, ratified, ``PREAUTHORIZED_UNATTENDED_SSH``-
permitting grant) still runs with ``subprocess.run`` mocked, for the identical reason
``test_runtime_transport_independence.py`` discloses: no ``ssh``/``sshd`` binary is available in
this environment, and provisioning one would itself be a machine/service modification outside
this delivery's authorized scope. The real local-SSH-fixture vertical proof, and the real
unattended-dispatch-against-a-real-target proof, are both reported **pending** in this
delivery's own evidence -- never claimed here, and this package's own unattended SSH path is
never actually launched against anything from this test file or any other in this delivery.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from tests.fixtures.runtime_world import (
    bound,
    commit_target_identity,
    runtime_observation_grant_for,
    ssh_boundary_for,
)

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.adapter import SshRuntimeAdapter
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.route import observe_runtime_target
from manosube_agent_civilization.runtime.transport_control import select_transport

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


def _boundary_matching(grant: dict[str, Any]) -> dict[str, Any]:
    """An SSH Boundary naming the identical endpoint the grant itself scopes -- a grant and the
    Boundary it gates describe one target's own transport, never two independently chosen
    ones."""

    return ssh_boundary_for(
        host=grant["host"],
        port=grant["port"],
        user=grant["user"],
        probe_identity=grant["probe_identity"],
        permitted_fields=["hostname"],
        issued_at=_NOW,
        expires_at="2026-06-01T01:00:00Z",
    )


def test_a_ratified_grant_reaches_a_real_observed_outcome_through_the_identical_route(
    _world: dict[str, Any],
) -> None:
    """The one positive path: ``select_transport`` admits ``PREAUTHORIZED_UNATTENDED_SSH``
    because the grant names it, and the identical canonical
    :func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` -- not a second,
    unattended-only route -- carries out the observation."""

    grant = runtime_observation_grant_for(project_id=_world["project_id"])
    transport = select_transport(
        actions_status="UNAVAILABLE",
        requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
        grant=grant,
        now=_NOW,
    )
    assert transport == "PREAUTHORIZED_UNATTENDED_SSH"

    probe_report = {
        "ok": True,
        "fields": {"hostname": "vps1"},
        "deployment_identity": _DEPLOYMENT_FINGERPRINT,
        "reason": None,
    }
    with patch("manosube_agent_civilization.runtime.adapter.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(probe_report) + "\n"
        mock_run.return_value.stderr = ""
        outcome = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=_world["target_identity"],
            boundary=_boundary_matching(grant),
            adapter=SshRuntimeAdapter(),
            observed_at=_NOW,
        )
    assert mock_run.call_count == 1
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["envelope"]["observed_fields"] == {"hostname": "vps1"}
    assert outcome["receipt"].status == "VERIFIED"


def test_no_grant_at_all_is_refused_before_any_transport_is_even_chosen(
    _world: dict[str, Any],
) -> None:
    with pytest.raises(RuntimeRequirementError):
        select_transport(
            actions_status="UNAVAILABLE",
            requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
            grant=None,
            now=_NOW,
        )


def test_an_expired_grant_is_refused_with_zero_adapter_calls(_world: dict[str, Any]) -> None:
    grant = runtime_observation_grant_for(
        project_id=_world["project_id"],
        issued_at="2025-01-01T00:00:00Z",
        expires_at="2025-02-01T00:00:00Z",
    )
    with (
        patch("manosube_agent_civilization.runtime.adapter.subprocess.run") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        select_transport(
            actions_status="UNAVAILABLE",
            requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
            grant=grant,
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

    grant = runtime_observation_grant_for(
        project_id=_world["project_id"], permitted_transports=["MANUAL_SSH"]
    )
    with (
        patch("manosube_agent_civilization.runtime.adapter.subprocess.run") as mock_run,
        pytest.raises(RuntimeRequirementError),
    ):
        select_transport(
            actions_status="UNAVAILABLE",
            requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
            grant=grant,
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

    grant = runtime_observation_grant_for(project_id=_world["project_id"])
    with patch("manosube_agent_civilization.runtime.adapter.subprocess.run") as mock_run:
        with pytest.raises(RuntimeRequirementError):
            select_transport(
                actions_status="UNAVAILABLE",
                requested_transport=None,
                grant=grant,
                now=_NOW,
            )
        with pytest.raises(RuntimeRequirementError):
            select_transport(
                actions_status="UNKNOWN",
                requested_transport=None,
                grant=grant,
                now=_NOW,
            )
    assert mock_run.call_count == 0


def test_a_grant_scoped_to_a_different_project_still_only_gates_transport_not_the_target(
    _world: dict[str, Any],
) -> None:
    """``project_id`` on a grant is the Human-ratified scope of *this authorization*, not a
    second identity check Boundary enforcement already owns -- a grant naming the wrong project
    is still just an ordinary valid-grant-for-a-different-scope fact a caller is responsible for
    matching to the right target. This module makes no claim about enforcing that match itself
    (it owns transport authorization only, never Boundary/target validation, per its own module
    docstring); recorded here so that boundary stays explicit rather than assumed."""

    grant = runtime_observation_grant_for(project_id="some-other-project")
    transport = select_transport(
        actions_status="UNAVAILABLE",
        requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
        grant=grant,
        now=_NOW,
    )
    assert transport == "PREAUTHORIZED_UNATTENDED_SSH"
