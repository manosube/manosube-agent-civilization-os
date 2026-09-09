"""P15-R1-F6 / P15-R2-F2: deployed identity verification is no longer circular, and the
declaration that anchors it is signed by, and bound to, the currently Boot-verified Human
Authority.

Structural Review Round 1 found that ``target_identity["deployment_fingerprint"]`` was an
arbitrary caller string and ``observed_deployment_identity`` was read straight out of the
target's own HTTP response -- so the route's comparison of the two proved only that *the
endpoint echoed the expected string*, which anyone controlling both the target declaration and
the responding endpoint can arrange trivially. That is not independent verification.

The declared side is now anchored: ``target_identity`` carries a required
``deployment_declaration_ref``, which must resolve to a genuinely committed, content-addressed,
Human-Authority-declared ``runtime_deployment_declaration`` whose own independently recomputed
identity matches, and which independently restates every one of this target's identifying
fields. Only then does the existing observed-vs-declared comparison run, unchanged.

**Structural Review Round 2 (P15-R2-F2)** found that anchor still too weak. The declaration
carried a caller-supplied ``human_authority_ref`` but no signature, no signed payload, no
Authority Decision, and no ``status``: its identity functions merely content-addressed that
self-asserted body. Any Store-writing caller could construct a declaration naming any Human
Authority and any deployment fingerprint; ``route._resolve_deployment_declaration``
deliberately did not compare the declaration's own ``human_authority_ref`` against the Human
Authority freshly restored by Boot, and performed no cryptographic verification at all -- so an
old-authority declaration survived a legitimate Human Authority re-binding, and a
fabricated-but-internally-consistent record could anchor whatever fingerprint an attacker's own
endpoint echoed.

The record now carries a required ``status`` (``ACTIVE``/``REVOKED``) and a required Ed25519
``signature`` over its own adopted semantic fields, and the route additionally requires: the
declaration to be ``ACTIVE``; its ``human_authority_ref`` to equal the exact reference *this
call's own Boot* just restored; and its signature to verify against the exact
``human_authority_signing_key`` *that same Boot* restored from the current Project Binding.

Classification, disclosed: every refusal in this file is a
:class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` with **zero
adapter calls and zero commits**, never an ``IDENTITY_MISMATCH`` observation outcome.
``IDENTITY_MISMATCH`` is a statement about what a genuinely reached target reported; here
nothing has been reached at all, because the *request itself* is not anchored -- so there is no
observation to classify, and none is committed.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest
from tests.fixtures.runtime_world import (
    DEFAULT_DEPLOYMENT_FINGERPRINT,
    DEPLOYMENT_DECLARATION_RECORD_KIND,
    REBOUND_SIGNING_KEY_ID,
    alternate_human_authority_signing_key,
    alternate_signing_private_key,
    bound,
    boundary_for,
    canonical_signing_private_key,
    commit_deployment_declaration,
    commit_records,
    commit_target_identity,
    deployment_declaration_for,
    human_authority_signing_key,
    rebind_with_rotated_signing_key,
    rebound_human_authority_signing_key,
    rebound_signing_private_key,
    target_identity_for,
)

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.runtime.adapter import FakeRuntimeAdapter
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.identity import (
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
)
from manosube_agent_civilization.runtime.route import observe_runtime_target

_SPOOFED_FINGERPRINT = "sha256:" + "5" * 64
_ALTERNATE_HUMAN_AUTHORITY_REF = {"kind": "human_authority", "id": "AUTH-ELSEWHERE-0001"}


def _attacker_private_key() -> Ed25519PrivateKey:
    """A fourth fixed, deterministic, test-only Ed25519 key -- one no Project Binding in this
    repository has ever declared. An attacker who can write Store records can produce a
    perfectly valid signature with it; that is exactly what must not be enough."""

    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(b"tests P15-R2-F2 attacker deployment declaration key").digest()
    )


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


def _observe(
    world: dict[str, Any], target_identity: dict[str, Any], adapter: Any
) -> dict[str, Any]:
    return observe_runtime_target(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=target_identity,
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


def _seeded(target_identity: dict[str, Any], **kwargs: Any) -> FakeRuntimeAdapter:
    adapter = FakeRuntimeAdapter()
    adapter.seed_target(target_identity=target_identity, fields={"status": "ok"}, **kwargs)
    return adapter


# ---------------------------------------------------------------------------
# The anchored happy path
# ---------------------------------------------------------------------------


def test_a_target_anchored_to_a_genuinely_committed_declaration_is_observed(
    _world: dict[str, Any],
) -> None:
    target_identity = commit_target_identity(
        _world["store"],
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
    )
    outcome = _observe(_world, target_identity, _seeded(target_identity))
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert (
        outcome["envelope"]["target_identity"]["deployment_declaration_ref"]["kind"]
        == DEPLOYMENT_DECLARATION_RECORD_KIND
    )


def test_an_anchored_target_whose_endpoint_reports_a_different_identity_is_still_a_mismatch(
    _world: dict[str, Any],
) -> None:
    """Anchoring the *declared* side does not weaken the existing observed-vs-declared check --
    a genuinely reached target reporting some other identity is still ``IDENTITY_MISMATCH``,
    exactly as before."""

    target_identity = commit_target_identity(
        _world["store"],
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
    )
    adapter = _seeded(target_identity, observed_deployment_identity="sha256:" + "f" * 64)
    outcome = _observe(_world, target_identity, adapter)
    assert outcome["envelope"]["observation_outcome"] == "IDENTITY_MISMATCH"


# ---------------------------------------------------------------------------
# The spoofing control
# ---------------------------------------------------------------------------


def test_a_caller_selected_fingerprint_with_no_committed_declaration_is_refused(
    _world: dict[str, Any],
) -> None:
    """The exact finding: a caller controls both the declaration and the endpoint, and makes
    them agree on a fingerprint that has no canonical record behind it at all. Before this
    correction that produced a perfectly ``OBSERVED`` Envelope."""

    target_identity = target_identity_for(
        _world["project_binding_id"],
        deployment_declaration_ref={
            "kind": DEPLOYMENT_DECLARATION_RECORD_KIND,
            "id": "RUNTIME-DEPLOYMENT-DECLARATION-" + "0" * 64,
        },
        deployment_fingerprint=_SPOOFED_FINGERPRINT,
    )
    adapter = _seeded(target_identity)  # the endpoint happily echoes the spoofed fingerprint
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, target_identity, adapter)
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


def test_a_declared_fingerprint_diverging_from_its_own_committed_declaration_is_refused(
    _world: dict[str, Any],
) -> None:
    """A genuinely committed declaration exists, and the endpoint agrees with the caller -- but
    the caller's claimed fingerprint is not the one the canonical record actually declares."""

    declaration = deployment_declaration_for(
        _world["project_id"], _world["project_binding_id"], _world["human_authority_ref"]
    )
    ref = commit_deployment_declaration(_world["store"], _world["project_id"], declaration)
    target_identity = target_identity_for(
        _world["project_binding_id"],
        deployment_declaration_ref=ref,
        deployment_fingerprint=_SPOOFED_FINGERPRINT,
    )
    adapter = _seeded(target_identity)
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, target_identity, adapter)
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


