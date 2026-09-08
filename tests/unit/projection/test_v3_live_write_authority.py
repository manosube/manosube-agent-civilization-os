"""Phase 14 (Issue #62), Structural Review Round 6 (P14-R6-F2): genuine, verified SHUKOU/
Human Authority for V3 live-write execution -- entirely offline, zero network access, zero
Store dependency claims. Structural Review Round 8 (P14-R8-F1): the genuine article is a real
Project Binding plus signed ``github_projection_grant``/``github_projection_grant_declaration``
records, verified through the identical canonical Authority/Binding route
(:func:`~manosube_agent_civilization.authority.projection_authorization.
evaluate_projection_authorization`) a real GitHub projection call already uses. Structural
Review Round 9 (P14-R9-F1): those records are no longer accepted as caller-supplied bodies at
all -- the live gate now resolves the real Project Binding through the identical canonical
Boot route (:func:`~manosube_agent_civilization.boot.boot_project`) and each grant/declaration
through the Store's own ``resolve_record`` surface, from project-scoped **references** only,
and returns one immutable :class:`~tests.fixtures.v3_live_write_authority.
V3AuthorizedExecutionContext` a caller must thread unchanged into the exact execution function
that reaches the adapter.

Every negative control here proves :func:`resolve_v3_live_write_authority` fails closed
(returns ``None``, never raises) before any network access could ever occur. No test in this
file constructs a ``RealGitHubAdapter`` or touches ``urllib``. Every test uses a real,
``tmp_path``-rooted ``FileStateStore`` -- there is no longer an offline-only material shape
this module accepts.
"""

from __future__ import annotations

import dataclasses
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures.v3_authority_test_material import (
    bind_v3_test_project,
    commit_genuine_v3_grants_and_declarations,
    commit_v3_grant_with_declaration_signed_by_the_wrong_key,
    genuine_project_binding,
)
from tests.fixtures.v3_live_write_authority import (
    V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV,
    V3_PROJECTION_KINDS,
    V3AuthorizedExecutionContext,
    V3LiveWriteAuthorityReferences,
    load_v3_live_write_authority_references,
    open_v3_live_write_store,
    resolve_v3_live_write_authority,
    v3_configuration_subject_ref,
    v3_execution_context_still_current,
)
from tests.fixtures.v3_target_configuration import V3TargetConfiguration

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


def _genuine(tmp_path: Path) -> V3LiveWriteAuthorityReferences:
    store, ctx = bind_v3_test_project(tmp_path)
    return commit_genuine_v3_grants_and_declarations(store, ctx, _CONFIG)


def _store_for(references: V3LiveWriteAuthorityReferences) -> Any:
    store = open_v3_live_write_store(references)
    assert store is not None
    return store


# ---------------------------------------------------------------------------
# Positive route
# ---------------------------------------------------------------------------


def test_genuine_references_resolve_and_authorize_the_exact_configuration_they_were_issued_for(
    tmp_path: Path,
) -> None:
    references = _genuine(tmp_path)
    store = _store_for(references)
    context = resolve_v3_live_write_authority(store, _CONFIG, references)
    assert context is not None
    assert isinstance(context, V3AuthorizedExecutionContext)
    assert context.project_id == references.project_id
    assert context.project_binding_id == references.project_binding_id
    assert context.github_projection_grant_refs == references.github_projection_grant_refs
    assert (
        context.github_projection_grant_declaration_refs
        == references.github_projection_grant_declaration_refs
    )
    assert set(context.decisions) == set(V3_PROJECTION_KINDS)
    for decision in context.decisions.values():
        assert decision["decision"] == "PROJECTION_AUTHORIZED"


def test_context_still_current_immediately_after_authorization(tmp_path: Path) -> None:
    references = _genuine(tmp_path)
    store = _store_for(references)
    context = resolve_v3_live_write_authority(store, _CONFIG, references)
    assert context is not None
    assert v3_execution_context_still_current(context) is True


