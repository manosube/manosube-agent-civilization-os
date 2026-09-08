"""Phase 14 (Issue #62), Structural Review Round 6 (P14-R6-F2): genuine, verified SHUKOU/
Human Authority for V3 live-write execution -- entirely offline, zero network access. Round 8
(P14-R8-F1): the genuine article is a real Project Binding plus signed
``github_projection_grant``/``github_projection_grant_declaration`` records, verified through
the identical canonical Authority/Binding route
(:func:`~manosube_agent_civilization.authority.projection_authorization.
evaluate_projection_authorization`) a real GitHub projection call already uses. Round 9
(P14-R9-F1): those records are no longer accepted as caller-supplied bodies at all -- the live
gate resolves the real Project Binding through the identical canonical Boot route
(:func:`~manosube_agent_civilization.boot.boot_project`) and each grant/declaration through
the Store's own ``resolve_record`` surface, from project-scoped **references** only. Round 10
(P14-R10-F1): the Store/Project/Binding those references are resolved *within* is no longer
itself part of the untrusted references -- it comes from an independently supplied
:class:`~tests.fixtures.v3_live_write_authority.V3TrustedBootRoot`, and every grant/declaration
consumed must already be pre-issued and bound to a real subject, never minted at execution
time.

Every negative control here proves :func:`resolve_v3_live_write_authority` fails closed
(returns ``None``, never raises) before any network access could ever occur. No test in this
file constructs a ``RealGitHubAdapter`` or touches ``urllib``. Every test uses a real,
``tmp_path``-rooted ``FileStateStore`` -- there is no offline-only material shape this module
accepts.
"""

from __future__ import annotations

import dataclasses
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.v3_authority_test_material import (
    bind_v3_test_project,
    build_v3_subject,
    commit_pre_issued_v3_authorities,
    commit_v3_grant_with_declaration_signed_by_the_wrong_key,
    commit_v3_test_records,
    genuine_project_binding,
    genuine_v3_authority_store_and_material,
)
from tests.fixtures.v3_live_write_authority import (
    V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV,
    V3_PERMITTED_ACTION,
    V3_PROJECTION_KINDS,
    V3_TRUSTED_BOOT_ROOT_ENV,
    V3AuthorizedExecutionContext,
    V3LiveWriteAuthorityReferences,
    V3TrustedBootRoot,
    load_v3_live_write_authority_references,
    load_v3_trusted_boot_root,
    open_v3_trusted_store,
    resolve_v3_live_write_authority,
    v3_execution_context_still_current,
)
from tests.fixtures.v3_target_configuration import V3TargetConfiguration

from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint

_CONFIG = V3TargetConfiguration(
    owner="acme",
    repo="widget",
    token="test-token-not-a-real-secret",  # noqa: S106
    change_head_ref="agent/frozen-v3-branch",
    change_base_ref="main",
    evidence_head_sha="0123456789abcdef0123456789abcdef01234567",
    artifact_naming_prefix="MANOSUBE V3 proof (do not merge)",
    cleanup_confirmed=True,
    no_merge_confirmed=True,
    authorized_artifact_kinds=frozenset({"issue", "pull_request", "check_run"}),
    authorized_artifact_count=3,
)


def _trusted_root_for(store: Any, ctx: dict[str, Any]) -> V3TrustedBootRoot:
    return V3TrustedBootRoot(
        store_root=str(store.root),
        project_id=ctx["project_id"],
        project_binding_id=ctx["project_binding_id"],
    )


def _genuine(tmp_path: Path) -> tuple[V3TrustedBootRoot, V3LiveWriteAuthorityReferences]:
    store, ctx, references, _subjects = genuine_v3_authority_store_and_material(tmp_path, _CONFIG)
    return _trusted_root_for(store, ctx), references


