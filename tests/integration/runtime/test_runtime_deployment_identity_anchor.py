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

**Structural Review Round 3 (P15-R3-F2)** found two things still missing after Round 2: the
declaration had no validity window at all, and -- more fundamentally -- revocation was not
*effective*. Because the record is immutable and content-addressed, minting a new record with
``status="REVOKED"`` never invalidated the original ``ACTIVE`` one, which keeps its own unchanged
id and stays individually resolvable forever, so a target already referencing it could keep
presenting that exact reference indefinitely. Round 2's own "revoked" test proved only that a
*separately constructed* REVOKED record is refused. Both bounds of a required
``valid_from``/``valid_until`` window are now covered by the record's own content address and by
the Human Authority's own signature and compared against this observation's own instant; and
"current" now means what Project State's own canonical pointer names
(``semantic_state.runtime.claims[<target_key>]``, moved atomically by the shipped
``commit_runtime_deployment_declaration``), never "whatever the caller happens to reference".
The Round 3 controls are in the last three sections of this file.

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

from collections.abc import Mapping
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
from manosube_agent_civilization.runtime.deployment_registry import (
    current_deployment_declaration_id,
)
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.identity import (
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
    runtime_deployment_target_key,
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


def _target_for(declaration: Mapping[str, Any], ref: Mapping[str, str]) -> dict[str, Any]:
    return target_identity_for(
        str(declaration["project_binding_ref"]["id"]),
        deployment_declaration_ref=ref,
        provider=str(declaration["provider"]),
        deployment_id=str(declaration["deployment_id"]),
        instance_identity=str(declaration["instance_identity"]),
        deployment_fingerprint=str(declaration["deployment_fingerprint"]),
    )


def _commit_and_target(world: dict[str, Any], declaration: dict[str, Any]) -> dict[str, Any]:
    """Commit *declaration* through the canonical commit-and-supersede path (so it is genuinely
    this target's own *current* declaration -- P15-R3-F2) and return the ``target_identity`` that
    names it and restates it exactly -- so every refusal below is caused by the declaration's own
    defect, never by an incidental field mismatch the earlier P15-R1-F6 checks would catch
    first, and never by the pointer simply being unset."""

    ref = commit_deployment_declaration(world["store"], world["project_id"], declaration)
    return _target_for(declaration, ref)


def _commit_raw_and_target(
    world: dict[str, Any], declaration: dict[str, Any], transaction_id: str
) -> dict[str, Any]:
    """Insert *declaration* as a raw Store record, deliberately bypassing the canonical
    commit-and-supersede path, and return the matching ``target_identity``.

    Needed for the controls whose record is *not schema-valid* and therefore cannot go through
    the canonical committer at all (which validates before it commits, exactly as it should).
    The route's own schema check fires long before the P15-R3-F2 currency check, so the refusal
    each such control asserts is still the one its own name claims.
    """

    commit_records(
        world["store"],
        world["project_id"],
        world["store"].load_current(world["project_id"]),
        transaction_id,
        [
            (
                DEPLOYMENT_DECLARATION_RECORD_KIND,
                str(declaration["runtime_deployment_declaration_id"]),
                declaration,
            )
        ],
    )
    return _target_for(
        declaration,
        {
            "kind": DEPLOYMENT_DECLARATION_RECORD_KIND,
            "id": str(declaration["runtime_deployment_declaration_id"]),
        },
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
    # P15-R3-F2's own two new refusals.
    "window": "falls outside resolved runtime_deployment_declaration",
    "currency": "is no longer the current one for this target",
    "unregistered": "no runtime_deployment_declaration is currently registered for this target",
}


def _refuses_with_nothing_reached(
    world: dict[str, Any],
    target_identity: dict[str, Any],
    *,
    because: str,
    project_binding_id: str | None = None,
    already_committed_envelopes: int = 0,
) -> None:
    """Every P15-R2-F2 (and P15-R3-F2) refusal is the identical shape:
    ``RuntimeRequirementError``, zero adapter calls, zero *new* committed Envelopes -- and, per
    *because*, raised by the specific check the calling control is about.

    *already_committed_envelopes* is non-zero only for the Round 3 supersession controls, which
    deliberately observe successfully **first** (to prove the declaration genuinely worked before
    it was superseded) and then prove the later refusal adds nothing.
    """

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
    assert _envelope_count(world) == already_committed_envelopes


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
    # Inserted raw: since Round 3 the canonical committer schema-validates before it commits, so
    # an unsigned record cannot go through it at all -- which is itself correct, and is why this
    # control has to plant the record directly to reach the *route's* own schema refusal.
    _refuses_with_nothing_reached(
        _world,
        _commit_raw_and_target(_world, unsigned, "TX-RUNTIME-UNSIGNED-DEPLOYMENT-DECLARATION"),
        because="schema",
    )


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


# ---------------------------------------------------------------------------
# P15-R3-F2: the declaration's own validity window
# ---------------------------------------------------------------------------
#
# Round 2's declaration had no validity window at all. Both bounds are now required schema
# fields, both participate in the record's own content address *and* in the Human Authority's
# own signature (so a declaration cannot be re-dated after signing without breaking either), and
# the route compares them against this observation's own ``observed_at`` as real UTC instants,
# inclusive at both ends -- the identical convention ``_require_within_time_window`` already
# applies to the Observation Boundary's own window.
#
# Every ``_observe`` in this file observes at ``2026-01-01T00:30:00Z``.


def test_a_declaration_whose_validity_window_has_not_opened_yet_is_refused(
    _world: dict[str, Any],
) -> None:
    """**Stale.** Genuine in every other respect -- ACTIVE, correctly signed, correctly restating
    its own target, and genuinely the current declaration for it -- but its ``valid_from`` is
    still in the future at this observation's own instant."""

    declaration = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        valid_from="2026-06-01T00:00:00Z",
        valid_until="2026-12-31T23:59:59Z",
    )
    _refuses_with_nothing_reached(_world, _commit_and_target(_world, declaration), because="window")