def test_store_none_or_config_none_or_references_none_refuses_immediately(tmp_path: Path) -> None:
    references = _genuine(tmp_path)
    store = _store_for(references)
    assert resolve_v3_live_write_authority(None, _CONFIG, references) is None
    assert resolve_v3_live_write_authority(store, None, references) is None
    assert resolve_v3_live_write_authority(store, _CONFIG, None) is None
    assert resolve_v3_live_write_authority(None, None, None) is None


def test_v3_projection_kinds_covers_exactly_the_three_harness_kinds() -> None:
    assert set(V3_PROJECTION_KINDS) == {
        "DIFFERENCE_ISSUE",
        "CHANGE_PULL_REQUEST",
        "EVIDENCE_ARTIFACT",
    }


# ---------------------------------------------------------------------------
# Required negative controls (Structural Review Round 9, P14-R9-F1): wrong project, binding,
# signer, decision, configuration, target, action, kinds/count, validity, revoked-status, an
# unresolved/never-committed reference, and stale Store revision / post-check substitution.
# ---------------------------------------------------------------------------


def test_wrong_project_id_refuses(tmp_path: Path) -> None:
    """*references* naming a ``project_id`` the real, committed Project Binding does not
    actually carry -- Boot itself refuses to restore, before any grant/declaration is even
    read."""

    references = _genuine(tmp_path)
    store = _store_for(references)
    tampered = replace(references, project_id="PRJ-SOME-OTHER-PROJECT")
    assert resolve_v3_live_write_authority(store, _CONFIG, tampered) is None


def test_wrong_project_binding_id_refuses(tmp_path: Path) -> None:
    """*references* naming a ``project_binding_id`` that was never actually committed --
    Boot's own ``store.resolve_record`` lookup fails, refused before any grant/declaration is
    even read."""

    references = _genuine(tmp_path)
    store = _store_for(references)
    tampered = replace(references, project_binding_id="PB-DOES-NOT-EXIST")
    assert resolve_v3_live_write_authority(store, _CONFIG, tampered) is None


def test_unresolved_never_committed_grant_reference_refuses(tmp_path: Path) -> None:
    """Structural Review Round 9's own required control: a fully self-consistent,
    correctly-signed Project Binding and declarations that were built entirely offline and
    never actually committed to this Store must authorize nothing -- ``store.resolve_record``
    returns ``None`` for a reference nothing ever committed, refused before
    ``evaluate_projection_authorization`` is ever reached."""

    references = _genuine(tmp_path)
    store = _store_for(references)
    fabricated_binding = genuine_project_binding()
    fabricated_grant_ref = {
        "kind": "github_projection_grant",
        "id": f"GH-PROJ-GRANT-NEVER-COMMITTED-{fabricated_binding['project_binding_id']}",
    }
    tampered = replace(references, github_projection_grant_refs=(fabricated_grant_ref,))
    assert resolve_v3_live_write_authority(store, _CONFIG, tampered) is None


def test_unresolved_never_committed_declaration_reference_refuses(tmp_path: Path) -> None:
    references = _genuine(tmp_path)
    store = _store_for(references)
    fabricated_declaration_ref = {
        "kind": "github_projection_grant_declaration",
        "id": "GH-PROJ-GRANT-DECL-NEVER-COMMITTED-0001",
    }
    tampered = replace(
        references, github_projection_grant_declaration_refs=(fabricated_declaration_ref,)
    )
    assert resolve_v3_live_write_authority(store, _CONFIG, tampered) is None


def test_wrong_signer_refuses(tmp_path: Path) -> None:
    """A declaration genuinely resolvable from the Store -- but signed by a key other than the
    real project_binding's own registered key -- the exact regression Structural Review
    Round 8 corrected, still refused now that resolution itself goes through the Store."""

    store, ctx = bind_v3_test_project(tmp_path)
    references = commit_v3_grant_with_declaration_signed_by_the_wrong_key(
        store, ctx, _CONFIG, projection_kind="DIFFERENCE_ISSUE"
    )
    assert resolve_v3_live_write_authority(store, _CONFIG, references) is None


