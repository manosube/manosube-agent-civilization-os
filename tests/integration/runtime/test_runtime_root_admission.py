"""P15-R3-F1: a trusted runtime root is admitted by an externally anchored, signed, canonical
record -- and by nothing else.

**The finding, restated.** Round 2 deleted the public ``provision_trusted_runtime_root`` factory
and concluded that shipped code therefore had no production-legitimate way to obtain a
``TrustedRuntimeRoot`` at all, deferring real issuance to "a future Phase". Round 3 rejected that
in both directions at once:

- Issue #64 assigns this production runtime-provisioning boundary to *this* Phase. A bootstrap
  with no production-legitimate way to obtain its own required first argument does not satisfy
  this Phase's own V5 requirement.
- The test-only issuer's "structural unavailability" was illusory. It worked by importing
  ``bootstrap._PROVISIONING_SENTINEL`` and calling ``TrustedRuntimeRoot(..., sentinel)``
  directly, and Python's leading-underscore convention is not access control -- *any* caller able
  to import the shipped module could do the identical thing over an arbitrary Store.

**What replaced it, and why reintroducing a public constructor is not a walk-back of Round 2.**
Until this round, the security boundary was "possessing a ``TrustedRuntimeRoot`` is sufficient to
reach an adapter" -- which is exactly what was wrong, since a caller could always get one,
through the deleted factory or through the "private" sentinel. After this round, **possessing a
root grants nothing by itself.** ``bootstrap_projection_execution_capability`` admits a root only
against a canonical, Store-committed, ACTIVE ``runtime_root_admission`` record naming exactly
that project and that Project Binding and genuinely signed by the private key matching the
``trust_anchor_public_key_hex`` *the caller of that function supplies from deployment-time
configuration*. The check reruns on every call, before any grant resolution and before
``evaluate_projection_authorization`` is ever reached, whatever the root's provenance.

So a directly constructed root -- via the old sentinel trick, via the public constructor, over
any Store at all -- gets exactly zero benefit. That is what this file proves, test by test, and
it is why Round 2's own mechanical facts (no reintroduced factory, no shipped callable returning
the type, no shipped construction site) are all still asserted, unchanged, in
``tests/contract/runtime/test_runtime_static_conformance.py``.

**Why the trust anchor is deliberately not the project's own Human Authority key.** An
attacker's fully self-consistent alternate world has its own internally-valid Human Authority
signing key. If the admission record's trust rested on *that* key -- or on anything else
resolvable from inside the Store being admitted -- the attacker would simply self-sign a matching
admission record inside their own world and pass. The record therefore carries no
``human_authority_ref`` field at all, and the anchor is supplied from outside. The two
alternate-world controls below are the ones that would fail under any Store-resolvable scheme.
"""

from __future__ import annotations

from copy import deepcopy
import inspect
from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.runtime_world import (
    ROOT_ADMISSION_RECORD_KIND,
    admitted_root,
    alternate_bound,
    alternate_signing_private_key,
    bound,
    commit_declaration,
    commit_grant,
    commit_records,
    commit_root_admission,
    foreign_trust_anchor_private_key,
    root_admission_for,
    sign_alternate_github_projection_grant_declaration,
    trust_anchor_public_key_hex,
    trusted_runtime_root,
)

from manosube_agent_civilization.authority import evaluate_projection_authorization
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import FakeGitHubAdapter, ProjectionExecutionCapability
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.runtime import bootstrap as bootstrap_module
from manosube_agent_civilization.runtime.bootstrap import (
    TrustedRuntimeRoot,
    bootstrap_projection_execution_capability,
)
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.identity import (
    runtime_root_admission_id,
    runtime_root_admission_semantic_fingerprint,
)

_TARGET_REPOSITORY = {"host": "github", "owner": "acme", "repo": "widget"}
_PAYLOAD = {
    "name": "MANOSUBE Evidence Check",
    "head_sha": "a" * 40,
    "status": "completed",
    "conclusion": "neutral",
    "output": {"title": "Evidence artifact", "summary": "hello"},
}