# ---------------------------------------------------------------------------
# The replay control
# ---------------------------------------------------------------------------


def test_a_declaration_for_one_target_may_not_anchor_a_different_target(
    _world: dict[str, Any],
) -> None:
    """Target A's own legitimately committed declaration, presented alongside Target B's
    provider/deployment/instance fields. Every field the declaration restates is compared, so a
    valid declaration cannot be replayed as the anchor for anything but its own target."""

    declaration_a = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        provider="local",
        deployment_id="widget-service",
        instance_identity="widget-service-1",
    )
    ref_a = commit_deployment_declaration(_world["store"], _world["project_id"], declaration_a)

    target_b = target_identity_for(
        _world["project_binding_id"],
        deployment_declaration_ref=ref_a,
        provider="local",
        deployment_id="billing-service",
        instance_identity="billing-service-9",
        deployment_fingerprint=DEFAULT_DEPLOYMENT_FINGERPRINT,
    )
    adapter = _seeded(target_b)
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, target_b, adapter)
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


def test_a_declaration_bound_to_a_different_project_binding_is_refused(
    _world: dict[str, Any],
) -> None:
    """The declaration is committed in this project's own Store and is internally valid, but
    binds a different Project Binding than the target claims."""

    declaration = deployment_declaration_for(
        _world["project_id"], "PROJBIND-SOMEWHERE-ELSE", _world["human_authority_ref"]
    )
    ref = commit_deployment_declaration(_world["store"], _world["project_id"], declaration)
    target_identity = target_identity_for(
        _world["project_binding_id"], deployment_declaration_ref=ref
    )
    adapter = _seeded(target_identity)
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, target_identity, adapter)
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