def test_a_declaration_whose_validity_window_has_already_closed_is_refused(
    _world: dict[str, Any],
) -> None:
    """**Expired.** The mirror case: ``valid_until`` is already in the past. A deployment
    declaration that has simply run out is refused before any adapter call, exactly as an expired
    Observation Boundary already is."""

    declaration = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        valid_from="2025-01-01T00:00:00Z",
        valid_until="2025-12-31T23:59:59Z",
    )
    _refuses_with_nothing_reached(_world, _commit_and_target(_world, declaration), because="window")


@pytest.mark.parametrize("bound_field", ["valid_from", "valid_until"])
def test_an_observation_exactly_on_either_validity_bound_is_observed(
    _world: dict[str, Any], bound_field: str
) -> None:
    """**The inclusive-bound positive controls.** ``observed_at == valid_from`` and
    ``observed_at == valid_until`` must both succeed: this route's own existing time-window
    convention is closed at both ends (``issued_at <= observed <= expires_at``), and a
    declaration window that silently excluded its own stated bounds would mean something
    different from what the Human Authority signed.

    They also make the two refusals above mean something: the window is enforced, not merely
    narrowed by an off-by-one.
    """

    observed_at = "2026-01-01T00:30:00Z"
    valid_from = observed_at if bound_field == "valid_from" else "2026-01-01T00:00:00Z"
    valid_until = observed_at if bound_field == "valid_until" else "2026-12-31T23:59:59Z"
    declaration = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        valid_from=valid_from,
        valid_until=valid_until,
    )
    assert declaration[bound_field] == observed_at
    target_identity = _commit_and_target(_world, declaration)
    outcome = _observe(_world, target_identity, _seeded(target_identity))
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"


