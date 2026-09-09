"""P15-R2-F1, as Round 4 (P15-R4-F1) leaves it: the deleted minting factory stays deleted, the
trust-root type it minted no longer exists at all, and the one shipped callable that hands back a
deployment authority is the composition entry point that owns the trust decision.

**What Round 2 found, and what Round 3 changed.** Round 1 closed P15-R1-F4 by removing
``store``/``project_id``/``project_binding_id`` from
``bootstrap_projection_execution_capability``'s own signature and introducing a public
``provision_trusted_runtime_root(store, project_id, project_binding_id)`` factory in front of
it. Round 2 found that factory *was itself* the caller-selected trust anchor -- it accepted
exactly the tuple the correction existed to stop an untrusted surface from choosing -- deleted
it, and left construction behind a module-private sentinel, concluding that shipped code
therefore had no production-legitimate way to obtain a root at all.

Round 3 rejected that conclusion and the reasoning under it. The sentinel was a naming
convention rather than a control (any caller able to import ``runtime.bootstrap`` could read it
and construct a root over an arbitrary Store, which is precisely what the test-only issuer did),
and Issue #64 assigns this production provisioning boundary to *this* Phase rather than a later
one. The fix was not a better-hidden constructor but to stop the type from being the boundary:
possessing a ``TrustedRuntimeRoot`` now grants **nothing**, because every provisioning call must
additionally present a canonical ``runtime_root_admission`` record verified against an
externally supplied trust anchor. See ``test_runtime_root_admission.py``, which owns that proof.

**What Round 4 changed again.** Round 3 had *moved* the trust decision rather than closed it: the
admission reference and the trust anchor were still parameters of the request-facing capability
call, so a caller who brought a matching attacker anchor along with a self-consistent alternate
world passed every check. Round 4 made the composition boundary the owner of every trust-deciding
value, and removed the trust-root type entirely -- there is nothing left for a minting factory to
mint.

**Why this file survives, and in strictly stronger form.** Every fact it pins is still true and
still load-bearing, and pinning them is exactly what keeps each round's correction from being
*read* as a quiet restoration of Round 1's factory:

- the deleted factory is not importable from anywhere shipped, under its own name;
- the ``TrustedRuntimeRoot`` name is now absent from every code position in the whole shipped
  package -- strictly stronger than Rounds 2 and 3, which could only say no shipped callable
  returned one and no shipped module constructed one;
- exactly one shipped public callable hands back a ``RuntimeDeploymentAuthority``, it is the
  composition entry point, and it cannot produce one without a deployment-supplied anchor and a
  currently-admitted, anchor-signed admission record;
- the request-facing capability call still refuses every non-authority first argument, before
  Boot;
- ``observe_runtime_target``, the one public observation route, names neither the removed type,
  the new authority type, nor either bootstrap half, so no ambient live path can be steered
  through any of them.
"""

from __future__ import annotations

import importlib
import inspect
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

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import ProjectionExecutionCapability
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
import manosube_agent_civilization.runtime as runtime_package
import manosube_agent_civilization.runtime.bootstrap as bootstrap_module
from manosube_agent_civilization.runtime.bootstrap import (
    RuntimeDeploymentAuthority,
    bootstrap_projection_execution_capability,
    compose_trusted_runtime_deployment_authority,
)
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
import manosube_agent_civilization.runtime.route as route_module

_TARGET_REPOSITORY = {"host": "github", "owner": "acme", "repo": "widget"}
_PAYLOAD = {
    "name": "MANOSUBE Evidence Check",
    "head_sha": "a" * 40,
    "status": "completed",
    "conclusion": "neutral",
    "output": {"title": "Evidence artifact", "summary": "hello"},
}

#: The exact name Round 1 shipped and Round 2 deletes. Named as a literal here so that
#: reintroducing it -- under this name, anywhere in the shipped package -- fails immediately.
_DELETED_MINTING_FACTORY_NAME = "provision_trusted_runtime_root"

#: The trust-root type Rounds 1-3 carried and Round 4 removes outright. Pinned as a literal for
#: the identical reason: a quiet reintroduction under its own name fails immediately.
_REMOVED_TRUST_ROOT_TYPE_NAME = "TrustedRuntimeRoot"


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
        "admitted": admitted_root(
            store,
            project_id=ctx["project_id"],
            project_binding_id=ctx["project_binding_id"],
        ),
    }