# ---------------------------------------------------------------------------
# The tamper control
# ---------------------------------------------------------------------------


def test_a_committed_declaration_whose_own_identity_does_not_reproduce_is_refused(
    _world: dict[str, Any],
) -> None:
    """A declaration committed directly (a hypothetical bug or an attacker able to write
    records) whose declared content does not reproduce its own content address is refused, the
    identical ``_resolve_*``-with-identity-reverification discipline ``bootstrap.py`` already
    applies to grants and declarations."""

    declaration = deployment_declaration_for(
        _world["project_id"], _world["project_binding_id"], _world["human_authority_ref"]
    )
    forged = deepcopy(declaration)
    forged["deployment_fingerprint"] = _SPOOFED_FINGERPRINT  # id/fingerprint now stale
    commit_records(
        _world["store"],
        _world["project_id"],
        _world["store"].load_current(_world["project_id"]),
        "TX-RUNTIME-FORGED-DEPLOYMENT-DECLARATION",
        [
            (
                DEPLOYMENT_DECLARATION_RECORD_KIND,
                forged["runtime_deployment_declaration_id"],
                forged,
            )
        ],
    )
    target_identity = target_identity_for(
        _world["project_binding_id"],
        deployment_declaration_ref={
            "kind": DEPLOYMENT_DECLARATION_RECORD_KIND,
            "id": forged["runtime_deployment_declaration_id"],
        },
        deployment_fingerprint=_SPOOFED_FINGERPRINT,
    )
    adapter = _seeded(target_identity)
    with pytest.raises(RuntimeRequirementError):
        _observe(_world, target_identity, adapter)
    assert adapter.observe_call_count == 0
    assert _envelope_count(_world) == 0


def test_a_declaration_committed_under_another_project_never_anchors_this_one(
    tmp_path: Path,
) -> None:
    """A genuinely legitimate declaration from an entirely separate Store simply never resolves
    here -- the reference is resolved exclusively within the Store being observed."""

    store_a, ctx_a = bound(tmp_path / "world-a")
    store_b, ctx_b = bound(tmp_path / "world-b")
    boot_b = boot_project(
        store_b, project_id=ctx_b["project_id"], project_binding_id=ctx_b["project_binding_id"]
    )
    declaration_b = deployment_declaration_for(
        ctx_b["project_id"], ctx_b["project_binding_id"], dict(boot_b.human_authority_ref)
    )
    ref_b = commit_deployment_declaration(store_b, ctx_b["project_id"], declaration_b)

    target_identity = target_identity_for(
        ctx_a["project_binding_id"], deployment_declaration_ref=ref_b
    )
    adapter = _seeded(target_identity)
    with pytest.raises(RuntimeRequirementError):
        observe_runtime_target(
            store_a,
            project_id=ctx_a["project_id"],
            project_binding_id=ctx_a["project_binding_id"],
            target_identity=target_identity,
            boundary=boundary_for(),
            adapter=adapter,
            observed_at="2026-01-01T00:30:00Z",
        )
    assert adapter.observe_call_count == 0


# ---------------------------------------------------------------------------
# P15-R2-F2: the declaration must be ACTIVE, Boot-Authority-bound, and genuinely signed
# ---------------------------------------------------------------------------


def _observe_under_binding(
    world: dict[str, Any],
    target_identity: dict[str, Any],
    adapter: Any,
    *,
    project_binding_id: str,
) -> dict[str, Any]:
    """:func:`_observe`, with the Boot-restored Project Binding named explicitly -- needed by
    the re-binding and cross-Binding controls, which are precisely about *which* Binding this
    call restores."""

    return observe_runtime_target(
        world["store"],
        project_id=world["project_id"],
        project_binding_id=project_binding_id,
        target_identity=target_identity,
        boundary=boundary_for(),
        adapter=adapter,
        observed_at="2026-01-01T00:30:00Z",
    )


