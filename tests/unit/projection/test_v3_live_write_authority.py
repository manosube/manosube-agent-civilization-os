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
(P14-R10-F1): the Store/Project/Binding those references are resolved *within* came from an
independently supplied ``V3TrustedBootRoot``, itself read from a dedicated environment
variable. Round 11 (P14-R11-F1) removes that environment variable entirely -- any environment
variable a caller-controlling entity can set is still caller input, however narrowly scoped its
own JSON shape is. :func:`~tests.fixtures.v3_live_write_authority.
resolve_v3_live_write_authority` now takes the already-open Store object, and the project
identity strings to Boot-restore within it, as plain, caller-injected parameters -- this module
never opens, selects, or constructs a Store itself, and holds no capability to. Round 11 also
requires every projection kind's own subject (Difference/Change/Evidence) to be resolved by
exact reference from that identical Store, never accepted as a caller-supplied body or a
separate ``subjects`` mapping.

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
    V3AuthorizedExecutionContext,
    V3LiveWriteAuthorityReferences,
    load_v3_live_write_authority_references,
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


def _genuine(tmp_path: Path) -> tuple[Any, str, str, V3LiveWriteAuthorityReferences]:
    """Build a real, committed Store plus fully pre-issued references -- simulating, entirely
    in plain Python, what a genuine runtime bootstrap would already have on hand before ever
    calling :func:`resolve_v3_live_write_authority` (Structural Review Round 11, P14-R11-F1):
    an already-open Store object and Boot-verified project identity, never anything loaded from
    an environment variable."""

    store, ctx, references = genuine_v3_authority_store_and_material(tmp_path, _CONFIG)
    return store, ctx["project_id"], ctx["project_binding_id"], references


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


def _attacker_genuine(tmp_path: Path) -> tuple[Any, str, str, V3LiveWriteAuthorityReferences]:
    store, ctx, references = genuine_v3_authority_store_and_material(tmp_path, _ATTACKER_CONFIG)
    return store, ctx["project_id"], ctx["project_binding_id"], references


# ---------------------------------------------------------------------------
# Positive route
# ---------------------------------------------------------------------------


def test_genuine_references_resolve_and_authorize_within_the_injected_store(
    tmp_path: Path,
) -> None:
    store, project_id, project_binding_id, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(
        store, project_id, project_binding_id, _CONFIG, references
    )
    assert context is not None
    assert isinstance(context, V3AuthorizedExecutionContext)
    assert context.store is store
    assert context.project_id == project_id
    assert context.project_binding_id == project_binding_id
    assert set(context.authorities) == set(V3_PROJECTION_KINDS)
    assert set(context.decisions) == set(V3_PROJECTION_KINDS)
    for projection_kind in V3_PROJECTION_KINDS:
        assert context.authorities[projection_kind].projection_kind == projection_kind
        assert context.decisions[projection_kind]["decision"] == "PROJECTION_AUTHORIZED"


def test_context_authorities_carry_the_resolved_subject_record(tmp_path: Path) -> None:
    """Structural Review Round 11 (P14-R11-F1) §3/§8.4: the frozen context already carries each
    projection kind's own resolved, identity-verified subject body -- ``project_to_github``
    never needs, and this module never offers, a caller-supplied subject body or a separate
    subject mapping of any kind."""

    store, project_id, project_binding_id, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(
        store, project_id, project_binding_id, _CONFIG, references
    )
    assert context is not None
    for projection_kind in V3_PROJECTION_KINDS:
        authority = context.authorities[projection_kind]
        assert authority.subject_record is not None
        assert authority.subject_ref["kind"] in {"difference", "change", "observation_evidence"}
        if authority.subject_ref["kind"] in {"difference", "change"}:
            # observation_evidence records carry no project_id field of their own (unchanged
            # by this round -- the same shape project_to_github's own Store-resolution branch
            # for observation_evidence has always accepted).
            assert authority.subject_record.get("project_id") == project_id


