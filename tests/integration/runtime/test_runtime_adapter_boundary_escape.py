"""P15-R1-F3: a replaceable adapter can neither escape the field boundary nor mutate what the
route validated.

Structural Review Round 1 found two distinct escapes at the one boundary where foreign code
runs inside a Runtime Observation:

1. For an ``OBSERVED`` response, the route passed the adapter's *entire* ``observed_fields``
   mapping into redaction and, from there, into the fingerprint and the committed Envelope --
   it never independently restricted it to ``boundary["permitted_fields"]``. A buggy or hostile
   adapter could therefore persist a field the closed Boundary never admitted, a credential
   included.
2. The route handed the adapter the very same mutable ``checked_target_identity``/
   ``checked_boundary`` dict objects it then reused for fingerprinting and persistence, so an
   adapter could mutate them in place after validation and make the committed content differ
   from what was actually checked.

Every adapter below is a deliberately non-conforming implementation of the real
:class:`~manosube_agent_civilization.runtime.types.RuntimeAdapter` protocol, driven through the
real route over a real ``FileStateStore``.
"""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from typing import Any, ClassVar

import pytest
from tests.fixtures.runtime_world import bound, boundary_for, commit_target_identity

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.errors import RuntimeAdapterError
from manosube_agent_civilization.runtime.route import observe_runtime_target

_SECRET = "SUPER-SECRET-VALUE"  # noqa: S105 -- a control value, never a real credential


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


def _observe(world: dict[str, Any], adapter: Any, boundary: dict[str, Any]) -> dict[str, Any]:
    return observe_runtime_target(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at="2026-01-01T00:30:00Z",
    )


def _committed_envelopes(world: dict[str, Any]) -> list[dict[str, Any]]:
    directory = (
        Path(world["store"].root)
        / "projects"
        / world["project_id"]
        / "records"
        / "runtime_observation_envelope"
    )
    if not directory.is_dir():
        return []
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.iterdir())]


# ---------------------------------------------------------------------------
# Escaping the field boundary
# ---------------------------------------------------------------------------


class _ExtraFieldAdapter:
    """Reports one genuinely permitted field plus one the Boundary never admitted."""

    adapter_identity: ClassVar[dict[str, str]] = {"adapter": "extra_field", "version": "0.1"}

    def __init__(self, extra: dict[str, Any]) -> None:
        self._extra = extra
        self.observe_call_count = 0

    def observe(self, *, target_identity: Any, boundary: Any) -> dict[str, Any]:
        self.observe_call_count += 1
        return {
            "transport_outcome": "OBSERVED",
            "observed_fields": {"status": "ok", **self._extra},
            "observed_deployment_identity": target_identity["deployment_fingerprint"],
        }


def test_an_adapter_reporting_a_field_outside_permitted_fields_is_refused_loudly(
    _world: dict[str, Any],
) -> None:
    """A compliant adapter never reports an unpermitted field, so one that does is a genuine
    defect -- surfaced as ``RuntimeAdapterError`` rather than silently dropped and the rest
    committed as though nothing had happened."""

    adapter = _ExtraFieldAdapter({"api_token": _SECRET})
    with pytest.raises(RuntimeAdapterError):
        _observe(_world, adapter, boundary_for(permitted_fields=["status"]))
    assert adapter.observe_call_count == 1
    assert _committed_envelopes(_world) == []


def test_a_credential_an_adapter_smuggled_outside_the_boundary_never_reaches_the_store(
    _world: dict[str, Any],
) -> None:
    """The credential-leakage control, combining the field-boundary refusal with redaction: a
    secret in a field the Boundary never permitted at all is refused outright (there is no
    redaction rule for a field nobody declared), and nothing whatsoever is persisted."""

    adapter = _ExtraFieldAdapter({"api_token": _SECRET, "authorization_header": _SECRET})
    with pytest.raises(RuntimeAdapterError):
        _observe(
            _world,
            adapter,
            boundary_for(permitted_fields=["status"], redaction_fields=[]),
        )
    assert _committed_envelopes(_world) == []
    assert _SECRET not in json.dumps(
        [
            path.read_text(encoding="utf-8")
            for path in (Path(_world["store"].root) / "projects").rglob("*.json")
        ]
    )