def _commit_and_target(world: dict[str, Any], declaration: dict[str, Any]) -> dict[str, Any]:
    """Commit *declaration* and return the ``target_identity`` that names it and restates it
    exactly -- so every refusal below is caused by the declaration's own defect, never by an
    incidental field mismatch the earlier P15-R1-F6 checks would catch first."""

    ref = commit_deployment_declaration(world["store"], world["project_id"], declaration)
    return target_identity_for(
        str(declaration["project_binding_ref"]["id"]),
        deployment_declaration_ref=ref,
        provider=str(declaration["provider"]),
        deployment_id=str(declaration["deployment_id"]),
        instance_identity=str(declaration["instance_identity"]),
        deployment_fingerprint=str(declaration["deployment_fingerprint"]),
    )


#: The distinguishing fragment of each P15-R2-F2 refusal's own message, so a control proves the
#: check it names actually fired -- not merely that *something* refused. Without this, a test
#: could pass for an entirely unrelated reason (a field mismatch an earlier P15-R1-F6 check
#: catches) and silently stop testing what its name claims.
_REFUSAL_REASONS = {
    "schema": "is not schema-valid",
    "status": "is not ACTIVE",
    "authority": "does not name the Human Authority this call's own Boot just restored",
    "signature": "carries no genuine Human Authority signature",
    "restatement": "may never anchor a different one",
    "identity": "own recomputed identity does not equal its own declared value",
}


def _refuses_with_nothing_reached(
    world: dict[str, Any],
    target_identity: dict[str, Any],
    *,
    because: str,
    project_binding_id: str | None = None,
) -> None:
    """Every P15-R2-F2 refusal is the identical shape: ``RuntimeRequirementError``, zero adapter
    calls, zero committed Envelopes -- and, per *because*, raised by the specific check the
    calling control is about."""

    adapter = _seeded(target_identity)
    with pytest.raises(RuntimeRequirementError) as raised:
        _observe_under_binding(
            world,
            target_identity,
            adapter,
            project_binding_id=project_binding_id or world["project_binding_id"],
        )
    assert _REFUSAL_REASONS[because] in str(raised.value), str(raised.value)
    assert adapter.observe_call_count == 0
    assert _envelope_count(world) == 0


def test_an_unsigned_declaration_is_refused(_world: dict[str, Any]) -> None:
    """The plainest case: a declaration with no ``signature`` field at all. Before Round 2 this
    *was* the record shape, and it anchored targets happily. It is now refused at canonical
    schema validation, before the route's own signature check is even reached."""

    declaration = deployment_declaration_for(
        _world["project_id"], _world["project_binding_id"], _world["human_authority_ref"]
    )
    unsigned = deepcopy(declaration)
    unsigned.pop("signature")
    # The content address deliberately does not cover ``signature`` (a signature cannot cover
    # its own value), so this record is still perfectly self-consistent on its own terms -- the
    # refusal has to come from the schema requiring a signature, not from a broken identity.
    assert (
        unsigned["runtime_deployment_declaration_id"]
        == declaration["runtime_deployment_declaration_id"]
    )
    _refuses_with_nothing_reached(_world, _commit_and_target(_world, unsigned), because="schema")


def test_a_self_authored_declaration_signed_by_an_attackers_own_key_is_refused(
    _world: dict[str, Any],
) -> None:
    """The exact finding. An attacker who can write Store records mints their own Ed25519 key
    pair, produces a genuinely valid signature over a perfectly well-formed declaration, and
    even claims the canonical ``key_id`` so the composition's own ``key_id`` check passes --
    everything self-consistent, nothing issued by the real Human Authority. The cryptographic
    check against the Boot-restored ``human_authority_signing_key`` is what refuses it."""

    declaration = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        deployment_fingerprint=_SPOOFED_FINGERPRINT,
        signer=_attacker_private_key(),
        signing_key_id=str(human_authority_signing_key()["key_id"]),
    )
    assert declaration["signature"]["key_id"] == human_authority_signing_key()["key_id"]
    _refuses_with_nothing_reached(
        _world, _commit_and_target(_world, declaration), because="signature"
    )


