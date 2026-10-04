"""Issue #105: the bounded-SSH-observation grant, and the transport selection it gates.

Pins :mod:`manosube_agent_civilization.runtime.transport_control`'s own closed decisions,
corrected by PR #108 Structural Review Round 1 (F1): a grant is never admitted on the
strength of a self-asserted ``decision_status`` string alone -- it must carry a genuine
Ed25519 signature, verified against the exact Project Binding's own Human Authority signing
key a fresh ``boot_project`` call restores for the exact ``project_id``/``project_binding_id``
the attempt is actually using, and it must independently bind the real target/scope an
attempt is about to use (:func:`require_grant_matches_attempt`). The zero-call, real-route
proof that a grant's own gate sits in front of the real
:func:`~manosube_agent_civilization.runtime.observe_runtime_target`, and that
:class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter` itself enforces this
gate at construction (so no caller can bypass it by constructing the adapter directly), lives
in ``tests/integration/runtime/test_runtime_unattended_ssh.py``; these are this module's own
pure-function proofs, run against a real, Boot-bound world.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from tests.fixtures.runtime_world import (
    DEFAULT_DEPLOYMENT_FINGERPRINT,
    alternate_signing_private_key,
    bound,
    foreign_trust_anchor_private_key,
    runtime_observation_grant_for,
    sign_runtime_observation_grant,
)

from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.transport_control import (
    DISPATCH_STATUSES,
    PERMITTED_TRANSPORT_MODES,
    classify_actions_dispatch,
    compute_runtime_observation_attempt_id,
    render_manual_ssh_command,
    require_grant_matches_attempt,
    require_grant_not_expired,
    require_grant_permits_transport,
    require_valid_grant,
    select_transport,
    select_transport_with_automatic_fallback,
)

_NOW = "2026-06-01T00:00:00Z"


@pytest.fixture
def _world(tmp_path: Path) -> dict[str, Any]:
    store, ctx = bound(tmp_path)
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
    }


def _grant_for_world(world: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    return runtime_observation_grant_for(
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        **overrides,
    )


def test_a_complete_genuinely_signed_grant_is_admitted(_world: dict[str, Any]) -> None:
    grant = _grant_for_world(_world)
    checked = require_valid_grant(
        grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
    )
    assert checked["grant_id"] == grant["grant_id"]
    assert checked["permitted_transports"] == grant["permitted_transports"]


def test_a_grant_scoped_to_a_different_project_or_binding_is_refused_with_zero_boot_calls(
    _world: dict[str, Any],
) -> None:
    """PR #108 SR1 F1: a grant's own declared project/Binding is compared against the real
    attempt *before* any Boot call -- proved here by mocking ``boot_project`` itself and
    asserting it is never invoked for a scope mismatch, whichever side is wrong."""

    grant = _grant_for_world(_world)
    with patch("manosube_agent_civilization.runtime.transport_control.boot_project") as mock_boot:
        with pytest.raises(RuntimeRequirementError):
            require_valid_grant(
                grant,
                store=_world["store"],
                project_id="some-other-project",
                project_binding_id=_world["project_binding_id"],
            )
        with pytest.raises(RuntimeRequirementError):
            require_valid_grant(
                grant,
                store=_world["store"],
                project_id=_world["project_id"],
                project_binding_id="PROJBIND-OTHER",
            )
    assert mock_boot.call_count == 0


def test_a_grant_with_a_forged_or_tampered_signature_is_refused(_world: dict[str, Any]) -> None:
    """A grant that is otherwise perfectly well-formed, scoped to the real world, and
    declares ``decision_status: RATIFIED`` must still be refused once its own signature does
    not verify -- the exact self-asserted-authority gap PR #108 SR1 F1 closes."""

    grant = _grant_for_world(_world)
    tampered = dict(grant)
    tampered["signature"] = dict(tampered["signature"], value="00" * 64)
    with pytest.raises(RuntimeRequirementError):
        require_valid_grant(
            tampered,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
        )


def test_a_grant_signed_by_a_foreign_key_is_refused(_world: dict[str, Any]) -> None:
    """A grant genuinely signed, but by a key that is not this exact Project Binding's own
    Human Authority signing key, must be refused -- a real signature over the real payload is
    not enough; it must be *this project's own* signature."""

    grant = _grant_for_world(_world, signer=alternate_signing_private_key())
    with pytest.raises(RuntimeRequirementError):
        require_valid_grant(
            grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
        )


