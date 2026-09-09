"""P15-R1-F5: post-check mutation may not cross the adapter boundary, and stale authority may
not be committed.

Structural Review Round 1 found that ``observe_runtime_target`` Boot-verified once at the
start, called the adapter, and then committed under bounded Compare-And-Swap retries, without
ever re-proving that the Project Binding / Human Authority it verified were *still* the ones in
force at either later boundary. A deterministic mutation landing exactly before adapter entry
therefore reached a live target under stale context, and a later retry could commit an Envelope
carrying a now-stale ``human_authority_ref`` into newer State.

Both barriers are now re-proved: immediately before ``adapter.observe`` (refusing with zero
adapter calls), and on **every** commit attempt (refusing to commit rather than persisting
stale authority). Two things this file must keep apart, and does:

- a genuine **Binding/Authority identity change** must refuse; and
- an ordinary **unrelated Store mutation** -- which bumps ``state_revision`` and nothing else --
  must not block anything at all, because a Runtime Observation re-verifies Boot fresh on every
  call and that contention is exactly what the bounded retry exists to absorb. The comparison
  is therefore over the authority-defining projection (Binding identity, Human Authority
  reference, Human Authority signing key), never over ``state_revision``.

**A disclosed structural note.** Within this Kernel a Project Binding is content-addressed over
its own ``human_authority_ref``/``human_authority_signing_key`` (``binding/identity.py``'s own
``_IDENTITY_PAYLOAD_FIELDS``) and Boot re-verifies that address on every restore, so a genuinely
substituted Binding *cannot* also satisfy Boot for the same ``project_binding_id`` -- it is
caught by Boot itself. The barrier-store tests below therefore prove the required behavioural
fact (the adapter is never reached; nothing is committed) through the real Store, while the
controlled-Boot tests prove this route's own comparison, in its own vocabulary
(:class:`~manosube_agent_civilization.runtime.errors.RuntimeAuthorityFreshnessError`), for the
case this route must still defend against: ``observe_runtime_target``'s ``store`` parameter is
``Any``, so a caller may inject any object at all, and this route never assumes the one it was
given is a content-addressed ``FileStateStore``.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from tests.fixtures.runtime_world import bound, boundary_for, commit_records, commit_target_identity

from manosube_agent_civilization.binding.errors import BindingError
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime import route as route_module
from manosube_agent_civilization.runtime.adapter import FakeRuntimeAdapter
from manosube_agent_civilization.runtime.errors import RuntimeAuthorityFreshnessError
from manosube_agent_civilization.runtime.route import observe_runtime_target

_SUBSTITUTED_AUTHORITY = {"kind": "human_authority", "id": "AUTH-SUBSTITUTED-0001"}


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


def _observe(world: dict[str, Any], store: Any, adapter: Any) -> dict[str, Any]:
    return observe_runtime_target(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
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


def _seeded(world: dict[str, Any]) -> FakeRuntimeAdapter:
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=world["target_identity"], fields={"status": "ok"})
    return adapter


# ---------------------------------------------------------------------------
# A real Store, with a deterministic barrier substituting the Binding
# ---------------------------------------------------------------------------


class _BindingBarrierStore:
    """A real ``FileStateStore``, with one deterministic barrier: after *arm_after* resolutions
    of the ``project_binding`` record, every later resolution returns a Binding naming a
    different Human Authority.

    This is the "deterministic mutation landing exactly before/during adapter entry" the
    finding names, expressed as a Store whose answer genuinely changes mid-call -- which is
    precisely the shape ``observe_runtime_target`` must survive, since its own ``store``
    parameter accepts any object a caller injects.
    """

    def __init__(self, delegate: Any, *, arm_after: int) -> None:
        self._delegate = delegate
        self._arm_after = arm_after
        self.binding_resolutions = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def resolve_record(self, project_id: str, kind: str, record_id: str) -> Any:
        resolved = self._delegate.resolve_record(project_id, kind, record_id)
        if kind != "project_binding" or resolved is None:
            return resolved
        self.binding_resolutions += 1
        if self.binding_resolutions <= self._arm_after:
            return resolved
        substituted = deepcopy(resolved)
        substituted["human_authority_ref"] = dict(_SUBSTITUTED_AUTHORITY)
        return substituted


def test_a_binding_substitution_before_the_adapter_call_produces_zero_adapter_calls(
    _world: dict[str, Any],
) -> None:
    """Armed to fire on the pre-adapter re-verification (the second Binding resolution of the
    call). Before this correction there was no second resolution at all, and the adapter was
    reached with stale context."""

    store = _BindingBarrierStore(_world["store"], arm_after=1)
    adapter = _seeded(_world)
    with pytest.raises((RuntimeAuthorityFreshnessError, BindingError)):
        _observe(_world, store, adapter)
    assert store.binding_resolutions >= 2, "the pre-adapter re-verification did not happen"
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


def test_a_binding_substitution_after_the_adapter_call_refuses_the_commit(
    _world: dict[str, Any],
) -> None:
    """Armed to fire on the pre-commit re-verification (the third Binding resolution). The
    adapter has already run -- that observation genuinely happened -- but it is never committed
    under an authority that is no longer in force."""

    store = _BindingBarrierStore(_world["store"], arm_after=2)
    adapter = _seeded(_world)
    with pytest.raises((RuntimeAuthorityFreshnessError, BindingError)):
        _observe(_world, store, adapter)
    assert store.binding_resolutions >= 3, "the pre-commit re-verification did not happen"
    assert adapter.observe_call_count == 1
    assert _envelope_count(_world) == 0


# ---------------------------------------------------------------------------
# The same two barriers, in this route's own vocabulary, under a controlled Boot
# ---------------------------------------------------------------------------


def _controlled_boot(
    monkeypatch: pytest.MonkeyPatch, world: dict[str, Any], *, substitute_from_call: int
) -> dict[str, int]:
    """Replace this route's own single ``boot_project`` call with one that answers honestly
    until *substitute_from_call*, and from then on returns a genuinely different Human
    Authority -- everything else (Binding body, current State) untouched and real."""

    real = boot_project
    calls = {"count": 0}

    def _boot(store: Any, *, project_id: str, project_binding_id: str) -> Any:
        calls["count"] += 1
        context = real(store, project_id=project_id, project_binding_id=project_binding_id)
        if calls["count"] < substitute_from_call:
            return context
        return SimpleNamespace(
            project_id=context.project_id,
            project_binding=context.project_binding,
            project_binding_id=context.project_binding_id,
            objective_revision=context.objective_revision,
            objective_revision_id=context.objective_revision_id,
            authority_rule=context.authority_rule,
            authority_rule_id=context.authority_rule_id,
            current_state=context.current_state,
            human_authority_ref=dict(_SUBSTITUTED_AUTHORITY),
        )

    monkeypatch.setattr(route_module, "boot_project", _boot)
    return calls


def test_the_pre_adapter_check_refuses_a_changed_human_authority_in_this_routes_own_words(
    _world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _controlled_boot(monkeypatch, _world, substitute_from_call=2)
    adapter = _seeded(_world)
    with pytest.raises(RuntimeAuthorityFreshnessError):
        _observe(_world, _world["store"], adapter)
    assert calls["count"] == 2
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


def test_the_pre_commit_check_refuses_a_changed_human_authority_in_this_routes_own_words(
    _world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _controlled_boot(monkeypatch, _world, substitute_from_call=3)
    adapter = _seeded(_world)
    with pytest.raises(RuntimeAuthorityFreshnessError):
        _observe(_world, _world["store"], adapter)
    assert calls["count"] == 3
    assert adapter.observe_call_count == 1
    assert _envelope_count(_world) == 0


def test_an_unchanged_authority_reaches_the_adapter_and_commits_normally(
    _world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control for the two tests above: with the identical controlled Boot never
    substituting anything, all three re-verifications agree and the observation completes --
    so the refusals above are caused by the substitution, not by the re-verification existing.
    """

    calls = _controlled_boot(monkeypatch, _world, substitute_from_call=99)
    adapter = _seeded(_world)
    outcome = _observe(_world, _world["store"], adapter)
    assert calls["count"] == 3
    assert adapter.observe_call_count == 1
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert _envelope_count(_world) == 1