def test_a_declarations_validity_window_cannot_be_re_dated_after_signing(
    _world: dict[str, Any],
) -> None:
    """Both bounds are covered by the single shared derivation, so widening a window after the
    fact breaks the record's own content address (caught first) and, once re-addressed, its own
    signature. Proved here at the record level so the window is not merely *checked* but
    genuinely *declared* by the Human Authority."""

    expired = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        valid_from="2025-01-01T00:00:00Z",
        valid_until="2025-12-31T23:59:59Z",
    )
    widened = deepcopy(expired)
    widened["valid_until"] = "2027-12-31T23:59:59Z"
    assert (
        runtime_deployment_declaration_id(widened) != widened["runtime_deployment_declaration_id"]
    )

    re_addressed = deepcopy(widened)
    re_addressed["runtime_deployment_declaration_id"] = runtime_deployment_declaration_id(widened)
    re_addressed["runtime_deployment_declaration_semantic_fingerprint"] = (
        runtime_deployment_declaration_semantic_fingerprint(widened)
    )
    assert re_addressed["signature"] == expired["signature"]
    _refuses_with_nothing_reached(
        _world, _commit_and_target(_world, re_addressed), because="signature"
    )


# ---------------------------------------------------------------------------
# P15-R3-F2: revocation and supersession are genuinely effective
# ---------------------------------------------------------------------------
#
# The defect, restated. A ``runtime_deployment_declaration`` is immutable and content-addressed,
# so minting a new record with ``status="REVOKED"`` does not invalidate the original ``ACTIVE``
# one: that record keeps its own unchanged id and stays individually resolvable, individually
# signature-valid, and individually within its own window forever. Round 2's own "revoked"
# regression test proved only that a *separately constructed* REVOKED record is refused -- never
# that an *already-issued* ACTIVE declaration could actually be revoked.
#
# "Current" now means what Project State's own pointer names
# (``semantic_state.runtime.claims[<target_key>]``), moved atomically by the shipped
# ``commit_runtime_deployment_declaration`` whenever any new declaration is issued for that
# target. The controls below all present a declaration that is *still perfectly genuine on its
# own terms* and is refused purely because it is no longer what the pointer names.


def _target_key_for(target_identity: Mapping[str, Any]) -> str:
    return runtime_deployment_target_key(dict(target_identity))


def _pointer(world: dict[str, Any], target_identity: Mapping[str, Any]) -> str | None:
    return current_deployment_declaration_id(
        world["store"].load_current(world["project_id"]), _target_key_for(target_identity)
    )


def _issue(world: dict[str, Any], *, committed_at: str, **fields: Any) -> dict[str, Any]:
    """Issue one declaration for the default target through the shipped canonical
    commit-and-supersede path, and return ``(declaration, target_identity)`` as a dict."""

    declaration = deployment_declaration_for(
        world["project_id"],
        world["project_binding_id"],
        world["human_authority_ref"],
        **fields,
    )
    ref = commit_deployment_declaration(
        world["store"], world["project_id"], declaration, committed_at=committed_at
    )
    return {"declaration": declaration, "target_identity": _target_for(declaration, ref)}


def test_an_already_issued_active_declaration_is_genuinely_revoked_by_a_later_revocation(
    _world: dict[str, Any],
) -> None:
    """**Revoked-after-issuance** -- the exact case Round 2 could not close.

    Declaration A is issued ACTIVE for a target and *observed successfully*, so it is
    unambiguously working. A new declaration B is then issued for the **same target key** with
    ``status="REVOKED"``, through the canonical path, which atomically moves the pointer to B.
    Presenting A's own still-individually-valid, still-in-window, still-correctly-signed
    reference is now refused -- not because anything about A changed (nothing did; it is still
    byte-identical in the Store) but because A is no longer what the pointer names.
    """

    issued_a = _issue(
        _world, committed_at="2026-09-09T00:00:00Z", declared_at="2026-09-08T00:00:00Z"
    )
    target_a = issued_a["target_identity"]
    a_id = str(issued_a["declaration"]["runtime_deployment_declaration_id"])
    assert _pointer(_world, target_a) == a_id

    outcome = _observe(_world, target_a, _seeded(target_a))
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"

    issued_b = _issue(
        _world,
        committed_at="2026-09-09T01:00:00Z",
        declared_at="2026-09-08T02:00:00Z",
        status="REVOKED",
    )
    b_id = str(issued_b["declaration"]["runtime_deployment_declaration_id"])
    assert b_id != a_id
    assert _pointer(_world, target_a) == b_id

    # A itself is untouched: still resolvable, still byte-identical, still ACTIVE, still signed.
    resolved_a = _world["store"].resolve_record(
        _world["project_id"], DEPLOYMENT_DECLARATION_RECORD_KIND, a_id
    )
    assert resolved_a == issued_a["declaration"]
    assert resolved_a["status"] == "ACTIVE"

    _refuses_with_nothing_reached(
        _world, target_a, because="currency", already_committed_envelopes=1
    )