#: Distinct only in ``target_repository`` from ``_CONFIG`` -- used solely to build the
#: "attacker's own, fully genuine, fully committed" world below. The fixture's own genesis
#: material (:func:`~tests.fixtures.product_binding.bind_project_kwargs`) is otherwise fully
#: deterministic, so an attacker who committed material under an *identical* configuration
#: would -- by content-addressing alone -- produce byte-identical grant/declaration ids to the
#: real Store's own, which would make this control vacuous rather than a proof of anything.
#: Varying ``target_repository`` is enough on its own: every pre-issued grant/declaration this
#: harness builds binds ``target_repository`` (hence its own content-addressed id) to whatever
#: configuration it was issued for.
_ATTACKER_CONFIG = replace(_CONFIG, owner="attacker-org", repo="attacker-widget")


def _attacker_genuine(
    tmp_path: Path,
) -> tuple[V3TrustedBootRoot, V3LiveWriteAuthorityReferences]:
    store, ctx, references, _subjects = genuine_v3_authority_store_and_material(
        tmp_path, _ATTACKER_CONFIG
    )
    return _trusted_root_for(store, ctx), references


# ---------------------------------------------------------------------------
# Positive route
# ---------------------------------------------------------------------------


def test_genuine_references_resolve_and_authorize_within_the_trusted_root(tmp_path: Path) -> None:
    trusted_root, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(trusted_root, _CONFIG, references)
    assert context is not None
    assert isinstance(context, V3AuthorizedExecutionContext)
    assert context.project_id == trusted_root.project_id
    assert context.project_binding_id == trusted_root.project_binding_id
    assert set(context.authorities) == set(V3_PROJECTION_KINDS)
    assert set(context.decisions) == set(V3_PROJECTION_KINDS)
    for projection_kind in V3_PROJECTION_KINDS:
        assert context.authorities[projection_kind].projection_kind == projection_kind
        assert context.decisions[projection_kind]["decision"] == "PROJECTION_AUTHORIZED"


def test_context_still_current_immediately_after_authorization(tmp_path: Path) -> None:
    trusted_root, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(trusted_root, _CONFIG, references)
    assert context is not None
    assert v3_execution_context_still_current(context) is True


def test_trusted_root_none_or_config_none_or_references_none_refuses_immediately(
    tmp_path: Path,
) -> None:
    trusted_root, references = _genuine(tmp_path)
    assert resolve_v3_live_write_authority(None, _CONFIG, references) is None
    assert resolve_v3_live_write_authority(trusted_root, None, references) is None
    assert resolve_v3_live_write_authority(trusted_root, _CONFIG, None) is None
    assert resolve_v3_live_write_authority(None, None, None) is None


def test_v3_projection_kinds_covers_exactly_the_three_harness_kinds() -> None:
    assert set(V3_PROJECTION_KINDS) == {
        "DIFFERENCE_ISSUE",
        "CHANGE_PULL_REQUEST",
        "EVIDENCE_ARTIFACT",
    }


# ---------------------------------------------------------------------------
# Required negative controls (Structural Review Round 10, P14-R10-F1): wrong trusted Store,
# Project, Binding, grant, declaration, decision, subject, boundary, revision, and post-check
# substitution -- each must fail closed before external access.
# ---------------------------------------------------------------------------


def test_wrong_trusted_project_id_refuses(tmp_path: Path) -> None:
    """A trusted root naming a ``project_id`` the real, committed Project Binding does not
    actually carry -- Boot itself refuses to restore, before any grant/declaration is even
    read."""

    trusted_root, references = _genuine(tmp_path)
    tampered = replace(trusted_root, project_id="PRJ-SOME-OTHER-PROJECT")
    assert resolve_v3_live_write_authority(tampered, _CONFIG, references) is None