def test_wrong_configuration_refuses(tmp_path: Path) -> None:
    """References genuinely issued for one configuration checked against a *different*
    configuration (one changed field) -- subject_fingerprint/target_repository no longer match
    what the resolved grants/declarations actually name, so every projection kind refuses."""

    references = _genuine(tmp_path)
    store = _store_for(references)
    changed_config = replace(_CONFIG, repo="a-different-widget")
    assert resolve_v3_live_write_authority(store, changed_config, references) is None


def test_wrong_target_repository_refuses(tmp_path: Path) -> None:
    """A grant genuinely resolvable from the Store, but whose own ``target_repository`` names
    a different repository than *config*'s own -- the request built from the real (untampered)
    configuration no longer matches what the resolved grant itself declares."""

    from tests.fixtures.v3_authority_test_material import commit_v3_test_records
    from tests.fixtures.v3_live_write_authority import V3_PERMITTED_ACTION

    from manosube_agent_civilization.authority.identity import github_projection_grant_id

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    subject_ref = v3_configuration_subject_ref(_CONFIG)
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": subject_ref,
        "subject_fingerprint": _CONFIG.configuration_fingerprint,
        "projection_kind": "DIFFERENCE_ISSUE",
        "target_repository": {"host": "github", "owner": "acme", "repo": "a-different-widget"},
        "payload_fingerprint": _CONFIG.configuration_fingerprint,
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
    references = replace(
        commit_genuine_v3_grants_and_declarations(store, ctx, _CONFIG),
        github_projection_grant_refs=(
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        ),
    )
    assert resolve_v3_live_write_authority(store, _CONFIG, references) is None


def test_wrong_kinds_count_refuses(tmp_path: Path) -> None:
    """Only two of the three required projection kinds are named by *references* -- the
    missing kind's own authorization request finds no matching grant, so the whole set of
    references refuses (all three kinds must independently authorize)."""

    store, ctx = bind_v3_test_project(tmp_path)
    references = commit_genuine_v3_grants_and_declarations(store, ctx, _CONFIG)
    narrowed = replace(
        references,
        github_projection_grant_refs=references.github_projection_grant_refs[:2],
        github_projection_grant_declaration_refs=(
            references.github_projection_grant_declaration_refs[:2]
        ),
    )
    assert resolve_v3_live_write_authority(store, _CONFIG, narrowed) is None


def test_revoked_grant_status_refuses(tmp_path: Path) -> None:
    """A grant committed with ``status="REVOKED"`` genuinely resolves from the Store -- but
    ``evaluate_projection_authorization`` itself refuses a non-``ACTIVE`` grant."""

    from tests.fixtures.v3_authority_test_material import commit_v3_test_records
    from tests.fixtures.v3_live_write_authority import V3_PERMITTED_ACTION

    from manosube_agent_civilization.authority.identity import github_projection_grant_id

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    subject_ref = v3_configuration_subject_ref(_CONFIG)
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": subject_ref,
        "subject_fingerprint": _CONFIG.configuration_fingerprint,
        "projection_kind": "DIFFERENCE_ISSUE",
        "target_repository": dict(_CONFIG.target_repository),
        "payload_fingerprint": _CONFIG.configuration_fingerprint,
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
    references = replace(
        commit_genuine_v3_grants_and_declarations(store, ctx, _CONFIG),
        github_projection_grant_refs=(
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]},
        ),
    )
    assert resolve_v3_live_write_authority(store, _CONFIG, references) is None