def test_a_declaration_signed_by_a_different_legitimate_human_authority_is_refused(
    _world: dict[str, Any],
) -> None:
    """Not a forgery at all -- a genuine signature by a genuinely legitimate *other* Human
    Authority (the alternate world's own key, which really does sign that world's own records).
    Presented against the canonical Boot-restored signing key, it verifies against nothing."""

    declaration = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        signer=alternate_signing_private_key(),
        signing_key_id=str(alternate_human_authority_signing_key()["key_id"]),
    )
    assert declaration["signature"]["key_id"] != human_authority_signing_key()["key_id"]
    _refuses_with_nothing_reached(
        _world, _commit_and_target(_world, declaration), because="signature"
    )


def test_a_declaration_naming_a_human_authority_boot_did_not_restore_is_refused(
    _world: dict[str, Any],
) -> None:
    """A genuinely signed declaration -- by the canonical key, over its own real payload -- that
    names some *other* Human Authority as its declarer. Round 1 deliberately left this
    unchecked; Round 2 requires the declaration's own ``human_authority_ref`` to equal the exact
    reference this call's own Boot just restored."""

    declaration = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _ALTERNATE_HUMAN_AUTHORITY_REF,
    )
    assert declaration["human_authority_ref"] != _world["human_authority_ref"]
    _refuses_with_nothing_reached(
        _world, _commit_and_target(_world, declaration), because="authority"
    )


def test_a_revoked_declaration_is_refused(_world: dict[str, Any]) -> None:
    """Everything about this record is genuine -- correctly signed by the real Human Authority,
    correctly addressed, correctly restating its own target. It is simply revoked, and a revoked
    deployment declaration anchors nothing."""

    declaration = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        status="REVOKED",
    )
    _refuses_with_nothing_reached(_world, _commit_and_target(_world, declaration), because="status")


def test_the_identical_declaration_is_observed_when_its_status_is_active(
    _world: dict[str, Any],
) -> None:
    """The control for the revocation refusal above: the byte-identical record with
    ``status="ACTIVE"`` is observed normally, so the refusal is caused by the revocation and not
    by anything else this suite changed."""

    declaration = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        status="ACTIVE",
    )
    target_identity = _commit_and_target(_world, declaration)
    outcome = _observe(_world, target_identity, _seeded(target_identity))
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"


def test_a_declaration_tampered_after_signing_breaks_its_own_content_address(
    _world: dict[str, Any],
) -> None:
    """A signature that was genuinely valid at signing time, with another covered field edited
    afterwards and both digests left stale. The existing P15-R1-F6 tamper check catches this
    first -- proved here explicitly so that adding a signature requirement is not mistaken for
    having *replaced* the identity check with it."""

    declaration = deployment_declaration_for(
        _world["project_id"], _world["project_binding_id"], _world["human_authority_ref"]
    )
    tampered = deepcopy(declaration)
    tampered["instance_identity"] = "widget-service-99"
    assert (
        runtime_deployment_declaration_id(tampered) != tampered["runtime_deployment_declaration_id"]
    )
    commit_records(
        _world["store"],
        _world["project_id"],
        _world["store"].load_current(_world["project_id"]),
        "TX-RUNTIME-TAMPERED-AFTER-SIGNING",
        [
            (
                DEPLOYMENT_DECLARATION_RECORD_KIND,
                str(tampered["runtime_deployment_declaration_id"]),
                tampered,
            )
        ],
    )
    _refuses_with_nothing_reached(
        _world,
        target_identity_for(
            _world["project_binding_id"],
            deployment_declaration_ref={
                "kind": DEPLOYMENT_DECLARATION_RECORD_KIND,
                "id": str(tampered["runtime_deployment_declaration_id"]),
            },
            instance_identity="widget-service-99",
        ),
        because="identity",
    )


def test_a_declaration_tampered_and_re_addressed_still_fails_the_signature(
    _world: dict[str, Any],
) -> None:
    """The mirror of the case above, and the one that proves the two checks are genuinely
    independent: the tamperer *also* recomputes both digests, so the record's own identity
    reproduces perfectly and the P15-R1-F6 tamper check passes. Only the signature -- which is
    over the identical payload the identity is computed over, and which the tamperer cannot
    reproduce without the Human Authority's private key -- refuses it."""

    declaration = deployment_declaration_for(
        _world["project_id"], _world["project_binding_id"], _world["human_authority_ref"]
    )
    tampered = deepcopy(declaration)
    tampered["deployment_fingerprint"] = _SPOOFED_FINGERPRINT
    tampered["runtime_deployment_declaration_id"] = runtime_deployment_declaration_id(tampered)
    tampered["runtime_deployment_declaration_semantic_fingerprint"] = (
        runtime_deployment_declaration_semantic_fingerprint(tampered)
    )
    assert tampered["signature"] == declaration["signature"]
    assert (
        runtime_deployment_declaration_id(tampered) == tampered["runtime_deployment_declaration_id"]
    )
    _refuses_with_nothing_reached(_world, _commit_and_target(_world, tampered), because="signature")