def test_the_revoking_declaration_itself_is_refused_on_its_own_status(
    _world: dict[str, Any],
) -> None:
    """The other half of a revocation: presenting B, the REVOKED record the pointer now names,
    is refused too -- at the ``status`` check Round 2 already established. A revocation therefore
    closes both doors at once: the old reference is no longer current, and the new one is not
    ACTIVE."""

    _issue(_world, committed_at="2026-09-09T00:00:00Z", declared_at="2026-09-08T00:00:00Z")
    issued_b = _issue(
        _world,
        committed_at="2026-09-09T01:00:00Z",
        declared_at="2026-09-08T02:00:00Z",
        status="REVOKED",
    )
    _refuses_with_nothing_reached(_world, issued_b["target_identity"], because="status")


def test_a_superseded_declaration_is_refused_purely_because_it_is_no_longer_current(
    _world: dict[str, Any],
) -> None:
    """**Superseded** -- the same shape as the revocation above, but B is a *rotation*, not a
    revocation: a new, entirely legitimate ACTIVE declaration for the identical target under a
    new ``deployment_fingerprint``.

    The distinction from ``revoked-after-issuance`` above matters and is deliberately proved
    separately: there, one could argue A was refused "because the deployment was revoked". Here
    nothing was revoked, nothing about A became invalid, and B is as ACTIVE as A ever was. A is
    refused for exactly one reason -- it is not current -- which is the property that makes
    supersession genuinely effective rather than merely declared.

    Note the target key deliberately excludes ``deployment_fingerprint``, which is what makes a
    rotation *supersede* rather than fork into a second, independently-current pointer.
    """

    issued_a = _issue(
        _world, committed_at="2026-09-09T00:00:00Z", declared_at="2026-09-08T00:00:00Z"
    )
    target_a = issued_a["target_identity"]
    a_id = str(issued_a["declaration"]["runtime_deployment_declaration_id"])

    issued_b = _issue(
        _world,
        committed_at="2026-09-09T01:00:00Z",
        declared_at="2026-09-08T02:00:00Z",
        deployment_fingerprint="sha256:" + "b" * 64,
    )
    b_id = str(issued_b["declaration"]["runtime_deployment_declaration_id"])
    assert issued_b["declaration"]["status"] == "ACTIVE"
    assert _target_key_for(target_a) == _target_key_for(issued_b["target_identity"])
    assert _pointer(_world, target_a) == b_id != a_id

    _refuses_with_nothing_reached(_world, target_a, because="currency")

    # And the rotation itself works: B observes normally, so nothing about the mechanism broke.
    target_b = issued_b["target_identity"]
    outcome = _observe(_world, target_b, _seeded(target_b))
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"