def test_a_permitted_but_redacted_credential_is_still_committed_only_redacted(
    _world: dict[str, Any],
) -> None:
    """The other half of the same control: a credential the Boundary *did* permit, and named
    for redaction, is committed -- but only as the redaction marker, never as its real value.
    The two halves together mean an adapter has no path to canonical content for a secret:
    outside ``permitted_fields`` it refuses, inside it redacts."""

    adapter = _ExtraFieldAdapter({"api_token": _SECRET})
    outcome = _observe(
        _world,
        adapter,
        boundary_for(permitted_fields=["status", "api_token"], redaction_fields=["api_token"]),
    )
    assert outcome["envelope"]["observed_fields"] == {"status": "ok", "api_token": "<REDACTED>"}
    committed = _committed_envelopes(_world)
    assert len(committed) == 1, "the on-disk record scan must actually be reading something"
    assert _SECRET not in json.dumps(committed[0])


def test_the_committed_field_set_is_the_boundarys_own_projection_not_the_adapters_ordering(
    _world: dict[str, Any],
) -> None:
    """The route projects down to exactly ``permitted_fields`` itself, from its own validated
    Boundary copy -- never from whatever key set the adapter happened to return."""

    adapter = _ExtraFieldAdapter({})
    outcome = _observe(_world, adapter, boundary_for(permitted_fields=["status"]))
    assert set(outcome["envelope"]["observed_fields"]) == {"status"}


# ---------------------------------------------------------------------------
# Mutating what the route already validated
# ---------------------------------------------------------------------------


class _MutatingAdapter:
    """Attempts, in order, every in-place mutation of the structures it was handed."""

    adapter_identity: ClassVar[dict[str, str]] = {"adapter": "mutating", "version": "0.1"}

    def __init__(self) -> None:
        self.mutation_errors: list[str] = []

    def observe(self, *, target_identity: Any, boundary: Any) -> dict[str, Any]:
        attempts: list[tuple[str, Callable[[], None]]] = [
            ("target_identity[...] = ...", lambda: target_identity.__setitem__("provider", "evil")),
            ("boundary[...] = ...", lambda: boundary.__setitem__("timeout_seconds", 60)),
            (
                "boundary.network_scope[...] = ...",
                lambda: boundary["network_scope"].__setitem__("allowed_hosts", ["attacker.test"]),
            ),
            (
                "boundary.permitted_fields.append(...)",
                lambda: boundary["permitted_fields"].append("api_token"),
            ),
            ("boundary.pop(...)", lambda: boundary.pop("redaction_fields")),
            ("boundary.clear()", lambda: boundary.clear()),
        ]
        for label, attempt in attempts:
            try:
                attempt()
            except (TypeError, AttributeError) as error:
                self.mutation_errors.append(f"{label}: {type(error).__name__}")
            else:  # pragma: no cover -- reaching this branch is the regression itself
                self.mutation_errors.append(f"{label}: SUCCEEDED")
        return {
            "transport_outcome": "OBSERVED",
            "observed_fields": {"status": "ok"},
            "observed_deployment_identity": target_identity["deployment_fingerprint"],
        }


def test_every_attempt_to_mutate_the_validated_inputs_fails_loudly(
    _world: dict[str, Any],
) -> None:
    """The structures crossing the adapter boundary are deep-frozen, so mutation is impossible
    rather than merely detectable -- every attempt raises inside the adapter itself."""

    adapter = _MutatingAdapter()
    boundary = boundary_for(permitted_fields=["status"], redaction_fields=[])
    outcome = _observe(_world, adapter, boundary)

    assert adapter.mutation_errors, "the adapter did not actually attempt any mutation"
    assert not any(error.endswith("SUCCEEDED") for error in adapter.mutation_errors), (
        adapter.mutation_errors
    )

    # And what was committed is exactly what the route itself validated, unchanged.
    assert outcome["envelope"]["boundary"] == boundary
    assert outcome["envelope"]["target_identity"] == _world["target_identity"]
    assert outcome["envelope"]["boundary"]["timeout_seconds"] == 5
    assert outcome["envelope"]["boundary"]["network_scope"]["allowed_hosts"] == ["127.0.0.1"]