@pytest.fixture
def _worlds(tmp_path: Path) -> dict[str, Any]:
    canonical_store, canonical_ctx = bound(tmp_path / "canonical")
    alternate_store, alternate_ctx = alternate_bound(tmp_path / "alternate")
    canonical = _authority_world(
        canonical_store,
        canonical_ctx,
        recorded_at="2026-09-09T00:00:00Z",
        transaction_prefix="TX-NO-MINT-CANONICAL",
    )
    alternate = _authority_world(
        alternate_store,
        alternate_ctx,
        recorded_at="2026-09-09T00:00:02Z",
        signer=sign_alternate_github_projection_grant_declaration,
        transaction_prefix="TX-NO-MINT-ALTERNATE",
    )
    return {"canonical": canonical, "alternate": alternate}


# ---------------------------------------------------------------------------
# (a) Both worlds are real, and the alternate one really is internally legitimate
# ---------------------------------------------------------------------------


def test_both_worlds_are_genuinely_distinct_and_the_alternate_one_is_self_consistent(
    _worlds: dict[str, Any],
) -> None:
    """The non-vacuity control. The alternate world is bound through the identical real
    ``bind_project`` route under its own external Human Authority and its own Ed25519 signing
    key, with its own genuinely signed grant and declaration, and its own genuinely
    anchor-signed, currently-admitted root admission -- so composing an authority *within itself*
    produces a real ``ProjectionExecutionCapability``.

    So the alternate world is exactly the kind of world Round 1's factory would have accepted.
    Everything below is therefore a statement about the absence of a shipped minting path and
    about who owns the trust decision, never a statement that this particular world happens to be
    malformed.
    """

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]
    assert alternate["human_authority_ref"] == ALTERNATE_HUMAN_AUTHORITY_REF
    assert alternate["human_authority_ref"] != canonical["human_authority_ref"]
    assert alternate["project_binding_id"] != canonical["project_binding_id"]

    capability = bootstrap_projection_execution_capability(
        alternate["admitted"]["deployment_authority"],
        github_projection_grant_refs=[alternate["grant_ref"]],
        github_projection_grant_declaration_refs=[alternate["declaration_ref"]],
    )
    assert isinstance(capability, ProjectionExecutionCapability)


# ---------------------------------------------------------------------------
# (b) Nothing in the shipped surface offers a way to reach or mint such a root
# ---------------------------------------------------------------------------


def test_the_deleted_minting_factory_is_not_importable_from_anywhere_shipped() -> None:
    """The exact function Round 2 removes, checked dynamically on the live, imported package --
    the complement to the static AST walk in ``test_runtime_static_conformance.py``."""

    assert not hasattr(bootstrap_module, _DELETED_MINTING_FACTORY_NAME)
    assert not hasattr(runtime_package, _DELETED_MINTING_FACTORY_NAME)
    assert not hasattr(route_module, _DELETED_MINTING_FACTORY_NAME)
    assert _DELETED_MINTING_FACTORY_NAME not in runtime_package.__all__
    assert _DELETED_MINTING_FACTORY_NAME not in bootstrap_module.__all__

    # A real import attempt, by the exact name a caller written against Round 1 would use. The
    # module is deliberately named indirectly here so that this file itself does not
    # reintroduce the literal into anything importable, and so a static reader of the shipped
    # package's own conformance scan is never confused by a test-side occurrence.
    module = importlib.import_module("manosube_agent_civilization.runtime")
    with pytest.raises(AttributeError):
        getattr(module, _DELETED_MINTING_FACTORY_NAME)


def test_the_removed_trust_root_type_appears_in_no_shipped_code_position(
    _worlds: dict[str, Any],
) -> None:
    """Round 4's strictly stronger successor to Rounds 2 and 3's own return-type and
    construction-site assertions.

    Those could only say that no shipped callable *returned* a ``TrustedRuntimeRoot`` and that no
    shipped module *constructed* one. The type is now gone outright, so the honest statement is
    the stronger one: the name occurs in no code position anywhere in the shipped package, and is
    not an attribute of any shipped module. Historical prose in a docstring is deliberately not
    matched -- each round's record has to be able to say what was removed and why, and a docstring
    re-exports nothing (the static AST version of this scan lives in
    ``tests/contract/runtime/test_runtime_static_conformance.py``).
    """

    assert _worlds["canonical"]["project_id"]
    assert not hasattr(bootstrap_module, _REMOVED_TRUST_ROOT_TYPE_NAME)
    assert not hasattr(runtime_package, _REMOVED_TRUST_ROOT_TYPE_NAME)
    assert _REMOVED_TRUST_ROOT_TYPE_NAME not in runtime_package.__all__
    assert _REMOVED_TRUST_ROOT_TYPE_NAME not in bootstrap_module.__all__


