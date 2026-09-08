"""Phase 9 (Issue #43) Product Binding engine: cross-field structural checks the schema
layer alone cannot express (boundary escape, duplicate/conflicting registrations, the
secret/moving-reference scan) -- ``assemble_project_binding`` exercised directly, the same
level ``tests/unit/reflow/`` already exercises its own engine at."""

from __future__ import annotations

from copy import deepcopy

import pytest
from tests.fixtures.product_binding import (
    authority_policy_ref,
    boundary,
    command_policy,
    human_authority_ref,
    human_authority_signing_key,
    objective_revision,
    secret_exclusion_policy,
    source_registrations,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding.engine import assemble_project_binding
from manosube_agent_civilization.binding.errors import BindingValidationError
from manosube_agent_civilization.difference.errors import SecurityRejectionError

BOUND_AT = "2026-09-06T09:00:00Z"


def _kwargs(**overrides: object) -> dict:
    base = {
        "project_id": "PRJ-ENGINE-0001",
        "objective_revision_ref": {
            "kind": "objective_revision",
            "id": objective_revision()["objective_revision_id"],
        },
        "boundary": boundary(),
        "authority_policy_ref": authority_policy_ref(),
        "source_registrations": source_registrations(),
        "command_policy": command_policy(),
        "secret_exclusion_policy": secret_exclusion_policy(),
        "human_authority_ref": human_authority_ref(),
        "human_authority_signing_key": human_authority_signing_key(),
        "bound_at": BOUND_AT,
        "schema_root": SCHEMA_ROOT,
    }
    base.update(overrides)
    return base


def test_a_real_declaration_assembles_cleanly() -> None:
    record = assemble_project_binding(**_kwargs())
    assert record["project_binding_id"].startswith("PROJBIND-")


# --- boundary escape ---------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "unsafe_root",
    [
        "/etc/passwd",
        "~/secrets",
        "C:\\Windows",
        "\\\\server\\share",
        "../escape",
        "repo/../../escape",
    ],
)
def test_boundary_root_path_escape_is_rejected(unsafe_root: str) -> None:
    unsafe_boundary = {**boundary(), "root_paths": [unsafe_root]}
    with pytest.raises(BindingValidationError, match="not permitted"):
        assemble_project_binding(**_kwargs(boundary=unsafe_boundary))


def test_boundary_conflicting_include_and_exclude_pattern_is_rejected() -> None:
    conflicting = {**boundary(), "include_patterns": ["*.py"], "exclude_patterns": ["*.py"]}
    with pytest.raises(BindingValidationError, match="conflicting"):
        assemble_project_binding(**_kwargs(boundary=conflicting))


# --- source registration -------------------------------------------------------------------- #


def test_source_registration_locator_outside_the_boundary_is_rejected() -> None:
    outside = deepcopy(source_registrations())
    outside[0]["locator"] = "somewhere/else"
    with pytest.raises(BindingValidationError, match="outside the declared boundary"):
        assemble_project_binding(**_kwargs(source_registrations=outside))


def test_source_registration_locator_boundary_match_is_by_path_segment_not_string_prefix() -> None:
    """``repo-other/src`` must not be accepted merely because it shares the string prefix
    ``repo`` with a declared root -- only a real path-segment match counts."""

    narrow_boundary = {**boundary(), "root_paths": ["repo"]}
    lookalike = deepcopy(source_registrations())
    lookalike[0]["locator"] = "repo-other/src"
    with pytest.raises(BindingValidationError, match="outside the declared boundary"):
        assemble_project_binding(
            **_kwargs(boundary=narrow_boundary, source_registrations=lookalike)
        )


@pytest.mark.parametrize(
    "unsafe_locator",
    ["/etc/passwd", "~/secrets", "repo/../../escape"],
)
def test_source_registration_locator_escape_is_rejected(unsafe_locator: str) -> None:
    unsafe = deepcopy(source_registrations())
    unsafe[0]["locator"] = unsafe_locator
    with pytest.raises(BindingValidationError, match="not permitted"):
        assemble_project_binding(**_kwargs(source_registrations=unsafe))


def test_duplicate_source_id_is_rejected() -> None:
    duplicated = source_registrations() + deepcopy(source_registrations())
    with pytest.raises(BindingValidationError, match="duplicate source_registration source_id"):
        assemble_project_binding(**_kwargs(source_registrations=duplicated))


def test_duplicate_source_type_and_locator_pair_under_a_different_id_is_rejected() -> None:
    original = source_registrations()
    same_pair_different_id = deepcopy(original)
    same_pair_different_id[0]["source_id"] = "SRC-BIND-0002"
    with pytest.raises(
        BindingValidationError, match="duplicate source_registration \\(source_type, locator\\)"
    ):
        assemble_project_binding(**_kwargs(source_registrations=original + same_pair_different_id))


def test_source_registration_own_conflicting_include_exclude_is_rejected() -> None:
    conflicting = deepcopy(source_registrations())
    conflicting[0]["include_patterns"] = ["*.py"]
    conflicting[0]["exclude_patterns"] = ["*.py"]
    with pytest.raises(BindingValidationError, match="conflicting"):
        assemble_project_binding(**_kwargs(source_registrations=conflicting))


# --- secret / moving-reference scan --------------------------------------------------------- #


def test_a_recognizable_secret_value_anywhere_in_the_declaration_is_rejected() -> None:
    leaking_boundary = {**boundary(), "exclude_patterns": ["ghp_" + "a" * 30]}
    with pytest.raises(SecurityRejectionError, match="secret-bearing value"):
        assemble_project_binding(**_kwargs(boundary=leaking_boundary))


def test_secret_exclusion_policy_itself_is_never_flagged_by_the_secret_key_scan() -> None:
    """The subtree's own field names (``allowed_secret_reference_kinds``, ...) legitimately
    name the concept they forbid -- this must not itself trip the repo-wide secret-*key*-
    name scan. A regression here would make every real declaration unusable."""

    record = assemble_project_binding(**_kwargs())
    assert record["secret_exclusion_policy"] == secret_exclusion_policy()


def test_a_moving_reference_id_anywhere_in_the_declaration_is_rejected() -> None:
    moving_ref = {"kind": "authority_rule", "id": "HEAD"}
    with pytest.raises(SecurityRejectionError):
        assemble_project_binding(**_kwargs(authority_policy_ref=moving_ref))