def test_context_still_current_immediately_after_authorization(tmp_path: Path) -> None:
    store, project_id, project_binding_id, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(
        store, project_id, project_binding_id, _CONFIG, references
    )
    assert context is not None
    assert v3_execution_context_still_current(context) is True


def test_missing_store_or_identity_or_config_or_references_refuses_immediately(
    tmp_path: Path,
) -> None:
    store, project_id, project_binding_id, references = _genuine(tmp_path)
    assert (
        resolve_v3_live_write_authority(None, project_id, project_binding_id, _CONFIG, references)
        is None
    )
    assert (
        resolve_v3_live_write_authority(store, None, project_binding_id, _CONFIG, references)
        is None
    )
    assert resolve_v3_live_write_authority(store, project_id, None, _CONFIG, references) is None
    assert (
        resolve_v3_live_write_authority(store, project_id, project_binding_id, None, references)
        is None
    )
    assert (
        resolve_v3_live_write_authority(store, project_id, project_binding_id, _CONFIG, None)
        is None
    )
    assert resolve_v3_live_write_authority(None, None, None, None, None) is None


def test_v3_projection_kinds_covers_exactly_the_three_harness_kinds() -> None:
    assert set(V3_PROJECTION_KINDS) == {
        "DIFFERENCE_ISSUE",
        "CHANGE_PULL_REQUEST",
        "EVIDENCE_ARTIFACT",
    }


# ---------------------------------------------------------------------------
# Required negative controls (Structural Review Round 10, P14-R10-F1; extended for the
# caller-injected Store and Store-resolved subjects, Round 11, P14-R11-F1): wrong Store,
# Project, Binding, grant, declaration, decision, subject, boundary, revision, and post-check
# substitution -- each must fail closed before external access.
# ---------------------------------------------------------------------------


def test_wrong_project_id_refuses(tmp_path: Path) -> None:
    """A ``project_id`` the real, committed Project Binding does not actually carry -- Boot
    itself refuses to restore, before any grant/declaration is even read."""

    store, _project_id, project_binding_id, references = _genuine(tmp_path)
    assert (
        resolve_v3_live_write_authority(
            store, "PRJ-SOME-OTHER-PROJECT", project_binding_id, _CONFIG, references
        )
        is None
    )


def test_wrong_project_binding_id_refuses(tmp_path: Path) -> None:
    """A ``project_binding_id`` that was never actually committed -- Boot's own
    ``store.resolve_record`` lookup fails, refused before any grant/declaration is even read."""

    store, project_id, _project_binding_id, references = _genuine(tmp_path)
    assert (
        resolve_v3_live_write_authority(store, project_id, "PB-DOES-NOT-EXIST", _CONFIG, references)
        is None
    )


def test_attacker_controlled_but_fully_committed_substitute_store_produces_zero_calls(
    tmp_path: Path,
) -> None:
    """Structural Review Round 10's own required control, restated for Round 11's
    caller-injected Store (P14-R11-F1): a *fully committed*, internally self-consistent,
    genuinely Ed25519-signed attacker-controlled Store/Binding/authority universe -- built with
    the identical routes and shapes this repository's own genuine material uses -- must still
    produce zero adapter/network calls when the real, legitimately injected Store is what a
    caller actually passes, because the attacker's own Store object is never even reachable
    from here: this module has no mechanism of any kind (no string, path, or reference) capable
    of substituting one Store object for another -- the parameter itself *is* the trust
    boundary, and only whoever legitimately calls this function ever holds the real one."""

    attacker_tmp_path = tmp_path / "attacker-controlled-store"
    attacker_tmp_path.mkdir()
    attacker_store, attacker_project_id, attacker_project_binding_id, attacker_references = (
        _attacker_genuine(attacker_tmp_path)
    )
    # Fully genuine, fully committed, fully self-consistent -- proven by authorizing fine when
    # it is genuinely the Store/identity actually passed, under the configuration it was
    # actually issued for.
    assert (
        resolve_v3_live_write_authority(
            attacker_store,
            attacker_project_id,
            attacker_project_binding_id,
            _ATTACKER_CONFIG,
            attacker_references,
        )
        is not None
    )

    # The real Store's own references must never resolve against the attacker's material, and
    # the attacker's own references must never resolve against the real Store -- neither
    # object is ever substituted for the other by anything reachable through this function's
    # own parameters.
    real_store, real_project_id, real_project_binding_id, _real_references = _genuine(tmp_path)
    assert real_store is not attacker_store
    assert (
        resolve_v3_live_write_authority(
            real_store, real_project_id, real_project_binding_id, _CONFIG, attacker_references
        )
        is None
    )