def test_a_replayed_old_active_declaration_reference_is_refused(_world: dict[str, Any]) -> None:
    """**Replayed-old-ACTIVE** -- the scenario the review's own disposition names by that phrase,
    stated in its own terms rather than folded into the test above.

    Overlap, stated explicitly: the *mechanism* is identical to ``superseded`` -- an old ACTIVE
    declaration, still individually genuine, refused because the pointer has moved on. The
    difference is what is being demonstrated. ``superseded`` proves the **issuer** side: rotating
    a declaration invalidates its predecessor for new observations. This proves the **caller**
    side: a target that recorded A's reference earlier and keeps presenting that exact reference
    -- indefinitely, across arbitrarily many later observations, exactly as a target legitimately
    may -- does not thereby keep A alive. Both are proved rather than one standing in for the
    other, because the review named the replay case specifically.
    """

    issued_a = _issue(
        _world, committed_at="2026-09-09T00:00:00Z", declared_at="2026-09-08T00:00:00Z"
    )
    replayed_reference = deepcopy(issued_a["target_identity"])

    # The target observes happily, repeatedly, on the reference it holds.
    for observed_at in ("2026-01-01T00:30:00Z", "2026-01-01T00:31:00Z"):
        adapter = _seeded(replayed_reference)
        result = observe_runtime_target(
            _world["store"],
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=replayed_reference,
            boundary=boundary_for(),
            adapter=adapter,
            observed_at=observed_at,
        )
        assert result["envelope"]["observation_outcome"] == "OBSERVED"

    _issue(
        _world,
        committed_at="2026-09-09T01:00:00Z",
        declared_at="2026-09-08T02:00:00Z",
        deployment_fingerprint="sha256:" + "c" * 64,
    )

    # The identical reference the target has been replaying all along now anchors nothing.
    _refuses_with_nothing_reached(
        _world, replayed_reference, because="currency", already_committed_envelopes=2
    )


def test_a_reference_to_another_targets_own_declaration_is_refused(
    _world: dict[str, Any],
) -> None:
    """**Wrong-current-record.** A target presents a reference to an entirely different,
    validly-committed, genuinely current declaration -- one belonging to *another target's* own
    history, and therefore not the record the pointer for this target's own key names.

    Disclosed refusal point, in the same spirit as Round 2's own cross-Binding disclosure
    (``RUNTIME_CONTRACT.md`` §11.3, item 5): because a declaration restates the very fields the
    target key is derived from, a record belonging to another target necessarily fails the
    P15-R1-F6 field-restatement check *before* the P15-R3-F2 currency check is reached. The two
    checks are genuinely independent -- the currency check catches records that restate this
    target correctly and are simply no longer current, proved by the three controls above -- and
    neither stands in for the other.
    """

    other_target_declaration = deployment_declaration_for(
        _world["project_id"],
        _world["project_binding_id"],
        _world["human_authority_ref"],
        deployment_id="billing-service",
        instance_identity="billing-service-9",
    )
    other_ref = commit_deployment_declaration(
        _world["store"], _world["project_id"], other_target_declaration
    )
    # That declaration really is current -- for its own target.
    assert _pointer(_world, _target_for(other_target_declaration, other_ref)) == str(
        other_target_declaration["runtime_deployment_declaration_id"]
    )

    mine = _issue(_world, committed_at="2026-09-09T00:00:00Z", declared_at="2026-09-08T00:00:00Z")
    borrowed = deepcopy(mine["target_identity"])
    borrowed["deployment_declaration_ref"] = dict(other_ref)
    _refuses_with_nothing_reached(_world, borrowed, because="restatement")


def test_a_declaration_never_registered_through_the_canonical_path_anchors_nothing(
    _world: dict[str, Any],
) -> None:
    """The absent-pointer case, and the reason it is a refusal rather than a pass.

    This record is perfectly genuine in every individual respect -- ACTIVE, correctly signed by
    the real Human Authority, correctly restating its own target, in window, and its own content
    address reproduces. It was simply inserted as a raw Store record, never made current through
    ``commit_runtime_deployment_declaration``. Before Round 3 that was enough to anchor a target;
    it is exactly the "anyone who can write a record can anchor anything" gap the pointer closes.
    """

    declaration = deployment_declaration_for(
        _world["project_id"], _world["project_binding_id"], _world["human_authority_ref"]
    )
    target_identity = _commit_raw_and_target(
        _world, declaration, "TX-RUNTIME-UNREGISTERED-DEPLOYMENT-DECLARATION"
    )
    assert _pointer(_world, target_identity) is None
    _refuses_with_nothing_reached(_world, target_identity, because="unregistered")