# ---------------------------------------------------------------------------
# P15-R2-F2: a legitimate Human Authority signing-key re-binding invalidates the old
# declaration, and only a newly issued, newly signed one succeeds
# ---------------------------------------------------------------------------


@pytest.fixture
def _rebound_world(_world: dict[str, Any]) -> dict[str, Any]:
    """The identical project, legitimately re-bound: a genuinely new ``project_binding``,
    assembled through the real Binding producer under the identical Human Authority but a
    rotated ``human_authority_signing_key``, committed alongside the original.

    This repository has no separate "re-bind" route -- ``bind_project`` owns genesis and genesis
    is strictly one-shot -- so a re-binding is exactly this: a new content-addressed Binding
    record that Boot restores exactly as it restores the original.
    """

    rebound = rebind_with_rotated_signing_key(_world["store"], _world["project_id"])
    rebound_id = str(rebound["project_binding_id"])
    assert rebound_id != _world["project_binding_id"]
    boot_context = boot_project(
        _world["store"], project_id=_world["project_id"], project_binding_id=rebound_id
    )
    # The Human Authority itself is unchanged; only its declared signing key rotated -- which is
    # precisely the case a ``human_authority_ref`` comparison alone would miss.
    assert dict(boot_context.human_authority_ref) == _world["human_authority_ref"]
    assert (
        boot_context.project_binding["human_authority_signing_key"]
        == rebound_human_authority_signing_key()
    )
    return {**_world, "rebound_project_binding_id": rebound_id}


def test_the_declaration_issued_before_a_legitimate_re_binding_is_refused_after_it(
    _rebound_world: dict[str, Any],
) -> None:
    """The old declaration in full: it restates the *old* Binding and is signed by the *old*
    key. Under the old Binding it was, and remains, entirely legitimate; presented once the
    project has been re-bound it anchors nothing, and there is no silent carry-forward."""

    old_declaration = deployment_declaration_for(
        _rebound_world["project_id"],
        _rebound_world["project_binding_id"],
        _rebound_world["human_authority_ref"],
        signer=canonical_signing_private_key(),
        signing_key_id=str(human_authority_signing_key()["key_id"]),
    )
    ref = commit_deployment_declaration(
        _rebound_world["store"], _rebound_world["project_id"], old_declaration
    )
    # The target must name the Binding this call actually restores, so the stale declaration's
    # own restated Binding is the first thing that no longer agrees.
    target_identity = target_identity_for(
        _rebound_world["rebound_project_binding_id"], deployment_declaration_ref=ref
    )
    _refuses_with_nothing_reached(
        _rebound_world,
        target_identity,
        because="restatement",
        project_binding_id=_rebound_world["rebound_project_binding_id"],
    )


def test_a_declaration_restated_for_the_new_binding_but_signed_by_the_stale_key_is_refused(
    _rebound_world: dict[str, Any],
) -> None:
    """The isolating case, and the one the finding really names. This declaration passes every
    earlier check: it restates the new Binding exactly, names the correct -- and genuinely
    current -- Human Authority, is ACTIVE, and its own content address reproduces. Only its
    signature was produced by the pre-re-binding key. Nothing else can be responsible for the
    refusal."""

    stale_signed = deployment_declaration_for(
        _rebound_world["project_id"],
        _rebound_world["rebound_project_binding_id"],
        _rebound_world["human_authority_ref"],
        signer=canonical_signing_private_key(),
        signing_key_id=str(human_authority_signing_key()["key_id"]),
    )
    assert stale_signed["human_authority_ref"] == _rebound_world["human_authority_ref"]
    assert stale_signed["signature"]["key_id"] != REBOUND_SIGNING_KEY_ID
    assert (
        runtime_deployment_declaration_id(stale_signed)
        == stale_signed["runtime_deployment_declaration_id"]
    )
    _refuses_with_nothing_reached(
        _rebound_world,
        _commit_and_target(_rebound_world, stale_signed),
        because="signature",
        project_binding_id=_rebound_world["rebound_project_binding_id"],
    )