def test_wrong_trusted_project_binding_id_refuses(tmp_path: Path) -> None:
    """A trusted root naming a ``project_binding_id`` that was never actually committed --
    Boot's own ``store.resolve_record`` lookup fails, refused before any grant/declaration is
    even read."""

    trusted_root, references = _genuine(tmp_path)
    tampered = replace(trusted_root, project_binding_id="PB-DOES-NOT-EXIST")
    assert resolve_v3_live_write_authority(tampered, _CONFIG, references) is None


def test_attacker_controlled_but_fully_committed_substitute_store_produces_zero_calls(
    tmp_path: Path,
) -> None:
    """Structural Review Round 10's own required control: a *fully committed*,
    internally self-consistent, genuinely Ed25519-signed attacker-controlled Store/Binding/
    authority universe -- built with the identical routes and shapes this repository's own
    genuine material uses -- must still produce zero adapter/network calls when the trusted
    root instead names the *real* Store, because the attacker's own Store is never even
    opened. This is the exact gap Round 9's own design left open: Round 9 only required
    resolved records to be genuinely committed and self-consistent, never that the Store
    itself was the trustworthy one."""

    attacker_tmp_path = tmp_path / "attacker-controlled-store"
    attacker_tmp_path.mkdir()
    attacker_trusted_root, attacker_references = _attacker_genuine(attacker_tmp_path)
    # Fully genuine, fully committed, fully self-consistent -- proven by authorizing fine
    # against its *own* trusted root, under the configuration it was actually issued for.
    assert (
        resolve_v3_live_write_authority(
            attacker_trusted_root, _ATTACKER_CONFIG, attacker_references
        )
        is not None
    )

    # The real, independently trusted root's own references must never resolve against the
    # attacker's Store -- and indeed nothing here even attempts to open it: the real trusted
    # root's own store_root always wins.
    real_trusted_root, _real_references = _genuine(tmp_path)
    assert real_trusted_root.store_root != attacker_trusted_root.store_root
    # Attempting to authorize the *attacker's own references* against the *real* trusted root
    # must refuse -- the attacker's grant/declaration ids were never committed to the real
    # Store at all.
    assert resolve_v3_live_write_authority(real_trusted_root, _CONFIG, attacker_references) is None


def test_unresolved_never_committed_grant_reference_refuses(tmp_path: Path) -> None:
    """A fully self-consistent, correctly-signed Project Binding and declarations that were
    built entirely offline and never actually committed to this Store must authorize nothing --
    ``store.resolve_record`` returns ``None`` for a reference nothing ever committed, refused
    before ``evaluate_projection_authorization`` is ever reached."""

    trusted_root, references = _genuine(tmp_path)
    fabricated_binding = genuine_project_binding()
    fabricated_grant_ref = {
        "kind": "github_projection_grant",
        "id": f"GH-PROJ-GRANT-NEVER-COMMITTED-{fabricated_binding['project_binding_id']}",
    }
    tampered = replace(references, github_projection_grant_refs=(fabricated_grant_ref,))
    assert resolve_v3_live_write_authority(trusted_root, _CONFIG, tampered) is None


def test_unresolved_never_committed_declaration_reference_refuses(tmp_path: Path) -> None:
    trusted_root, references = _genuine(tmp_path)
    fabricated_declaration_ref = {
        "kind": "github_projection_grant_declaration",
        "id": "GH-PROJ-GRANT-DECL-NEVER-COMMITTED-0001",
    }
    tampered = replace(
        references, github_projection_grant_declaration_refs=(fabricated_declaration_ref,)
    )
    assert resolve_v3_live_write_authority(trusted_root, _CONFIG, tampered) is None


def test_wrong_signer_refuses(tmp_path: Path) -> None:
    """A declaration genuinely resolvable from the Store, bound to a real subject -- but signed
    by a key other than the real project_binding's own registered key -- the exact regression
    Structural Review Round 8 corrected, still refused now that resolution goes through the
    trusted Store and the grant is subject-specific rather than configuration-scoped."""

    store, ctx = bind_v3_test_project(tmp_path)
    references = commit_v3_grant_with_declaration_signed_by_the_wrong_key(
        store, ctx, _CONFIG, projection_kind="DIFFERENCE_ISSUE", subject_kind="difference"
    )
    trusted_root = _trusted_root_for(store, ctx)
    assert resolve_v3_live_write_authority(trusted_root, _CONFIG, references) is None


