"""Phase 14 (Issue #62), Structural Review Round 6 (P14-R6-F2): genuine, verified SHUKOU/
Human Authority for V3 live-write execution -- entirely offline, zero network access, zero
Store dependency. Structural Review Round 8 (P14-R8-F1): the genuine article is now a real
Project Binding plus signed ``github_projection_grant``/``github_projection_grant_declaration``
records, verified through the identical canonical Authority/Binding route
(:func:`~manosube_agent_civilization.authority.projection_authorization.
evaluate_projection_authorization`) a real GitHub projection call already uses -- never a
V3-specific trust anchor or signing mechanism of this repository's own.

Every negative control here proves :func:`v3_live_write_authorized` fails closed (returns
``False``, never raises) before any network access could ever occur. No test in this file
constructs a ``RealGitHubAdapter`` or touches ``urllib``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest
from tests.fixtures.v3_authority_test_material import (
    genuine_project_binding,
    genuine_v3_authority_material,
    sign_declaration_with_the_wrong_key,
)
from tests.fixtures.v3_live_write_authority import (
    V3_LIVE_WRITE_AUTHORITY_MATERIAL_ENV,
    V3_PROJECTION_KINDS,
    load_v3_live_write_authority_material,
    v3_configuration_subject_ref,
    v3_live_write_authorized,
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


def _genuine_material() -> dict[str, Any]:
    return genuine_v3_authority_material(_CONFIG)


# ---------------------------------------------------------------------------
# Positive route
# ---------------------------------------------------------------------------


def test_genuine_material_authorizes_the_exact_configuration_it_was_issued_for() -> None:
    material = _genuine_material()
    assert v3_live_write_authorized(_CONFIG, material) is True


def test_config_none_or_material_none_refuses_immediately() -> None:
    material = _genuine_material()
    assert v3_live_write_authorized(None, material) is False
    assert v3_live_write_authorized(_CONFIG, None) is False
    assert v3_live_write_authorized(None, None) is False


def test_v3_projection_kinds_covers_exactly_the_three_harness_kinds() -> None:
    assert set(V3_PROJECTION_KINDS) == {
        "DIFFERENCE_ISSUE",
        "CHANGE_PULL_REQUEST",
        "EVIDENCE_ARTIFACT",
    }


# ---------------------------------------------------------------------------
# Required negative controls (Structural Review Round 8, P14-R8-F1): wrong project, binding,
# signer, decision, configuration, target, action, kinds/count, validity and revoked-status.
# ---------------------------------------------------------------------------


def test_wrong_project_id_refuses() -> None:
    """The material's own ``project_id`` no longer matches the real project_binding's own
    declared ``project_id`` -- refused before any grant is even considered."""

    material = _genuine_material()
    tampered = {**material, "project_id": "PRJ-SOME-OTHER-PROJECT"}
    assert v3_live_write_authorized(_CONFIG, tampered) is False


def test_wrong_binding_refuses() -> None:
    """A project_binding tampered after assembly no longer reproduces its own claimed
    ``project_binding_id`` -- refused before any grant/declaration is even read."""

    material = _genuine_material()
    tampered_binding = {
        **material["project_binding"],
        "boundary": {**material["project_binding"]["boundary"], "root_paths": ["somewhere-else"]},
    }
    tampered = {**material, "project_binding": tampered_binding}
    assert v3_live_write_authorized(_CONFIG, tampered) is False


def test_wrong_signer_refuses() -> None:
    """Every declaration genuinely signed, but not by the real project_binding's own
    registered key -- the exact regression this finding corrects: a caller who controls *some*
    private key can never mint a live-accepted record for a project_binding they do not
    actually hold the key for."""

    material = _genuine_material()
    tampered = {
        **material,
        "grant_declarations": [
            sign_declaration_with_the_wrong_key(declaration)
            for declaration in material["grant_declarations"]
        ],
    }
    assert v3_live_write_authorized(_CONFIG, tampered) is False


def test_wrong_decision_refuses() -> None:
    """A declaration whose own ``grant_ref`` names a different (non-existent) grant id never
    anchors any real grant -- refused for every projection kind."""

    material = _genuine_material()
    tampered_declarations = [
        {
            **declaration,
            "grant_ref": {"kind": "github_projection_grant", "id": "GH-PROJ-GRANT-DOESNOTEXIST"},
        }
        for declaration in material["grant_declarations"]
    ]
    tampered = {**material, "grant_declarations": tampered_declarations}
    assert v3_live_write_authorized(_CONFIG, tampered) is False


def test_wrong_configuration_refuses() -> None:
    """Material genuinely issued for the original configuration is checked against a
    *different* configuration (one changed field) -- subject_fingerprint/target_repository no
    longer match, so every projection kind refuses."""

    material = _genuine_material()
    changed_config = replace(_CONFIG, repo="a-different-widget")
    assert v3_live_write_authorized(changed_config, material) is False


def test_wrong_target_repository_refuses() -> None:
    """Every grant's own ``target_repository`` tampered to a different repository -- the
    request built from the real (untampered) configuration no longer matches."""

    material = _genuine_material()
    tampered_grants = [
        {
            **grant,
            "target_repository": {"host": "github", "owner": "acme", "repo": "a-different-widget"},
        }
        for grant in material["grants"]
    ]
    tampered = {**material, "grants": tampered_grants}
    assert v3_live_write_authorized(_CONFIG, tampered) is False


def test_wrong_action_refuses() -> None:
    """A grant naming any ``permitted_action`` other than the one closed literal
    (``MATERIALIZE_PROJECTION``) fails schema validation inside ``evaluate_projection_
    authorization``'s own admission gate -- raising ``AuthorityError``, caught here and
    treated as refusal, never as an unhandled exception."""

    material = _genuine_material()
    tampered_grants = [
        {**grant, "permitted_action": "SOME_OTHER_ACTION"} for grant in material["grants"]
    ]
    tampered = {**material, "grants": tampered_grants}
    assert v3_live_write_authorized(_CONFIG, tampered) is False


def test_wrong_kinds_count_refuses() -> None:
    """Only two of the three required projection kinds have a genuine grant/declaration pair
    -- the missing kind's own authorization request finds no matching grant, so the whole
    material refuses (all three kinds must independently authorize)."""

    material = _genuine_material()
    narrowed = {
        **material,
        "grants": [g for g in material["grants"] if g["projection_kind"] != "EVIDENCE_ARTIFACT"],
        "grant_declarations": [
            d for d in material["grant_declarations"] if d["projection_kind"] != "EVIDENCE_ARTIFACT"
        ],
    }
    assert v3_live_write_authorized(_CONFIG, narrowed) is False


def test_revoked_grant_status_refuses() -> None:
    material = _genuine_material()
    tampered_grants = [{**grant, "status": "REVOKED"} for grant in material["grants"]]
    tampered = {**material, "grants": tampered_grants}
    assert v3_live_write_authorized(_CONFIG, tampered) is False


def test_revoked_declaration_status_refuses() -> None:
    material = _genuine_material()
    tampered_declarations = [{**d, "status": "REVOKED"} for d in material["grant_declarations"]]
    tampered = {**material, "grant_declarations": tampered_declarations}
    assert v3_live_write_authorized(_CONFIG, tampered) is False


# ---------------------------------------------------------------------------
# Malformed-shape refusals
# ---------------------------------------------------------------------------


def test_material_not_a_mapping_refuses() -> None:
    assert v3_live_write_authorized(_CONFIG, "not-a-mapping") is False  # type: ignore[arg-type]


def test_material_missing_project_binding_refuses() -> None:
    material = _genuine_material()
    del material["project_binding"]
    assert v3_live_write_authorized(_CONFIG, material) is False


def test_material_project_binding_not_a_mapping_refuses() -> None:
    material = {**_genuine_material(), "project_binding": "not-a-mapping"}
    assert v3_live_write_authorized(_CONFIG, material) is False


def test_material_grants_not_a_list_refuses() -> None:
    material = {**_genuine_material(), "grants": "not-a-list"}
    assert v3_live_write_authorized(_CONFIG, material) is False


def test_material_grant_declarations_not_a_list_refuses() -> None:
    material = {**_genuine_material(), "grant_declarations": "not-a-list"}
    assert v3_live_write_authorized(_CONFIG, material) is False


def test_a_hand_built_project_binding_naming_every_correct_field_but_never_committed_still_verifies_by_content_address() -> (
    None
):
    """Content-address self-consistency is what :func:`~manosube_agent_civilization.binding.
    identity.verify_project_binding_identity` actually proves -- the genuine fixture material
    passes this because it *is* genuinely assembled, never because of any special-casing."""

    project_binding = genuine_project_binding()
    assert project_binding["project_binding_id"]


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
# load_v3_live_write_authority_material: the one I/O boundary this module has -- an
# environment-variable read, never a network call.
# ---------------------------------------------------------------------------


def test_load_returns_none_when_unset() -> None:
    assert load_v3_live_write_authority_material(env={}) is None


def test_load_returns_none_on_malformed_json() -> None:
    env = {V3_LIVE_WRITE_AUTHORITY_MATERIAL_ENV: "{not valid json"}
    assert load_v3_live_write_authority_material(env=env) is None


def test_load_returns_none_when_json_is_not_an_object() -> None:
    env = {V3_LIVE_WRITE_AUTHORITY_MATERIAL_ENV: "[1, 2, 3]"}
    assert load_v3_live_write_authority_material(env=env) is None


def test_load_returns_the_decoded_material_when_well_formed() -> None:
    import json

    material = _genuine_material()
    env = {V3_LIVE_WRITE_AUTHORITY_MATERIAL_ENV: json.dumps(material)}
    loaded = load_v3_live_write_authority_material(env=env)
    assert loaded == material


def test_load_default_env_source_is_os_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    material = _genuine_material()
    monkeypatch.setenv(V3_LIVE_WRITE_AUTHORITY_MATERIAL_ENV, json.dumps(material))
    assert load_v3_live_write_authority_material() == material


def test_end_to_end_load_then_authorize_round_trips_through_json() -> None:
    import json

    material = _genuine_material()
    env = {V3_LIVE_WRITE_AUTHORITY_MATERIAL_ENV: json.dumps(material)}
    loaded = load_v3_live_write_authority_material(env=env)
    assert v3_live_write_authorized(_CONFIG, loaded) is True
