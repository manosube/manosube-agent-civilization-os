"""Phase 16 (Issue #66) shared Model Runtime test world.

Deliberately mirrors ``tests/fixtures/runtime_world.py``'s own ``bound``/``commit_records``/
``commit_grant`` shape rather than importing it (that module is Phase 15's own fixture world,
and cross-phase fixture reuse is exactly what makes one phase's negative control silently depend
on another phase's positive one) -- the identical "self-contained fixture layer" discipline every
other phase in this repository already keeps.

Everything Human-declared is *genuinely* declared here, test-side: the Ed25519 private half that
signs a ``model_execution_grant`` lives only in this module, exactly as every other signing
helper in this repository's own fixture layer does, and shipped code only ever verifies. A real
Human's private key never touches this system.

Every Difference this module builds is produced by the public Difference producer
(``derive_differences``, reached through :mod:`tests.difference_helpers`), never hand-written --
the identical discipline :mod:`tests.authority_helpers`' own docstring states and justifies.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision as difference_objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    state_fingerprint,
)
from tests.fixtures.product_binding import (
    PROJECT_ID,
    _signing_private_key as canonical_signing_private_key,
    bind_project_kwargs,
    genesis_records,
    human_authority_ref as canonical_human_authority_ref,
    human_authority_signing_key,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority import evaluate_model_execution_authorization
from manosube_agent_civilization.authority.identity import (
    model_execution_grant_id,
    model_execution_grant_signing_payload,
    rule_id,
)
from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.identity import difference_id as compute_difference_id
from manosube_agent_civilization.model_runtime.engine import derive_model_work_unit
from manosube_agent_civilization.model_runtime.identity import (
    model_execution_boundary_id,
    model_execution_boundary_semantic_fingerprint,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

BOUNDARY_RECORD_KIND = "model_execution_boundary"
GRANT_RECORD_KIND = "model_execution_grant"
DIFFERENCE_RECORD_KIND = "difference"

REQUIRED_CAPABILITY = "PROPOSE_EVIDENCE_CANDIDATE"
PERMITTED_CANDIDATE_FIELDS: tuple[str, ...] = ("summary", "observed_status")
DECLARED_AT = "2026-09-08T00:00:00Z"
GRANTED_AT = "2026-09-08T01:00:00Z"

#: A second, complete project bound into the *same* Store -- the cross-project control's own
#: subject. Genuinely bound through the real genesis route, not a relabelled copy of the first.
SECOND_PROJECT_ID = "PRJ-BIND-0002"


# --------------------------------------------------------------------------- #
# A real, genuinely bound world (one Store, one or two projects)
# --------------------------------------------------------------------------- #


def _rebind(value: Any, old: str, new: str) -> Any:
    if isinstance(value, Mapping):
        return {key: _rebind(item, old, new) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_rebind(item, old, new) for item in value)
    if isinstance(value, list):
        return [_rebind(item, old, new) for item in value]
    return new if value == old else value


def bind_into(store: FileStateStore, *, project_id: str = PROJECT_ID) -> dict[str, Any]:
    """Bind one real project into *store* through the real genesis route and return its
    context."""

    kwargs = _rebind(bind_project_kwargs(), PROJECT_ID, project_id)
    # The Authority Rule's own content address is a function of its body, and its body carries
    # the project id -- so rebinding a project necessarily re-addresses its rule. Recomputing the
    # rule's own declared id and then `authority_policy_ref` through Authority's own `rule_id`
    # keeps all three genuine rather than restating hand-written addresses the real genesis route
    # would (correctly) refuse.
    kwargs["authority_rule"]["authority_rule_id"] = rule_id(kwargs["authority_rule"])
    kwargs["authority_policy_ref"] = {
        "kind": "authority_rule",
        "id": kwargs["authority_rule"]["authority_rule_id"],
    }
    records = [
        (kind, identity, _rebind(body, PROJECT_ID, project_id))
        for kind, identity, body in genesis_records()
    ]
    result = bind_project(
        store, **kwargs, additional_genesis_records=records, schema_root=SCHEMA_ROOT
    )
    return {
        "project_id": project_id,
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
        "human_authority_ref": dict(canonical_human_authority_ref()),
    }


def bound(tmp_path: Path, *, subdir: str = "backend") -> tuple[FileStateStore, dict[str, Any]]:
    """One real ``FileStateStore`` with one real, genuinely bound project.

    *subdir* exists so a test can build a **second, entirely separate Store** under the same
    ``tmp_path`` -- the cross-Store control's own subject, which is genuinely a different Store
    rather than merely a different directory name for the same one.
    """

    store = FileStateStore(tmp_path / subdir, schema_root=SCHEMA_ROOT)
    return store, bind_into(store)


def commit_records(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    transaction_id: str,
    records: list[tuple[str, str, Mapping[str, Any]]],
    *,
    committed_at: str = "2026-09-09T00:00:00Z",
) -> dict[str, Any]:
    """Commit *records* over *current_state* and return the resulting next State.

    Deliberately bypasses this package's own routes: this helper exists only to seed the
    pre-existing, Human-declared world state (a Difference, a Model Execution Boundary, a signed
    Model Execution Grant) that a real route call then resolves and verifies -- the identical
    shape every other fixture-side commit in this repository's own test suite uses.
    """

    successor = dict(current_state)
    successor["state_revision"] = current_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": transaction_id,
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": current_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": current_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": committed_at,
    }
    store.commit(
        project_id,
        current_state["state_revision"],
        current_state["semantic_fingerprint"],
        successor,
        event,
        records=records,
    )
    return successor


def touch_state(
    store: FileStateStore, project_id: str, *, transaction_id: str = "TX-MODEL-UNRELATED-0001"
) -> dict[str, Any]:
    """Advance this project's own State by one wholly unrelated, record-free transition.

    The V4 stale-State controls need a way to move the Store underneath an already-Booted
    execution contract without changing anything the contract is *about*; this is it.
    """

    return commit_records(store, project_id, store.load_current(project_id), transaction_id, [])


# --------------------------------------------------------------------------- #
# The real Difference this work is about -- produced through the public producer
# --------------------------------------------------------------------------- #


def difference_for(project_id: str, *, fact_value: str = "NOT-READY") -> dict[str, Any]:
    """One real, schema-valid, content-addressed Difference bound to *project_id*.

    *fact_value* exists so a test can build a genuinely **second, distinct** Difference inside
    the same project -- the wrong-Difference control's own subject -- without hand-writing a
    record the producer would never emit.
    """

    fingerprint = state_fingerprint()
    scope = observation_scope()
    request = derivation_request(
        difference_objective_revision(),
        [
            {
                "target_predicate_id": PREDICATE_ID,
                "observation_scope": scope,
                "observation_bundle": observed_bundle(
                    scope,
                    [raw_fact(value=fact_value)],
                    fingerprint,
                    negative_claims=[negative_claim("NO_RESULT")],
                ),
            }
        ],
        fingerprint,
    )
    difference: dict[str, Any] = dict(derive_differences(request)["differences"][0])
    difference["project_id"] = project_id
    difference["difference_id"] = compute_difference_id(difference)
    return difference


def commit_difference(
    store: FileStateStore,
    project_id: str,
    *,
    fact_value: str = "NOT-READY",
    transaction_id: str = "TX-MODEL-DIFFERENCE-0001",
) -> tuple[dict[str, str], dict[str, Any]]:
    """Commit one real Difference and return ``(ref, difference)``."""

    difference = difference_for(project_id, fact_value=fact_value)
    commit_records(
        store,
        project_id,
        store.load_current(project_id),
        transaction_id,
        [(DIFFERENCE_RECORD_KIND, difference["difference_id"], difference)],
    )
    return {"kind": DIFFERENCE_RECORD_KIND, "id": difference["difference_id"]}, difference


# --------------------------------------------------------------------------- #
# The Human-declared Model Execution Boundary
# --------------------------------------------------------------------------- #


def boundary_for(
    project_id: str,
    project_binding_id: str,
    *,
    permitted_capability: str = REQUIRED_CAPABILITY,
    permitted_candidate_kinds: tuple[str, ...] = ("OBSERVATION_CANDIDATE",),
    permitted_candidate_fields: tuple[str, ...] = PERMITTED_CANDIDATE_FIELDS,
    declared_by: Mapping[str, Any] | None = None,
    declared_at: str = DECLARED_AT,
) -> dict[str, Any]:
    """One real, schema-valid, content-addressed ``model_execution_boundary`` body."""

    boundary: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": project_id,
        "project_binding_ref": {"kind": "project_binding", "id": project_binding_id},
        "permitted_capability": permitted_capability,
        "permitted_candidate_kinds": list(permitted_candidate_kinds),
        "permitted_candidate_fields": list(permitted_candidate_fields),
        "declared_by": dict(declared_by or canonical_human_authority_ref()),
        "declared_at": declared_at,
    }
    boundary["model_execution_boundary_id"] = model_execution_boundary_id(boundary)
    boundary["model_execution_boundary_semantic_fingerprint"] = (
        model_execution_boundary_semantic_fingerprint(boundary)
    )
    return boundary


def commit_boundary(
    store: FileStateStore,
    project_id: str,
    project_binding_id: str,
    *,
    transaction_id: str = "TX-MODEL-BOUNDARY-0001",
    **boundary_fields: Any,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Commit one real Model Execution Boundary and return ``(ref, boundary)``."""

    boundary = boundary_for(project_id, project_binding_id, **boundary_fields)
    commit_records(
        store,
        project_id,
        store.load_current(project_id),
        transaction_id,
        [(BOUNDARY_RECORD_KIND, boundary["model_execution_boundary_id"], boundary)],
    )
    return (
        {"kind": BOUNDARY_RECORD_KIND, "id": boundary["model_execution_boundary_id"]},
        boundary,
    )