def test_a_grant_signed_by_an_unrelated_trust_anchor_key_is_refused(_world: dict[str, Any]) -> None:
    grant = _grant_for_world(_world, signer=foreign_trust_anchor_private_key())
    with pytest.raises(RuntimeRequirementError):
        require_valid_grant(
            grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
        )


def test_a_grant_whose_key_id_does_not_name_the_real_signing_key_is_refused(
    _world: dict[str, Any],
) -> None:
    grant = _grant_for_world(_world, signing_key_id="AUTH-KEY-NOT-REAL-0001")
    with pytest.raises(RuntimeRequirementError):
        require_valid_grant(
            grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
        )


def test_self_asserting_decision_status_alone_is_never_enough(_world: dict[str, Any]) -> None:
    """The exact first-delivery defect: a caller cannot simply declare
    ``decision_status: RATIFIED`` with no genuine signature at all and have it admitted."""

    grant = _grant_for_world(_world)
    forged = dict(grant)
    forged["signature"] = {"algorithm": "ed25519", "key_id": "FORGED", "value": "ab" * 64}
    with pytest.raises(RuntimeRequirementError):
        require_valid_grant(
            forged,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
        )


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
        lambda g: g.update({"permitted_fields": []}),
        lambda g: g.update({"permitted_fields": ["hostname", "hostname"]}),
        lambda g: g.update({"max_output_bytes": 0}),
        lambda g: g.update({"max_output_bytes": 10_000_000}),
        lambda g: g.update({"max_lines": 0}),
        lambda g: g.update({"deployment_fingerprint": ""}),
        lambda g: g.update({"deployment_fingerprint": 7}),
        lambda g: g.update({"probe_script_sha256": "not-a-digest"}),
        lambda g: g.update({"probe_script_sha256": "0" * 64}),
        lambda g: g.update({"probe_script_sha256": "A" * 64}),
        lambda g: g.update({"max_timeout_seconds": 0}),
        lambda g: g.update({"max_timeout_seconds": 10_000}),
        lambda g: g.update({"max_timeout_seconds": "30"}),
        lambda g: g.pop("probe_script_sha256"),
        lambda g: g.pop("deployment_fingerprint"),
        lambda g: g.pop("max_timeout_seconds"),
        lambda g: g.update({"permitted_transports": []}),
        lambda g: g.update({"permitted_transports": ["NOT_A_TRANSPORT"]}),
        lambda g: g.update({"permitted_transports": "MANUAL_SSH"}),
        lambda g: g.update({"issued_at": "not-a-timestamp"}),
        lambda g: g.update({"issued_at": "2026-12-01T00:00:00Z", "expires_at": "2026-06-01T00:00:00Z"}),
        lambda g: g.update({"decision_status": "DRAFT"}),
    ],
)
def test_an_unreadable_or_insufficient_grant_is_always_refused(
    _world: dict[str, Any], mutate: Any
) -> None:
    """Unreadable (wrong shape, unknown/missing key, malformed field) and readable-but-
    insufficient (an unratified decision, an unrecognized transport/probe) both land here, on
    the identical raised error -- there is no default-admit path for either kind. Every
    mutation here changes a field the signature itself covers, so even if a mutation were
    applied *before* signing it would still be refused by shape alone; applying it after
    signing (as done here) additionally breaks the signature, which is the point."""

    grant = _grant_for_world(_world)
    mutate(grant)
    with pytest.raises(RuntimeRequirementError):
        require_valid_grant(
            grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
        )


def test_not_a_mapping_is_refused(_world: dict[str, Any]) -> None:
    with pytest.raises(RuntimeRequirementError):
        require_valid_grant(
            "not-a-mapping",
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
        )


def test_require_grant_permits_transport_admits_exactly_what_it_names(
    _world: dict[str, Any],
) -> None:
    grant = _grant_for_world(_world, permitted_transports=["MANUAL_SSH"])
    require_grant_permits_transport(
        grant,
        "MANUAL_SSH",
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
    )
    with pytest.raises(RuntimeRequirementError):
        require_grant_permits_transport(
            grant,
            "PREAUTHORIZED_UNATTENDED_SSH",
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
        )


def test_require_grant_permits_transport_refuses_an_unrecognized_transport_name(
    _world: dict[str, Any],
) -> None:
    grant = _grant_for_world(_world, permitted_transports=["MANUAL_SSH"])
    with pytest.raises(RuntimeRequirementError):
        require_grant_permits_transport(
            grant,
            "CARRIER_PIGEON",
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
        )