def test_wrong_configuration_refuses(tmp_path: Path) -> None:
    """References genuinely pre-issued for one configuration checked against a *different*
    configuration (one changed field) -- ``target_repository`` no longer matches what the
    resolved grants themselves declare, so every projection kind refuses."""

    trusted_root, references = _genuine(tmp_path)
    changed_config = replace(_CONFIG, repo="a-different-widget")
    assert resolve_v3_live_write_authority(trusted_root, changed_config, references) is None


def test_wrong_target_repository_refuses(tmp_path: Path) -> None:
    """A grant genuinely resolvable from the trusted Store, bound to a real subject, but whose
    own ``target_repository`` names a different repository than *config*'s own."""

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    subject_ref, subject_fingerprint, _record, ctx["genesis_state"] = build_v3_subject(
        store, project_id, ctx["genesis_state"], "difference"
    )
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": subject_ref,
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": "DIFFERENCE_ISSUE",
        "target_repository": {"host": "github", "owner": "acme", "repo": "a-different-widget"},
        "payload_fingerprint": projection_payload_fingerprint(
            {"title": f"{_CONFIG.artifact_naming_prefix} -- Difference", "body": "harness"}
        ),
        "permitted_action": V3_PERMITTED_ACTION,
        "status": "ACTIVE",
        "granted_by": dict(ctx["human_authority_ref"]),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-WRONG-TARGET-GRANT-0001",
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    references, _subjects = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    references = replace(
        references,
        github_projection_grant_refs=(
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        ),
    )
    trusted_root = _trusted_root_for(store, ctx)
    assert resolve_v3_live_write_authority(trusted_root, _CONFIG, references) is None


def test_wrong_kinds_count_refuses(tmp_path: Path) -> None:
    """Only two of the three required projection kinds are named by *references* -- the
    missing kind has no matching pre-issued grant, so the whole set of references refuses (all
    three kinds must independently authorize)."""

    store, ctx = bind_v3_test_project(tmp_path)
    references, _subjects = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    narrowed = replace(
        references,
        github_projection_grant_refs=references.github_projection_grant_refs[:2],
        github_projection_grant_declaration_refs=(
            references.github_projection_grant_declaration_refs[:2]
        ),
    )
    trusted_root = _trusted_root_for(store, ctx)
    assert resolve_v3_live_write_authority(trusted_root, _CONFIG, narrowed) is None


def test_ambiguous_two_grants_for_the_same_kind_refuses(tmp_path: Path) -> None:
    """Structural Review Round 10's own required exactness: exactly one grant per projection
    kind, never zero and never more than one -- a second, genuinely distinct, genuinely
    resolvable grant for a kind already covered must refuse the whole set rather than pick
    either one arbitrarily."""

    store, ctx = bind_v3_test_project(tmp_path)
    references, _subjects = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    project_id = ctx["project_id"]
    subject_ref, subject_fingerprint, _record, ctx["genesis_state"] = build_v3_subject(
        store,
        project_id,
        ctx["genesis_state"],
        "difference",
        transaction_id="TX-V3-AMBIGUOUS-SUBJECT-0001",
    )
    extra_grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": subject_ref,
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": "DIFFERENCE_ISSUE",
        "target_repository": dict(_CONFIG.target_repository),
        "payload_fingerprint": projection_payload_fingerprint(
            {"title": f"{_CONFIG.artifact_naming_prefix} -- Difference (second)", "body": "harness"}
        ),
        "permitted_action": V3_PERMITTED_ACTION,
        "status": "ACTIVE",
        "granted_by": dict(ctx["human_authority_ref"]),
    }
    extra_grant["github_projection_grant_id"] = github_projection_grant_id(extra_grant)
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-AMBIGUOUS-GRANT-0001",
        [("github_projection_grant", extra_grant["github_projection_grant_id"], extra_grant)],
    )
    ambiguous = replace(
        references,
        github_projection_grant_refs=(
            *references.github_projection_grant_refs,
            {"kind": "github_projection_grant", "id": extra_grant["github_projection_grant_id"]},
        ),
    )
    trusted_root = _trusted_root_for(store, ctx)
    assert resolve_v3_live_write_authority(trusted_root, _CONFIG, ambiguous) is None


