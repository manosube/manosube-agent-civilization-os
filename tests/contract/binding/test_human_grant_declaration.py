"""Structural Review Round 5 (P13-R5, canonical Human Grant Declaration anchor), superseded
in shape by Structural Review Round 5-R1 (Issue #51, P13-R5-R1,
``ADOPT_P13_R5_R1_SIGNED_HUMAN_DECLARATION_AND_SINGLE_COMMITTER``).

A ``verifier_selection_grant`` that genuinely resolves against a Store record (Round 4,
P13-R4) is still not, by itself, proof that a Human declared it -- any Store-write-capable
caller could commit a self-hashed grant. Round 5's own answer (a declaration whose
``grant_ref`` merely names the grant by content address) closed that gap only partially: a
Store-write-capable caller could still commit a self-consistent declaration with no Human
signature at all. R5-R1 requires the declaration to carry a real Ed25519 signature, verified
against the real Project Binding's own ``human_authority_signing_key``, over a payload that
directly restates the grant's own ``requirement_id``/``selection_id``/``verifier_identity``/
``permitted_boundary`` rather than binding them only through ``grant_ref``'s content address.

This suite proves the Binding owner's own public route, ``declare_human_grant``, and its pure
assembler, ``assemble_human_grant_declaration``: schema conformance, content-addressed
identity (forgery detection), signature verification (unsigned/forged/wrong-key/tampered-
payload all refused), and the route's own required re-resolution of the real Project Binding
and the real grant from the Store -- a caller can never substitute either.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest
from tests.fixtures.product_binding import (
    PROJECT_ID,
    bind_project_kwargs,
    genesis_records,
    human_authority_signing_key,
    sign_human_grant_declaration,
)
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
_REQUIREMENT_ID = "VREQ-0001"
_SELECTION_ID = "VSEL-0001"
_VERIFIER_IDENTITY = {"kind": "deterministic_test_runner", "id": "VERIFIER-0001"}
_BOUNDARY = {"scope": "repository", "boundary_id": "VB-0001"}
_SIGNING_KEY = human_authority_signing_key()


def _fields(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "project_id": PROJECT_ID,
        "project_binding_id": _PROJECT_BINDING_ID,
        "grant_ref": dict(_GRANT_REF),
        "declared_by": dict(_HUMAN),
        "requirement_id": _REQUIREMENT_ID,
        "selection_id": _SELECTION_ID,
        "verifier_identity": dict(_VERIFIER_IDENTITY),
        "permitted_boundary": dict(_BOUNDARY),
        "status": "ACTIVE",
        "declared_at": _DECLARED_AT,
    }
    fields.update(overrides)
    return fields


def _assembled(
    *,
    signing_key: dict[str, Any] | None = None,
    signature: dict[str, Any] | None = None,
    signed_fields: dict[str, Any] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Assemble one real declaration. *signed_fields*, when given, is the field set the
    *signature* is actually computed over -- distinct from the assembled record's own fields,
    so a caller can construct a signature that does not cover what it is attached to (the
    exact "signature computed over different content" class of forgery)."""

    fields = _fields(**overrides)
    if signature is None:
        signature = sign_human_grant_declaration(**(signed_fields or fields))
    key = _SIGNING_KEY if signing_key is None else signing_key
    return assemble_human_grant_declaration(
        **fields,
        signature=signature,
        signing_key=key,
        schema_root=SCHEMA_ROOT,
    )


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
    assert record["requirement_id"] == _REQUIREMENT_ID
    assert record["selection_id"] == _SELECTION_ID
    assert record["verifier_identity"] == _VERIFIER_IDENTITY
    assert record["permitted_boundary"] == _BOUNDARY
    assert record["signature"]["algorithm"] == "ed25519"


# --- required-field / unknown-field negative controls -------------------------------------- #