def _authority_world(
    store: Any,
    ctx: dict[str, Any],
    *,
    recorded_at: str,
    signer: Any = None,
    transaction_prefix: str,
) -> dict[str, Any]:
    """Commit one genuine subject/grant/declaration triple into *store* -- the identical real
    records ``bootstrap_projection_execution_capability`` resolves, whichever world they live
    in."""

    evidence = derive_evidence(observation_evidence_request(recorded_at=recorded_at))
    commit_records(
        store,
        ctx["project_id"],
        store.load_current(ctx["project_id"]),
        f"{transaction_prefix}-EVIDENCE",
        [("observation_evidence", evidence["evidence_id"], evidence)],
    )
    boot_context = boot_project(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    human_authority_ref = dict(boot_context.human_authority_ref)
    grant_ref, grant = commit_grant(
        store,
        ctx["project_id"],
        human_authority_ref,
        f"{transaction_prefix}-GRANT",
        subject_ref={"kind": "observation_evidence", "id": evidence["evidence_id"]},
        subject_fingerprint=evidence_semantic_fingerprint(evidence),
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        payload_fingerprint=projection_payload_fingerprint(dict(_PAYLOAD)),
    )
    declaration_ref = commit_declaration(
        store,
        ctx["project_id"],
        ctx["project_binding_id"],
        human_authority_ref,
        grant,
        signer=signer,
    )
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "human_authority_ref": human_authority_ref,
        "grant_ref": grant_ref,
        "declaration_ref": declaration_ref,
    }


@pytest.fixture
def _canonical(tmp_path: Path) -> dict[str, Any]:
    store, ctx = bound(tmp_path / "canonical")
    world = _authority_world(
        store, ctx, recorded_at="2026-09-09T00:00:00Z", transaction_prefix="TX-ADMISSION-CANONICAL"
    )
    world["admitted"] = admitted_root(
        store, project_id=ctx["project_id"], project_binding_id=ctx["project_binding_id"]
    )
    return world


@pytest.fixture
def _alternate(tmp_path: Path) -> dict[str, Any]:
    """One complete, fully self-consistent alternate world -- its own external Human Authority,
    its own Ed25519 signing key, its own Project Binding, its own genuinely signed grants,
    declarations, and subjects -- built through the identical real ``bind_project`` route.

    This is the world Round 1's own factory would have accepted, and it is the world every
    Store-resolvable trust scheme would still accept.
    """

    store, ctx = alternate_bound(tmp_path / "alternate")
    return _authority_world(
        store,
        ctx,
        recorded_at="2026-09-09T00:00:02Z",
        signer=sign_alternate_github_projection_grant_declaration,
        transaction_prefix="TX-ADMISSION-ALTERNATE",
    )


def _counted_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    world: dict[str, Any],
    *,
    root: TrustedRuntimeRoot,
    admission_ref: Any,
    anchor: str,
) -> dict[str, int]:
    """Attempt one provisioning call and return ``{"count": <authorization evaluations>}``.

    The call-count assertion is the same style of proof Round 2's own decisive test established:
    a refusal that happens *after* an authorization evaluation would prove far less than one that
    happens before any evaluation exists at all.
    """

    calls = {"count": 0}

    def _counting_evaluate(request: Any) -> Any:
        calls["count"] += 1
        return evaluate_projection_authorization(request)

    monkeypatch.setattr(bootstrap_module, "evaluate_projection_authorization", _counting_evaluate)

    with pytest.raises(RuntimeRequirementError):
        bootstrap_projection_execution_capability(
            root,
            runtime_root_admission_ref=admission_ref,
            trust_anchor_public_key_hex=anchor,
            github_projection_grant_refs=[world["grant_ref"]],
            github_projection_grant_declaration_refs=[world["declaration_ref"]],
        )
    return calls


# ---------------------------------------------------------------------------
# The genuine positive path, end to end, through entirely shipped code
# ---------------------------------------------------------------------------