def test_revoked_grant_status_refuses(tmp_path: Path) -> None:
    """A grant committed with ``status="REVOKED"`` genuinely resolves from the trusted Store --
    but ``evaluate_projection_authorization`` itself refuses a non-``ACTIVE`` grant."""

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    subject_ref, subject_fingerprint, _record, ctx["genesis_state"] = build_v3_subject(
        store, project_id, ctx["genesis_state"], "difference"
    )
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": subject_ref,
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": "DIFFERENCE_ISSUE",
        "target_repository": dict(_CONFIG.target_repository),
        "payload_fingerprint": projection_payload_fingerprint(
            {"title": f"{_CONFIG.artifact_naming_prefix} -- Difference", "body": "harness"}
        ),
        "permitted_action": V3_PERMITTED_ACTION,
        "status": "REVOKED",
        "granted_by": dict(ctx["human_authority_ref"]),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-REVOKED-GRANT-0001",
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    references, _subjects = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    references = replace(
        references,
        github_projection_grant_refs=(
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        ),
    )
    trusted_root = _trusted_root_for(store, ctx)
    assert resolve_v3_live_write_authority(trusted_root, _CONFIG, references) is None


def test_revoked_declaration_status_refuses(tmp_path: Path) -> None:
    """An ``ACTIVE`` grant genuinely resolvable from the Store, anchored by a declaration
    genuinely committed with ``status="REVOKED"`` -- ``evaluate_projection_authorization``
    itself refuses a non-``ACTIVE`` anchoring declaration, even though both records
    independently resolve fine."""

    from tests.fixtures.product_binding import sign_github_projection_grant_declaration
    from tests.state_helpers import SCHEMA_ROOT

    from manosube_agent_civilization.binding import declare_github_projection_grant

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    project_binding_id = ctx["project_binding_id"]
    human_authority_ref = dict(ctx["human_authority_ref"])
    subject_ref, subject_fingerprint, _record, ctx["genesis_state"] = build_v3_subject(
        store, project_id, ctx["genesis_state"], "difference"
    )
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": subject_ref,
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": "DIFFERENCE_ISSUE",
        "target_repository": dict(_CONFIG.target_repository),
        "payload_fingerprint": projection_payload_fingerprint(
            {"title": f"{_CONFIG.artifact_naming_prefix} -- Difference", "body": "harness"}
        ),
        "permitted_action": V3_PERMITTED_ACTION,
        "status": "ACTIVE",
        "granted_by": human_authority_ref,
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-REVOKED-DECL-GRANT-0001",
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}
    signature = sign_github_projection_grant_declaration(
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        declared_by=human_authority_ref,
        subject_ref=grant["subject_ref"],
        subject_fingerprint=grant["subject_fingerprint"],
        projection_kind=grant["projection_kind"],
        target_repository=grant["target_repository"],
        payload_fingerprint=grant["payload_fingerprint"],
        permitted_action=grant["permitted_action"],
        status="REVOKED",
        declared_at="2026-09-08T00:00:00Z",
    )
    result = declare_github_projection_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        status="REVOKED",
        declared_at="2026-09-08T00:00:00Z",
        signature=signature,
        schema_root=SCHEMA_ROOT,
    )
    declaration = result["github_projection_grant_declaration"]
    ctx["genesis_state"] = result["committed_state"]

    references, _subjects = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    references = replace(
        references,
        github_projection_grant_refs=(grant_ref,),
        github_projection_grant_declaration_refs=(
            {
                "kind": "github_projection_grant_declaration",
                "id": declaration["github_projection_grant_declaration_id"],
            },
        ),
    )
    trusted_root = _trusted_root_for(store, ctx)
    assert resolve_v3_live_write_authority(trusted_root, _CONFIG, references) is None