def test_unresolved_never_committed_grant_reference_refuses(tmp_path: Path) -> None:
    """A fully self-consistent, correctly-signed Project Binding and declarations that were
    built entirely offline and never actually committed to this Store must authorize nothing --
    ``store.resolve_record`` returns ``None`` for a reference nothing ever committed, refused
    before ``evaluate_projection_authorization`` is ever reached."""

    store, project_id, project_binding_id, references = _genuine(tmp_path)
    fabricated_binding = genuine_project_binding()
    fabricated_grant_ref = {
        "kind": "github_projection_grant",
        "id": f"GH-PROJ-GRANT-NEVER-COMMITTED-{fabricated_binding['project_binding_id']}",
    }
    tampered = replace(references, github_projection_grant_refs=(fabricated_grant_ref,))
    assert (
        resolve_v3_live_write_authority(store, project_id, project_binding_id, _CONFIG, tampered)
        is None
    )


def test_unresolved_never_committed_declaration_reference_refuses(tmp_path: Path) -> None:
    store, project_id, project_binding_id, references = _genuine(tmp_path)
    fabricated_declaration_ref = {
        "kind": "github_projection_grant_declaration",
        "id": "GH-PROJ-GRANT-DECL-NEVER-COMMITTED-0001",
    }
    tampered = replace(
        references, github_projection_grant_declaration_refs=(fabricated_declaration_ref,)
    )
    assert (
        resolve_v3_live_write_authority(store, project_id, project_binding_id, _CONFIG, tampered)
        is None
    )


def test_wrong_signer_refuses(tmp_path: Path) -> None:
    """A declaration genuinely resolvable from the Store, bound to a real, Store-resolvable
    subject -- but signed by a key other than the real project_binding's own registered key --
    the exact regression Structural Review Round 8 corrected, still refused now that resolution
    goes through the caller-injected Store and the grant is subject-specific rather than
    configuration-scoped."""

    store, ctx = bind_v3_test_project(tmp_path)
    references = commit_v3_grant_with_declaration_signed_by_the_wrong_key(
        store, ctx, _CONFIG, projection_kind="DIFFERENCE_ISSUE", subject_kind="difference"
    )
    assert (
        resolve_v3_live_write_authority(
            store, ctx["project_id"], ctx["project_binding_id"], _CONFIG, references
        )
        is None
    )


def test_wrong_configuration_refuses(tmp_path: Path) -> None:
    """References genuinely pre-issued for one configuration checked against a *different*
    configuration (one changed field) -- ``target_repository`` no longer matches what the
    resolved grants themselves declare, so every projection kind refuses."""

    store, project_id, project_binding_id, references = _genuine(tmp_path)
    changed_config = replace(_CONFIG, repo="a-different-widget")
    assert (
        resolve_v3_live_write_authority(
            store, project_id, project_binding_id, changed_config, references
        )
        is None
    )