@pytest.mark.parametrize("now", ["2026-05-01T00:00:00Z", "2026-12-02T00:00:00Z"])
def test_a_grant_outside_its_own_window_is_refused(_world: dict[str, Any], now: str) -> None:
    grant = _grant_for_world(
        _world, issued_at="2026-06-01T00:00:00Z", expires_at="2026-12-01T00:00:00Z"
    )
    with pytest.raises(RuntimeRequirementError):
        require_grant_not_expired(
            grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=now,
        )


def test_a_grant_inside_its_own_window_is_not_expired(_world: dict[str, Any]) -> None:
    grant = _grant_for_world(
        _world, issued_at="2026-06-01T00:00:00Z", expires_at="2026-12-01T00:00:00Z"
    )
    require_grant_not_expired(
        grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now="2026-07-01T00:00:00Z",
    )


def _boundary(**overrides: Any) -> dict[str, Any]:
    endpoint = {
        "host": "127.0.0.1",
        "port": 22,
        "user": "probe",
        "probe_identity": "OS_HEALTH_SNAPSHOT_BOUNDED",
    }
    endpoint.update(overrides.pop("endpoint", {}))
    boundary = {
        "observation_method": "SSH_EXEC_BOUNDED",
        "endpoint": endpoint,
        "permitted_fields": ["hostname"],
        "timeout_seconds": 5,
    }
    boundary.update(overrides)
    return boundary


def _target(**overrides: Any) -> dict[str, Any]:
    target = {
        "provider": "local",
        "deployment_id": "widget-service",
        "instance_identity": "widget-service-1",
        "deployment_fingerprint": DEFAULT_DEPLOYMENT_FINGERPRINT,
    }
    target.update(overrides)
    return target


def test_require_grant_matches_attempt_admits_the_identical_target_and_scope(
    _world: dict[str, Any],
) -> None:
    grant = _grant_for_world(_world)
    require_grant_matches_attempt(grant, target_identity=_target(), boundary=_boundary())


@pytest.mark.parametrize(
    "boundary_overrides",
    [
        {"endpoint": {"host": "127.0.0.2"}},
        {"endpoint": {"port": 2222}},
        {"endpoint": {"user": "someone-else"}},
        {"endpoint": {"probe_identity": "SOURCE_LOG_EXCERPT_BOUNDED"}},
        {"permitted_fields": ["hostname", "uptime_seconds"]},
        {"timeout_seconds": 999_999},
        {"timeout_seconds": "30"},
    ],
)
def test_require_grant_matches_attempt_refuses_a_boundary_the_grant_does_not_authorize(
    _world: dict[str, Any], boundary_overrides: dict[str, Any]
) -> None:
    grant = _grant_for_world(_world)
    with pytest.raises(RuntimeRequirementError):
        require_grant_matches_attempt(
            grant, target_identity=_target(), boundary=_boundary(**boundary_overrides)
        )


def test_require_grant_matches_attempt_admits_a_timeout_exactly_at_the_grants_own_ceiling(
    _world: dict[str, Any],
) -> None:
    """SR2-F2: the grant's own ``max_timeout_seconds`` is an inclusive ceiling -- an attempt
    whose own ``boundary.timeout_seconds`` exactly equals it is admitted, not refused."""

    grant = _grant_for_world(_world, max_timeout_seconds=30)
    require_grant_matches_attempt(
        grant, target_identity=_target(), boundary=_boundary(timeout_seconds=30)
    )


@pytest.mark.parametrize(
    "target_overrides",
    [
        {"provider": "elsewhere"},
        {"deployment_id": "billing-service"},
        {"instance_identity": "widget-service-2"},
        {"deployment_fingerprint": "sha256:" + "f" * 64},
    ],
)
def test_require_grant_matches_attempt_refuses_a_different_real_target(
    _world: dict[str, Any], target_overrides: dict[str, Any]
) -> None:
    """The exact first-delivery gap: a grant genuinely valid for one target must never be
    accepted for a different one, even though every other check passes. SR2-F2 extends this
    to the target's own claimed ``deployment_fingerprint`` -- a grant issued against one
    declared identity must never be reused once the target has rotated to a new one, even
    though its stable provider/deployment/instance coordinates are unchanged."""

    grant = _grant_for_world(_world)
    with pytest.raises(RuntimeRequirementError):
        require_grant_matches_attempt(
            grant, target_identity=_target(**target_overrides), boundary=_boundary()
        )