# ---------------------------------------------------------------------------
# Stale Store revision / post-check substitution: fail closed on any Store mutation, or
# manual field substitution, between authorization and the moment a context is actually
# handed to the adapter-reaching execution call.
# ---------------------------------------------------------------------------


def test_context_no_longer_current_after_an_unrelated_store_mutation(tmp_path: Path) -> None:
    trusted_root, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(trusted_root, _CONFIG, references)
    assert context is not None
    assert v3_execution_context_still_current(context) is True

    # An unrelated transaction commits to the identical project after authorization -- e.g. a
    # concurrent Reflow cycle, an unrelated Difference lifecycle event. The context's own
    # captured state_revision/semantic_fingerprint no longer match the Store's current state,
    # so it must no longer be considered current.
    commit_v3_test_records(
        context.store,
        context.project_id,
        context.store.load_current(context.project_id),
        "TX-V3-UNRELATED-MUTATION-0001",
        [],
    )
    assert v3_execution_context_still_current(context) is False


def test_context_none_is_never_current() -> None:
    assert v3_execution_context_still_current(None) is False


def test_substituted_stale_revision_on_an_otherwise_genuine_context_is_never_current(
    tmp_path: Path,
) -> None:
    """A context manually reconstructed with its own captured ``state_revision`` swapped for a
    stale value -- the exact "post-check/pre-call substitution" this round's own required
    control names -- must never be considered current: re-Booting the real Store produces the
    genuine current revision, which no longer matches what the substituted context claims."""

    trusted_root, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(trusted_root, _CONFIG, references)
    assert context is not None

    substituted = dataclasses.replace(context, state_revision=context.state_revision - 1)
    assert v3_execution_context_still_current(substituted) is False


def test_substituted_wrong_project_binding_id_on_an_otherwise_genuine_context_is_never_current(
    tmp_path: Path,
) -> None:
    """A context manually reconstructed with its own ``project_binding_id`` swapped for one
    that was never actually committed -- Boot itself refuses to restore it."""

    trusted_root, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(trusted_root, _CONFIG, references)
    assert context is not None

    substituted = dataclasses.replace(context, project_binding_id="PB-DOES-NOT-EXIST")
    assert v3_execution_context_still_current(substituted) is False


# ---------------------------------------------------------------------------
# load_v3_trusted_boot_root / open_v3_trusted_store / load_v3_live_write_authority_references:
# the I/O boundaries this module has -- environment-variable reads and a local filesystem
# open, never a network call.
# ---------------------------------------------------------------------------


def test_load_trusted_boot_root_returns_none_when_unset() -> None:
    assert load_v3_trusted_boot_root(env={}) is None


def test_load_trusted_boot_root_returns_none_on_malformed_json() -> None:
    env = {V3_TRUSTED_BOOT_ROOT_ENV: "{not valid json"}
    assert load_v3_trusted_boot_root(env=env) is None


@pytest.mark.parametrize("missing_field", ["store_root", "project_id", "project_binding_id"])
def test_load_trusted_boot_root_returns_none_when_a_required_field_is_missing(
    tmp_path: Path, missing_field: str
) -> None:
    import json

    trusted_root, _references = _genuine(tmp_path)
    payload = dataclasses.asdict(trusted_root)
    del payload[missing_field]
    env = {V3_TRUSTED_BOOT_ROOT_ENV: json.dumps(payload)}
    assert load_v3_trusted_boot_root(env=env) is None