def test_wrong_target_repository_refuses(tmp_path: Path) -> None:
    """A grant genuinely resolvable from the injected Store, bound to a real subject, but whose
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
    references = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    references = replace(
        references,
        github_projection_grant_refs=(
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        ),
    )
    assert (
        resolve_v3_live_write_authority(
            store, project_id, ctx["project_binding_id"], _CONFIG, references
        )
        is None
    )


def test_wrong_kinds_count_refuses(tmp_path: Path) -> None:
    """Only two of the three required projection kinds are named by *references* -- the
    missing kind has no matching pre-issued grant, so the whole set of references refuses (all
    three kinds must independently authorize)."""

    store, ctx = bind_v3_test_project(tmp_path)
    references = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    narrowed = replace(
        references,
        github_projection_grant_refs=references.github_projection_grant_refs[:2],
        github_projection_grant_declaration_refs=(
            references.github_projection_grant_declaration_refs[:2]
        ),
    )
    assert (
        resolve_v3_live_write_authority(
            store, ctx["project_id"], ctx["project_binding_id"], _CONFIG, narrowed
        )
        is None
    )


def test_ambiguous_two_grants_for_the_same_kind_refuses(tmp_path: Path) -> None:
    """Structural Review Round 10's own required exactness: exactly one grant per projection
    kind, never zero and never more than one -- a second, genuinely distinct, genuinely
    resolvable grant for a kind already covered must refuse the whole set rather than pick
    either one arbitrarily."""

    store, ctx = bind_v3_test_project(tmp_path)
    references = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
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
    assert (
        resolve_v3_live_write_authority(
            store, project_id, ctx["project_binding_id"], _CONFIG, ambiguous
        )
        is None
    )


def test_revoked_grant_status_refuses(tmp_path: Path) -> None:
    """A grant committed with ``status="REVOKED"`` genuinely resolves from the injected Store,
    bound to a genuinely Store-resolvable subject -- but ``evaluate_projection_authorization``
    itself refuses a non-``ACTIVE`` grant."""

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    subject_ref, subject_fingerprint, subject_record, ctx["genesis_state"] = build_v3_subject(
        store, project_id, ctx["genesis_state"], "difference"
    )
    assert subject_record is not None
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-REVOKED-GRANT-SUBJECT-COMMIT-0001",
        [("difference", subject_ref["id"], subject_record)],
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
    references = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    references = replace(
        references,
        github_projection_grant_refs=(
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        ),
    )
    assert (
        resolve_v3_live_write_authority(
            store, project_id, ctx["project_binding_id"], _CONFIG, references
        )
        is None
    )


def test_revoked_declaration_status_refuses(tmp_path: Path) -> None:
    """An ``ACTIVE`` grant genuinely resolvable from the Store and bound to a genuinely
    Store-resolvable subject, anchored by a declaration genuinely committed with
    ``status="REVOKED"`` -- ``evaluate_projection_authorization`` itself refuses a non-``ACTIVE``
    anchoring declaration, even though every record independently resolves fine."""

    from tests.fixtures.product_binding import sign_github_projection_grant_declaration
    from tests.state_helpers import SCHEMA_ROOT

    from manosube_agent_civilization.binding import declare_github_projection_grant

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    project_binding_id = ctx["project_binding_id"]
    human_authority_ref = dict(ctx["human_authority_ref"])
    subject_ref, subject_fingerprint, subject_record, ctx["genesis_state"] = build_v3_subject(
        store, project_id, ctx["genesis_state"], "difference"
    )
    assert subject_record is not None
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-REVOKED-DECL-SUBJECT-COMMIT-0001",
        [("difference", subject_ref["id"], subject_record)],
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

    references = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
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
    assert (
        resolve_v3_live_write_authority(store, project_id, project_binding_id, _CONFIG, references)
        is None
    )


# ---------------------------------------------------------------------------
# Required negative controls (Structural Review Round 11, P14-R11-F1 §3/§8.5): the subject
# itself must be genuinely, exactly, and correctly Store-resolvable -- never merely a claim the
# grant makes about it.
# ---------------------------------------------------------------------------


def test_subject_never_committed_to_store_refuses(tmp_path: Path) -> None:
    """A grant's own ``subject_ref`` names a subject that was built (via
    :func:`~tests.fixtures.v3_authority_test_material.build_v3_subject`) but never actually
    committed to the Store -- ``store.resolve_record`` returns ``None``, refused before
    ``evaluate_projection_authorization`` is ever reached."""

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    subject_ref, subject_fingerprint, _subject_record, ctx["genesis_state"] = build_v3_subject(
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
        "granted_by": dict(ctx["human_authority_ref"]),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-SUBJECT-NEVER-COMMITTED-GRANT-0001",
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    references = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    references = replace(
        references,
        github_projection_grant_refs=(
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        ),
    )
    assert (
        resolve_v3_live_write_authority(
            store, project_id, ctx["project_binding_id"], _CONFIG, references
        )
        is None
    )


def test_subject_kind_mismatch_refuses(tmp_path: Path) -> None:
    """A ``DIFFERENCE_ISSUE`` grant whose own ``subject_ref.kind`` names a ``change`` subject
    instead of a ``difference`` one -- even a genuinely committed, genuinely Store-resolvable
    ``change`` subject must never authorize a projection kind that requires a different subject
    kind."""

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    subject_ref, subject_fingerprint, subject_record, ctx["genesis_state"] = build_v3_subject(
        store, project_id, ctx["genesis_state"], "change"
    )
    assert subject_record is not None
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-KIND-MISMATCH-SUBJECT-COMMIT-0001",
        [("change", subject_ref["id"], subject_record)],
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
        "granted_by": dict(ctx["human_authority_ref"]),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-KIND-MISMATCH-GRANT-0001",
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    references = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    references = replace(
        references,
        github_projection_grant_refs=(
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        ),
    )
    assert (
        resolve_v3_live_write_authority(
            store, project_id, ctx["project_binding_id"], _CONFIG, references
        )
        is None
    )


def test_grant_claiming_the_wrong_subject_fingerprint_refuses(tmp_path: Path) -> None:
    """A grant naming a genuinely committed, genuinely Store-resolvable subject -- but claiming
    a ``subject_fingerprint`` that does not equal that subject's own independently recomputed
    fingerprint. The grant's own claim is never trusted merely because it resolves."""

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    subject_ref, _real_fingerprint, subject_record, ctx["genesis_state"] = build_v3_subject(
        store, project_id, ctx["genesis_state"], "difference"
    )
    assert subject_record is not None
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-WRONG-FINGERPRINT-SUBJECT-COMMIT-0001",
        [("difference", subject_ref["id"], subject_record)],
    )
    wrong_fingerprint = "sha256:" + "0" * 64
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": subject_ref,
        "subject_fingerprint": wrong_fingerprint,
        "projection_kind": "DIFFERENCE_ISSUE",
        "target_repository": dict(_CONFIG.target_repository),
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
        "TX-V3-WRONG-FINGERPRINT-GRANT-0001",
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    references = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    references = replace(
        references,
        github_projection_grant_refs=(
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        ),
    )
    assert (
        resolve_v3_live_write_authority(
            store, project_id, ctx["project_binding_id"], _CONFIG, references
        )
        is None
    )