def test_a_newly_issued_declaration_signed_under_the_new_binding_is_observed(
    _rebound_world: dict[str, Any],
) -> None:
    """The positive control that makes the two refusals above mean something: re-issue the
    identical deployment declaration under the new Binding, signed by the new key, and the
    identical observation succeeds. A re-binding invalidates old declarations; it does not break
    the mechanism."""

    reissued = deployment_declaration_for(
        _rebound_world["project_id"],
        _rebound_world["rebound_project_binding_id"],
        _rebound_world["human_authority_ref"],
        signer=rebound_signing_private_key(),
        signing_key_id=REBOUND_SIGNING_KEY_ID,
    )
    target_identity = _commit_and_target(_rebound_world, reissued)
    outcome = _observe_under_binding(
        _rebound_world,
        target_identity,
        _seeded(target_identity),
        project_binding_id=_rebound_world["rebound_project_binding_id"],
    )
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"


def test_a_declaration_genuinely_valid_under_one_binding_never_anchors_under_another(
    _rebound_world: dict[str, Any],
) -> None:
    """The cross-Binding control: a declaration correctly restated for, and correctly signed
    under, the *new* Binding, presented while the *original* Binding is the one Boot restores.

    Disclosed: within this Kernel a Project Binding is content-addressed over its own
    ``human_authority_ref``/``human_authority_signing_key``, so "which Binding is in force" and
    "which key signs" are inseparable -- this refusal is therefore reached at the
    ``project_binding_ref`` restatement check, before the signature check. The isolating
    signature-only case is the stale-key test above; both are proved rather than one standing in
    for the other.
    """

    new_binding_declaration = deployment_declaration_for(
        _rebound_world["project_id"],
        _rebound_world["rebound_project_binding_id"],
        _rebound_world["human_authority_ref"],
        signer=rebound_signing_private_key(),
        signing_key_id=REBOUND_SIGNING_KEY_ID,
    )
    ref = commit_deployment_declaration(
        _rebound_world["store"], _rebound_world["project_id"], new_binding_declaration
    )
    _refuses_with_nothing_reached(
        _rebound_world,
        target_identity_for(_rebound_world["project_binding_id"], deployment_declaration_ref=ref),
        because="restatement",
        project_binding_id=_rebound_world["project_binding_id"],
    )


# ---------------------------------------------------------------------------
# P15-R2-F2: the Round 1 replay/cross-project controls still test what they claim to
# ---------------------------------------------------------------------------


def test_the_replayed_declaration_is_itself_a_genuinely_signed_accepted_record(
    _world: dict[str, Any],
) -> None:
    """Round 2 requires the replay control above to keep testing *field restatement*, not to
    start passing for the accidental reason that its declaration is now unsigned. The identical
    declaration the replay test presents against Target B is shown here to observe Target A --
    its own target -- successfully, so its refusal there is genuinely about which target it
    restates."""

    declaration_a = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        provider="local",
        deployment_id="widget-service",
        instance_identity="widget-service-1",
    )
    target_a = _commit_and_target(_world, declaration_a)
    outcome = _observe(_world, target_a, _seeded(target_a))
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"


def test_the_cross_project_declaration_is_itself_genuinely_signed_and_accepted_at_home(
    tmp_path: Path,
) -> None:
    """The same non-vacuity check for the cross-project control: World B's own declaration is
    genuinely signed and genuinely observable *in World B*. Its refusal in World A is therefore
    about resolution scope, not about a missing or broken signature."""

    store_b, ctx_b = bound(tmp_path / "world-b")
    boot_b = boot_project(
        store_b, project_id=ctx_b["project_id"], project_binding_id=ctx_b["project_binding_id"]
    )
    world_b = {
        "store": store_b,
        "project_id": ctx_b["project_id"],
        "project_binding_id": ctx_b["project_binding_id"],
        "human_authority_ref": dict(boot_b.human_authority_ref),
    }
    target_identity = commit_target_identity(
        store_b,
        ctx_b["project_id"],
        ctx_b["project_binding_id"],
        dict(boot_b.human_authority_ref),
    )
    outcome = _observe(world_b, target_identity, _seeded(target_identity))
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
