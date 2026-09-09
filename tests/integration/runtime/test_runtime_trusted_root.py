"""P15-R1-F4 / P15-R4-F1: an alternate Authority world can never be substituted into runtime
provisioning -- and after Round 4 there is no longer a call shape through which it could be tried.

Structural Review Round 1's finding, restated: as first delivered,
``bootstrap_projection_execution_capability(store, project_id=..., project_binding_id=..., ...)``
proved only that the world *inside the Store it was handed* was internally self-consistent. An
attacker can assemble a completely separate Store -- its own Human Authority signing key, its
own Project Binding, its own grants, declarations and subjects, each one genuinely valid on its
own terms -- pass that in, and receive a real ``ProjectionExecutionCapability``, because nothing
in the signature distinguished "the canonical adopted Store" from "any internally consistent
Store a caller happens to pass".

This file is the decisive control the review requires, and it builds *both* worlds for real:

- the canonical world (``bound``), with genuinely committed, Boot-verified grants, declarations
  and subjects; and
- a fully self-consistent alternate world (``alternate_bound``), bound through the identical
  real ``bind_project`` route under its **own external Human Authority and its own Ed25519
  signing key**, with its own grants and declarations signed by that key -- and, since Round 3,
  with its **own genuinely anchor-signed root admission** as well, so that no refusal below can
  pass or fail for the accidental reason that one world simply lacked an admission record.

**Round 2 (P15-R2-F1)** deleted Round 1's own ``provision_trusted_runtime_root`` factory, having
found that this very file demonstrated the bypass rather than closing it. **Round 3 (P15-R3-F1)**
moved the boundary off the type entirely and onto an externally anchored admission record.
**Round 4 (P15-R4-F1)** found that this had *moved* the defect rather than closed it: the anchor
and the admission reference were still parameters of the request-facing call, so an attacker who
brought a matching attacker anchor along with the alternate world passed every check.

So the (a)-group below is rewritten again, and this time the fact it pins is structural rather
than behavioural: every trust-deciding value is owned by
``compose_trusted_runtime_deployment_authority``, and the request-facing call has **no parameter
at all** for a Store, a Project, a Binding, an admission, or an anchor. Groups (b) and (c) are
unchanged in substance. ``test_runtime_deployment_authority_composition.py`` owns the composition
boundary's own controls, including the anchor-absence proof and the admission lifecycle.
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
)

from manosube_agent_civilization.authority import evaluate_projection_authorization
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import ProjectionExecutionCapability
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.runtime import bootstrap as bootstrap_module
from manosube_agent_civilization.runtime.bootstrap import (
    RuntimeDeploymentAuthority,
    bootstrap_projection_execution_capability,
    compose_trusted_runtime_deployment_authority,
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
        # P15-R3-F1 / P15-R4-F1: every world here, canonical or alternate, admits its own root
        # against the *same* externally supplied trust anchor and composes a real deployment
        # authority through the shipped composition entry point, so that nothing below can pass or
        # fail for the accidental reason that one world simply lacked an admission.
        "admitted": admitted_root(
            store,
            project_id=ctx["project_id"],
            project_binding_id=ctx["project_binding_id"],
        ),
    }


def _bootstrap(world: dict[str, Any], *, grant_refs: list[Any], declaration_refs: list[Any]) -> Any:
    """One request-facing provisioning call against *world*'s own composed deployment authority.

    Note the shape: the authority is the *only* thing that names a world here (P15-R4-F1). There
    is nothing else this helper could pass even if it wanted to.
    """

    return bootstrap_projection_execution_capability(
        world["admitted"]["deployment_authority"],
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
    world that *would* have been accepted, not merely a broken one."""

    alternate = _worlds["alternate"]
    canonical = _worlds["canonical"]
    assert alternate["human_authority_ref"] == ALTERNATE_HUMAN_AUTHORITY_REF
    assert alternate["human_authority_ref"] != canonical["human_authority_ref"]
    assert alternate["project_binding_id"] != canonical["project_binding_id"]

    # It bootstraps a real capability entirely within itself -- including its own genuine,
    # currently-admitted admission record. That is deliberate: this world is legitimate on its own
    # terms *and* legitimately admitted within itself, so every refusal below is about ownership
    # and resolution scope, never about a missing admission.
    capability = _bootstrap(
        alternate,
        grant_refs=[alternate["grant_ref"]],
        declaration_refs=[alternate["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)


# ---------------------------------------------------------------------------
# (a) Every trust-deciding value is owned by composition, not by the request path
# ---------------------------------------------------------------------------


def test_composition_is_the_only_shipped_path_to_a_deployment_authority(
    _worlds: dict[str, Any],
) -> None:
    """Round 4 (P15-R4-F1) replaces Round 3's own inverted assertion here.

    Round 1 shipped a public minting factory; Round 2 deleted it; Round 3 made the trust-root type
    inert and freely constructible, and gated the capability call on an admission record whose
    anchor the *caller of that call* supplied. Round 4 removes the type altogether: what a
    deployment now holds is an opaque authority, obtainable only from the one shipped composition
    entry point, which is where the Store, Project, Binding, admission selection and anchor are
    all owned.
    """

    canonical = _worlds["canonical"]
    authority = canonical["admitted"]["deployment_authority"]
    assert isinstance(authority, RuntimeDeploymentAuthority)
    assert not hasattr(bootstrap_module, "TrustedRuntimeRoot")
    # Recomposing over the identical inputs is a perfectly ordinary thing for a deployment to do,
    # and produces an equally usable authority -- composition is a step, not a one-shot token.
    recomposed = compose_trusted_runtime_deployment_authority(
        canonical["store"],
        project_id=canonical["project_id"],
        project_binding_id=canonical["project_binding_id"],
        runtime_root_admission_ref=canonical["admitted"]["runtime_root_admission_ref"],
        trust_anchor_public_key_hex=canonical["admitted"]["trust_anchor_public_key_hex"],
    )
    assert isinstance(recomposed, RuntimeDeploymentAuthority)
    capability = bootstrap_projection_execution_capability(
        recomposed,
        github_projection_grant_refs=[canonical["grant_ref"]],
        github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)


def test_composing_against_a_nonexistent_admission_confers_nothing(
    _worlds: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Round 3 control, re-rooted at the boundary that now owns the question.

    Naming the genuinely canonical Store, the genuine project, the genuine Binding and the genuine
    configured anchor -- with genuinely committed, genuinely signed grants and declarations
    sitting right there -- still reaches nothing at all unless an admission record this Store
    actually contains, and currently points at, is named. Zero authorization evaluations, and no
    authority object ever comes into existence to be passed on.
    """

    canonical = _worlds["canonical"]
    authorization_calls = {"count": 0}

    def _counting_evaluate(request: Any) -> Any:
        authorization_calls["count"] += 1
        return evaluate_projection_authorization(request)

    monkeypatch.setattr(bootstrap_module, "evaluate_projection_authorization", _counting_evaluate)

    with pytest.raises(RuntimeRequirementError):
        compose_trusted_runtime_deployment_authority(
            canonical["store"],
            project_id=canonical["project_id"],
            project_binding_id=canonical["project_binding_id"],
            runtime_root_admission_ref={
                "kind": "runtime_root_admission",
                "id": "RUNTIME-ROOT-ADMISSION-" + "0" * 64,
            },
            trust_anchor_public_key_hex=canonical["admitted"]["trust_anchor_public_key_hex"],
        )
    assert authorization_calls["count"] == 0


def test_a_composed_authority_is_frozen(_worlds: dict[str, Any]) -> None:
    authority = _worlds["canonical"]["admitted"]["deployment_authority"]
    for attribute, value in (
        ("_store", _worlds["alternate"]["store"]),
        ("_project_id", "PRJ-ELSEWHERE"),
        ("_project_binding_id", "PROJBIND-ELSEWHERE"),
        ("_runtime_root_admission_id", "RUNTIME-ROOT-ADMISSION-" + "0" * 64),
    ):
        with pytest.raises((AttributeError, TypeError)):
            setattr(authority, attribute, value)


@pytest.mark.parametrize(
    ("project_id", "project_binding_id"),
    [
        ("", "PROJBIND-X"),
        ("PRJ-A", ""),
        ("../escape", "PROJBIND-X"),
        ("PRJ-A", "https://attacker.test/binding"),
    ],
)
def test_composition_refuses_a_non_canonical_identity(
    _worlds: dict[str, Any], project_id: str, project_binding_id: str
) -> None:
    """The canonical-identity check that lived on the trust-root type in Rounds 2 and 3 now lives
    at composition, where the name is actually chosen -- a composition can still never name a
    path, URL, or locator instead of a canonical identity. This is a shape check on a *name*, not
    a trust decision; the trust decision is the anchor-signed, currently-pointed-to admission."""

    with pytest.raises(RuntimeRequirementError):
        compose_trusted_runtime_deployment_authority(
            _worlds["canonical"]["store"],
            project_id=project_id,
            project_binding_id=project_binding_id,
            runtime_root_admission_ref=_worlds["canonical"]["admitted"][
                "runtime_root_admission_ref"
            ],
            trust_anchor_public_key_hex=_worlds["canonical"]["admitted"][
                "trust_anchor_public_key_hex"
            ],
        )


# ---------------------------------------------------------------------------
# (b) The alternate world's own references never resolve inside the canonical authority
# ---------------------------------------------------------------------------


def test_the_alternate_worlds_references_never_resolve_within_the_canonical_authority(
    _worlds: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The decisive control. The alternate world's grant/declaration references are genuine
    records -- *there*. Presented against the canonical authority, they simply do not exist, so
    the refusal happens at resolution and nothing reaches
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


def test_no_request_facing_argument_can_redirect_a_capability_call_into_another_world(
    _worlds: dict[str, Any],
) -> None:
    """The structural half of the same control, and the shape Round 4 required (P15-R4-F1).

    Round 3's version of this test could only rule out ``store`` and ``project_binding_id``,
    because ``runtime_root_admission_ref`` and ``trust_anchor_public_key_hex`` were still genuine
    parameters -- which is precisely the gap Round 4 named. Every one of the five is now a
    ``TypeError``: the parameters do not exist, so an attacker holding a canonical authority
    cannot redirect a request into the alternate world by any argument at all, and cannot bring
    their own anchor along either.
    """

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]
    authority = canonical["admitted"]["deployment_authority"]
    substitutions: list[dict[str, Any]] = [
        {"store": alternate["store"]},
        {"project_id": alternate["project_id"]},
        {"project_binding_id": alternate["project_binding_id"]},
        {"runtime_root_admission_ref": alternate["admitted"]["runtime_root_admission_ref"]},
        {"trust_anchor_public_key_hex": alternate["admitted"]["trust_anchor_public_key_hex"]},
    ]
    for substitution in substitutions:
        with pytest.raises(TypeError):
            bootstrap_projection_execution_capability(
                authority,
                github_projection_grant_refs=[canonical["grant_ref"]],
                github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
                **substitution,
            )


def test_an_authority_composed_over_the_alternate_world_cannot_borrow_canonical_references(
    _worlds: dict[str, Any],
) -> None:
    """The mirror image: an alternate authority plus the canonical world's own genuine references
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
        raise AssertionError("Boot must never be reached for a non-authority argument")

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
    """Duck typing is not enough -- an object shaped exactly like a composed authority, naming the
    alternate world (including a plausible bound-admission id and generation), is refused because
    it is not a genuine ``RuntimeDeploymentAuthority``.

    Stated precisely, because Round 4's own framing demands it: this type check is *not* the trust
    control. The trust control is that composition owns every trust-deciding value and the
    request-facing signature can name none of them. This check exists so that a caller who
    fabricates a look-alike gets a clear refusal rather than an obscure attribute error.
    """

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]

    class _LookAlikeAuthority:
        _store = alternate["store"]
        _project_id = alternate["project_id"]
        _project_binding_id = alternate["project_binding_id"]
        _runtime_root_admission_id = alternate["admitted"]["runtime_root_admission_ref"]["id"]
        _runtime_root_admission_generation = 0

    def _boot_must_not_run(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError("Boot must never be reached for a look-alike authority")

    monkeypatch.setattr(bootstrap_module, "boot_project", _boot_must_not_run)

    with pytest.raises(RuntimeRequirementError):
        bootstrap_projection_execution_capability(
            _LookAlikeAuthority(),  # type: ignore[arg-type]
            github_projection_grant_refs=[canonical["grant_ref"]],
            github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
        )
