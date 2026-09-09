"""P15-R1-F4: the trusted runtime bootstrap no longer accepts a caller-selected Authority world.

Structural Review Round 1's finding, restated: as first delivered,
``bootstrap_projection_execution_capability(store, project_id=..., project_binding_id=..., ...)``
proved only that the world *inside the Store it was handed* was internally self-consistent. An
attacker can assemble a completely separate Store -- its own Human Authority signing key, its
own Project Binding, its own grants, declarations and subjects, each one genuinely valid on its
own terms -- pass that in, and receive a real ``ProjectionExecutionCapability``, because nothing
in the signature distinguished "the canonical adopted Store" from "any internally consistent
Store a caller happens to pass".

This file is the decisive control the review requires. It builds *both* worlds for real:

- the canonical world (``bound``), with genuinely committed, Boot-verified grants, declarations
  and subjects; and
- a fully self-consistent alternate world (``alternate_bound``), bound through the identical
  real ``bind_project`` route under its **own external Human Authority and its own Ed25519
  signing key**, with its own grants and declarations signed by that key -- a world that is
  valid, and that ``bootstrap_projection_execution_capability`` would happily have accepted
  before this correction.

and then proves the three facts (a)/(b)/(c) the correction rests on.

**Structural Review Round 2 (P15-R2-F1) changed what this file may claim.** Round 2 found that
Round 1's own ``provision_trusted_runtime_root(store, project_id, project_binding_id)`` factory
*was* the caller-selected trust anchor, merely relocated one call earlier -- and that this very
file demonstrated the bypass rather than closing it, by provisioning a root over the alternate
Store and obtaining a real capability from it. The shipped factory was deleted.

**Structural Review Round 3 (P15-R3-F1) changed it again, and more deeply.** Round 3 rejected
Round 2's "no shipped minting path, therefore no production-legitimate first argument" position
outright, and observed that Round 2's module-private sentinel was a naming convention rather than
a control. The boundary is no longer the *type* at all: constructing a ``TrustedRuntimeRoot`` is
public and unrestricted again, and grants nothing, because
``bootstrap_projection_execution_capability`` now admits a root only against a canonical,
Store-committed ``runtime_root_admission`` record verified against an externally supplied trust
anchor -- on every call, whatever the root's provenance.

So the (a)-group tests below have been rewritten rather than deleted: the facts they used to pin
("direct construction raises", "the sentinel is dropped once checked") no longer exist and would
be false if asserted; what survives, and is now proved instead, is that the type is still frozen,
still refuses a non-canonical identity, and -- decisively -- that holding one confers nothing.
Groups (b) and (c) are unchanged in substance: the alternate world's records never resolve inside
the canonical root, and no argument on the capability call can redirect it.
``test_runtime_root_admission.py`` owns the Round 3 controls themselves.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.runtime_world import (
    ALTERNATE_HUMAN_AUTHORITY_REF,
    admitted_root,
    alternate_bound,
    bound,
    commit_declaration,
    commit_grant,
    commit_records,
    sign_alternate_github_projection_grant_declaration,
    trusted_runtime_root,
)

from manosube_agent_civilization.authority import evaluate_projection_authorization
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import ProjectionExecutionCapability
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.runtime import bootstrap as bootstrap_module
from manosube_agent_civilization.runtime.bootstrap import (
    TrustedRuntimeRoot,
    bootstrap_projection_execution_capability,
)
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError

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
        # P15-R3-F1: every world here, canonical or alternate, admits its own root against the
        # *same* externally supplied trust anchor, so that nothing below can pass or fail for
        # the accidental reason that one world simply lacked an admission record.
        "admitted": admitted_root(
            store,
            project_id=ctx["project_id"],
            project_binding_id=ctx["project_binding_id"],
        ),
    }


def _bootstrap(world: dict[str, Any], *, grant_refs: list[Any], declaration_refs: list[Any]) -> Any:
    """One legitimately admitted provisioning call against *world*'s own root (P15-R3-F1)."""

    admitted = world["admitted"]
    return bootstrap_projection_execution_capability(
        admitted["trusted_runtime_root"],
        runtime_root_admission_ref=admitted["runtime_root_admission_ref"],
        trust_anchor_public_key_hex=admitted["trust_anchor_public_key_hex"],
        github_projection_grant_refs=grant_refs,
        github_projection_grant_declaration_refs=declaration_refs,
    )