def test_revoked_declaration_status_refuses(tmp_path: Path) -> None:
    """An ``ACTIVE`` grant genuinely resolvable from the Store, anchored by a declaration
    genuinely committed with ``status="REVOKED"`` -- ``evaluate_projection_authorization``
    itself refuses a non-``ACTIVE`` anchoring declaration, even though both records
    independently resolve fine."""

    from tests.fixtures.product_binding import sign_github_projection_grant_declaration
    from tests.fixtures.v3_authority_test_material import commit_v3_test_records
    from tests.fixtures.v3_live_write_authority import V3_PERMITTED_ACTION
    from tests.state_helpers import SCHEMA_ROOT

    from manosube_agent_civilization.authority.identity import github_projection_grant_id
    from manosube_agent_civilization.binding import declare_github_projection_grant

    store, ctx = bind_v3_test_project(tmp_path)
    project_id = ctx["project_id"]
    project_binding_id = ctx["project_binding_id"]
    human_authority_ref = dict(ctx["human_authority_ref"])
    subject_ref = v3_configuration_subject_ref(_CONFIG)
    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": subject_ref,
        "subject_fingerprint": _CONFIG.configuration_fingerprint,
        "projection_kind": "DIFFERENCE_ISSUE",
        "target_repository": dict(_CONFIG.target_repository),
        "payload_fingerprint": _CONFIG.configuration_fingerprint,
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

    references = replace(
        commit_genuine_v3_grants_and_declarations(store, ctx, _CONFIG),
        github_projection_grant_refs=(grant_ref,),
        github_projection_grant_declaration_refs=(
            {
                "kind": "github_projection_grant_declaration",
                "id": declaration["github_projection_grant_declaration_id"],
            },
        ),
    )
    assert resolve_v3_live_write_authority(store, _CONFIG, references) is None


# ---------------------------------------------------------------------------
# Stale Store revision / post-check substitution (Structural Review Round 9, P14-R9-F1): fail
# closed on any Store mutation, or manual field substitution, between authorization and the
# moment a context is actually handed to the adapter-reaching execution call.
# ---------------------------------------------------------------------------