def test_a_genuinely_admitted_root_reaches_a_real_capability_end_to_end(
    _canonical: dict[str, Any],
) -> None:
    """The production-legitimate path Round 3 requires to exist.

    A deployment composition boundary constructs a ``TrustedRuntimeRoot`` (public shipped API),
    presents the ``runtime_root_admission`` record it committed for exactly this project and
    Binding, and supplies the ``trust_anchor_public_key_hex`` that record was signed under --
    a genuinely independent Ed25519 key pair, **not** this project's own
    ``human_authority_signing_key``. A real ``ProjectionExecutionCapability`` comes back and
    reaches a controlled adapter.

    Only *shipped* code runs along that path: the fixture layer supplies inputs (a Store, records,
    and the anchor's own signature -- test-side signing, this repository's universal convention),
    and every function that actually decides anything lives in ``src/``.
    """

    admitted = _canonical["admitted"]
    assert admitted["trust_anchor_public_key_hex"] == trust_anchor_public_key_hex()

    capability = bootstrap_projection_execution_capability(
        admitted["trusted_runtime_root"],
        runtime_root_admission_ref=admitted["runtime_root_admission_ref"],
        trust_anchor_public_key_hex=admitted["trust_anchor_public_key_hex"],
        github_projection_grant_refs=[_canonical["grant_ref"]],
        github_projection_grant_declaration_refs=[_canonical["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)

    adapter = FakeGitHubAdapter()  # controlled -- zero live network calls
    result = capability.execute(
        projection_kind="EVIDENCE_ARTIFACT",
        target_repository=_TARGET_REPOSITORY,
        projection_payload=_PAYLOAD,
        adapter=adapter,
        materialized_at="2026-09-09T00:00:00Z",
        attempt_claim_token="RUNTIME-ADMISSION-ATTEMPT-0001",  # noqa: S106
    )
    assert adapter.materialize_call_count == 1
    assert result["receipt"].status == "VERIFIED"


def test_the_trust_anchor_is_not_the_projects_own_human_authority_signing_key(
    _canonical: dict[str, Any],
) -> None:
    """The non-vacuity control for the positive path above, and the whole architectural point.

    If the anchor happened to be the project's own Boot-restored signing key, the check would be
    self-referential: an attacker's alternate world carries its own internally valid Human
    Authority key, and could self-sign a matching admission record with it. The anchor is
    genuinely independent, and is resolvable from no Store in this repository.
    """

    boot_context = boot_project(
        _canonical["store"],
        project_id=_canonical["project_id"],
        project_binding_id=_canonical["project_binding_id"],
    )
    project_key = boot_context.project_binding["human_authority_signing_key"]["public_key"]
    assert trust_anchor_public_key_hex() != project_key


def test_the_shipped_admission_path_imports_no_tests_module(_canonical: dict[str, Any]) -> None:
    """The path the positive proof above exercises is entirely shipped: neither the bootstrap
    module nor the admission verifier names any ``tests.*`` module, in imports or in source."""

    assert _canonical["project_id"]
    for module in (bootstrap_module, bootstrap_module.__dict__["require_valid_root_admission"]):
        source = inspect.getsource(inspect.getmodule(module) or module)
        assert "import tests" not in source
        assert "from tests" not in source


# ---------------------------------------------------------------------------
# A directly constructed root, with no genuine admission, reaches nothing
# ---------------------------------------------------------------------------


def test_a_directly_constructed_root_without_any_admission_reaches_nothing(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The decisive control for the reintroduced public constructor.

    A caller constructs a genuine ``TrustedRuntimeRoot`` over the genuinely canonical Store --
    exactly what the deleted factory, and the "private" sentinel, both allowed -- and presents a
    reference to an admission record that was never committed. Nothing is resolved, nothing is
    evaluated, nothing is reached.
    """

    calls = _counted_bootstrap(
        monkeypatch,
        _canonical,
        root=TrustedRuntimeRoot(
            _canonical["store"], _canonical["project_id"], _canonical["project_binding_id"]
        ),
        admission_ref={
            "kind": ROOT_ADMISSION_RECORD_KIND,
            "id": "RUNTIME-ROOT-ADMISSION-" + "0" * 64,
        },
        anchor=trust_anchor_public_key_hex(),
    )
    assert calls["count"] == 0


def test_a_directly_constructed_root_with_a_self_signed_admission_reaches_nothing(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same caller, one step more determined: they can write Store records, so they mint a
    perfectly well-formed, correctly addressed ``runtime_root_admission`` for exactly this
    project and Binding -- and sign it with their own Ed25519 key pair. Everything about it is
    self-consistent; it is simply not signed by the anchor the deployment supplied."""

    # A distinct ``declared_at``, so this is a genuinely different record rather than a
    # different *signature* over the byte-identical payload the fixture already committed --
    # the content address deliberately does not cover ``signature`` (a signature cannot cover
    # its own value), so re-signing alone would collide with that record's own address.
    forged = root_admission_for(
        _canonical["project_id"],
        _canonical["project_binding_id"],
        declared_at="2026-09-08T00:00:07Z",
        signer=foreign_trust_anchor_private_key(),
    )
    ref = commit_root_admission(_canonical["store"], _canonical["project_id"], forged)
    calls = _counted_bootstrap(
        monkeypatch,
        _canonical,
        root=TrustedRuntimeRoot(
            _canonical["store"], _canonical["project_id"], _canonical["project_binding_id"]
        ),
        admission_ref=ref,
        anchor=trust_anchor_public_key_hex(),
    )
    assert calls["count"] == 0


def test_the_admission_reference_must_name_the_right_record_kind(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    admitted = _canonical["admitted"]
    calls = _counted_bootstrap(
        monkeypatch,
        _canonical,
        root=admitted["trusted_runtime_root"],
        admission_ref={
            "kind": "runtime_deployment_declaration",
            "id": admitted["runtime_root_admission_ref"]["id"],
        },
        anchor=trust_anchor_public_key_hex(),
    )
    assert calls["count"] == 0


@pytest.mark.parametrize("anchor", ["", "not-hex", "ab" * 31, None])
def test_a_malformed_or_wrong_trust_anchor_admits_nothing(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch, anchor: Any
) -> None:
    """A genuine admission record, presented under an anchor that is empty, not hex, the wrong
    length, or not a string at all. Fail-closed as a value inside the verifier, a refusal at the
    route -- never an exception escaping from the cryptography layer."""

    admitted = _canonical["admitted"]
    calls = _counted_bootstrap(
        monkeypatch,
        _canonical,
        root=admitted["trusted_runtime_root"],
        admission_ref=admitted["runtime_root_admission_ref"],
        anchor=anchor,
    )
    assert calls["count"] == 0


def test_a_genuine_admission_under_a_different_anchor_admits_nothing(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not malformed at all -- a real, well-formed Ed25519 public key that simply is not the one
    this admission was signed under. This is the deployment-side mirror of the "wrong signer"
    control: the anchor decides, and only the anchor."""

    admitted = _canonical["admitted"]
    other_anchor = foreign_trust_anchor_private_key().public_key().public_bytes_raw().hex()
    assert other_anchor != trust_anchor_public_key_hex()
    calls = _counted_bootstrap(
        monkeypatch,
        _canonical,
        root=admitted["trusted_runtime_root"],
        admission_ref=admitted["runtime_root_admission_ref"],
        anchor=other_anchor,
    )
    assert calls["count"] == 0


# ---------------------------------------------------------------------------
# The alternate world's own self-signed admission fails against the external anchor
# ---------------------------------------------------------------------------


def test_the_alternate_world_is_genuinely_self_consistent_and_admissible_on_its_own_terms(
    _alternate: dict[str, Any],
) -> None:
    """Without this, every alternate-world refusal below would prove nothing.

    The alternate world is bound through the identical real ``bind_project`` route under its own
    external Human Authority and its own Ed25519 signing key, with its own genuinely signed grant
    and declaration -- and, handed an admission record genuinely signed by *the* deployment trust
    anchor, it provisions a real capability. So it is exactly the kind of world that is
    legitimate on its own terms, and the refusals below are about the anchor, never about the
    world being broken.
    """

    admitted = admitted_root(
        _alternate["store"],
        project_id=_alternate["project_id"],
        project_binding_id=_alternate["project_binding_id"],
    )
    capability = bootstrap_projection_execution_capability(
        admitted["trusted_runtime_root"],
        runtime_root_admission_ref=admitted["runtime_root_admission_ref"],
        trust_anchor_public_key_hex=admitted["trust_anchor_public_key_hex"],
        github_projection_grant_refs=[_alternate["grant_ref"]],
        github_projection_grant_declaration_refs=[_alternate["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)


def test_an_alternate_world_self_signing_with_its_own_human_authority_key_is_refused(
    _alternate: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The control the whole architecture exists for.

    The alternate world mints its **own** ``runtime_root_admission`` record, for its own project
    and its own Binding, and signs it with its **own** internally-legitimate Human Authority
    signing key -- the exact key its own Boot-restored Project Binding really carries, and which
    really does validate every other declaration in that world. Everything is self-consistent;
    the record is genuine *there*.

    It fails, because the externally supplied ``trust_anchor_public_key_hex`` is a key that world
    has never had and cannot produce. This is precisely the case a Store-resolvable trust scheme
    -- including one that verified against the target project's own Boot-restored
    ``human_authority_signing_key`` -- would accept, which is why this record kind deliberately
    carries no ``human_authority_ref`` at all.
    """

    self_signed = root_admission_for(
        _alternate["project_id"],
        _alternate["project_binding_id"],
        signer=alternate_signing_private_key(),
    )
    ref = commit_root_admission(_alternate["store"], _alternate["project_id"], self_signed)
    calls = _counted_bootstrap(
        monkeypatch,
        _alternate,
        root=trusted_runtime_root(
            _alternate["store"],
            project_id=_alternate["project_id"],
            project_binding_id=_alternate["project_binding_id"],
        ),
        admission_ref=ref,
        anchor=trust_anchor_public_key_hex(),
    )
    assert calls["count"] == 0


# ---------------------------------------------------------------------------
# Tamper / reuse controls, in the deployment-declaration suite's own style
# ---------------------------------------------------------------------------


def test_an_admission_for_a_different_project_admits_nothing(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """One admission artifact anchors exactly one project. A record genuinely signed by the real
    anchor, but naming some other project, is not an unbounded trust grant to be reused here."""

    elsewhere = root_admission_for("PRJ-ELSEWHERE-0001", _canonical["project_binding_id"])
    ref = commit_root_admission(_canonical["store"], _canonical["project_id"], elsewhere)
    calls = _counted_bootstrap(
        monkeypatch,
        _canonical,
        root=_canonical["admitted"]["trusted_runtime_root"],
        admission_ref=ref,
        anchor=trust_anchor_public_key_hex(),
    )
    assert calls["count"] == 0


def test_an_admission_for_a_different_project_binding_admits_nothing(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """...and exactly one Project Binding. Same project, same real anchor signature, different
    Binding -- refused, so an admission issued for one Binding can never be replayed across a
    legitimate re-binding, or across a substituted one."""

    other_binding = root_admission_for(_canonical["project_id"], "PROJBIND-SOMEWHERE-ELSE")
    ref = commit_root_admission(_canonical["store"], _canonical["project_id"], other_binding)
    calls = _counted_bootstrap(
        monkeypatch,
        _canonical,
        root=_canonical["admitted"]["trusted_runtime_root"],
        admission_ref=ref,
        anchor=trust_anchor_public_key_hex(),
    )
    assert calls["count"] == 0


def test_a_revoked_admission_admits_nothing(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Everything about this record is genuine -- correctly signed by the real anchor, correctly
    addressed, naming exactly this project and Binding. It is simply revoked."""

    revoked = root_admission_for(
        _canonical["project_id"], _canonical["project_binding_id"], status="REVOKED"
    )
    ref = commit_root_admission(_canonical["store"], _canonical["project_id"], revoked)
    calls = _counted_bootstrap(
        monkeypatch,
        _canonical,
        root=_canonical["admitted"]["trusted_runtime_root"],
        admission_ref=ref,
        anchor=trust_anchor_public_key_hex(),
    )
    assert calls["count"] == 0
    # ``status`` participates in the signed/addressed payload, so a revocation is a genuinely
    # different record -- never the ACTIVE one edited in place.
    assert (
        revoked["runtime_root_admission_id"]
        != _canonical["admitted"]["runtime_root_admission"]["runtime_root_admission_id"]
    )


def test_an_admission_tampered_after_signing_breaks_its_own_content_address(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A signature genuinely valid at signing time, with a covered field edited afterwards and
    both digests left stale. The identity recomputation catches this before the signature check
    is even reached -- proved explicitly so that adding a signature requirement is not mistaken
    for having *replaced* the identity check with it."""

    # Built at a distinct ``declared_at`` and never committed in its untampered form, so the
    # stale address this record keeps is its own and collides with nothing already in the Store.
    genuine = root_admission_for(
        _canonical["project_id"],
        _canonical["project_binding_id"],
        declared_at="2026-09-08T00:00:11Z",
    )
    tampered = deepcopy(genuine)
    tampered["project_binding_ref"] = {"kind": "project_binding", "id": "PROJBIND-TAMPERED-0001"}
    assert runtime_root_admission_id(tampered) != tampered["runtime_root_admission_id"]
    commit_records(
        _canonical["store"],
        _canonical["project_id"],
        _canonical["store"].load_current(_canonical["project_id"]),
        "TX-RUNTIME-TAMPERED-ROOT-ADMISSION",
        [
            (
                ROOT_ADMISSION_RECORD_KIND,
                str(tampered["runtime_root_admission_id"]),
                tampered,
            )
        ],
    )
    calls = _counted_bootstrap(
        monkeypatch,
        _canonical,
        root=_canonical["admitted"]["trusted_runtime_root"],
        admission_ref={
            "kind": ROOT_ADMISSION_RECORD_KIND,
            "id": str(tampered["runtime_root_admission_id"]),
        },
        anchor=trust_anchor_public_key_hex(),
    )
    assert calls["count"] == 0


def test_an_admission_tampered_and_re_addressed_still_fails_the_anchor_signature(
    _canonical: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mirror of the case above, and the one proving the two checks are independent: the
    tamperer *also* recomputes both digests, so the record's own identity reproduces perfectly
    and the tamper check passes. Only the anchor signature -- over the identical payload the
    identity is computed over, and which the tamperer cannot reproduce without the anchor's
    private key -- refuses it."""

    genuine = _canonical["admitted"]["runtime_root_admission"]
    tampered = deepcopy(genuine)
    tampered["declared_at"] = "2026-09-08T00:00:01Z"  # re-addressed below, so no collision
    tampered["runtime_root_admission_id"] = runtime_root_admission_id(tampered)
    tampered["runtime_root_admission_semantic_fingerprint"] = (
        runtime_root_admission_semantic_fingerprint(tampered)
    )
    assert tampered["signature"] == genuine["signature"]
    ref = commit_root_admission(_canonical["store"], _canonical["project_id"], tampered)
    calls = _counted_bootstrap(
        monkeypatch,
        _canonical,
        root=_canonical["admitted"]["trusted_runtime_root"],
        admission_ref=ref,
        anchor=trust_anchor_public_key_hex(),
    )
    assert calls["count"] == 0


def test_an_admission_committed_under_another_store_never_admits_this_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A genuinely anchor-signed admission from an entirely separate Store simply never resolves
    here -- the reference is resolved exclusively within the root's own Store, exactly as every
    other reference in this package is."""

    store_a, ctx_a = bound(tmp_path / "world-a")
    world_a = _authority_world(
        store_a, ctx_a, recorded_at="2026-09-09T00:00:00Z", transaction_prefix="TX-ADMISSION-A"
    )
    store_b, ctx_b = bound(tmp_path / "world-b")
    admitted_b = admitted_root(
        store_b, project_id=ctx_b["project_id"], project_binding_id=ctx_b["project_binding_id"]
    )

    calls = _counted_bootstrap(
        monkeypatch,
        world_a,
        root=trusted_runtime_root(
            store_a,
            project_id=ctx_a["project_id"],
            project_binding_id=ctx_a["project_binding_id"],
        ),
        admission_ref=admitted_b["runtime_root_admission_ref"],
        anchor=trust_anchor_public_key_hex(),
    )
    assert calls["count"] == 0