@pytest.fixture
def _worlds(tmp_path: Path) -> dict[str, Any]:
    canonical_store, canonical_ctx = bound(tmp_path / "canonical")
    alternate_store, alternate_ctx = alternate_bound(tmp_path / "alternate")
    canonical = _authority_world(
        canonical_store,
        canonical_ctx,
        recorded_at="2026-09-09T00:00:00Z",
        transaction_prefix="TX-TRUSTED-ROOT-CANONICAL",
    )
    alternate = _authority_world(
        alternate_store,
        alternate_ctx,
        recorded_at="2026-09-09T00:00:02Z",
        signer=sign_alternate_github_projection_grant_declaration,
        transaction_prefix="TX-TRUSTED-ROOT-ALTERNATE",
    )
    return {"canonical": canonical, "alternate": alternate}


# ---------------------------------------------------------------------------
# The alternate world really is legitimate on its own terms
# ---------------------------------------------------------------------------


def test_the_alternate_world_is_genuinely_self_consistent_under_its_own_authority(
    _worlds: dict[str, Any],
) -> None:
    """Without this, every refusal below would prove nothing: the alternate world must be a
    world that *would* have been accepted, not merely a broken one.

    Note precisely what the capability construction below shows and does not show. It shows the
    alternate world is internally legitimate -- its own Boot, its own Ed25519-signed grants and
    declarations, its own subjects all check out on their own terms. It does **not** show that
    any shipped surface can reach it: the root is minted by the test-only issuer, which exists
    only in ``tests/`` (P15-R2-F1)."""

    alternate = _worlds["alternate"]
    canonical = _worlds["canonical"]
    assert alternate["human_authority_ref"] == ALTERNATE_HUMAN_AUTHORITY_REF
    assert alternate["human_authority_ref"] != canonical["human_authority_ref"]
    assert alternate["project_binding_id"] != canonical["project_binding_id"]

    # It bootstraps a real capability entirely within itself -- including its own genuine
    # admission record, admitted against the identical externally supplied trust anchor. That is
    # deliberate: this world is legitimate on its own terms *and* legitimately admitted, so every
    # refusal below is about reference resolution scope, never about a missing admission.
    capability = _bootstrap(
        alternate,
        grant_refs=[alternate["grant_ref"]],
        declaration_refs=[alternate["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)


# ---------------------------------------------------------------------------
# (a) A TrustedRuntimeRoot is an ordinary public value that confers nothing
# ---------------------------------------------------------------------------


def test_constructing_a_trusted_runtime_root_directly_is_public_and_unrestricted(
    _worlds: dict[str, Any],
) -> None:
    """Round 3 (P15-R3-F1) inverts Round 2's own assertion here, deliberately and visibly.

    Round 2 pinned "direct construction raises", protected by a module-private sentinel. Round 3
    found that gate to be a naming convention rather than a control -- any caller able to import
    ``runtime.bootstrap`` could read ``_PROVISIONING_SENTINEL`` and construct a root over an
    arbitrary Store, exactly as the test-only issuer did -- and, more importantly, found the
    framing itself wrong. The type is no longer the boundary, so restricting its construction
    protects nothing and merely preserves the illusion. It is now ordinary public API, and the
    three positional arguments a caller supplies are just a *name* for a world.

    What actually gates access is proved in ``test_runtime_root_admission.py``.
    """

    canonical = _worlds["canonical"]
    root = TrustedRuntimeRoot(
        canonical["store"], canonical["project_id"], canonical["project_binding_id"]
    )
    assert root.store is canonical["store"]
    assert root.project_id == canonical["project_id"]
    assert root.project_binding_id == canonical["project_binding_id"]


def test_holding_a_root_confers_nothing_without_a_genuine_admission(
    _worlds: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The replacement for Round 2's "the sentinel is dropped once checked" control, and a
    strictly stronger statement than it was.

    Round 2 proved only that holding a legitimate root could not mint a *second* root naming a
    different Store. Round 3 proves the thing that actually matters: holding a genuine,
    directly constructed root over the genuinely canonical Store -- with genuinely committed,
    genuinely signed grants and declarations sitting right there -- reaches nothing at all
    unless the caller also presents an admission record this Store does not contain. Zero
    authorization evaluations.
    """

    canonical = _worlds["canonical"]
    authorization_calls = {"count": 0}

    def _counting_evaluate(request: Any) -> Any:
        authorization_calls["count"] += 1
        return evaluate_projection_authorization(request)

    monkeypatch.setattr(bootstrap_module, "evaluate_projection_authorization", _counting_evaluate)

    with pytest.raises(RuntimeRequirementError):
        bootstrap_projection_execution_capability(
            TrustedRuntimeRoot(
                canonical["store"], canonical["project_id"], canonical["project_binding_id"]
            ),
            runtime_root_admission_ref={
                "kind": "runtime_root_admission",
                "id": "RUNTIME-ROOT-ADMISSION-" + "0" * 64,
            },
            trust_anchor_public_key_hex=canonical["admitted"]["trust_anchor_public_key_hex"],
            github_projection_grant_refs=[canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
        )
    assert authorization_calls["count"] == 0


def test_a_provisioned_root_is_frozen(_worlds: dict[str, Any]) -> None:
    canonical = _worlds["canonical"]
    root = trusted_runtime_root(
        canonical["store"],
        project_id=canonical["project_id"],
        project_binding_id=canonical["project_binding_id"],
    )
    for attribute, value in (
        ("store", _worlds["alternate"]["store"]),
        ("project_id", "PRJ-ELSEWHERE"),
        ("project_binding_id", "PROJBIND-ELSEWHERE"),
    ):
        with pytest.raises((AttributeError, TypeError)):
            setattr(root, attribute, value)


@pytest.mark.parametrize(
    ("project_id", "project_binding_id"),
    [
        ("", "PROJBIND-X"),
        ("PRJ-A", ""),
        ("../escape", "PROJBIND-X"),
        ("PRJ-A", "https://attacker.test/binding"),
    ],
)
def test_root_construction_refuses_a_non_canonical_identity(
    _worlds: dict[str, Any], project_id: str, project_binding_id: str
) -> None:
    """The canonical-identity check moved onto the type itself in Round 2 (P15-R2-F1), since
    the factory that used to perform it before construction no longer exists, and Round 3
    (P15-R3-F1) keeps it there even though construction is public again -- a root can still
    never name a path, URL, or locator instead of a canonical identity. This is a shape check on
    a *name*, not a trust decision; the trust decision is the admission record."""

    with pytest.raises(RuntimeRequirementError):
        trusted_runtime_root(
            _worlds["canonical"]["store"],
            project_id=project_id,
            project_binding_id=project_binding_id,
        )


# ---------------------------------------------------------------------------
# (b) The alternate world's own references never resolve inside the canonical root
# ---------------------------------------------------------------------------


def test_the_alternate_worlds_references_never_resolve_within_the_canonical_root(
    _worlds: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The decisive control. The alternate world's grant/declaration references are genuine
    records -- *there*. Presented against the canonical root, they simply do not exist, so the
    refusal happens at resolution and nothing reaches
    ``evaluate_projection_authorization`` at all."""

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]
    assert alternate["grant_ref"]["id"] != canonical["grant_ref"]["id"]
    assert alternate["declaration_ref"]["id"] != canonical["declaration_ref"]["id"]

    authorization_calls = {"count": 0}

    def _counting_evaluate(request: Any) -> Any:
        authorization_calls["count"] += 1
        return evaluate_projection_authorization(request)

    monkeypatch.setattr(bootstrap_module, "evaluate_projection_authorization", _counting_evaluate)

    with pytest.raises(RuntimeRequirementError):
        _bootstrap(
            canonical,
            grant_refs=[alternate["grant_ref"]],
            declaration_refs=[alternate["declaration_ref"]],
        )
    assert authorization_calls["count"] == 0


def test_the_alternate_worlds_store_can_no_longer_be_named_at_the_capability_call_at_all(
    _worlds: dict[str, Any],
) -> None:
    """The structural half of the same control: the only place a Store is ever named is the
    provisioning call, so a caller holding the canonical root cannot redirect a capability
    request into the alternate world by any argument -- the parameter does not exist."""

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]
    canonical_root = canonical["admitted"]["trusted_runtime_root"]
    with pytest.raises(TypeError):
        bootstrap_projection_execution_capability(  # type: ignore[call-arg]
            canonical_root,
            store=alternate["store"],
            runtime_root_admission_ref=canonical["admitted"]["runtime_root_admission_ref"],
            trust_anchor_public_key_hex=canonical["admitted"]["trust_anchor_public_key_hex"],
            github_projection_grant_refs=[canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
        )
    with pytest.raises(TypeError):
        bootstrap_projection_execution_capability(  # type: ignore[call-arg]
            canonical_root,
            project_binding_id=alternate["project_binding_id"],
            runtime_root_admission_ref=canonical["admitted"]["runtime_root_admission_ref"],
            trust_anchor_public_key_hex=canonical["admitted"]["trust_anchor_public_key_hex"],
            github_projection_grant_refs=[canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
        )


def test_a_root_provisioned_over_the_alternate_world_cannot_borrow_canonical_references(
    _worlds: dict[str, Any],
) -> None:
    """The mirror image: an alternate root plus the canonical world's own genuine references
    also refuses, since those records exist only in the canonical Store."""

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]
    with pytest.raises(RuntimeRequirementError):
        _bootstrap(
            alternate,
            grant_refs=[canonical["grant_ref"]],
            declaration_refs=[canonical["declaration_ref"]],
        )


# ---------------------------------------------------------------------------
# (c) A bare store is refused at the type check, before Boot
# ---------------------------------------------------------------------------


def test_a_bare_store_is_refused_at_the_type_check_before_boot(
    _worlds: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    canonical = _worlds["canonical"]

    def _boot_must_not_run(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError("Boot must never be reached for a non-TrustedRuntimeRoot argument")

    monkeypatch.setattr(bootstrap_module, "boot_project", _boot_must_not_run)

    with pytest.raises(RuntimeRequirementError):
        bootstrap_projection_execution_capability(
            canonical["store"],
            runtime_root_admission_ref=canonical["admitted"]["runtime_root_admission_ref"],
            trust_anchor_public_key_hex=canonical["admitted"]["trust_anchor_public_key_hex"],
            github_projection_grant_refs=[canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
        )


def test_a_look_alike_object_carrying_the_right_attributes_is_still_refused(
    _worlds: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Duck typing is not enough -- an object shaped exactly like a root, naming the alternate
    world, is refused because it is not a genuine ``TrustedRuntimeRoot``."""

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]

    class _LookAlikeRoot:
        store = alternate["store"]
        project_id = alternate["project_id"]
        project_binding_id = alternate["project_binding_id"]

    def _boot_must_not_run(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError("Boot must never be reached for a look-alike root")

    monkeypatch.setattr(bootstrap_module, "boot_project", _boot_must_not_run)

    with pytest.raises(RuntimeRequirementError):
        bootstrap_projection_execution_capability(
            _LookAlikeRoot(),  # type: ignore[arg-type]
            runtime_root_admission_ref=canonical["admitted"]["runtime_root_admission_ref"],
            trust_anchor_public_key_hex=canonical["admitted"]["trust_anchor_public_key_hex"],
            github_projection_grant_refs=[canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
        )
