"""Structural Review Round 5 (P13-R5, canonical Human Grant Declaration anchor).

A ``verifier_selection_grant`` that genuinely resolves against a Store record (Round 4,
P13-R4) is still not, by itself, proof that a Human declared it -- any Store-write-capable
caller could commit a self-hashed grant. This suite proves the Binding owner's own new
public route, ``declare_human_grant``, and its pure assembler, ``assemble_human_grant_
declaration``: schema conformance, content-addressed identity (forgery detection), and the
route's own required re-resolution of the real Project Binding and the real grant from the
Store -- a caller can never substitute either.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from tests.fixtures.product_binding import PROJECT_ID, bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import verifier_selection_grant_id
from manosube_agent_civilization.binding import (
    BindingValidationError,
    assemble_human_grant_declaration,
    bind_project,
    declare_human_grant,
    human_grant_declaration_id,
    verify_human_grant_declaration_identity,
)
from manosube_agent_civilization.binding.errors import BindingIdentityError
from manosube_agent_civilization.binding.validation import (
    BINDING_SCHEMA_BASE,
    _validators,
    validate_record,
)
from manosube_agent_civilization.store import FileStateStore

_DECLARED_AT = "2026-09-07T13:00:00Z"
_PROJECT_BINDING_ID = "PROJBIND-" + "0" * 64
_HUMAN = {"kind": "human_authority", "id": "AUTH-BIND-0001"}
_GRANT_REF = {"kind": "verifier_selection_grant", "id": "VSEL-GRANT-" + "0" * 64}


def _assembled(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "project_id": PROJECT_ID,
        "project_binding_id": _PROJECT_BINDING_ID,
        "grant_ref": dict(_GRANT_REF),
        "declared_by": dict(_HUMAN),
        "status": "ACTIVE",
        "declared_at": _DECLARED_AT,
        "schema_root": SCHEMA_ROOT,
    }
    fields.update(overrides)
    return assemble_human_grant_declaration(**fields)


# --- schema registration and positive control -------------------------------------------- #


def test_the_human_grant_declaration_schema_registers_with_a_stable_id() -> None:
    validators = _validators(SCHEMA_ROOT)
    assert BINDING_SCHEMA_BASE + "human_grant_declaration.schema.json" in validators


def test_a_real_assembled_declaration_validates_against_its_own_schema() -> None:
    record = _assembled()
    validate_record(record, "human_grant_declaration.schema.json", schema_root=SCHEMA_ROOT)
    assert record["human_grant_declaration_id"].startswith("HGD-")
    assert record["schema_version"] == "0.1"
    assert record["grant_ref"] == _GRANT_REF
    assert record["declared_by"] == _HUMAN


# --- required-field / unknown-field negative controls -------------------------------------- #


@pytest.mark.parametrize(
    "field",
    ["project_id", "project_binding_id", "grant_ref", "declared_by", "status", "declared_at"],
)
def test_a_missing_required_field_is_schema_refused(field: str) -> None:
    record = _assembled()
    del record[field]
    with pytest.raises(BindingValidationError):
        validate_record(record, "human_grant_declaration.schema.json", schema_root=SCHEMA_ROOT)


def test_an_unknown_field_is_schema_refused() -> None:
    record = _assembled()
    record["approved_by_review_comment"] = True
    with pytest.raises(BindingValidationError):
        validate_record(record, "human_grant_declaration.schema.json", schema_root=SCHEMA_ROOT)


def test_declared_by_must_be_a_human_authority_reference() -> None:
    with pytest.raises(BindingValidationError, match="Human Authority reference"):
        _assembled(declared_by={"kind": "agent", "id": "AGENT-0001"})


def test_grant_ref_must_name_a_verifier_selection_grant() -> None:
    with pytest.raises(BindingValidationError, match="verifier_selection_grant reference"):
        _assembled(grant_ref={"kind": "observation_evidence", "id": "EVID-0001"})


@pytest.mark.parametrize("status", ["PENDING", "EXPIRED", "", None])
def test_an_unrecognized_status_is_refused(status: Any) -> None:
    with pytest.raises(BindingValidationError, match="status"):
        _assembled(status=status)


@pytest.mark.parametrize("status", ["ACTIVE", "REVOKED"])
def test_the_two_canonical_statuses_are_both_accepted(status: str) -> None:
    record = _assembled(status=status)
    assert record["status"] == status
    validate_record(record, "human_grant_declaration.schema.json", schema_root=SCHEMA_ROOT)


# --- content-addressed identity: determinism, exclusions, and forgery detection ------------ #


def test_the_id_is_deterministic_and_declared_at_is_excluded() -> None:
    first = _assembled(declared_at="2026-09-07T13:00:00Z")
    second = _assembled(declared_at="2099-01-01T00:00:00Z")
    assert first["human_grant_declaration_id"] == second["human_grant_declaration_id"]


@pytest.mark.parametrize(
    "override",
    [
        {"project_id": "OTHER-PROJECT"},
        {"grant_ref": {"kind": "verifier_selection_grant", "id": "VSEL-GRANT-" + "1" * 64}},
        {"declared_by": {"kind": "human_authority", "id": "AUTH-OTHER"}},
        {"status": "REVOKED"},
    ],
)
def test_every_semantic_field_participates_in_the_id(override: dict[str, Any]) -> None:
    baseline = _assembled()
    changed = _assembled(**override)
    assert baseline["human_grant_declaration_id"] != changed["human_grant_declaration_id"]


def test_a_record_edited_after_its_identity_was_computed_fails_reverification() -> None:
    forged = _assembled()
    forged["status"] = "REVOKED"  # payload changed, identity left behind
    with pytest.raises(BindingIdentityError, match="does not reproduce"):
        verify_human_grant_declaration_identity(forged)


def test_human_grant_declaration_id_is_a_pure_function_of_the_adopted_payload() -> None:
    record = _assembled()
    recomputed = human_grant_declaration_id(record)
    assert recomputed == record["human_grant_declaration_id"]


# --- declare_human_grant: the real Binding route, over a real Store ----------------------- #


class _RealRoute:
    """A real bound Project plus one real, Store-committed ``verifier_selection_grant`` --
    everything ``declare_human_grant`` needs to independently re-resolve both, never trusting
    an in-memory copy a caller supplies."""

    def __init__(self, tmp_path: Any) -> None:
        store_root = tmp_path / "backend"
        self.store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
        kwargs = bind_project_kwargs()
        result = bind_project(
            self.store,
            **kwargs,
            additional_genesis_records=genesis_records(),
            schema_root=SCHEMA_ROOT,
        )
        self.project_id = kwargs["project_id"]
        self.project_binding_id = result["project_binding_id"]
        self.human_authority_ref = kwargs["human_authority_ref"]
        genesis_state = result["committed_state"]

        grant: dict[str, Any] = {
            "schema_version": "0.1",
            "verifier_selection_grant_id": "",
            "project_id": self.project_id,
            "requirement_id": "VREQ-0001",
            "selection_id": "VSEL-0001",
            "verifier_identity": {"kind": "deterministic_test_runner", "id": "VERIFIER-0001"},
            "permitted_boundary": {"scope": "repository", "boundary_id": "VB-0001"},
            "status": "ACTIVE",
            "granted_by": dict(self.human_authority_ref),
        }
        grant["verifier_selection_grant_id"] = verifier_selection_grant_id(grant)
        self.grant = grant
        self.grant_ref = {
            "kind": "verifier_selection_grant",
            "id": grant["verifier_selection_grant_id"],
        }

        successor = deepcopy(genesis_state)
        successor["state_revision"] = genesis_state["state_revision"] + 1
        successor["previous_state_fingerprint"] = genesis_state["semantic_fingerprint"]
        successor["lineage_head_ref"] = {
            "kind": "state_transition",
            "id": "TX-HUMAN-GRANT-DECLARATION-TEST-0001",
        }
        from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

        successor["semantic_fingerprint"] = fingerprint_project_state(
            successor, schema_root=SCHEMA_ROOT
        ).as_dict()
        event = {
            "schema_version": "0.1",
            "transaction_id": "TX-HUMAN-GRANT-DECLARATION-TEST-0001",
            "event_type": "TRANSITION",
            "project_id": self.project_id,
            "from_revision": genesis_state["state_revision"],
            "to_revision": successor["state_revision"],
            "before_fingerprint": genesis_state["semantic_fingerprint"],
            "after_fingerprint": successor["semantic_fingerprint"],
            "after_state": successor,
            "evidence_refs": [],
            "committed_at": _DECLARED_AT,
        }
        self.store.commit(
            self.project_id,
            genesis_state["state_revision"],
            genesis_state["semantic_fingerprint"],
            successor,
            event,
            records=[
                ("verifier_selection_grant", grant["verifier_selection_grant_id"], grant),
            ],
        )


@pytest.fixture()
def real_route(tmp_path: Any) -> _RealRoute:
    return _RealRoute(tmp_path)


def test_declare_human_grant_commits_a_real_resolvable_declaration(real_route: _RealRoute) -> None:
    result = declare_human_grant(
        real_route.store,
        project_id=real_route.project_id,
        project_binding_id=real_route.project_binding_id,
        grant_ref=real_route.grant_ref,
        status="ACTIVE",
        declared_at=_DECLARED_AT,
        schema_root=SCHEMA_ROOT,
    )
    declaration = result["human_grant_declaration"]
    declaration_id = result["human_grant_declaration_id"]

    assert declaration["human_grant_declaration_id"] == declaration_id
    assert declaration["project_id"] == real_route.project_id
    assert declaration["project_binding_id"] == real_route.project_binding_id
    assert declaration["grant_ref"] == real_route.grant_ref
    assert declaration["status"] == "ACTIVE"

    resolved = real_route.store.resolve_record(
        real_route.project_id, "human_grant_declaration", declaration_id
    )
    assert resolved == declaration


def test_declare_human_grant_derives_declared_by_from_the_real_project_binding(
    real_route: _RealRoute,
) -> None:
    """``declare_human_grant`` takes no ``declared_by`` argument at all -- the returned
    declaration's own ``declared_by`` is always the real, Store-resolved Project Binding's
    ``human_authority_ref``, never a caller-suppliable value."""

    result = declare_human_grant(
        real_route.store,
        project_id=real_route.project_id,
        project_binding_id=real_route.project_binding_id,
        grant_ref=real_route.grant_ref,
        status="ACTIVE",
        declared_at=_DECLARED_AT,
        schema_root=SCHEMA_ROOT,
    )
    assert result["human_grant_declaration"]["declared_by"] == real_route.human_authority_ref


def test_declare_human_grant_rejects_an_unresolvable_project_binding_id(
    real_route: _RealRoute,
) -> None:
    with pytest.raises(BindingValidationError, match="project_binding does not resolve"):
        declare_human_grant(
            real_route.store,
            project_id=real_route.project_id,
            project_binding_id="PROJBIND-" + "F" * 64,
            grant_ref=real_route.grant_ref,
            status="ACTIVE",
            declared_at=_DECLARED_AT,
            schema_root=SCHEMA_ROOT,
        )


def test_declare_human_grant_rejects_an_unresolvable_grant(real_route: _RealRoute) -> None:
    never_committed = {"kind": "verifier_selection_grant", "id": "VSEL-GRANT-" + "F" * 64}
    with pytest.raises(BindingValidationError, match="does not resolve"):
        declare_human_grant(
            real_route.store,
            project_id=real_route.project_id,
            project_binding_id=real_route.project_binding_id,
            grant_ref=never_committed,
            status="ACTIVE",
            declared_at=_DECLARED_AT,
            schema_root=SCHEMA_ROOT,
        )


def test_declare_human_grant_rejects_a_wrong_kind_grant_ref(real_route: _RealRoute) -> None:
    wrong_kind = {
        "kind": "observation_evidence",
        "id": real_route.grant["verifier_selection_grant_id"],
    }
    with pytest.raises(BindingValidationError, match="does not name a verifier_selection_grant"):
        declare_human_grant(
            real_route.store,
            project_id=real_route.project_id,
            project_binding_id=real_route.project_binding_id,
            grant_ref=wrong_kind,
            status="ACTIVE",
            declared_at=_DECLARED_AT,
            schema_root=SCHEMA_ROOT,
        )


def test_declare_human_grant_can_commit_distinct_active_and_revoked_declarations(
    real_route: _RealRoute,
) -> None:
    """Two declarations differing only in ``status`` (``declared_at`` excluded from identity)
    are two distinct, independently resolvable records -- explicit revocation is a new
    declaration, never a mutation of the genuine one."""

    active = declare_human_grant(
        real_route.store,
        project_id=real_route.project_id,
        project_binding_id=real_route.project_binding_id,
        grant_ref=real_route.grant_ref,
        status="ACTIVE",
        declared_at=_DECLARED_AT,
        schema_root=SCHEMA_ROOT,
    )["human_grant_declaration"]
    revoked = declare_human_grant(
        real_route.store,
        project_id=real_route.project_id,
        project_binding_id=real_route.project_binding_id,
        grant_ref=real_route.grant_ref,
        status="REVOKED",
        declared_at=_DECLARED_AT,
        schema_root=SCHEMA_ROOT,
    )["human_grant_declaration"]

    assert active["human_grant_declaration_id"] != revoked["human_grant_declaration_id"]
    assert (
        real_route.store.resolve_record(
            real_route.project_id,
            "human_grant_declaration",
            active["human_grant_declaration_id"],
        )
        == active
    )
    assert (
        real_route.store.resolve_record(
            real_route.project_id,
            "human_grant_declaration",
            revoked["human_grant_declaration_id"],
        )
        == revoked
    )
