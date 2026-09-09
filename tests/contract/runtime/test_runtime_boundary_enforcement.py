"""P15-R1-F1/F2: the closed Observation Boundary is enforced before any adapter is reached.

Every test in this file drives the real
:func:`~manosube_agent_civilization.runtime.route.observe_runtime_target` over a real
``FileStateStore`` and asserts ``adapter.observe_call_count == 0`` -- the whole point of both
findings is that a Boundary which is malformed, expired, not yet valid, or pointed outside its
own declared network scope must never produce a transport call at all, whichever adapter a
caller supplied.

Round 1's two findings this file covers:

- **F1** -- the route never consulted ``network_scope.allowed_hosts``, so a Boundary could name
  one allowed host and send the request to another. The host-allowlist decision now lives in
  the route's own Boundary validation, so the refusal is structural (zero-call for every
  adapter implementation) rather than each adapter's own to remember.
- **F2** -- the route hand-checked only an observation method, two non-empty timestamp strings,
  and a non-empty ``permitted_fields``; everything else in the declared shape was validated
  only later, inside ``derive_runtime_observation_envelope``, *after* ``adapter.observe`` had
  already run. And the time window was compared lexicographically, which is genuinely unsound
  over this schema's own timestamp grammar (see
  :func:`test_a_fractional_second_past_expiry_is_refused_although_it_sorts_earlier`).
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.runtime_world import bound, boundary_for, commit_target_identity

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.adapter import FakeRuntimeAdapter
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.route import observe_runtime_target


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
    )
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "target_identity": target_identity,
    }


def _refuses_with_zero_adapter_calls(
    world: dict[str, Any],
    boundary: dict[str, Any],
    *,
    observed_at: str = "2026-01-01T00:30:00Z",
    target_identity: dict[str, Any] | None = None,
) -> None:
    adapter = FakeRuntimeAdapter()
    # Seeded with the world's own genuine target, never the deliberately malformed one under
    # test: the adapter is fully able to answer, so a zero call count can only mean the route
    # itself refused before reaching it.
    adapter.seed_target(target_identity=world["target_identity"], fields={"status": "ok"})
    with pytest.raises(RuntimeRequirementError):
        observe_runtime_target(
            world["store"],
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            target_identity=target_identity or world["target_identity"],
            boundary=boundary,
            adapter=adapter,
            observed_at=observed_at,
        )
    assert adapter.observe_call_count == 0


# ---------------------------------------------------------------------------
# F1 -- network scope
# ---------------------------------------------------------------------------


def test_an_endpoint_outside_the_declared_allowed_hosts_never_reaches_the_adapter(
    _world: dict[str, Any],
) -> None:
    """The exact finding: a Boundary naming one allowed host and an endpoint on another."""

    _refuses_with_zero_adapter_calls(
        _world,
        boundary_for(base_url="http://127.0.0.2:8080", allowed_hosts=["127.0.0.1"]),
    )


@pytest.mark.parametrize(
    "base_url",
    [
        "http://allowed.test@attacker.test",
        "http://user:password@127.0.0.1:8080",
        "file:///etc",
        "ftp://127.0.0.1",
        "http://127.0.0.1:abc",
        "http://127.0.0.1:99999",
        "http://127.0.0.%31",
    ],
)
def test_an_ambiguous_or_unsupported_endpoint_never_reaches_the_adapter(
    _world: dict[str, Any], base_url: str
) -> None:
    _refuses_with_zero_adapter_calls(
        _world, boundary_for(base_url=base_url, allowed_hosts=["127.0.0.1", "attacker.test"])
    )


@pytest.mark.parametrize(
    "network_scope",
    [
        {},
        {"allowed_hosts": []},
        {"allowed_hosts": "127.0.0.1"},
        {"allowed_hosts": [""]},
        {"allowed_hosts": ["127.0.0.1", "127.0.0.1"]},
        {"allowed_hosts": ["127.0.0.1"], "unexpected_key": True},
        "not-a-mapping",
    ],
)
def test_a_malformed_network_scope_never_reaches_the_adapter(
    _world: dict[str, Any], network_scope: Any
) -> None:
    boundary = boundary_for()
    boundary["network_scope"] = network_scope
    _refuses_with_zero_adapter_calls(_world, boundary)


# ---------------------------------------------------------------------------
# F2 -- complete Boundary/target shape validation before the adapter
# ---------------------------------------------------------------------------


def _drop(boundary: dict[str, Any], key: str) -> dict[str, Any]:
    mutated = deepcopy(boundary)
    mutated.pop(key)
    return mutated


@pytest.mark.parametrize(
    "missing_key",
    [
        "endpoint",
        "permitted_fields",
        "time_window",
        "network_scope",
        "timeout_seconds",
        "redaction_fields",
    ],
)
def test_a_boundary_missing_any_required_field_never_reaches_the_adapter(
    _world: dict[str, Any], missing_key: str
) -> None:
    """Before this correction only ``observation_method``/``time_window``/``permitted_fields``
    were checked here at all -- a Boundary missing its endpoint, network scope, timeout, or
    redaction fields reached the adapter and was only rejected afterwards, at Envelope
    derivation."""

    _refuses_with_zero_adapter_calls(_world, _drop(boundary_for(), missing_key))


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("endpoint", {"base_url": "http://127.0.0.1:1"}),
        ("endpoint", {"base_url": "http://127.0.0.1:1", "path": "/h", "extra": 1}),
        ("permitted_fields", []),
        ("permitted_fields", ["status", "status"]),
        ("permitted_fields", [""]),
        ("permitted_fields", "status"),
        ("timeout_seconds", 0),
        ("timeout_seconds", -1),
        ("timeout_seconds", 600),
        ("timeout_seconds", "5"),
        ("redaction_fields", "api_token"),
        ("redaction_fields", ["api_token", "api_token"]),
        ("observation_method", "HTTP_POST_UNBOUNDED"),
        ("expected_field", ""),
        ("time_window", {"issued_at": "2026-01-01T00:00:00Z"}),
        ("time_window", {"issued_at": "not-a-timestamp", "expires_at": "2026-01-01T01:00:00Z"}),
        (
            "time_window",
            {"issued_at": "2026-01-01T00:00:00+00:00", "expires_at": "2026-01-01T01:00:00Z"},
        ),
        (
            "time_window",
            {"issued_at": "2026-01-01T00:00:00Z", "expires_at": "2026-01-01T01:00:00Z", "extra": 1},
        ),
    ],
)
def test_a_boundary_with_a_malformed_field_never_reaches_the_adapter(
    _world: dict[str, Any], key: str, value: Any
) -> None:
    boundary = boundary_for()
    boundary[key] = value
    _refuses_with_zero_adapter_calls(_world, boundary)


def test_a_boundary_carrying_an_undeclared_extra_key_never_reaches_the_adapter(
    _world: dict[str, Any],
) -> None:
    boundary = boundary_for()
    boundary["follow_redirects"] = True
    _refuses_with_zero_adapter_calls(_world, boundary)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda t: t.pop("deployment_declaration_ref"),
        lambda t: t.pop("deployment_fingerprint"),
        lambda t: t.update({"provider": ""}),
        lambda t: t.update({"instance_identity": 7}),
        lambda t: t.update({"unexpected_key": "x"}),
        lambda t: t.update({"project_binding_ref": {"kind": "observation", "id": "OBS-1"}}),
        lambda t: t.update(
            {"deployment_declaration_ref": {"kind": "project_binding", "id": "P-1"}}
        ),
    ],
)
def test_a_target_identity_with_a_malformed_field_never_reaches_the_adapter(
    _world: dict[str, Any], mutate: Any
) -> None:
    target_identity = deepcopy(_world["target_identity"])
    mutate(target_identity)
    _refuses_with_zero_adapter_calls(_world, boundary_for(), target_identity=target_identity)


# ---------------------------------------------------------------------------
# F2 -- real-instant time-window comparison
# ---------------------------------------------------------------------------


def test_a_fractional_second_past_expiry_is_refused_although_it_sorts_earlier(
    _world: dict[str, Any],
) -> None:
    """The empirical proof that lexicographic comparison was genuinely unsound, not merely
    inelegant.

    ``common/timestamp.schema.json`` admits an optional fractional part, and ``"."`` (0x2E)
    sorts *below* ``"Z"`` (0x5A). So for the window below::

        "2026-01-01T00:10:00.5Z" < "2026-01-01T00:10:00Z"   # lexicographically True
        00:10:00.5                    > 00:10:00                 # chronologically later

    The old string comparison therefore *accepted* an observation half a second after the
    Boundary had already expired. Real instants refuse it.
    """

    boundary = boundary_for(issued_at="2026-01-01T00:00:00Z", expires_at="2026-01-01T00:10:00Z")
    expired_but_lexically_earlier = "2026-01-01T00:10:00.5Z"
    assert expired_but_lexically_earlier < boundary["time_window"]["expires_at"]
    _refuses_with_zero_adapter_calls(_world, boundary, observed_at=expired_but_lexically_earlier)


def test_a_fractional_second_after_issue_is_accepted_although_it_sorts_earlier(
    _world: dict[str, Any],
) -> None:
    """The other direction of the identical unsoundness: an observation half a second *after*
    a whole-second ``issued_at`` is genuinely inside the window, and the old lexicographic
    check refused it (``"...00.5Z" < "...00Z"``). It must now be accepted."""

    boundary = boundary_for(issued_at="2026-01-01T00:00:00Z", expires_at="2026-01-01T01:00:00Z")
    observed_at = "2026-01-01T00:00:00.5Z"
    assert observed_at < boundary["time_window"]["issued_at"]

    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=_world["target_identity"], fields={"status": "ok"})
    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=_world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at=observed_at,
    )
    assert adapter.observe_call_count == 1
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"


def test_a_window_whose_expiry_precedes_its_issue_never_reaches_the_adapter(
    _world: dict[str, Any],
) -> None:
    """A genuinely ordered window is now required rather than implicitly assumed -- an
    inverted window admits nothing at all, and says so, instead of silently refusing every
    instant for a reason no diagnostic named."""

    _refuses_with_zero_adapter_calls(
        _world,
        boundary_for(issued_at="2026-01-01T02:00:00Z", expires_at="2026-01-01T01:00:00Z"),
        observed_at="2026-01-01T01:30:00Z",
    )


def test_a_zero_width_window_never_reaches_the_adapter(_world: dict[str, Any]) -> None:
    _refuses_with_zero_adapter_calls(
        _world,
        boundary_for(issued_at="2026-01-01T01:00:00Z", expires_at="2026-01-01T01:00:00Z"),
        observed_at="2026-01-01T01:00:00Z",
    )


@pytest.mark.parametrize(
    "observed_at", ["not-a-timestamp", "2026-01-01T00:30:00+00:00", "2026-01-01 00:30:00Z"]
)
def test_a_malformed_observed_at_never_reaches_the_adapter(
    _world: dict[str, Any], observed_at: str
) -> None:
    _refuses_with_zero_adapter_calls(_world, boundary_for(), observed_at=observed_at)