@pytest.mark.parametrize(
    "field",
    [
        "project_id",
        "project_binding_id",
        "grant_ref",
        "declared_by",
        "requirement_id",
        "selection_id",
        "verifier_identity",
        "permitted_boundary",
        "status",
        "declared_at",
        "signature",
    ],
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


def test_the_id_is_deterministic_for_the_identical_declared_at() -> None:
    first = _assembled(declared_at="2026-09-07T13:00:00Z")
    second = _assembled(declared_at="2026-09-07T13:00:00Z")
    assert first["human_grant_declaration_id"] == second["human_grant_declaration_id"]


def test_declared_at_now_participates_in_the_id_r5_r1() -> None:
    """R5-R1 supersedes Round 5's own ``bound_at``-modeled exclusion: the signature must
    bind *when* a Human declared, or a signature would validate identically at any later
    replay instant -- so ``declared_at`` is no longer excluded from the identity payload."""

    first = _assembled(declared_at="2026-09-07T13:00:00Z")
    second = _assembled(declared_at="2099-01-01T00:00:00Z")
    assert first["human_grant_declaration_id"] != second["human_grant_declaration_id"]


@pytest.mark.parametrize(
    "override",
    [
        {"project_id": "OTHER-PROJECT"},
        {"grant_ref": {"kind": "verifier_selection_grant", "id": "VSEL-GRANT-" + "1" * 64}},
        {"declared_by": {"kind": "human_authority", "id": "AUTH-OTHER"}},
        {"requirement_id": "VREQ-OTHER"},
        {"selection_id": "VSEL-OTHER"},
        {"verifier_identity": {"kind": "deterministic_test_runner", "id": "OTHER-VERIFIER"}},
        {"permitted_boundary": {"scope": "repository", "boundary_id": "VB-OTHER"}},
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


# --- signature verification: the R5-R1 anchor itself ---------------------------------------- #


def test_an_unsigned_declaration_is_refused() -> None:
    with pytest.raises(BindingValidationError):
        _assembled(signature={})


def test_a_declaration_with_no_signature_value_is_refused() -> None:
    signature = sign_human_grant_declaration(**_fields())
    del signature["value"]
    with pytest.raises(BindingValidationError):
        _assembled(signature=signature)


def test_a_forged_signature_value_is_refused() -> None:
    signature = sign_human_grant_declaration(**_fields())
    genuine = bytearray.fromhex(signature["value"])
    genuine[0] ^= 0xFF
    signature["value"] = bytes(genuine).hex()
    with pytest.raises(BindingValidationError, match="signature does not verify"):
        _assembled(signature=signature)


def test_a_signature_signed_by_a_different_key_is_refused() -> None:
    """Wrong Binding -- a genuine Ed25519 signature, but over a *different* private key from
    the one the real Project Binding's own ``human_authority_signing_key`` actually names."""

    impostor_private_key = Ed25519PrivateKey.from_private_bytes(b"\x01" * 32)
    from manosube_agent_civilization.binding.identity import (
        human_grant_declaration_signing_payload,
    )

    fields = _fields()
    payload_record = {
        "schema_version": "0.1",
        "project_id": fields["project_id"],
        "project_binding_id": fields["project_binding_id"],
        "grant_ref": fields["grant_ref"],
        "declared_by": fields["declared_by"],
        "requirement_id": fields["requirement_id"],
        "selection_id": fields["selection_id"],
        "verifier_identity": fields["verifier_identity"],
        "permitted_boundary": fields["permitted_boundary"],
        "status": fields["status"],
        "declared_at": fields["declared_at"],
    }
    message = human_grant_declaration_signing_payload(payload_record)
    signature = {
        "algorithm": "ed25519",
        "key_id": _SIGNING_KEY["key_id"],
        "value": impostor_private_key.sign(message).hex(),
    }
    with pytest.raises(BindingValidationError, match="signature does not verify"):
        _assembled(signature=signature)


def test_a_wrong_public_key_never_verifies_a_genuine_signature() -> None:
    """Wrong key -- the real signature, checked against a structurally well-formed but wrong
    ``human_authority_signing_key`` (a different Ed25519 public key)."""

    other_private_key = Ed25519PrivateKey.from_private_bytes(b"\x02" * 32)
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    wrong_signing_key = {
        "algorithm": "ed25519",
        "key_id": _SIGNING_KEY["key_id"],
        "public_key": other_private_key.public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
        .hex(),
    }
    with pytest.raises(BindingValidationError, match="signature does not verify"):
        _assembled(signing_key=wrong_signing_key)


def test_a_signature_with_a_mismatched_algorithm_is_refused() -> None:
    signature = sign_human_grant_declaration(**_fields())
    signature["algorithm"] = "rsa"
    with pytest.raises(BindingValidationError):
        _assembled(signature=signature)


@pytest.mark.parametrize(
    "diverging_field,diverging_value",
    [
        ("project_id", "OTHER-PROJECT"),
        ("project_binding_id", "PROJBIND-" + "9" * 64),
        ("grant_ref", {"kind": "verifier_selection_grant", "id": "VSEL-GRANT-" + "1" * 64}),
        ("declared_by", {"kind": "human_authority", "id": "AUTH-OTHER"}),
        ("requirement_id", "VREQ-OTHER"),
        ("selection_id", "VSEL-OTHER"),
        ("verifier_identity", {"kind": "deterministic_test_runner", "id": "OTHER-VERIFIER"}),
        ("permitted_boundary", {"scope": "repository", "boundary_id": "VB-OTHER"}),
        ("status", "REVOKED"),
        ("declared_at", "2099-01-01T00:00:00Z"),
    ],
)
def test_a_signature_computed_over_different_content_is_refused(
    diverging_field: str, diverging_value: Any
) -> None:
    """A genuine signature over one field set, attached to a record whose own value at
    *diverging_field* differs -- the exact "wrong project"/"wrong grant"/"wrong Human"/
    mismatched requirement-or-selection-or-verifier-or-boundary class SHUKOU's own R5-R1
    adoption requires refused: the signature payload and the record's own claimed content
    have silently diverged, exactly as any other content-addressed forgery."""

    signed_fields = _fields()
    with pytest.raises(BindingValidationError, match="signature does not verify"):
        _assembled(signed_fields=signed_fields, **{diverging_field: diverging_value})


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
            "requirement_id": _REQUIREMENT_ID,
            "selection_id": _SELECTION_ID,
            "verifier_identity": dict(_VERIFIER_IDENTITY),
            "permitted_boundary": dict(_BOUNDARY),
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

    def sign(self, *, status: str = "ACTIVE", declared_at: str = _DECLARED_AT) -> dict[str, Any]:
        """The real signature a Human genuinely declaring this real grant would produce --
        computed over the real, resolved fields ``declare_human_grant`` itself will restate."""

        return sign_human_grant_declaration(
            project_id=self.project_id,
            project_binding_id=self.project_binding_id,
            grant_ref=self.grant_ref,
            declared_by=self.human_authority_ref,
            requirement_id=self.grant["requirement_id"],
            selection_id=self.grant["selection_id"],
            verifier_identity=self.grant["verifier_identity"],
            permitted_boundary=self.grant["permitted_boundary"],
            status=status,
            declared_at=declared_at,
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
        signature=real_route.sign(),
        schema_root=SCHEMA_ROOT,
    )
    declaration = result["human_grant_declaration"]
    declaration_id = result["human_grant_declaration_id"]

    assert declaration["human_grant_declaration_id"] == declaration_id
    assert declaration["project_id"] == real_route.project_id
    assert declaration["project_binding_id"] == real_route.project_binding_id
    assert declaration["grant_ref"] == real_route.grant_ref
    assert declaration["status"] == "ACTIVE"
    assert declaration["requirement_id"] == real_route.grant["requirement_id"]
    assert declaration["selection_id"] == real_route.grant["selection_id"]
    assert declaration["verifier_identity"] == real_route.grant["verifier_identity"]
    assert declaration["permitted_boundary"] == real_route.grant["permitted_boundary"]

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
        signature=real_route.sign(),
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
            signature=real_route.sign(),
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
            signature=real_route.sign(),
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
            signature=real_route.sign(),
            schema_root=SCHEMA_ROOT,
        )


def test_declare_human_grant_rejects_an_unsigned_declaration(real_route: _RealRoute) -> None:
    with pytest.raises(BindingValidationError):
        declare_human_grant(
            real_route.store,
            project_id=real_route.project_id,
            project_binding_id=real_route.project_binding_id,
            grant_ref=real_route.grant_ref,
            status="ACTIVE",
            declared_at=_DECLARED_AT,
            signature={},
            schema_root=SCHEMA_ROOT,
        )


def test_declare_human_grant_rejects_a_forged_signature(real_route: _RealRoute) -> None:
    signature = real_route.sign()
    genuine = bytearray.fromhex(signature["value"])
    genuine[0] ^= 0xFF
    signature["value"] = bytes(genuine).hex()
    with pytest.raises(BindingValidationError, match="signature does not verify"):
        declare_human_grant(
            real_route.store,
            project_id=real_route.project_id,
            project_binding_id=real_route.project_binding_id,
            grant_ref=real_route.grant_ref,
            status="ACTIVE",
            declared_at=_DECLARED_AT,
            signature=signature,
            schema_root=SCHEMA_ROOT,
        )


def test_declare_human_grant_rejects_a_signature_signed_for_a_different_status(
    real_route: _RealRoute,
) -> None:
    """A genuine signature over ``status="ACTIVE"`` never authorizes a declaration whose own
    claimed ``status`` is ``"REVOKED"`` -- the signature's own payload and the route's own
    resolved/declared fields must agree exactly."""

    active_signature = real_route.sign(status="ACTIVE")
    with pytest.raises(BindingValidationError, match="signature does not verify"):
        declare_human_grant(
            real_route.store,
            project_id=real_route.project_id,
            project_binding_id=real_route.project_binding_id,
            grant_ref=real_route.grant_ref,
            status="REVOKED",
            declared_at=_DECLARED_AT,
            signature=active_signature,
            schema_root=SCHEMA_ROOT,
        )


def test_declare_human_grant_can_commit_distinct_active_and_revoked_declarations(
    real_route: _RealRoute,
) -> None:
    """Two declarations differing only in ``status`` are two distinct, independently
    resolvable records, each genuinely and separately signed -- explicit revocation is a new
    Human declaration, never a mutation of the genuine one."""

    active = declare_human_grant(
        real_route.store,
        project_id=real_route.project_id,
        project_binding_id=real_route.project_binding_id,
        grant_ref=real_route.grant_ref,
        status="ACTIVE",
        declared_at=_DECLARED_AT,
        signature=real_route.sign(status="ACTIVE"),
        schema_root=SCHEMA_ROOT,
    )["human_grant_declaration"]
    revoked = declare_human_grant(
        real_route.store,
        project_id=real_route.project_id,
        project_binding_id=real_route.project_binding_id,
        grant_ref=real_route.grant_ref,
        status="REVOKED",
        declared_at=_DECLARED_AT,
        signature=real_route.sign(status="REVOKED"),
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