# --------------------------------------------------------------------------- #
# The Human-Authority-signed Model Execution Grant
# --------------------------------------------------------------------------- #


def foreign_signing_private_key() -> Ed25519PrivateKey:
    """A second, genuinely different signing key pair -- what an attacker able to write Store
    records, or an alternate world signing its own grant with its own internally legitimate key,
    actually holds. Never the key any Project Binding in this fixture world declares."""

    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(b"tests.fixtures.model_runtime_world foreign human authority").digest()
    )


def foreign_signing_key() -> dict[str, Any]:
    """The public half of :func:`foreign_signing_private_key`, in a Project Binding's own
    ``human_authority_signing_key`` shape."""

    return {
        "algorithm": "ed25519",
        "key_id": "AUTH-KEY-0001",
        "public_key": (
            foreign_signing_private_key()
            .public_key()
            .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
            .hex()
        ),
    }


def sign_model_execution_grant(
    grant: Mapping[str, Any],
    *,
    private_key: Ed25519PrivateKey | None = None,
    key_id: str = "AUTH-KEY-0001",
) -> dict[str, Any]:
    """Sign the exact canonical payload
    :func:`~manosube_agent_civilization.authority.identity.model_execution_grant_signing_payload`
    derives from *grant*'s own adopted semantic fields.

    *private_key* defaults to the canonical fixture Human Authority's own key -- the one a
    canonical world's Boot-restored Project Binding actually verifies against -- so a test that
    simply wants a legitimate grant gets one, while every negative control passes an attacker's
    key explicitly.
    """

    signer = private_key or canonical_signing_private_key()
    return {
        "algorithm": "ed25519",
        "key_id": key_id,
        "value": signer.sign(model_execution_grant_signing_payload(dict(grant))).hex(),
    }


