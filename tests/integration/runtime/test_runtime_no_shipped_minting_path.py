"""P15-R2-F1, as Round 3 (P15-R3-F1) leaves it: the deleted minting factory stays deleted, and
no shipped callable hands back a ``TrustedRuntimeRoot``.

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

**Why this file survives Round 3 unchanged in substance.** Every fact it pins is still true and
still load-bearing, and pinning them is exactly what keeps the Round 3 correction from being
*read* as a quiet restoration of Round 1's factory:

- the deleted factory is not importable from anywhere shipped, under its own name;
- no shipped public callable declares ``TrustedRuntimeRoot`` as its return type, so a
  same-shaped factory under a *different* name would be caught too;
- the capability call still refuses every non-root first argument, before Boot;
- ``observe_runtime_target``, the one public observation route, still names neither the type nor
  the capability bootstrap, so no ambient live path can be steered through either.

What has changed is only the *reason* the first of these matters. It is no longer "because
minting must not exist"; it is "because the factory Round 2 removed conferred trust it had no
basis to confer, and reintroducing it would say something false about where trust now comes
from". The one test that genuinely could not survive -- Round 2's "the only issuer that exists
lives in tests" -- is replaced below by its Round 3 successor.
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
    trusted_runtime_root,
)

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection import ProjectionExecutionCapability
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
import manosube_agent_civilization.runtime as runtime_package
import manosube_agent_civilization.runtime.bootstrap as bootstrap_module
from manosube_agent_civilization.runtime.bootstrap import (
    TrustedRuntimeRoot,
    bootstrap_projection_execution_capability,
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
    key, with its own genuinely signed grant and declaration -- and, handed a root built by the
    *test-only* issuer, it produces a real ``ProjectionExecutionCapability`` entirely within
    itself.

    So the alternate world is exactly the kind of world Round 1's factory would have accepted.
    Everything below is therefore a statement about the absence of a shipped minting path, never
    a statement that this particular world happens to be malformed.
    """

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]
    assert alternate["human_authority_ref"] == ALTERNATE_HUMAN_AUTHORITY_REF
    assert alternate["human_authority_ref"] != canonical["human_authority_ref"]
    assert alternate["project_binding_id"] != canonical["project_binding_id"]

    capability = bootstrap_projection_execution_capability(
        alternate["admitted"]["trusted_runtime_root"],
        runtime_root_admission_ref=alternate["admitted"]["runtime_root_admission_ref"],
        trust_anchor_public_key_hex=alternate["admitted"]["trust_anchor_public_key_hex"],
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


def test_no_shipped_public_callable_returns_a_trusted_runtime_root(
    _worlds: dict[str, Any],
) -> None:
    """Every public callable this package exports, checked by its own declared return
    annotation: none of them produces a ``TrustedRuntimeRoot``. ``TrustedRuntimeRoot`` is
    exported as a *type* (a future deployment boundary needs to name it), never as something any
    shipped function hands back."""

    assert _worlds["canonical"]["project_id"]
    producers = []
    for name in runtime_package.__all__:
        member = getattr(runtime_package, name)
        if not callable(member) or isinstance(member, type):
            continue
        annotation = inspect.signature(member).return_annotation
        if TrustedRuntimeRoot in (annotation, getattr(annotation, "__origin__", None)) or (
            isinstance(annotation, str) and "TrustedRuntimeRoot" in annotation
        ):
            producers.append(name)
    assert producers == []


def test_the_root_type_is_public_shipped_api_and_the_fixture_helper_is_only_a_convenience(
    _worlds: dict[str, Any],
) -> None:
    """Round 3's replacement for Round 2's "the only issuer that exists lives in tests".

    That claim is no longer true and, more to the point, no longer *means* anything: a
    ``TrustedRuntimeRoot`` grants nothing, so where it is constructed is not a trust fact. What
    is worth pinning instead is that ``tests.fixtures.runtime_world.trusted_runtime_root`` is a
    plain convenience over the public shipped constructor and reaches no private internals at
    all -- so no reader can mistake it for a privileged test-side issuer, and deleting it would
    cost the suite nothing but three lines per call site.
    """

    assert trusted_runtime_root.__module__ == "tests.fixtures.runtime_world"
    from_helper = trusted_runtime_root(
        _worlds["canonical"]["store"],
        project_id=_worlds["canonical"]["project_id"],
        project_binding_id=_worlds["canonical"]["project_binding_id"],
    )
    directly = TrustedRuntimeRoot(
        _worlds["canonical"]["store"],
        _worlds["canonical"]["project_id"],
        _worlds["canonical"]["project_binding_id"],
    )
    assert isinstance(from_helper, TrustedRuntimeRoot)
    assert from_helper == directly


def test_the_capability_call_still_refuses_every_non_root_first_argument(
    _worlds: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no shipped minting path, the remaining question is whether the capability call can
    be reached *without* a genuine root at all -- a bare Store, or a look-alike object shaped
    exactly like one and naming the alternate world. Both are refused at the type check, with
    Boot never reached."""

    canonical = _worlds["canonical"]
    alternate = _worlds["alternate"]

    class _LookAlikeRoot:
        store = alternate["store"]
        project_id = alternate["project_id"]
        project_binding_id = alternate["project_binding_id"]

    def _boot_must_not_run(*args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError("Boot must never be reached without a genuine TrustedRuntimeRoot")

    monkeypatch.setattr(bootstrap_module, "boot_project", _boot_must_not_run)

    for first_argument in (canonical["store"], _LookAlikeRoot(), None, "PROJBIND-ANYTHING"):
        with pytest.raises(RuntimeRequirementError):
            bootstrap_projection_execution_capability(
                first_argument,  # type: ignore[arg-type]
                runtime_root_admission_ref=canonical["admitted"]["runtime_root_admission_ref"],
                trust_anchor_public_key_hex=(canonical["admitted"]["trust_anchor_public_key_hex"]),
                github_projection_grant_refs=[canonical["grant_ref"]],
                github_projection_grant_declaration_refs=[canonical["declaration_ref"]],
            )


def test_the_public_observation_route_mints_no_root_and_names_no_capability(
    _worlds: dict[str, Any],
) -> None:
    """``observe_runtime_target`` is the one public route a real deployment reaches today. It
    neither constructs a ``TrustedRuntimeRoot`` nor calls the capability bootstrap, so there is
    no ambient live path that could be steered into minting one -- the source itself names
    neither."""

    assert _worlds["canonical"]["project_id"]
    source = inspect.getsource(route_module)
    assert "TrustedRuntimeRoot" not in source
    assert "bootstrap_projection_execution_capability" not in source
    assert _DELETED_MINTING_FACTORY_NAME not in source