def test_subject_committed_under_the_wrong_id_refuses(tmp_path: Path) -> None:
    """A real Difference body, genuinely committed to the Store -- but under a record id that
    does not equal that body's own recomputed ``difference_id`` (a corrupted or tampered
    Store). Resolution succeeds (the record file exists and is committed), but the independent
    identity recomputation this module performs itself catches the mismatch."""

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    subject_ref, subject_fingerprint, subject_record, ctx["genesis_state"] = build_v3_subject(
        store, project_id, ctx["genesis_state"], "difference"
    )
    assert subject_record is not None
    wrong_id = "D-DOES-NOT-MATCH-ITS-OWN-RECOMPUTED-IDENTITY"
    ctx["genesis_state"] = commit_v3_test_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-V3-WRONG-SUBJECT-ID-COMMIT-0001",
        [("difference", wrong_id, subject_record)],
    )
    tampered_ref = {"kind": "difference", "id": wrong_id}
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": tampered_ref,
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": "DIFFERENCE_ISSUE",
        "target_repository": dict(_CONFIG.target_repository),
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
        "TX-V3-WRONG-SUBJECT-ID-GRANT-0001",
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    references = commit_pre_issued_v3_authorities(store, ctx, _CONFIG)
    references = replace(
        references,
        github_projection_grant_refs=(
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        ),
    )
    assert subject_ref["id"] != wrong_id
    assert (
        resolve_v3_live_write_authority(
            store, project_id, ctx["project_binding_id"], _CONFIG, references
        )
        is None
    )