def grant_for(
    project_id: str,
    difference_ref: Mapping[str, Any],
    boundary_ref: Mapping[str, Any],
    *,
    required_capability: str = REQUIRED_CAPABILITY,
    permitted_action: str = "EXECUTE_MODEL_WORK_UNIT",
    status: str = "ACTIVE",
    granted_by: Mapping[str, Any] | None = None,
    granted_at: str = GRANTED_AT,
    signer: Ed25519PrivateKey | None = None,
    signing_key_id: str = "AUTH-KEY-0001",
) -> dict[str, Any]:
    """One real, schema-valid, content-addressed, genuinely Ed25519-signed
    ``model_execution_grant`` body."""

    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": project_id,
        "difference_ref": dict(difference_ref),
        "required_capability": required_capability,
        "boundary_ref": dict(boundary_ref),
        "permitted_action": permitted_action,
        "status": status,
        "granted_by": dict(granted_by or canonical_human_authority_ref()),
        "granted_at": granted_at,
    }
    grant["model_execution_grant_id"] = model_execution_grant_id(grant)
    grant["signature"] = sign_model_execution_grant(
        grant, private_key=signer, key_id=signing_key_id
    )
    return grant


def commit_grant(
    store: FileStateStore,
    project_id: str,
    difference_ref: Mapping[str, Any],
    boundary_ref: Mapping[str, Any],
    *,
    transaction_id: str = "TX-MODEL-GRANT-0001",
    **grant_fields: Any,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Commit one real Model Execution Grant and return ``(ref, grant)``."""

    grant = grant_for(project_id, difference_ref, boundary_ref, **grant_fields)
    commit_records(
        store,
        project_id,
        store.load_current(project_id),
        transaction_id,
        [(GRANT_RECORD_KIND, grant["model_execution_grant_id"], grant)],
    )
    return {"kind": GRANT_RECORD_KIND, "id": grant["model_execution_grant_id"]}, grant


# --------------------------------------------------------------------------- #
# Planted material: the V4 matrix's own substituted / tampered / impossible subjects
# --------------------------------------------------------------------------- #


def decision_for(
    project_id: str,
    difference_ref: Mapping[str, Any],
    boundary_ref: Mapping[str, Any],
    grants: list[Mapping[str, Any]],
    *,
    required_capability: str = REQUIRED_CAPABILITY,
    human_authority_ref: Mapping[str, Any] | None = None,
    human_authority_signing_key_value: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Mint one real Model Execution Decision through the **shipped** Authority evaluator.

    Never a hand-written decision body: a planted decision the real evaluator would never emit
    would prove nothing about the route that resolves it.
    """

    return evaluate_model_execution_authorization(
        {
            "schema_version": "0.1",
            "project_id": project_id,
            "difference_ref": dict(difference_ref),
            "required_capability": required_capability,
            "boundary_ref": dict(boundary_ref),
            "human_authority_ref": dict(human_authority_ref or canonical_human_authority_ref()),
            "human_authority_signing_key": dict(
                human_authority_signing_key_value or human_authority_signing_key()
            ),
            "grants": [dict(grant) for grant in grants],
        }
    )


def work_unit_body(
    project_id: str,
    project_binding_id: str,
    *,
    opened_state_revision: int,
    opened_semantic_fingerprint: Mapping[str, Any],
    difference_ref: Mapping[str, Any],
    authority_ref: Mapping[str, Any],
    boundary_ref: Mapping[str, Any],
    required_capability: str = REQUIRED_CAPABILITY,
    opened_at: str = "2026-09-09T01:00:00Z",
) -> dict[str, Any]:
    """One real, schema-valid, fully self-consistent ``model_work_unit`` body, derived through
    the **shipped** deriver so its own two digests are genuine.

    This is what makes the substituted-reference controls decisive: the planted record is not
    malformed and not internally inconsistent -- it recomputes perfectly. The only thing wrong
    with it is what it *points at*, which is precisely what the route must catch.
    """

    return derive_model_work_unit(
        project_id=project_id,
        project_binding_ref={"kind": "project_binding", "id": project_binding_id},
        opened_state_revision=opened_state_revision,
        opened_semantic_fingerprint=dict(opened_semantic_fingerprint),
        difference_ref=dict(difference_ref),
        required_capability=required_capability,
        authority_ref=dict(authority_ref),
        boundary_ref=dict(boundary_ref),
        opened_at=opened_at,
    )


def plant_records(
    store: FileStateStore,
    project_id: str,
    records: list[tuple[str, str, Mapping[str, Any]]],
    *,
    transaction_id: str = "TX-MODEL-PLANTED-0001",
) -> dict[str, Any]:
    """Commit *records* directly, bypassing every route -- exactly what an attacker able to
    write Store records can do, and exactly what the route's own re-resolution must survive."""

    return commit_records(
        store, project_id, store.load_current(project_id), transaction_id, records
    )


# --------------------------------------------------------------------------- #
# The complete, ready-to-open world
# --------------------------------------------------------------------------- #


def authorized_world(
    tmp_path: Path, *, subdir: str = "backend", project_id: str = PROJECT_ID
) -> dict[str, Any]:
    """One real Store with one bound project, one committed Difference, one committed Model
    Execution Boundary, and one committed, genuinely signed Model Execution Grant -- everything
    :func:`~manosube_agent_civilization.model_runtime.open_model_work_unit` needs, and nothing it
    does not.

    Deliberately stops **before** opening a Work Unit: opening one is the route's own job, and a
    fixture that opened it would be the fixture proving the route rather than the route proving
    itself.
    """

    store = FileStateStore(tmp_path / subdir, schema_root=SCHEMA_ROOT)
    ctx = bind_into(store, project_id=project_id)
    difference_ref, difference = commit_difference(store, ctx["project_id"])
    boundary_ref, boundary = commit_boundary(store, ctx["project_id"], ctx["project_binding_id"])
    grant_ref, grant = commit_grant(store, ctx["project_id"], difference_ref, boundary_ref)
    return {
        "store": store,
        "project_id": ctx["project_id"],
        "project_binding_id": ctx["project_binding_id"],
        "human_authority_ref": ctx["human_authority_ref"],
        "human_authority_signing_key": human_authority_signing_key(),
        "difference_ref": difference_ref,
        "difference": difference,
        "boundary_ref": boundary_ref,
        "boundary": boundary,
        "grant_ref": grant_ref,
        "grant": grant,
    }


def open_kwargs(
    world: Mapping[str, Any], *, opened_at: str = "2026-09-09T01:00:00Z"
) -> dict[str, Any]:
    """Every keyword :func:`~manosube_agent_civilization.model_runtime.open_model_work_unit`
    needs for one real, successful open -- deep-copied so a caller may mutate one field for a
    negative control without perturbing *world*."""

    return deepcopy(
        {
            "project_id": world["project_id"],
            "project_binding_id": world["project_binding_id"],
            "difference_ref": world["difference_ref"],
            "required_capability": REQUIRED_CAPABILITY,
            "boundary_ref": world["boundary_ref"],
            "model_execution_grant_refs": [world["grant_ref"]],
            "opened_at": opened_at,
        }
    )


__all__ = [
    "BOUNDARY_RECORD_KIND",
    "DIFFERENCE_RECORD_KIND",
    "GRANT_RECORD_KIND",
    "PERMITTED_CANDIDATE_FIELDS",
    "PROJECT_ID",
    "REQUIRED_CAPABILITY",
    "SECOND_PROJECT_ID",
    "authorized_world",
    "bind_into",
    "bound",
    "boundary_for",
    "canonical_human_authority_ref",
    "canonical_signing_private_key",
    "commit_boundary",
    "commit_difference",
    "commit_grant",
    "commit_records",
    "decision_for",
    "difference_for",
    "foreign_signing_key",
    "foreign_signing_private_key",
    "grant_for",
    "human_authority_signing_key",
    "open_kwargs",
    "plant_records",
    "sign_model_execution_grant",
    "touch_state",
    "work_unit_body",
]