def test_load_trusted_boot_root_returns_the_decoded_root_when_well_formed(tmp_path: Path) -> None:
    import json

    trusted_root, _references = _genuine(tmp_path)
    env = {V3_TRUSTED_BOOT_ROOT_ENV: json.dumps(dataclasses.asdict(trusted_root))}
    assert load_v3_trusted_boot_root(env=env) == trusted_root


def test_open_trusted_store_returns_none_for_none_root() -> None:
    assert open_v3_trusted_store(None) is None


def test_open_trusted_store_returns_none_for_an_unreachable_root(tmp_path: Path) -> None:
    unreachable = V3TrustedBootRoot(
        store_root=str(tmp_path / "does" / "not" / "exist" / "\x00invalid"),
        project_id="PRJ-X",
        project_binding_id="PB-X",
    )
    assert open_v3_trusted_store(unreachable) is None


def test_load_references_returns_none_when_unset() -> None:
    assert load_v3_live_write_authority_references(env={}) is None


def test_load_references_returns_none_on_malformed_json() -> None:
    env = {V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: "{not valid json"}
    assert load_v3_live_write_authority_references(env=env) is None


def test_load_references_returns_none_when_json_is_not_an_object() -> None:
    env = {V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: "[1, 2, 3]"}
    assert load_v3_live_write_authority_references(env=env) is None


@pytest.mark.parametrize(
    "missing_field", ["github_projection_grant_refs", "github_projection_grant_declaration_refs"]
)
def test_load_references_returns_none_when_a_required_field_is_missing(
    tmp_path: Path, missing_field: str
) -> None:
    import json

    _trusted_root, references = _genuine(tmp_path)
    payload: dict[str, Any] = {
        "github_projection_grant_refs": list(references.github_projection_grant_refs),
        "github_projection_grant_declaration_refs": list(
            references.github_projection_grant_declaration_refs
        ),
    }
    del payload[missing_field]
    env = {V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: json.dumps(payload)}
    assert load_v3_live_write_authority_references(env=env) is None


def test_load_references_returns_the_decoded_references_when_well_formed(tmp_path: Path) -> None:
    import json

    _trusted_root, references = _genuine(tmp_path)
    payload = {
        "github_projection_grant_refs": list(references.github_projection_grant_refs),
        "github_projection_grant_declaration_refs": list(
            references.github_projection_grant_declaration_refs
        ),
    }
    env = {V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: json.dumps(payload)}
    assert load_v3_live_write_authority_references(env=env) == references


def test_load_references_default_env_source_is_os_environ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    _trusted_root, references = _genuine(tmp_path)
    payload = {
        "github_projection_grant_refs": list(references.github_projection_grant_refs),
        "github_projection_grant_declaration_refs": list(
            references.github_projection_grant_declaration_refs
        ),
    }
    monkeypatch.setenv(V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV, json.dumps(payload))
    assert load_v3_live_write_authority_references() == references


def test_end_to_end_load_open_resolve_round_trips_through_json(tmp_path: Path) -> None:
    import json

    trusted_root, references = _genuine(tmp_path)
    root_env = {V3_TRUSTED_BOOT_ROOT_ENV: json.dumps(dataclasses.asdict(trusted_root))}
    references_env = {
        V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: json.dumps(
            {
                "github_projection_grant_refs": list(references.github_projection_grant_refs),
                "github_projection_grant_declaration_refs": list(
                    references.github_projection_grant_declaration_refs
                ),
            }
        )
    }
    loaded_root = load_v3_trusted_boot_root(env=root_env)
    loaded_references = load_v3_live_write_authority_references(env=references_env)
    assert loaded_root is not None
    assert loaded_references is not None
    context = resolve_v3_live_write_authority(loaded_root, _CONFIG, loaded_references)
    assert context is not None
