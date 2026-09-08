"""Phase 9 (Issue #43) minimal, real Product Binding fixture world.

Deliberately self-contained for the Project Binding's own declared content (Objective
Revision, Boundary, Source Registrations, Command Policy, secret-exclusion policy) --
fidelity to the frozen ``01_SCHEMA/`` shapes, not duplication of another phase's own test
helpers, the identical design choice ``tests/fixtures/vertical_proof.py``'s own docstring
already states and justifies.

The one deliberate exception is genesis State's own shape: :func:`~tests.state_helpers.
initial_state`/:func:`~tests.state_helpers.genesis_source_snapshot_records` are Kernel-wide,
already-pinned, already-canonical infrastructure every Phase 7/8 test already depends on --
re-deriving a second genesis State shape here would itself be the duplication.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

PROJECT_ID = "PRJ-BIND-0001"
BOUND_AT = "2026-09-06T09:00:00Z"


def objective_revision() -> dict[str, Any]:
    """A real, schema-valid Objective Revision body -- the Human-declared input Product
    Binding accepts, validates against Objective's own schema, and persists verbatim."""

    return {
        "schema_version": "0.1",
        "objective_id": "OBJ-BIND-0001",
        "objective_revision_id": "OBJ-REV-BIND-0001",
        "project_id": PROJECT_ID,
        "statement": "The bound project reaches its declared operating boundary safely.",
        "owner_authority_ref": {"kind": "human_authority", "id": "AUTH-BIND-0001"},
        "target_predicates": [
            {
                "predicate_id": "TP-BIND-0001",
                "subject": "project.boundary",
                "operator": "exists",
                "expected_value": True,
                "observation_scope": "project",
                "evidence_requirement": "E1",
                "unknown_policy": "INCOMPLETE",
                "criticality": "mandatory",
            }
        ],
        "completion_policy": {"mode": "ALL", "contradiction_policy": "BLOCK"},
        "boundary_ref": {"kind": "objective_boundary", "id": "BOUND-BIND-0001"},
        "constitutional_constraints": [],
        "status": "ACTIVE",
        "revision": 0,
        "previous_objective_ref": None,
        "change_reason": "initial product binding",
        "base_semantic_fingerprint": None,
        "semantic_change_summary": "initial objective revision for the bound project",
        "human_authority_ref": {"kind": "human_authority", "id": "AUTH-BIND-0001"},
        "recorded_at": BOUND_AT,
    }


def boundary() -> dict[str, Any]:
    """A real, structurally valid Boundary -- one relative root, no traversal, no escape."""

    return {
        "schema_version": "0.1",
        "root_paths": ["repo"],
        "include_patterns": ["*.py"],
        "exclude_patterns": ["*.pyc"],
    }


def source_registrations() -> list[dict[str, Any]]:
    """One real Source Registration whose ``locator`` falls within :func:`boundary`'s own
    ``root_paths`` -- declares trust only, grants no Observation/Authority of its own."""

    return [
        {
            "schema_version": "0.1",
            "source_id": "SRC-BIND-0001",
            "source_type": "GIT_REPOSITORY",
            "locator": "repo/src",
            "include_patterns": ["*.py"],
            "exclude_patterns": [],
        }
    ]


def command_policy() -> dict[str, Any]:
    """A real Command Policy ceiling -- a closed set of command *classes*, never a raw
    command string, never a wildcard, never an authority grant."""

    return {
        "schema_version": "0.1",
        "allowed_command_classes": ["BUILD", "TEST", "LINT"],
        "max_commands_per_change": 10,
    }


def secret_exclusion_policy() -> dict[str, Any]:
    """A real secret-exclusion policy -- field *names* and a closed reference-kind enum
    only; never an actual secret value anywhere in this declaration."""

    return {
        "forbidden_field_names": ["password", "token", "private_key", "credential"],
        "allowed_secret_reference_kinds": ["ENVIRONMENT_VARIABLE_REFERENCE"],
    }


def human_authority_ref() -> dict[str, Any]:
    return {"kind": "human_authority", "id": "AUTH-BIND-0001"}


def _signing_private_key() -> Ed25519PrivateKey:
    """A fixed, deterministic Ed25519 test-only private key -- never a real Human's private
    key, which never touches this system's production code at all (see the module docstring
    of ``manosube_agent_civilization.binding.signature``, which only ever verifies). Fixed and
    deterministic so every test run signs and verifies against the identical key pair, exactly
    as every other fixture in this module is itself fully deterministic."""

    seed = hashlib.sha256(b"tests.fixtures.product_binding human_authority_signing_key").digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def human_authority_signing_key() -> dict[str, Any]:
    """The real Project Binding's own Ed25519 public verification key (Structural Review
    Round 5-R1, Issue #51, P13-R5-R1) -- the public half of :func:`_signing_private_key`,
    never the private key itself."""

    public_bytes = (
        _signing_private_key()
        .public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    )
    return {
        "algorithm": "ed25519",
        "key_id": "AUTH-KEY-0001",
        "public_key": public_bytes.hex(),
    }