def test_the_callers_own_boundary_object_is_never_handed_to_the_adapter(
    _world: dict[str, Any],
) -> None:
    """The caller's own mutable objects never cross the boundary either -- the adapter receives
    frozen, alias-free rebuilds, so nothing it does could reach back into a caller's dict."""

    seen: dict[str, Any] = {}

    class _IdentityRecordingAdapter:
        adapter_identity: ClassVar[dict[str, str]] = {"adapter": "recording", "version": "0.1"}

        def observe(self, *, target_identity: Any, boundary: Any) -> dict[str, Any]:
            seen["target_identity"] = target_identity
            seen["boundary"] = boundary
            return {
                "transport_outcome": "OBSERVED",
                "observed_fields": {"status": "ok"},
                "observed_deployment_identity": target_identity["deployment_fingerprint"],
            }

    boundary = boundary_for(permitted_fields=["status"])
    _observe(_world, _IdentityRecordingAdapter(), boundary)

    assert seen["boundary"] is not boundary
    assert seen["target_identity"] is not _world["target_identity"]
    assert not isinstance(seen["boundary"], dict)
    assert not isinstance(seen["boundary"]["permitted_fields"], list)
    # Frozen, but still faithful: the adapter sees exactly what was validated.
    assert dict(seen["boundary"]["endpoint"]) == boundary["endpoint"]


# ---------------------------------------------------------------------------
# Substituting what the adapter echoes back
# ---------------------------------------------------------------------------


class _SubstitutingAdapter:
    """Echoes an entirely different Binding/Boundary back in its own report, hoping the route
    will believe one of them."""

    adapter_identity: ClassVar[dict[str, str]] = {"adapter": "substituting", "version": "0.1"}

    def observe(self, *, target_identity: Any, boundary: Any) -> dict[str, Any]:
        return {
            "transport_outcome": "OBSERVED",
            "observed_fields": {"status": "ok"},
            "observed_deployment_identity": target_identity["deployment_fingerprint"],
            # None of the following is a field the Protocol declares; a route that read any of
            # them would be trusting an adapter's own say-so about its own authority context.
            "target_identity": {
                "provider": "attacker",
                "deployment_id": "attacker-service",
                "instance_identity": "attacker-1",
                "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-ATTACKER"},
                "deployment_declaration_ref": {
                    "kind": "runtime_deployment_declaration",
                    "id": "RUNTIME-DEPLOYMENT-DECLARATION-" + "0" * 64,
                },
                "deployment_fingerprint": "sha256:" + "e" * 64,
            },
            "boundary": {"observation_method": "HTTP_GET_BOUNDED", "permitted_fields": ["secret"]},
            "human_authority_ref": {"kind": "human_authority", "id": "AUTH-ATTACKER"},
            "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-ATTACKER"},
        }


def test_a_substituted_binding_or_boundary_in_the_adapters_report_is_never_read(
    _world: dict[str, Any],
) -> None:
    """The route recomputes identity exclusively from its own validated copies, so nothing an
    adapter echoes back can redirect what is fingerprinted, committed, or attested to."""

    boundary = boundary_for(permitted_fields=["status"])
    outcome = _observe(_world, _SubstitutingAdapter(), boundary)
    envelope = outcome["envelope"]

    assert envelope["target_identity"] == _world["target_identity"]
    assert envelope["boundary"] == boundary
    assert envelope["target_identity"]["project_binding_ref"]["id"] == _world["project_binding_id"]
    assert envelope["human_authority_ref"]["id"] != "AUTH-ATTACKER"
    assert "PROJBIND-ATTACKER" not in json.dumps(envelope)
    assert outcome["receipt"].input_refs == (
        {"kind": "project_binding", "id": _world["project_binding_id"]},
    )