# ---------------------------------------------------------------------------
# Stale Store revision / post-check substitution: fail closed on any Store mutation, or
# manual field substitution, between authorization and the moment a context is actually
# handed to the adapter-reaching execution call.
# ---------------------------------------------------------------------------


def test_context_no_longer_current_after_an_unrelated_store_mutation(tmp_path: Path) -> None:
    store, project_id, project_binding_id, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(
        store, project_id, project_binding_id, _CONFIG, references
    )
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

    store, project_id, project_binding_id, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(
        store, project_id, project_binding_id, _CONFIG, references
    )
    assert context is not None

    substituted = dataclasses.replace(context, state_revision=context.state_revision - 1)
    assert v3_execution_context_still_current(substituted) is False


def test_substituted_wrong_project_binding_id_on_an_otherwise_genuine_context_is_never_current(
    tmp_path: Path,
) -> None:
    """A context manually reconstructed with its own ``project_binding_id`` swapped for one
    that was never actually committed -- Boot itself refuses to restore it."""

    store, project_id, project_binding_id, references = _genuine(tmp_path)
    context = resolve_v3_live_write_authority(
        store, project_id, project_binding_id, _CONFIG, references
    )
    assert context is not None

    substituted = dataclasses.replace(context, project_binding_id="PB-DOES-NOT-EXIST")
    assert v3_execution_context_still_current(substituted) is False


# ---------------------------------------------------------------------------
# load_v3_live_write_authority_references: the one I/O boundary this module has -- an
# environment-variable read, never a Store construction of any kind and never a network call.
# ---------------------------------------------------------------------------


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

    _store, _project_id, _project_binding_id, references = _genuine(tmp_path)
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

    _store, _project_id, _project_binding_id, references = _genuine(tmp_path)
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

    _store, _project_id, _project_binding_id, references = _genuine(tmp_path)
    payload = {
        "github_projection_grant_refs": list(references.github_projection_grant_refs),
        "github_projection_grant_declaration_refs": list(
            references.github_projection_grant_declaration_refs
        ),
    }
    monkeypatch.setenv(V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV, json.dumps(payload))
    assert load_v3_live_write_authority_references() == references


def test_end_to_end_load_references_and_resolve_round_trips_through_json(tmp_path: Path) -> None:
    """The one genuinely environment-sourced input this module still has -- the untrusted
    grant/declaration references -- round-trips through JSON exactly as before; the Store and
    project identity are never environment-sourced at all any more (Structural Review Round 11,
    P14-R11-F1), so they are supplied here as the plain, directly-injected values a real runtime
    bootstrap would already hold."""

    import json

    store, project_id, project_binding_id, references = _genuine(tmp_path)
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
    loaded_references = load_v3_live_write_authority_references(env=references_env)
    assert loaded_references is not None
    context = resolve_v3_live_write_authority(
        store, project_id, project_binding_id, _CONFIG, loaded_references
    )
    assert context is not None