def test_exactly_one_shipped_callable_hands_back_a_deployment_authority(
    _worlds: dict[str, Any],
) -> None:
    """The Round 4 successor to "no shipped callable returns a trust root", and the fact that
    actually matters now.

    A capability *must* be obtainable somehow -- Round 3 established that a mechanism with no
    production-legitimate path is itself a defect. So the honest control is not "nothing returns
    one" but "exactly one thing does, and it is the trusted composition step". Checked by declared
    return annotation over every public callable the package exports, so a same-shaped factory
    reintroduced under a different name would be caught immediately.
    """

    assert _worlds["canonical"]["project_id"]
    producers = []
    for name in runtime_package.__all__:
        member = getattr(runtime_package, name)
        if not callable(member) or isinstance(member, type):
            continue
        annotation = inspect.signature(member).return_annotation
        rendered = (
            annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
        )
        if "RuntimeDeploymentAuthority" in str(rendered):
            producers.append(name)
    assert producers == ["compose_trusted_runtime_deployment_authority"]


def test_the_one_producer_cannot_produce_an_authority_without_the_deployment_anchor(
    _worlds: dict[str, Any],
) -> None:
    """And the producer is not a factory in the Round 1 sense: it cannot hand back an authority
    to a caller who does not hold the deployment's own configured trust anchor.

    The alternate world is fully self-consistent and holds a genuine, currently-admitted,
    correctly-anchor-signed admission of its own -- signed by *its* anchor. Presented with the
    canonical deployment's anchor, composition refuses; and the canonical world's own admission
    presented with the alternate anchor refuses too. Neither direction produces an object that
    could then be handed to the request-facing bootstrap.
    """

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]
    with pytest.raises(RuntimeRequirementError):
        compose_trusted_runtime_deployment_authority(
            canonical["store"],
            project_id=canonical["project_id"],
            project_binding_id=canonical["project_binding_id"],
            runtime_root_admission_ref=alternate["admitted"]["runtime_root_admission_ref"],
            trust_anchor_public_key_hex=canonical["admitted"]["trust_anchor_public_key_hex"],
        )
    with pytest.raises(RuntimeRequirementError):
        compose_trusted_runtime_deployment_authority(
            canonical["store"],
            project_id=canonical["project_id"],
            project_binding_id=canonical["project_binding_id"],
            runtime_root_admission_ref=canonical["admitted"]["runtime_root_admission_ref"],
            trust_anchor_public_key_hex="0" * 64,
        )


def test_the_capability_call_still_refuses_every_non_authority_first_argument(
    _worlds: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no shipped minting path, the remaining question is whether the request-facing
    capability call can be reached *without* a genuine composed authority at all -- a bare Store,
    or a look-alike object shaped exactly like one and naming the alternate world. Both are
    refused at the type check, with Boot never reached."""

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]

    class _LookAlikeAuthority:
        _store = alternate["store"]
        _project_id = alternate["project_id"]
        _project_binding_id = alternate["project_binding_id"]
        _runtime_root_admission_id = alternate["admitted"]["runtime_root_admission_ref"]["id"]
        _runtime_root_admission_generation = 0

    def _boot_must_not_run(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError("Boot must never be reached without a genuine deployment authority")

    monkeypatch.setattr(bootstrap_module, "boot_project", _boot_must_not_run)

    for first_argument in (canonical["store"], _LookAlikeAuthority(), None, "PROJBIND-ANYTHING"):
        with pytest.raises(RuntimeRequirementError):
            bootstrap_projection_execution_capability(
                first_argument,  # type: ignore[arg-type]
                github_projection_grant_refs=[canonical["grant_ref"]],
                github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
            )
    assert isinstance(canonical["admitted"]["deployment_authority"], RuntimeDeploymentAuthority)


def test_the_public_observation_route_mints_no_root_and_names_no_capability(
    _worlds: dict[str, Any],
) -> None:
    """``observe_runtime_target`` is the one public route a real deployment reaches today. It
    constructs no deployment authority, names neither half of the bootstrap, and does not name the
    removed trust-root type either -- so there is no ambient live path that could be steered into
    provisioning anything. The source itself names none of them."""

    assert _worlds["canonical"]["project_id"]
    source = inspect.getsource(route_module)
    assert _REMOVED_TRUST_ROOT_TYPE_NAME not in source
    assert "RuntimeDeploymentAuthority" not in source
    assert "bootstrap_projection_execution_capability" not in source
    assert "compose_trusted_runtime_deployment_authority" not in source
    assert _DELETED_MINTING_FACTORY_NAME not in source