# ---------------------------------------------------------------------------
# P15-R3-F2: the post-check-substitution barrier
# ---------------------------------------------------------------------------


class _PointerBarrierStore:
    """A real ``FileStateStore`` that lands one legitimate superseding declaration commit at a
    deterministic barrier: immediately before this route's own *first* Envelope commit attempt.

    Deliberately the identical shape as ``test_runtime_authority_freshness.py``'s own
    ``_UnrelatedContentionStore`` (P15-R1-F5), which lands an *unrelated* commit at exactly the
    same point and must **not** block anything. The two together are the whole distinction: an
    unrelated commit bumps ``state_revision`` and is absorbed by the bounded Compare-And-Swap
    retry; a commit that moves *this target's own current-declaration pointer* must refuse on
    the retry rather than persist an Envelope anchored to a declaration that was current when
    checked and is no longer current at commit time.
    """

    def __init__(self, delegate: Any, world: dict[str, Any]) -> None:
        self._delegate = delegate
        self._world = world
        self.injected = False
        self.superseding_id: str | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def commit(self, *args: Any, **kwargs: Any) -> Any:
        if not self.injected:
            self.injected = True
            superseding = deployment_declaration_for(
                self._world["project_id"],
                self._world["project_binding_id"],
                self._world["human_authority_ref"],
                declared_at="2026-09-08T03:00:00Z",
                deployment_fingerprint="sha256:" + "d" * 64,
            )
            commit_deployment_declaration(
                self._delegate,
                self._world["project_id"],
                superseding,
                committed_at="2026-09-09T02:00:00Z",
            )
            self.superseding_id = str(superseding["runtime_deployment_declaration_id"])
        return self._delegate.commit(*args, **kwargs)


def test_a_supersession_landing_after_the_check_but_before_the_commit_refuses_the_commit(
    _world: dict[str, Any],
) -> None:
    """**Post-check-substituted**, mirroring the Round 1 F5 authority-freshness pattern.

    The declaration is genuinely current when this route resolves it, and the adapter genuinely
    runs -- that observation really happened. A legitimate new declaration for the same target is
    then committed at a deterministic barrier that lands *after* resolution and *before* the
    Envelope is actually persisted. The commit is refused rather than persisting an Envelope
    anchored to a declaration that is no longer this target's own current deployment identity.

    Mechanically: the injected commit bumps ``state_revision``, so the route's own first commit
    attempt fails Compare-And-Swap and retries -- and the per-attempt currency re-check (the
    identical per-attempt discipline P15-R1-F5 established for the authority context, deliberately
    re-used rather than a second, parallel mechanism) refuses on that retry. Zero Envelopes.
    """

    issued = _issue(_world, committed_at="2026-09-09T00:00:00Z", declared_at="2026-09-08T00:00:00Z")
    target_identity = issued["target_identity"]
    store = _PointerBarrierStore(_world["store"], _world)
    adapter = _seeded(target_identity)

    with pytest.raises(RuntimeRequirementError) as raised:
        observe_runtime_target(
            store,
            project_id=_world["project_id"],
            project_binding_id=_world["project_binding_id"],
            target_identity=target_identity,
            boundary=boundary_for(),
            adapter=adapter,
            observed_at="2026-01-01T00:30:00Z",
        )
    assert _REFUSAL_REASONS["currency"] in str(raised.value), str(raised.value)
    assert store.injected
    assert adapter.observe_call_count == 1, "the observation itself genuinely happened"
    assert _envelope_count(_world) == 0, "nothing anchored to a superseded declaration persisted"
    assert _pointer(_world, target_identity) == store.superseding_id