def sign_human_grant_declaration(
    *,
    project_id: str,
    project_binding_id: str,
    grant_ref: dict[str, Any],
    declared_by: dict[str, Any],
    requirement_id: str,
    selection_id: str,
    verifier_identity: dict[str, Any],
    permitted_boundary: dict[str, Any],
    status: str,
    declared_at: str,
) -> dict[str, Any]:
    """Sign the exact canonical payload
    :func:`~manosube_agent_civilization.binding.identity.human_grant_declaration_signing_
    payload` recomputes once ``assemble_human_grant_declaration`` assembles the real record
    from these same fields -- the one shared signing helper every test that calls
    ``declare_human_grant``/``assemble_human_grant_declaration`` uses, rather than each
    reimplementing its own copy of the identical payload-construction logic
    :mod:`manosube_agent_civilization.binding.identity` already owns."""

    from manosube_agent_civilization.binding.identity import (
        human_grant_declaration_signing_payload,
    )

    payload_record = {
        "schema_version": "0.1",
        "project_id": project_id,
        "project_binding_id": project_binding_id,
        "grant_ref": grant_ref,
        "declared_by": declared_by,
        "requirement_id": requirement_id,
        "selection_id": selection_id,
        "verifier_identity": verifier_identity,
        "permitted_boundary": permitted_boundary,
        "status": status,
        "declared_at": declared_at,
    }
    message = human_grant_declaration_signing_payload(payload_record)
    signature_bytes = _signing_private_key().sign(message)
    return {
        "algorithm": "ed25519",
        "key_id": human_authority_signing_key()["key_id"],
        "value": signature_bytes.hex(),
    }


def authority_rule() -> dict[str, Any]:
    """A real, schema-valid Authority Rule body -- the Human-declared input Product Binding
    accepts, validates against Authority's own schema, identity-reverifies via Authority's
    own :func:`~manosube_agent_civilization.authority.identity.rule_id`, and persists
    verbatim (Issue #43 Phase 9 Round 1 P9-R1-F1: ``authority_policy_ref`` must resolve to a
    real canonical body, never a merely well-formed but unresolved id)."""

    from manosube_agent_civilization.authority.identity import rule_id

    body: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": PROJECT_ID,
        "action_kinds": ["READ_ONLY_QUERY"],
        "maximum_reversibility": "REVERSIBLE",
        "scope": {
            "repository": PROJECT_ID,
            "branch": "main",
            "paths": ["repo"],
            "subjects": ["binding"],
        },
        "decision": "AUTONOMOUS",
        "declared_by": human_authority_ref(),
    }
    body["authority_rule_id"] = rule_id(body)
    return body


def authority_policy_ref() -> dict[str, Any]:
    """A real, correctly-kinded reference to :func:`authority_rule`'s own content-addressed
    identity -- resolvable from a fresh Store once ``bind_project`` persists that real body
    alongside it, never a bare, unbacked id (Phase 9 Round 1 P9-R1-F1)."""

    return {"kind": "authority_rule", "id": authority_rule()["authority_rule_id"]}


def genesis_state() -> dict[str, Any]:
    """A fully assembled genesis ``project_state`` -- everything :func:`~manosube_agent_
    civilization.state.fingerprint.fingerprint_project_state` (the real State owner) needs
    except its own recomputed ``semantic_fingerprint``, which ``binding.route.bind_project``
    fills in itself, exactly as ``tests/reflow_helpers.py::store_ready_for_closure`` already
    does for every other vertical in this repository."""

    from tests.state_helpers import initial_state

    state = deepcopy(initial_state())
    state["project_id"] = PROJECT_ID
    state["objective_revision_id"] = objective_revision()["objective_revision_id"]
    return state


def genesis_records() -> list[tuple[str, str, dict[str, Any]]]:
    """The Store-adopted ``records`` :func:`genesis_state` itself references (its own real
    Kernel Source Snapshot) -- see ``tests/state_helpers.py::genesis_source_snapshot_
    records`` for why this is required alongside genesis, not merely convenient."""

    from tests.state_helpers import genesis_source_snapshot_records

    return genesis_source_snapshot_records(genesis_state())


def bind_project_kwargs() -> dict[str, Any]:
    """Every keyword :func:`~manosube_agent_civilization.binding.route.bind_project` needs
    for one real, successful Product Binding route -- deep-copied so a caller may mutate one
    field for a negative control without perturbing this module's own fixtures."""

    return {
        "project_id": PROJECT_ID,
        "objective_revision": objective_revision(),
        "boundary": boundary(),
        "authority_policy_ref": authority_policy_ref(),
        "authority_rule": authority_rule(),
        "source_registrations": source_registrations(),
        "command_policy": command_policy(),
        "secret_exclusion_policy": secret_exclusion_policy(),
        "human_authority_ref": human_authority_ref(),
        "human_authority_signing_key": human_authority_signing_key(),
        "bound_at": BOUND_AT,
        "genesis_state": genesis_state(),
    }
