"""Issue #105: the bounded-SSH-observation grant, and the transport selection it gates.

Pins :mod:`manosube_agent_civilization.runtime.transport_control`'s own closed decisions --
what a readable-but-insufficient grant looks like (always refused, never default-admitted),
what a grant's own validity window and ``permitted_transports`` actually bound, and the three
design requirements this module exists to satisfy: tool availability must not create
Authority, Actions-unavailable must never be misclassified, and the manual/unattended paths
must render the identical command. The zero-call, real-route proof that a grant's own gate sits
in front of the real :func:`~manosube_agent_civilization.runtime.observe_runtime_target` lives
in ``tests/integration/runtime/test_runtime_unattended_ssh.py``; these are this module's own
pure-function proofs.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.fixtures.runtime_world import runtime_observation_grant_for

from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.transport_control import (
    DISPATCH_STATUSES,
    HUMAN_AUTHORITY,
    PERMITTED_TRANSPORT_MODES,
    classify_actions_dispatch,
    render_manual_ssh_command,
    require_grant_not_expired,
    require_grant_permits_transport,
    require_valid_grant,
    select_transport,
)

_NOW = "2026-06-01T00:00:00Z"


def test_a_complete_ratified_grant_is_admitted() -> None:
    grant = runtime_observation_grant_for()
    checked = require_valid_grant(grant)
    assert checked["grant_id"] == grant["grant_id"]
    assert checked["permitted_transports"] == grant["permitted_transports"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda g: g.pop("host"),
        lambda g: g.update({"unexpected_key": "x"}),
        lambda g: g.update({"schema_version": "0.2"}),
        lambda g: g.update({"host": ""}),
        lambda g: g.update({"user": 7}),
        lambda g: g.update({"port": "22"}),
        lambda g: g.update({"port": 0}),
        lambda g: g.update({"port": 99999}),
        lambda g: g.update({"probe_identity": "NOT_PINNED"}),
        lambda g: g.update({"permitted_transports": []}),
        lambda g: g.update({"permitted_transports": ["NOT_A_TRANSPORT"]}),
        lambda g: g.update({"permitted_transports": "MANUAL_SSH"}),
        lambda g: g.update({"issued_at": "not-a-timestamp"}),
        lambda g: g.update({"issued_at": "2026-12-01T00:00:00Z", "expires_at": "2026-06-01T00:00:00Z"}),
        lambda g: g.update({"decision_authority": "CLAUDE_CODE"}),
        lambda g: g.update({"decision_status": "DRAFT"}),
    ],
)
def test_an_unreadable_or_insufficient_grant_is_always_refused(mutate: Any) -> None:
    """Unreadable (wrong shape, unknown/missing key, malformed field) and readable-but-
    insufficient (an unratified decision, an unrecognized transport/probe) both land here,
    on the identical raised error -- there is no default-admit path for either kind."""

    grant = runtime_observation_grant_for()
    mutate(grant)
    with pytest.raises(RuntimeRequirementError):
        require_valid_grant(grant)


def test_not_a_mapping_is_refused() -> None:
    with pytest.raises(RuntimeRequirementError):
        require_valid_grant("not-a-mapping")


def test_require_grant_permits_transport_admits_exactly_what_it_names() -> None:
    grant = runtime_observation_grant_for(permitted_transports=["MANUAL_SSH"])
    require_grant_permits_transport(grant, "MANUAL_SSH")
    with pytest.raises(RuntimeRequirementError):
        require_grant_permits_transport(grant, "PREAUTHORIZED_UNATTENDED_SSH")
    with pytest.raises(RuntimeRequirementError):
        require_grant_permits_transport(grant, "GITHUB_ACTIONS")


def test_require_grant_permits_transport_refuses_an_unrecognized_transport_name() -> None:
    grant = runtime_observation_grant_for(permitted_transports=["MANUAL_SSH"])
    with pytest.raises(RuntimeRequirementError):
        require_grant_permits_transport(grant, "CARRIER_PIGEON")


@pytest.mark.parametrize(
    "now",
    ["2026-05-01T00:00:00Z", "2026-12-02T00:00:00Z"],
)
def test_a_grant_outside_its_own_window_is_refused(now: str) -> None:
    grant = runtime_observation_grant_for(
        issued_at="2026-06-01T00:00:00Z", expires_at="2026-12-01T00:00:00Z"
    )
    with pytest.raises(RuntimeRequirementError):
        require_grant_not_expired(grant, now=now)


def test_a_grant_inside_its_own_window_is_not_expired() -> None:
    grant = runtime_observation_grant_for(
        issued_at="2026-06-01T00:00:00Z", expires_at="2026-12-01T00:00:00Z"
    )
    require_grant_not_expired(grant, now="2026-07-01T00:00:00Z")


def test_render_manual_ssh_command_matches_the_shared_argv_builder() -> None:
    grant = runtime_observation_grant_for(permitted_transports=["MANUAL_SSH"])
    command = render_manual_ssh_command(grant, now=_NOW)
    assert command == (
        "ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -p 22 "
        "probe@127.0.0.1 'python3 runtime_observation_probe.py OS_HEALTH_SNAPSHOT_BOUNDED'"
    )


def test_render_manual_ssh_command_refuses_a_grant_that_does_not_permit_manual_ssh() -> None:
    grant = runtime_observation_grant_for(permitted_transports=["PREAUTHORIZED_UNATTENDED_SSH"])
    with pytest.raises(RuntimeRequirementError):
        render_manual_ssh_command(grant, now=_NOW)


def test_render_manual_ssh_command_refuses_an_expired_grant() -> None:
    grant = runtime_observation_grant_for(
        permitted_transports=["MANUAL_SSH"],
        issued_at="2026-01-01T00:00:00Z",
        expires_at="2026-02-01T00:00:00Z",
    )
    with pytest.raises(RuntimeRequirementError):
        render_manual_ssh_command(grant, now=_NOW)


@pytest.mark.parametrize(
    ("dispatched", "runner_allocated", "start_deadline_exceeded", "expected"),
    [
        (True, True, False, "AVAILABLE"),
        (True, True, True, "AVAILABLE"),  # a runner that *did* get allocated is available,
        # regardless of the deadline fact -- runner_allocated is the one fact this module
        # ever trusts as confirming Actions could run at all.
        (True, False, True, "UNAVAILABLE"),
        (False, False, True, "UNAVAILABLE"),
        (False, False, False, "UNAVAILABLE"),
        (True, False, False, "UNKNOWN"),
    ],
)
def test_classify_actions_dispatch_is_purely_a_function_of_observed_facts(
    dispatched: bool, runner_allocated: bool, start_deadline_exceeded: bool, expected: str
) -> None:
    assert (
        classify_actions_dispatch(
            dispatched=dispatched,
            runner_allocated=runner_allocated,
            start_deadline_exceeded=start_deadline_exceeded,
        )
        == expected
    )
    assert expected in DISPATCH_STATUSES


def test_select_transport_prefers_actions_when_available_and_unrequested() -> None:
    grant = runtime_observation_grant_for()
    assert (
        select_transport(actions_status="AVAILABLE", requested_transport=None, grant=grant, now=_NOW)
        == "GITHUB_ACTIONS"
    )


def test_select_transport_uses_an_explicit_request_even_when_actions_is_available() -> None:
    grant = runtime_observation_grant_for(permitted_transports=["MANUAL_SSH"])
    assert (
        select_transport(
            actions_status="AVAILABLE", requested_transport="MANUAL_SSH", grant=grant, now=_NOW
        )
        == "MANUAL_SSH"
    )


def test_select_transport_never_auto_selects_a_fallback_when_actions_is_unavailable() -> None:
    """Design requirement 6: tool availability must not create Authority. Actions being
    unavailable must never, by itself, select any other transport -- an operator (or a
    caller with its own policy) must make an explicit choice."""

    grant = runtime_observation_grant_for()
    with pytest.raises(RuntimeRequirementError):
        select_transport(actions_status="UNAVAILABLE", requested_transport=None, grant=grant, now=_NOW)
    with pytest.raises(RuntimeRequirementError):
        select_transport(actions_status="UNKNOWN", requested_transport=None, grant=grant, now=_NOW)


def test_select_transport_refuses_an_explicit_request_the_grant_does_not_permit() -> None:
    grant = runtime_observation_grant_for(permitted_transports=["MANUAL_SSH"])
    with pytest.raises(RuntimeRequirementError):
        select_transport(
            actions_status="UNAVAILABLE",
            requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
            grant=grant,
            now=_NOW,
        )


def test_select_transport_refuses_an_unrecognized_actions_status() -> None:
    grant = runtime_observation_grant_for()
    with pytest.raises(RuntimeRequirementError):
        select_transport(
            actions_status="PROBABLY_FINE", requested_transport=None, grant=grant, now=_NOW
        )


def test_human_authority_and_permitted_transport_modes_are_the_closed_vocabularies_documented() -> None:
    assert HUMAN_AUTHORITY == "SHUKOU"
    assert {
        "GITHUB_ACTIONS",
        "MANUAL_SSH",
        "PREAUTHORIZED_UNATTENDED_SSH",
    } == PERMITTED_TRANSPORT_MODES