# ---------------------------------------------------------------------------
# Harmless unrelated mutation must still not block anything
# ---------------------------------------------------------------------------


class _UnrelatedContentionStore:
    """A real ``FileStateStore`` that lands exactly one unrelated commit immediately before the
    route's own first commit attempt -- forcing a genuine Compare-And-Swap retry."""

    def __init__(self, delegate: Any, project_id: str) -> None:
        self._delegate = delegate
        self._project_id = project_id
        self.injected = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def commit(self, *args: Any, **kwargs: Any) -> Any:
        if not self.injected:
            self.injected = True
            commit_records(
                self._delegate,
                self._project_id,
                self._delegate.load_current(self._project_id),
                "TX-RUNTIME-UNRELATED-CONTENTION",
                [
                    (
                        "runtime_deployment_declaration",
                        "RUNTIME-DEPLOYMENT-DECLARATION-" + "1" * 64,
                        {"note": "an unrelated record, touching no authority whatsoever"},
                    )
                ],
            )
        return self._delegate.commit(*args, **kwargs)


def test_an_unrelated_commit_landing_during_the_retry_loop_never_blocks_the_observation(
    _world: dict[str, Any],
) -> None:
    """The distinction the finding explicitly requires this correction to keep: an unrelated
    commit bumps ``state_revision`` and nothing else, so the per-attempt freshness check must
    pass and the bounded retry must simply succeed on the next attempt. A check written over
    ``state_revision`` instead of the authority projection would deadlock here."""

    store = _UnrelatedContentionStore(_world["store"], _world["project_id"])
    adapter = _seeded(_world)
    outcome = _observe(_world, store, adapter)
    assert store.injected
    assert adapter.observe_call_count == 1
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    resolved = _world["store"].resolve_record(
        _world["project_id"],
        "runtime_observation_envelope",
        outcome["envelope"]["runtime_observation_envelope_id"],
    )
    assert resolved == outcome["envelope"]