def test_context_no_longer_current_after_an_unrelated_store_mutation(tmp_path: Path) -> None:
    from tests.fixtures.v3_authority_test_material import commit_v3_test_records

    store, ctx = bind_v3_test_project(tmp_path)
    references = commit_genuine_v3_grants_and_declarations(store, ctx, _CONFIG)
    context = resolve_v3_live_write_authority(store, _CONFIG, references)
    assert context is not None
    assert v3_execution_context_still_current(context) is True

    # An unrelated transaction commits to the identical project after authorization --
    # e.g. a concurrent Reflow cycle, an unrelated Difference lifecycle event. The context's
    # own captured state_revision/semantic_fingerprint no longer match the Store's current
    # state, so it must no longer be considered current.
    commit_v3_test_records(
        store,
        ctx["project_id"],
        ctx["genesis_state"],
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

    references = _genuine(tmp_path)
    store = _store_for(references)
    context = resolve_v3_live_write_authority(store, _CONFIG, references)
    assert context is not None

    substituted = dataclasses.replace(context, state_revision=context.state_revision - 1)
    assert v3_execution_context_still_current(substituted) is False


def test_substituted_wrong_project_binding_id_on_an_otherwise_genuine_context_is_never_current(
    tmp_path: Path,
) -> None:
    """A context manually reconstructed with its own ``project_binding_id`` swapped for one
    that was never actually committed -- Boot itself refuses to restore it."""

    references = _genuine(tmp_path)
    store = _store_for(references)
    context = resolve_v3_live_write_authority(store, _CONFIG, references)
    assert context is not None

    substituted = dataclasses.replace(context, project_binding_id="PB-DOES-NOT-EXIST")
    assert v3_execution_context_still_current(substituted) is False


# ---------------------------------------------------------------------------
# v3_configuration_subject_ref: the V3-configuration-shaped subject every grant/declaration/
# decision this module consumes must name.
# ---------------------------------------------------------------------------


def test_v3_configuration_subject_ref_is_content_addressed_by_the_configuration_fingerprint() -> (
    None
):
    subject_ref = v3_configuration_subject_ref(_CONFIG)
    assert subject_ref == {
        "kind": "v3_target_configuration",
        "id": _CONFIG.configuration_fingerprint,
    }


def test_v3_configuration_subject_ref_changes_with_any_bound_configuration_field() -> None:
    changed_config = replace(_CONFIG, repo="a-different-widget")
    assert v3_configuration_subject_ref(_CONFIG) != v3_configuration_subject_ref(changed_config)


# ---------------------------------------------------------------------------
# load_v3_live_write_authority_references / open_v3_live_write_store: the two I/O boundaries
# this module has -- an environment-variable read and a local filesystem open, never a network
# call.
# ---------------------------------------------------------------------------


def test_load_returns_none_when_unset() -> None:
    assert load_v3_live_write_authority_references(env={}) is None


def test_load_returns_none_on_malformed_json() -> None:
    env = {V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: "{not valid json"}
    assert load_v3_live_write_authority_references(env=env) is None


def test_load_returns_none_when_json_is_not_an_object() -> None:
    env = {V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: "[1, 2, 3]"}
    assert load_v3_live_write_authority_references(env=env) is None


@pytest.mark.parametrize(
    "missing_field",
    [
        "store_root",
        "project_id",
        "project_binding_id",
        "github_projection_grant_refs",
        "github_projection_grant_declaration_refs",
    ],
)
def test_load_returns_none_when_a_required_field_is_missing(
    tmp_path: Path, missing_field: str
) -> None:
    import json

    references = _genuine(tmp_path)
    payload: dict[str, Any] = {
        "store_root": references.store_root,
        "project_id": references.project_id,
        "project_binding_id": references.project_binding_id,
        "github_projection_grant_refs": list(references.github_projection_grant_refs),
        "github_projection_grant_declaration_refs": list(
            references.github_projection_grant_declaration_refs
        ),
    }
    del payload[missing_field]
    env = {V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: json.dumps(payload)}
    assert load_v3_live_write_authority_references(env=env) is None


def test_load_returns_the_decoded_references_when_well_formed(tmp_path: Path) -> None:
    import json

    references = _genuine(tmp_path)
    payload = {
        "store_root": references.store_root,
        "project_id": references.project_id,
        "project_binding_id": references.project_binding_id,
        "github_projection_grant_refs": list(references.github_projection_grant_refs),
        "github_projection_grant_declaration_refs": list(
            references.github_projection_grant_declaration_refs
        ),
    }
    env = {V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: json.dumps(payload)}
    loaded = load_v3_live_write_authority_references(env=env)
    assert loaded == references


def test_load_default_env_source_is_os_environ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    references = _genuine(tmp_path)
    payload = {
        "store_root": references.store_root,
        "project_id": references.project_id,
        "project_binding_id": references.project_binding_id,
        "github_projection_grant_refs": list(references.github_projection_grant_refs),
        "github_projection_grant_declaration_refs": list(
            references.github_projection_grant_declaration_refs
        ),
    }
    monkeypatch.setenv(V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV, json.dumps(payload))
    assert load_v3_live_write_authority_references() == references


def test_open_store_returns_none_for_none_references() -> None:
    assert open_v3_live_write_store(None) is None


def test_open_store_returns_none_for_an_unreachable_root(tmp_path: Path) -> None:
    unreachable = V3LiveWriteAuthorityReferences(
        store_root=str(tmp_path / "does" / "not" / "exist" / "\x00invalid"),
        project_id="PRJ-X",
        project_binding_id="PB-X",
        github_projection_grant_refs=(),
        github_projection_grant_declaration_refs=(),
    )
    assert open_v3_live_write_store(unreachable) is None


def test_end_to_end_load_open_resolve_round_trips_through_json(tmp_path: Path) -> None:
    import json

    references = _genuine(tmp_path)
    payload = {
        "store_root": references.store_root,
        "project_id": references.project_id,
        "project_binding_id": references.project_binding_id,
        "github_projection_grant_refs": list(references.github_projection_grant_refs),
        "github_projection_grant_declaration_refs": list(
            references.github_projection_grant_declaration_refs
        ),
    }
    env = {V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: json.dumps(payload)}
    loaded = load_v3_live_write_authority_references(env=env)
    store = open_v3_live_write_store(loaded)
    assert store is not None
    context = resolve_v3_live_write_authority(store, _CONFIG, loaded)
    assert context is not None
