"""P15-R4-F2: a deployment declaration's lifecycle is a monotonic, signed transition chain.

**The defect, restated.** Round 3 (P15-R3-F2) made "current" mean what Project State's own
pointer names, and moved that pointer atomically whenever any new declaration was issued for a
target. That closed ineffective revocation, but it left the pointer freely re-pointable in *both*
directions, because nothing required a declaration to say what it replaced:

```text
A(ACTIVE)  -> B(REVOKED)   a genuine revocation                                      intended
B(REVOKED) -> A(ACTIVE)    replaying the already-issued, still-signed, still-valid    ACCEPTED
                           ancestor A moved the pointer straight back, and            and wrong
                           un-revoked a revoked deployment target
```

Round 4 makes a declaration's own place in its target's history a **signed** claim: ``generation``
and ``predecessor_ref`` are required fields covered by the record's own content address, its own
semantic fingerprint, and the Human Authority's own signature. The committer admits only genesis
into an empty chain, or a successor naming the exact current head with exactly one greater
generation; a ``REVOKED`` head is permanently terminal; replaying the already-current record is an
idempotent no-op; and a contention loser fails closed rather than re-aiming its own signed body at
a head it was never signed against.

The rules themselves are proved once, over a synthetic record kind, in
``tests/unit/runtime/test_runtime_transition_chain.py`` -- both shipped chains parameterize that
one mechanism. This file proves the *Store-level* consequences on the real declaration chain: what
actually happens to the pointer, to the Store, and to an observation made through a superseded
reference.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.runtime_world import (
    DEPLOYMENT_DECLARATION_RECORD_KIND,
    bound,
    boundary_for,
    commit_deployment_declaration,
    commit_records,
    declaration_successor_fields,
    deployment_declaration_for,
    rebind_with_rotated_signing_key,
    rebound_signing_private_key,
    target_identity_for,
)

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime import commit_runtime_deployment_declaration
from manosube_agent_civilization.runtime.adapter import FakeRuntimeAdapter
from manosube_agent_civilization.runtime.deployment_registry import (
    current_deployment_declaration_id,
)
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.identity import runtime_deployment_target_key
from manosube_agent_civilization.runtime.route import observe_runtime_target


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


def _declaration(world: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return deployment_declaration_for(
        world["project_id"],
        world["project_binding_id"],
        world["human_authority_ref"],
        **fields,
    )


def _commit(world: dict[str, Any], declaration: dict[str, Any], *, at: str) -> dict[str, Any]:
    return commit_runtime_deployment_declaration(
        world["store"], world["project_id"], declaration, committed_at=at
    )


def _successor(world: dict[str, Any], current: dict[str, Any], **fields: Any) -> dict[str, Any]:
    return _declaration(world, **declaration_successor_fields(current), **fields)


def _target_key(declaration: dict[str, Any]) -> str:
    return runtime_deployment_target_key(dict(declaration))


def _pointer(world: dict[str, Any], declaration: dict[str, Any]) -> str | None:
    return current_deployment_declaration_id(
        world["store"].load_current(world["project_id"]), _target_key(declaration)
    )


def _revision(world: dict[str, Any]) -> int:
    return int(world["store"].load_current(world["project_id"])["state_revision"])


def _resolves(world: dict[str, Any], declaration: dict[str, Any]) -> Any:
    return world["store"].resolve_record(
        world["project_id"],
        DEPLOYMENT_DECLARATION_RECORD_KIND,
        str(declaration["runtime_deployment_declaration_id"]),
    )


def _target_for(declaration: dict[str, Any]) -> dict[str, Any]:
    return target_identity_for(
        str(declaration["project_binding_ref"]["id"]),
        deployment_declaration_ref={
            "kind": DEPLOYMENT_DECLARATION_RECORD_KIND,
            "id": str(declaration["runtime_deployment_declaration_id"]),
        },
        provider=str(declaration["provider"]),
        deployment_id=str(declaration["deployment_id"]),
        instance_identity=str(declaration["instance_identity"]),
        deployment_fingerprint=str(declaration["deployment_fingerprint"]),
    )


def _observation_through(world: dict[str, Any], declaration: dict[str, Any]) -> FakeRuntimeAdapter:
    """Attempt one observation anchored to *declaration* and return the adapter, so a caller can
    assert on its call count. Every refusal in this file must cost **zero** adapter calls, which
    is also zero network calls: ``FakeRuntimeAdapter`` reaches nothing, and the count proves the
    route refused before it would have reached anything at all."""

    target_identity = _target_for(declaration)
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=target_identity, fields={"status": "ok"})
    with pytest.raises(RuntimeRequirementError):
        observe_runtime_target(
            world["store"],
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            target_identity=target_identity,
            boundary=boundary_for(),
            adapter=adapter,
            observed_at="2026-01-01T00:30:00Z",
        )
    return adapter


def _refuses_without_state_change(
    world: dict[str, Any], declaration: dict[str, Any], *, at: str, already_committed: bool = False
) -> str:
    """Commit *declaration*, require it to be refused, and prove the refusal cost nothing: the
    pointer is where it was, ``state_revision`` did not move, and -- unless the record was
    *already* legitimately in the Store from an earlier transition -- it was never written at all.

    *already_committed* is true exactly for the ancestor-replay controls, whose whole point is
    that the replayed record is still sitting in the Store, byte-identical and individually
    genuine. There the record's continued presence is the premise, not a leak; what must not
    change is the pointer, and it does not.
    """

    before_pointer = _pointer(world, declaration)
    before_revision = _revision(world)
    before_record = _resolves(world, declaration)
    if already_committed:
        assert before_record == declaration
    else:
        assert before_record is None
    with pytest.raises(RuntimeRequirementError) as raised:
        _commit(world, declaration, at=at)
    assert _pointer(world, declaration) == before_pointer
    assert _revision(world) == before_revision
    assert _resolves(world, declaration) == before_record
    return str(raised.value)


# ---------------------------------------------------------------------------
# Genesis, rotation, revocation -- the positive shapes
# ---------------------------------------------------------------------------


def test_the_chain_admits_genesis_then_rotation_then_revocation_in_order(
    _world: dict[str, Any],
) -> None:
    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    result_a = _commit(_world, a, at="2026-09-09T00:00:00Z")
    assert result_a["transition"] == "GENESIS"
    assert result_a["generation"] == 0
    assert _pointer(_world, a) == a["runtime_deployment_declaration_id"]

    b = _successor(
        _world, a, declared_at="2026-09-08T01:00:00Z", deployment_fingerprint="sha256:" + "b" * 64
    )
    result_b = _commit(_world, b, at="2026-09-09T01:00:00Z")
    assert result_b["transition"] == "SUCCESSOR"
    assert result_b["generation"] == 1
    assert _pointer(_world, a) == b["runtime_deployment_declaration_id"]

    c = _successor(_world, b, declared_at="2026-09-08T02:00:00Z", status="REVOKED")
    result_c = _commit(_world, c, at="2026-09-09T02:00:00Z")
    assert result_c["transition"] == "SUCCESSOR"
    assert result_c["generation"] == 2
    assert _pointer(_world, a) == c["runtime_deployment_declaration_id"]

    # Every superseded record remains exactly as resolvable and as byte-identical as it ever was.
    assert _resolves(_world, a) == a
    assert _resolves(_world, b) == b


# ---------------------------------------------------------------------------
# The two decisive rollback controls
# ---------------------------------------------------------------------------


def test_replaying_the_ancestor_after_a_revocation_leaves_the_pointer_at_the_revocation(
    _world: dict[str, Any],
) -> None:
    """**A(ACTIVE, g=0) -> B(REVOKED, g=1, pred=A) -> replay A** -- the decisive rollback control
    the review names by that exact shape.

    A is genuine in every individual respect after the revocation: byte-identical in the Store,
    still ``ACTIVE``, still correctly signed, still inside its own validity window, still
    restating its own target perfectly. Round 3's committer would have moved the pointer straight
    back to it and silently un-revoked a revoked deployment target. It is now refused, the pointer
    stays at B, and an observation attempted through A's own reference makes **zero** adapter (and
    therefore zero network) calls.
    """

    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")
    b = _successor(_world, a, declared_at="2026-09-08T01:00:00Z", status="REVOKED")
    _commit(_world, b, at="2026-09-09T01:00:00Z")
    b_id = str(b["runtime_deployment_declaration_id"])
    assert _pointer(_world, a) == b_id

    message = _refuses_without_state_change(
        _world, a, at="2026-09-09T02:00:00Z", already_committed=True
    )
    assert "terminal" in message, message
    assert _pointer(_world, a) == b_id

    # A is untouched and still individually genuine -- which is exactly why the pointer, and not
    # the record, has to be what decides.
    resolved = _resolves(_world, a)
    assert resolved == a
    assert resolved["status"] == "ACTIVE"

    adapter = _observation_through(_world, a)
    assert adapter.observe_call_count == 0


def test_replaying_the_ancestor_after_a_rotation_leaves_the_pointer_at_the_rotation(
    _world: dict[str, Any],
) -> None:
    """**A -> B(ACTIVE rotation) -> replay A.**

    Deliberately proved separately from the revocation case above, because the *reasons* differ
    and only one of them would survive a lazy implementation. There, one could argue A is refused
    "because the deployment was revoked". Here nothing was revoked and B is as ``ACTIVE`` as A
    ever was: A is refused purely because a genesis record may not be proposed into a chain that
    already exists, which is the ancestor-replay rule itself.
    """

    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")
    b = _successor(
        _world, a, declared_at="2026-09-08T01:00:00Z", deployment_fingerprint="sha256:" + "b" * 64
    )
    _commit(_world, b, at="2026-09-09T01:00:00Z")
    b_id = str(b["runtime_deployment_declaration_id"])
    assert b["status"] == "ACTIVE"
    assert _pointer(_world, a) == b_id

    message = _refuses_without_state_change(
        _world, a, at="2026-09-09T02:00:00Z", already_committed=True
    )
    assert "ancestor-replay" in message, message
    assert _pointer(_world, a) == b_id
    assert _observation_through(_world, a).observe_call_count == 0


def test_a_deep_chain_cannot_be_rewound_to_any_earlier_generation(
    _world: dict[str, Any],
) -> None:
    """Not only the immediate ancestor: no record anywhere in the chain's history may be replayed
    once the pointer has moved past it."""

    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")
    b = _successor(
        _world, a, declared_at="2026-09-08T01:00:00Z", deployment_fingerprint="sha256:" + "b" * 64
    )
    _commit(_world, b, at="2026-09-09T01:00:00Z")
    c = _successor(
        _world, b, declared_at="2026-09-08T02:00:00Z", deployment_fingerprint="sha256:" + "c" * 64
    )
    _commit(_world, c, at="2026-09-09T02:00:00Z")
    c_id = str(c["runtime_deployment_declaration_id"])

    for ancestor in (a, b):
        _refuses_without_state_change(
            _world, ancestor, at="2026-09-09T03:00:00Z", already_committed=True
        )
        assert _pointer(_world, a) == c_id


# ---------------------------------------------------------------------------
# Illegal transitions, each refusing without any State change
# ---------------------------------------------------------------------------


def test_a_successor_naming_the_wrong_predecessor_refuses_without_state_change(
    _world: dict[str, Any],
) -> None:
    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")
    b = _successor(
        _world, a, declared_at="2026-09-08T01:00:00Z", deployment_fingerprint="sha256:" + "b" * 64
    )
    _commit(_world, b, at="2026-09-09T01:00:00Z")

    # Signed against A, presented once the chain's head is B.
    stale_successor = _successor(
        _world, a, declared_at="2026-09-08T09:00:00Z", deployment_fingerprint="sha256:" + "9" * 64
    )
    message = _refuses_without_state_change(_world, stale_successor, at="2026-09-09T02:00:00Z")
    assert "predecessor_ref" in message, message


def test_a_successor_skipping_a_generation_refuses_without_state_change(
    _world: dict[str, Any],
) -> None:
    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")
    skipped = _declaration(
        _world,
        declared_at="2026-09-08T01:00:00Z",
        deployment_fingerprint="sha256:" + "b" * 64,
        generation=2,
        predecessor_ref={
            "kind": DEPLOYMENT_DECLARATION_RECORD_KIND,
            "id": str(a["runtime_deployment_declaration_id"]),
        },
    )
    message = _refuses_without_state_change(_world, skipped, at="2026-09-09T01:00:00Z")
    assert "one past" in message, message


def test_a_duplicate_generation_with_a_different_body_refuses_without_state_change(
    _world: dict[str, Any],
) -> None:
    """Two genuinely different, genuinely signed records both claiming ``generation=1`` from the
    same predecessor. The first is a legal rotation; the second is refused, because by the time it
    is proposed the pointer no longer names the predecessor it was signed against."""

    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")
    b = _successor(
        _world, a, declared_at="2026-09-08T01:00:00Z", deployment_fingerprint="sha256:" + "b" * 64
    )
    _commit(_world, b, at="2026-09-09T01:00:00Z")

    twin = _successor(
        _world, a, declared_at="2026-09-08T01:00:01Z", deployment_fingerprint="sha256:" + "e" * 64
    )
    assert twin["generation"] == b["generation"] == 1
    assert twin["runtime_deployment_declaration_id"] != b["runtime_deployment_declaration_id"]
    message = _refuses_without_state_change(_world, twin, at="2026-09-09T02:00:00Z")
    assert "predecessor_ref" in message, message


def test_a_successor_after_a_revocation_refuses_without_state_change(
    _world: dict[str, Any],
) -> None:
    """Terminality, at the Store level: a perfectly well-formed successor to a revoked head --
    correct predecessor, correct generation, genuinely signed -- is still refused, and refused
    *as terminal*.

    Scope, disclosed: this proves the terminal property, not a reactivation mechanism. The adopted
    contract states that any later reactivation "requires a separately adopted new target
    epoch/chain, not silent pointer movement", and deliberately does not require that epoch to be
    built in this round -- so it is not built (``10_RUNTIME/RUNTIME_CONTRACT.md`` §13.5, item 8).
    """

    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")
    b = _successor(_world, a, declared_at="2026-09-08T01:00:00Z", status="REVOKED")
    _commit(_world, b, at="2026-09-09T01:00:00Z")

    for status in ("ACTIVE", "REVOKED"):
        reactivation = _successor(
            _world,
            b,
            declared_at=f"2026-09-08T0{2 if status == 'ACTIVE' else 3}:00:00Z",
            status=status,
            deployment_fingerprint="sha256:" + "f" * 64,
        )
        message = _refuses_without_state_change(_world, reactivation, at="2026-09-09T02:00:00Z")
        assert "terminal" in message, message
    assert _pointer(_world, a) == b["runtime_deployment_declaration_id"]


def test_a_first_declaration_that_is_not_a_genesis_record_refuses_without_state_change(
    _world: dict[str, Any],
) -> None:
    """The empty-chain side of the same rule: a chain cannot be opened at generation 5, nor with
    a predecessor that does not exist."""

    for generation, predecessor in (
        (1, None),
        (
            0,
            {
                "kind": DEPLOYMENT_DECLARATION_RECORD_KIND,
                "id": "RUNTIME-DEPLOYMENT-DECLARATION-" + "0" * 64,
            },
        ),
    ):
        proposed = _declaration(
            _world,
            declared_at="2026-09-08T00:00:00Z",
            generation=generation,
            predecessor_ref=predecessor,
        )
        message = _refuses_without_state_change(_world, proposed, at="2026-09-09T00:00:00Z")
        assert "genesis" in message, message


# ---------------------------------------------------------------------------
# Idempotent replay of the exact current record
# ---------------------------------------------------------------------------


def test_replaying_the_exact_current_declaration_is_idempotent_and_moves_nothing(
    _world: dict[str, Any],
) -> None:
    """Item 6 of the canonical commit semantics. Proposing the record the pointer already names
    is a no-op success -- not a backward transition, and deliberately not a transition at all:
    ``state_revision`` does not move, no second State transition is recorded, and the returned
    ``transition`` says so."""

    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")
    revision = _revision(_world)
    pointer = _pointer(_world, a)

    replay = _commit(_world, deepcopy(a), at="2026-09-09T05:00:00Z")
    assert replay["transition"] == "IDEMPOTENT_REPLAY"
    assert replay["committed_state"] is None
    assert replay["runtime_deployment_declaration_ref"]["id"] == pointer
    assert _revision(_world) == revision
    assert _pointer(_world, a) == pointer

    # And the target still observes normally afterwards: a no-op really was a no-op.
    target_identity = _target_for(a)
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=target_identity, fields={"status": "ok"})
    outcome = observe_runtime_target(
        _world["store"],
        project_id=_world["project_id"],
        project_binding_id=_world["project_binding_id"],
        target_identity=target_identity,
        boundary=boundary_for(),
        adapter=adapter,
        observed_at="2026-01-01T00:30:00Z",
    )
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"


def test_replaying_a_revoked_current_declaration_is_also_idempotent(
    _world: dict[str, Any],
) -> None:
    """Terminality does not make the terminal record itself unrepeatable: re-proposing the exact
    record the pointer already names is still a no-op, because nothing moves. What terminality
    forbids is a *successor*, and that is proved separately above."""

    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")
    b = _successor(_world, a, declared_at="2026-09-08T01:00:00Z", status="REVOKED")
    _commit(_world, b, at="2026-09-09T01:00:00Z")
    revision = _revision(_world)

    replay = _commit(_world, deepcopy(b), at="2026-09-09T02:00:00Z")
    assert replay["transition"] == "IDEMPOTENT_REPLAY"
    assert _revision(_world) == revision


# ---------------------------------------------------------------------------
# The committer's own Boot + signature gate (canonical commit semantics, item 2)
# ---------------------------------------------------------------------------


def test_the_committer_refuses_an_unsigned_or_wrongly_signed_transition(
    _world: dict[str, Any],
) -> None:
    """Round 3's committer deliberately did **not** verify the signature, on the reasoning that
    the observation route re-checks it fresh and a second copy could drift. That reasoning rested
    on a premise Round 4 removes: Round 3's committer had no transition legality to gate at all,
    so verifying there would genuinely have bought nothing. It now decides whether a proposal may
    *move a chain*, and it cannot do that honestly while unable to tell a genuine Human Authority
    statement from a forged one -- ``generation`` and ``predecessor_ref`` are part of exactly what
    that signature covers.
    """

    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")

    wrongly_signed = _successor(
        _world,
        a,
        declared_at="2026-09-08T01:00:00Z",
        deployment_fingerprint="sha256:" + "b" * 64,
        signer=rebound_signing_private_key(),
    )
    message = _refuses_without_state_change(_world, wrongly_signed, at="2026-09-09T01:00:00Z")
    assert "genuine Human Authority signature" in message, message


def test_the_committer_refuses_a_declaration_naming_an_authority_boot_did_not_restore(
    _world: dict[str, Any],
) -> None:
    proposed = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        {"kind": "human_authority", "id": "AUTH-ELSEWHERE-0001"},
        declared_at="2026-09-08T00:00:00Z",
    )
    message = _refuses_without_state_change(_world, proposed, at="2026-09-09T00:00:00Z")
    assert "human_authority_ref" in message, message


def test_the_committers_boot_is_fresh_so_a_rebinding_invalidates_a_stale_signer(
    _world: dict[str, Any],
) -> None:
    """The committer Boots freshly on every attempt, so a legitimate Human Authority signing-key
    rotation takes effect for *writes* immediately -- exactly as
    ``observe_runtime_target``'s own independent, later Boot makes it take effect for *reads*.

    Both checks are deliberate and neither subsumes the other: this one gates who may write a
    transition, at commit time; the route's gates who may be trusted at the (possibly much later)
    moment an observation is actually made. They call the identical verifier over the identical
    signing payload, so "two checks" never means "two notions of an acceptable declaration".
    """

    rebound = rebind_with_rotated_signing_key(_world["store"], _world["project_id"])
    rebound_id = str(rebound["project_binding_id"])

    # Signed by the *old* key, but naming the new Binding: the committer's own fresh Boot restores
    # the rotated key and refuses it.
    stale = deployment_declaration_for(
        _world["project_id"],
        rebound_id,
        _world["human_authority_ref"],
        declared_at="2026-09-08T00:00:00Z",
    )
    with pytest.raises(RuntimeRequirementError, match="genuine Human Authority signature"):
        _commit(_world, stale, at="2026-09-09T00:00:00Z")

    # ...and the same declaration signed by the new key is admitted.
    fresh = deployment_declaration_for(
        _world["project_id"],
        rebound_id,
        _world["human_authority_ref"],
        declared_at="2026-09-08T00:00:00Z",
        signer=rebound_signing_private_key(),
        signing_key_id="AUTH-KEY-REBOUND-0001",
    )
    result = _commit(_world, fresh, at="2026-09-09T01:00:00Z")
    assert result["transition"] == "GENESIS"


# ---------------------------------------------------------------------------
# Concurrency: at most one successor wins, and the loser fails closed
# ---------------------------------------------------------------------------


class _CompetingSuccessorStore:
    """A real ``FileStateStore`` that lands one *legitimate competing successor* -- from the very
    same predecessor -- at a deterministic barrier: immediately before the call under test makes
    its own first commit attempt.

    Deliberately the identical technique this package's own
    ``test_runtime_authority_freshness.py`` (``_UnrelatedContentionStore``, P15-R1-F5) and
    ``test_runtime_deployment_identity_anchor.py`` (``_PointerBarrierStore``, P15-R3-F2) already
    use, rather than a new concurrency-simulation mechanism. The point is that the loser's retry
    genuinely re-observes a moved head: the harness never asserts an outcome it did not cause the
    real retry path to produce.
    """

    def __init__(self, delegate: Any, world: dict[str, Any], competitor: dict[str, Any]) -> None:
        self._delegate = delegate
        self._world = world
        self._competitor = competitor
        self.injected = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def commit(self, *args: Any, **kwargs: Any) -> Any:
        if not self.injected:
            self.injected = True
            commit_deployment_declaration(
                self._delegate,
                self._world["project_id"],
                self._competitor,
                committed_at="2026-09-09T01:30:00Z",
            )
        return self._delegate.commit(*args, **kwargs)


def test_two_concurrent_successors_from_the_same_head_resolve_to_at_most_one_winner(
    _world: dict[str, Any],
) -> None:
    """The concurrent-successor decisive control.

    Both proposals are genuine, both are signed by the real Human Authority, and both name the
    identical predecessor with the identical generation -- exactly what two deployment operators
    rotating the same target at the same instant would produce. One lands first. The other's own
    first commit attempt fails Compare-And-Swap, and its retry reloads State and re-evaluates the
    **entire** transition against the new head -- where its own signed ``predecessor_ref`` no
    longer matches, so it fails closed.

    That is not a design preference. Re-aiming the loser at the new head would mean committing a
    body whose own signed content no longer describes its true predecessor, and producing an
    honestly re-aimed one requires a **new signature over a new payload**, which only the Human
    Authority can create -- never this committer. So the loser cannot be "adjusted"; it can only
    be refused, and its operator must re-issue.
    """

    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")

    winner = _successor(
        _world, a, declared_at="2026-09-08T01:00:00Z", deployment_fingerprint="sha256:" + "b" * 64
    )
    loser = _successor(
        _world, a, declared_at="2026-09-08T01:00:01Z", deployment_fingerprint="sha256:" + "e" * 64
    )
    assert winner["generation"] == loser["generation"] == 1
    assert winner["predecessor_ref"] == loser["predecessor_ref"]

    store = _CompetingSuccessorStore(_world["store"], _world, winner)
    with pytest.raises(RuntimeRequirementError) as raised:
        commit_runtime_deployment_declaration(
            store, _world["project_id"], loser, committed_at="2026-09-09T02:00:00Z"
        )
    assert store.injected, "the competing commit must genuinely have landed at the barrier"
    assert "predecessor_ref" in str(raised.value), str(raised.value)

    # At most one winner: the pointer names the competitor, and the loser was never written.
    assert _pointer(_world, a) == winner["runtime_deployment_declaration_id"]
    assert _resolves(_world, winner) == winner
    assert _resolves(_world, loser) is None


def test_an_unrelated_state_bump_during_the_retry_loop_never_blocks_a_legal_transition(
    _world: dict[str, Any],
) -> None:
    """The Round 1 F5 precedent's own required control, deliberately not regressed.

    Round 4 makes the committer refuse rather than retry when *this chain's own* pointer has
    moved. It must still tolerate genuinely unrelated contention -- an unrelated record landing on
    this project, or another target's own declaration -- exactly as Rounds 1 and 3 established. A
    check written over ``state_revision`` instead of over the chain's own pointer would deadlock
    here.
    """

    a = _declaration(_world, declared_at="2026-09-08T00:00:00Z")
    _commit(_world, a, at="2026-09-09T00:00:00Z")
    successor = _successor(
        _world, a, declared_at="2026-09-08T01:00:00Z", deployment_fingerprint="sha256:" + "b" * 64
    )

    class _UnrelatedContentionStore:
        def __init__(self, delegate: Any, world: dict[str, Any]) -> None:
            self._delegate = delegate
            self._world = world
            self.injected = False

        def __getattr__(self, name: str) -> Any:
            return getattr(self._delegate, name)

        def commit(self, *args: Any, **kwargs: Any) -> Any:
            if not self.injected:
                self.injected = True
                # (a) an entirely unrelated record, touching no chain at all, and
                # (b) a genuine declaration for a *different* target, which moves that target's
                #     own pointer and no other.
                commit_records(
                    self._delegate,
                    self._world["project_id"],
                    self._delegate.load_current(self._world["project_id"]),
                    "TX-RUNTIME-CHAIN-UNRELATED-CONTENTION",
                    [
                        (
                            "runtime_deployment_declaration",
                            "RUNTIME-DEPLOYMENT-DECLARATION-" + "1" * 64,
                            {"note": "an unrelated record, touching no chain whatsoever"},
                        )
                    ],
                )
                commit_deployment_declaration(
                    self._delegate,
                    self._world["project_id"],
                    _declaration(
                        self._world,
                        declared_at="2026-09-08T04:00:00Z",
                        deployment_id="billing-service",
                        instance_identity="billing-service-9",
                    ),
                    committed_at="2026-09-09T01:30:00Z",
                )
            return self._delegate.commit(*args, **kwargs)

    store = _UnrelatedContentionStore(_world["store"], _world)
    result = commit_runtime_deployment_declaration(
        store, _world["project_id"], successor, committed_at="2026-09-09T02:00:00Z"
    )
    assert store.injected
    assert result["transition"] == "SUCCESSOR"
    assert _pointer(_world, a) == successor["runtime_deployment_declaration_id"]
