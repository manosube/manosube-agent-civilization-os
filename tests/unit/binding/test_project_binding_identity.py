"""Phase 9 (Issue #43) Project Binding identity: content-addressed, reverified."""

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
from manosube_agent_civilization.binding.errors import BindingIdentityError
from manosube_agent_civilization.binding.identity import (
    project_binding_id,
    verify_project_binding_identity,
)

BOUND_AT = "2026-09-06T09:00:00Z"


def _assembled() -> dict:
    return assemble_project_binding(
        project_id="PRJ-IDENTITY-0001",
        objective_revision_ref={
            "kind": "objective_revision",
            "id": objective_revision()["objective_revision_id"],
        },
        boundary=boundary(),
        authority_policy_ref=authority_policy_ref(),
        source_registrations=source_registrations(),
        command_policy=command_policy(),
        secret_exclusion_policy=secret_exclusion_policy(),
        human_authority_ref=human_authority_ref(),
        human_authority_signing_key=human_authority_signing_key(),
        bound_at=BOUND_AT,
        schema_root=SCHEMA_ROOT,
    )


def test_project_binding_id_is_deterministic_over_identical_semantic_fields() -> None:
    first = _assembled()
    second = _assembled()
    assert first["project_binding_id"] == second["project_binding_id"]


def test_project_binding_id_changes_when_any_semantic_field_changes() -> None:
    baseline = _assembled()
    changed = assemble_project_binding(
        project_id="PRJ-IDENTITY-0001",
        objective_revision_ref={
            "kind": "objective_revision",
            "id": objective_revision()["objective_revision_id"],
        },
        boundary=boundary(),
        authority_policy_ref=authority_policy_ref(),
        source_registrations=source_registrations(),
        command_policy={**command_policy(), "max_commands_per_change": 999},
        secret_exclusion_policy=secret_exclusion_policy(),
        human_authority_ref=human_authority_ref(),
        human_authority_signing_key=human_authority_signing_key(),
        bound_at=BOUND_AT,
        schema_root=SCHEMA_ROOT,
    )
    assert changed["project_binding_id"] != baseline["project_binding_id"]


def test_project_binding_id_excludes_bound_at_from_identity() -> None:
    """``bound_at`` is the instant a Binding was adopted, never part of what was adopted --
    two declarations differing only in ``bound_at`` share one identity, exactly as Reflow's
    own ``closure_evaluation_id`` excludes its later-stamped ``reflow_transition_ref``."""

    first = assemble_project_binding(
        project_id="PRJ-IDENTITY-0002",
        objective_revision_ref={
            "kind": "objective_revision",
            "id": objective_revision()["objective_revision_id"],
        },
        boundary=boundary(),
        authority_policy_ref=authority_policy_ref(),
        source_registrations=source_registrations(),
        command_policy=command_policy(),
        secret_exclusion_policy=secret_exclusion_policy(),
        human_authority_ref=human_authority_ref(),
        human_authority_signing_key=human_authority_signing_key(),
        bound_at="2026-09-06T09:00:00Z",
        schema_root=SCHEMA_ROOT,
    )
    second = assemble_project_binding(
        project_id="PRJ-IDENTITY-0002",
        objective_revision_ref={
            "kind": "objective_revision",
            "id": objective_revision()["objective_revision_id"],
        },
        boundary=boundary(),
        authority_policy_ref=authority_policy_ref(),
        source_registrations=source_registrations(),
        command_policy=command_policy(),
        secret_exclusion_policy=secret_exclusion_policy(),
        human_authority_ref=human_authority_ref(),
        human_authority_signing_key=human_authority_signing_key(),
        bound_at="2026-09-06T11:00:00Z",
        schema_root=SCHEMA_ROOT,
    )
    assert first["project_binding_id"] == second["project_binding_id"]
    assert first["bound_at"] != second["bound_at"]


def test_verify_project_binding_identity_accepts_a_self_consistent_record() -> None:
    record = _assembled()
    verify_project_binding_identity(record)  # must not raise


def test_verify_project_binding_identity_rejects_a_forged_id() -> None:
    """A record whose claimed ``project_binding_id`` does not reproduce from its own
    declared fields -- the same self-consistency check Reflow's own genesis lifecycle event
    admission already applies to a caller-supplied body -- is refused."""

    record = _assembled()
    record["project_binding_id"] = "PROJBIND-" + "0" * 64
    with pytest.raises(BindingIdentityError):
        verify_project_binding_identity(record)


def test_verify_project_binding_identity_rejects_a_body_mutated_after_minting() -> None:
    """Content-addressing means a same-id/different-body forgery is detectable purely by
    recomputation -- no Store round-trip required to prove it."""

    record = _assembled()
    tampered = deepcopy(record)
    tampered["command_policy"]["max_commands_per_change"] = 999
    with pytest.raises(BindingIdentityError):
        verify_project_binding_identity(tampered)


def test_project_binding_id_is_computable_directly_without_the_full_engine() -> None:
    record = _assembled()
    payload = {
        key: record[key]
        for key in (
            "schema_version",
            "project_id",
            "objective_revision_ref",
            "boundary",
            "authority_policy_ref",
            "source_registrations",
            "command_policy",
            "secret_exclusion_policy",
            "human_authority_ref",
            "human_authority_signing_key",
        )
    }
    assert project_binding_id(payload) == record["project_binding_id"]