def test_render_manual_ssh_command_matches_the_shared_argv_builder(_world: dict[str, Any]) -> None:
    grant = _grant_for_world(_world, permitted_transports=["MANUAL_SSH"])
    command = render_manual_ssh_command(
        grant,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        now=_NOW,
    )
    assert command == (
        "ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 -p 22 "
        "probe@127.0.0.1 'python3 runtime_observation_probe.py OS_HEALTH_SNAPSHOT_BOUNDED'"
    )


def test_render_manual_ssh_command_refuses_a_grant_that_does_not_permit_manual_ssh(
    _world: dict[str, Any],
) -> None:
    grant = _grant_for_world(_world, permitted_transports=["PREAUTHORIZED_UNATTENDED_SSH"])
    with pytest.raises(RuntimeRequirementError):
        render_manual_ssh_command(
            grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )


def test_render_manual_ssh_command_refuses_an_expired_grant(_world: dict[str, Any]) -> None:
    grant = _grant_for_world(
        _world,
        permitted_transports=["MANUAL_SSH"],
        issued_at="2026-01-01T00:00:00Z",
        expires_at="2026-02-01T00:00:00Z",
    )
    with pytest.raises(RuntimeRequirementError):
        render_manual_ssh_command(
            grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )


@pytest.mark.parametrize(
    ("dispatched", "runner_allocated", "start_deadline_exceeded", "expected"),
    [
        (True, True, False, "AVAILABLE"),
        (True, True, True, "AVAILABLE"),
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


def test_select_transport_prefers_actions_when_available_and_unrequested(
    _world: dict[str, Any],
) -> None:
    grant = _grant_for_world(_world)
    assert (
        select_transport(
            actions_status="AVAILABLE",
            requested_transport=None,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )
        == "GITHUB_ACTIONS"
    )


def test_select_transport_uses_an_explicit_request_even_when_actions_is_available(
    _world: dict[str, Any],
) -> None:
    grant = _grant_for_world(_world, permitted_transports=["MANUAL_SSH"])
    assert (
        select_transport(
            actions_status="AVAILABLE",
            requested_transport="MANUAL_SSH",
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )
        == "MANUAL_SSH"
    )


def test_select_transport_never_auto_selects_a_fallback_when_actions_is_unavailable(
    _world: dict[str, Any],
) -> None:
    """Design requirement 6: tool availability must not create Authority. Actions being
    unavailable must never, by itself, select any other transport -- an operator (or a
    caller with its own policy) must make an explicit choice."""

    grant = _grant_for_world(_world)
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


def test_select_transport_refuses_an_explicit_request_the_grant_does_not_permit(
    _world: dict[str, Any],
) -> None:
    grant = _grant_for_world(_world, permitted_transports=["MANUAL_SSH"])
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


def test_select_transport_refuses_an_unrecognized_actions_status(_world: dict[str, Any]) -> None:
    grant = _grant_for_world(_world)
    with pytest.raises(RuntimeRequirementError):
        select_transport(
            actions_status="PROBABLY_FINE",
            requested_transport=None,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )


def test_select_transport_with_automatic_fallback_resolves_once_actions_is_confirmed_unavailable(
    _world: dict[str, Any],
) -> None:
    """PR #108 Structural Review Round 2, SR2-F1: a grant that already, explicitly permits
    ``PREAUTHORIZED_UNATTENDED_SSH`` resolves to it automatically once Actions is *confirmed*
    unavailable and no explicit transport was requested -- no per-attempt Human selection
    required for this one case, because the authority already fully pre-exists in the signed
    grant itself."""

    grant = _grant_for_world(_world)
    assert (
        select_transport_with_automatic_fallback(
            actions_status="UNAVAILABLE",
            requested_transport=None,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )
        == "PREAUTHORIZED_UNATTENDED_SSH"
    )


def test_select_transport_with_automatic_fallback_refuses_an_unknown_actions_status(
    _world: dict[str, Any],
) -> None:
    """An ``UNKNOWN`` startup cause (Actions may still be about to allocate a runner) is never
    treated as confirmed unavailability -- this function requires the decisive answer, never
    the ambiguous one, however eager a caller is to fall back."""

    grant = _grant_for_world(_world)
    with pytest.raises(RuntimeRequirementError):
        select_transport_with_automatic_fallback(
            actions_status="UNKNOWN",
            requested_transport=None,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )
    with pytest.raises(RuntimeRequirementError):
        select_transport_with_automatic_fallback(
            actions_status="AVAILABLE",
            requested_transport=None,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )


def test_select_transport_with_automatic_fallback_refuses_an_explicit_request(
    _world: dict[str, Any],
) -> None:
    """This function's whole purpose is the no-per-attempt-Human-selection case -- a caller
    that already knows which transport it wants must call ``select_transport`` directly."""

    grant = _grant_for_world(_world)
    with pytest.raises(RuntimeRequirementError):
        select_transport_with_automatic_fallback(
            actions_status="UNAVAILABLE",
            requested_transport="PREAUTHORIZED_UNATTENDED_SSH",
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )


def test_select_transport_with_automatic_fallback_refuses_a_grant_that_does_not_permit_it(
    _world: dict[str, Any],
) -> None:
    grant = _grant_for_world(_world, permitted_transports=["MANUAL_SSH"])
    with pytest.raises(RuntimeRequirementError):
        select_transport_with_automatic_fallback(
            actions_status="UNAVAILABLE",
            requested_transport=None,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )


def test_select_transport_with_automatic_fallback_refuses_an_expired_grant(
    _world: dict[str, Any],
) -> None:
    grant = _grant_for_world(
        _world, issued_at="2025-01-01T00:00:00Z", expires_at="2025-02-01T00:00:00Z"
    )
    with pytest.raises(RuntimeRequirementError):
        select_transport_with_automatic_fallback(
            actions_status="UNAVAILABLE",
            requested_transport=None,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
        )


def test_select_transport_with_automatic_fallback_refuses_an_already_satisfied_attempt(
    _world: dict[str, Any],
) -> None:
    """A caller tracking its own bounded, local attempt correlation passes
    ``attempt_already_satisfied=True`` once it already knows this exact attempt reached a
    transport -- refusing a second, duplicate unattended execution."""

    grant = _grant_for_world(_world)
    with pytest.raises(RuntimeRequirementError):
        select_transport_with_automatic_fallback(
            actions_status="UNAVAILABLE",
            requested_transport=None,
            grant=grant,
            store=_world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            now=_NOW,
            attempt_already_satisfied=True,
        )


def test_compute_runtime_observation_attempt_id_is_a_pure_deterministic_function() -> None:
    """The identical inputs always agree; any different input never silently collides."""

    first = compute_runtime_observation_attempt_id(
        grant_id="GRANT-1", actions_status="UNAVAILABLE", now=_NOW
    )
    again = compute_runtime_observation_attempt_id(
        grant_id="GRANT-1", actions_status="UNAVAILABLE", now=_NOW
    )
    assert first == again
    assert first.startswith("RUNTIME-OBSERVATION-ATTEMPT-")

    different_grant = compute_runtime_observation_attempt_id(
        grant_id="GRANT-2", actions_status="UNAVAILABLE", now=_NOW
    )
    different_status = compute_runtime_observation_attempt_id(
        grant_id="GRANT-1", actions_status="UNKNOWN", now=_NOW
    )
    different_now = compute_runtime_observation_attempt_id(
        grant_id="GRANT-1", actions_status="UNAVAILABLE", now="2026-07-01T00:00:00Z"
    )
    assert len({first, different_grant, different_status, different_now}) == 4


def test_permitted_transport_modes_is_the_closed_vocabulary_documented() -> None:
    assert {
        "GITHUB_ACTIONS",
        "MANUAL_SSH",
        "PREAUTHORIZED_UNATTENDED_SSH",
    } == PERMITTED_TRANSPORT_MODES


def test_sign_runtime_observation_grant_matches_require_valid_grant(_world: dict[str, Any]) -> None:
    """A self-contained proof that the fixture's own signing helper and this module's own
    verifier agree about what is signed -- if the two ever drifted apart, every other test in
    this file would start failing for the wrong reason."""

    from tests.fixtures.runtime_world import (
        canonical_signing_private_key,
        human_authority_signing_key,
    )

    base = _grant_for_world(_world)
    base.pop("signature")
    resigned = sign_runtime_observation_grant(
        base,
        private_key=canonical_signing_private_key(),
        key_id=str(human_authority_signing_key()["key_id"]),
    )
    base["signature"] = resigned
    require_valid_grant(
        base,
        store=_world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
    )
