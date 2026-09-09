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
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import observation_evidence_request
from tests.fixtures.runtime_world import (
    ALTERNATE_HUMAN_AUTHORITY_REF,
    alternate_bound,
    bound,
    commit_declaration,
    commit_grant,
    commit_records,
    sign_alternate_github_projection_grant_declaration,
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
    provision_trusted_runtime_root,
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
    }


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
    world that *would* have been accepted, not merely a broken one."""

    alternate = _worlds["alternate"]
    canonical = _worlds["canonical"]
    assert alternate["human_authority_ref"] == ALTERNATE_HUMAN_AUTHORITY_REF
    assert alternate["human_authority_ref"] != canonical["human_authority_ref"]
    assert alternate["project_binding_id"] != canonical["project_binding_id"]

    # It provisions its own root and bootstraps a real capability entirely within itself.
    capability = bootstrap_projection_execution_capability(
        provision_trusted_runtime_root(
            alternate["store"],
            project_id=alternate["project_id"],
            project_binding_id=alternate["project_binding_id"],
        ),
        github_projection_grant_refs=[alternate["grant_ref"]],
        github_projection_grant_declaration_refs=[alternate["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)


# ---------------------------------------------------------------------------
# (a) A TrustedRuntimeRoot cannot be constructed directly
# ---------------------------------------------------------------------------


def test_constructing_a_trusted_runtime_root_directly_raises(_worlds: dict[str, Any]) -> None:
    canonical = _worlds["canonical"]
    with pytest.raises(TypeError):
        TrustedRuntimeRoot(  # type: ignore[call-arg]
            canonical["store"], canonical["project_id"], canonical["project_binding_id"]
        )
    with pytest.raises(RuntimeRequirementError):
        TrustedRuntimeRoot(
            canonical["store"],
            canonical["project_id"],
            canonical["project_binding_id"],
            object(),
        )
    with pytest.raises(RuntimeRequirementError):
        TrustedRuntimeRoot(
            canonical["store"], canonical["project_id"], canonical["project_binding_id"], None
        )


def test_a_legitimately_provisioned_root_does_not_retain_the_provisioning_capability(
    _worlds: dict[str, Any],
) -> None:
    """Holding a genuine root must not become a capability to mint further roots naming some
    other Store -- the sentinel is dropped once checked."""

    canonical = _worlds["canonical"]
    root = provision_trusted_runtime_root(
        canonical["store"],
        project_id=canonical["project_id"],
        project_binding_id=canonical["project_binding_id"],
    )
    assert root.provisioning_sentinel is None
    with pytest.raises(RuntimeRequirementError):
        TrustedRuntimeRoot(
            _worlds["alternate"]["store"],
            _worlds["alternate"]["project_id"],
            _worlds["alternate"]["project_binding_id"],
            root.provisioning_sentinel,
        )


def test_a_provisioned_root_is_frozen(_worlds: dict[str, Any]) -> None:
    canonical = _worlds["canonical"]
    root = provision_trusted_runtime_root(
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
def test_provisioning_refuses_a_non_canonical_identity(
    _worlds: dict[str, Any], project_id: str, project_binding_id: str
) -> None:
    with pytest.raises(RuntimeRequirementError):
        provision_trusted_runtime_root(
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
        bootstrap_projection_execution_capability(
            provision_trusted_runtime_root(
                canonical["store"],
                project_id=canonical["project_id"],
                project_binding_id=canonical["project_binding_id"],
            ),
            github_projection_grant_refs=[alternate["grant_ref"]],
            github_projection_grant_declaration_refs=[alternate["declaration_ref"]],
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
    canonical_root = provision_trusted_runtime_root(
        canonical["store"],
        project_id=canonical["project_id"],
        project_binding_id=canonical["project_binding_id"],
    )
    with pytest.raises(TypeError):
        bootstrap_projection_execution_capability(  # type: ignore[call-arg]
            canonical_root,
            store=alternate["store"],
            github_projection_grant_refs=[canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
        )
    with pytest.raises(TypeError):
        bootstrap_projection_execution_capability(  # type: ignore[call-arg]
            canonical_root,
            project_binding_id=alternate["project_binding_id"],
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
        bootstrap_projection_execution_capability(
            provision_trusted_runtime_root(
                alternate["store"],
                project_id=alternate["project_id"],
                project_binding_id=alternate["project_binding_id"],
            ),
            github_projection_grant_refs=[canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
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
            github_projection_grant_refs=[canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
        )
