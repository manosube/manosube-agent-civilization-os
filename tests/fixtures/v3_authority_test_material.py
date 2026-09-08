"""Test-only V3 live-write authority material builder (Structural Review Round 8, Issue #62,
P14-R8-F1; Store-committed material for Store/Boot-resolved authority, Round 9, P14-R9-F1;
trusted-Boot-root and pre-issued subject-specific authority, Round 10, P14-R10-F1; frozen
trusted runtime context to adapter chain, Round 11, P14-R11-F1).

Round 9 built a genuinely committed Store plus a signed ``github_projection_grant``/
``github_projection_grant_declaration`` pair per projection kind, each bound to a
V3-configuration-shaped subject -- but the live-authorized *execution* path still minted a
fresh, *subject*-specific grant/declaration for the actual Difference/Change/Evidence being
projected, using this repository's own test-only signing helper
(:mod:`tests.fixtures.product_binding`). Round 10 forbade exactly that: every subject-specific
grant, signed declaration, and Authority Decision ``project_to_github`` actually consumes must
already be externally issued, committed, Store-resolved, and identity-recomputed *before* the
live execution path is ever asked to project anything -- but the *subject* itself (the actual
Difference/Change record body) still had to be threaded into the harness through a separate
``subjects`` mapping this module returned, since nothing yet made it Store-resolvable by
reference the way ``observation_evidence`` already was. Round 11 closes that too: every subject
this module builds is now committed to the Store as a plain, generic record under its own
canonical kind (``difference``/``change``/``observation_evidence``) -- the identical Store
commit mechanism :func:`commit_v3_test_records` already used for ``observation_evidence`` --
so it is Store-resolvable by exact reference alone. This module has no ``subjects`` mapping to
return any more; :func:`~tests.fixtures.v3_live_write_authority.
resolve_v3_live_write_authority` resolves every subject itself, directly from the Store, and
preserves it inside the immutable execution context it returns.

This module builds, in one place, the real canonical subject (Difference/Change/Evidence) *and*
its own pre-issued, genuinely Ed25519-signed grant/declaration pair together
(:func:`commit_pre_issued_v3_authorities`) -- so the two can never drift apart -- committed
into a real, genuinely bound Store (:func:`bind_v3_test_project`, via the real genesis route
:func:`~manosube_agent_civilization.binding.route.bind_project`, never the offline-only
:func:`~manosube_agent_civilization.binding.engine.assemble_project_binding`). The live
execution path itself never calls any function in this module, never signs anything, and never
invokes :mod:`tests.fixtures.product_binding` -- it only consumes the already-resolved
:class:`~tests.fixtures.v3_live_write_authority.V3AuthorizedExecutionContext`
:func:`~tests.fixtures.v3_live_write_authority.resolve_v3_live_write_authority` returns.

:func:`genuine_project_binding` (offline-only, never committed to any Store) is retained
specifically for the required "fully self-consistent, correctly-signed, but never-committed
record must never authorize" negative control: a caller able to fabricate a byte-for-byte
genuine Project Binding and matching signed declarations, without ever actually committing any
of it to the real canonical Store, must still authorize zero adapter calls, because
``store.resolve_record`` never resolves a reference nothing ever committed.

**This module is never imported by** :mod:`tests.fixtures.v3_live_write_authority` **or by
the one formal execution interface it defines** (``execute_v3_authorized_projection``,
Structural Review Round 12, P14-R12-F1) -- a static conformance test
(``tests/contract/projection/test_v3_live_write_authority_static_conformance.py``) proves
this by AST-walking both modules' own import statements. The live gate consumes only
already-resolved Store records; nothing in it can construct or sign a new record.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tests.authority_helpers import action, derived_difference, rule, scope
from tests.change_helpers import route as change_route
from tests.evidence_helpers import observation_evidence_request
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import github_projection_grant_id
from manosube_agent_civilization.binding import (
    assemble_project_binding,
    bind_project,
    declare_github_projection_grant,
)
from manosube_agent_civilization.change import derive_change
from manosube_agent_civilization.change.identity import (
    change_id as compute_change_id,
    change_semantic_fingerprint,
)
from manosube_agent_civilization.difference.identity import difference_id as compute_difference_id
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

from . import product_binding
from .v3_live_write_authority import (
    V3_PERMITTED_ACTION,
    V3LiveWriteAuthorityReferences,
)
from .v3_target_configuration import V3TargetConfiguration

#: Which real canonical subject kind each projection kind's own pre-issued grant is bound to --
#: the identical pairing the V3 harness's own controlled-adapter proofs already use.
V3_RUN_PROJECTIONS: tuple[tuple[str, str], ...] = (
    ("DIFFERENCE_ISSUE", "difference"),
    ("CHANGE_PULL_REQUEST", "change"),
    ("EVIDENCE_ARTIFACT", "observation_evidence"),
)


def v3_run_payload(config: V3TargetConfiguration, projection_kind: str) -> dict[str, Any]:
    """The deterministic projection payload one full V3 run projects for *projection_kind* --
    shared by pre-issuance (so a pre-issued grant's own ``payload_fingerprint`` matches what
    execution actually projects) and by the harness's own execution-time payload
    construction."""

    if projection_kind == "DIFFERENCE_ISSUE":
        return {"title": f"{config.artifact_naming_prefix} -- Difference", "body": "harness"}
    if projection_kind == "CHANGE_PULL_REQUEST":
        return {
            "title": f"{config.artifact_naming_prefix} -- Change",
            "body": "harness",
            "head_ref": config.change_head_ref,
            "base_ref": config.change_base_ref,
        }
    return {
        "name": config.artifact_naming_prefix,
        "head_sha": config.evidence_head_sha,
        "status": "completed",
        "conclusion": "neutral",
        "output": {"title": config.artifact_naming_prefix, "summary": "harness"},
    }


def genuine_project_binding() -> dict[str, Any]:
    """The real, content-address-verifiable ``project_binding`` record
    :func:`tests.fixtures.product_binding.bind_project_kwargs`'s own fixture material
    produces -- assembled entirely offline, never committed to any Store. Retained solely for
    the "self-consistent, correctly-signed, but never-committed" negative control (Structural
    Review Round 9, P14-R9-F1)."""

    kwargs = product_binding.bind_project_kwargs()
    kwargs.pop("genesis_state")
    kwargs.pop("authority_rule")
    objective_revision = kwargs.pop("objective_revision")
    kwargs["objective_revision_ref"] = {
        "kind": "objective_revision",
        "id": objective_revision["objective_revision_id"],
    }
    return assemble_project_binding(**kwargs)


def bind_v3_test_project(tmp_path: Path) -> tuple[FileStateStore, dict[str, Any]]:
    """Genuinely bind one real Project into a real, committed ``FileStateStore`` rooted under
    *tmp_path* -- the real genesis route
    (:func:`~manosube_agent_civilization.binding.route.bind_project`), never the offline-only
    :func:`~manosube_agent_civilization.binding.engine.assemble_project_binding`. Returns the
    Store plus ``project_id``/``project_binding_id``/``genesis_state``/``human_authority_ref``,
    exactly what a real Boot Context later independently resolves and reverifies."""

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    kwargs = product_binding.bind_project_kwargs()
    result = bind_project(
        store,
        **kwargs,
        additional_genesis_records=product_binding.genesis_records(),
        schema_root=SCHEMA_ROOT,
    )
    return store, {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
        "human_authority_ref": dict(kwargs["human_authority_ref"]),
    }


def commit_v3_test_records(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    transaction_id: str,
    records: list[tuple[str, str, Mapping[str, Any]]],
) -> dict[str, Any]:
    """Commit *records* as one real State transition -- the identical shape every other
    fixture/test in this repository uses to advance a bound Project's own Store, never a
    second commit primitive of this module's own."""

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
        "committed_at": "2026-09-08T00:00:00Z",
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


def build_v3_subject(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    subject_kind: str,
    *,
    transaction_id: str = "TX-V3-EVIDENCE-0001",
) -> tuple[dict[str, Any], str, dict[str, Any] | None, dict[str, Any]]:
    """Build (and, for ``observation_evidence``, commit) one real canonical subject of
    *subject_kind* -- the identical subject-construction logic every projection-kind proof in
    this repository shares. Returns ``(subject_ref, subject_fingerprint, subject_record,
    current_state)`` -- *subject_record* is the full body for ``difference``/``change``
    (``project_to_github`` never Store-resolves those kinds) and ``None`` for
    ``observation_evidence`` (Store-resolved instead); *current_state* only advances for
    ``observation_evidence``, which must commit its own subject record before it can be
    referenced."""

    if subject_kind == "difference":
        difference = dict(derived_difference())
        difference["project_id"] = project_id
        difference["difference_id"] = compute_difference_id(difference)
        subject_ref = {"kind": "difference", "id": difference["difference_id"]}
        subject_fingerprint = (
            "sha256:" + hashlib.sha256(difference["difference_id"].encode("utf-8")).hexdigest()
        )
        return subject_ref, subject_fingerprint, difference, current_state
    if subject_kind == "change":
        difference = dict(derived_difference())
        difference["project_id"] = project_id
        difference["difference_id"] = compute_difference_id(difference)
        _authority_input, _decision, change_request = change_route(
            difference, action(), scope(), rules=[rule(project_id)]
        )
        change = derive_change(change_request)
        subject_ref = {"kind": "change", "id": compute_change_id(change)}
        subject_fingerprint = change_semantic_fingerprint(change)
        return subject_ref, subject_fingerprint, change, current_state

    evidence = derive_evidence(observation_evidence_request())
    current_state = commit_v3_test_records(
        store,
        project_id,
        current_state,
        transaction_id,
        [("observation_evidence", evidence["evidence_id"], evidence)],
    )
    subject_ref = {"kind": "observation_evidence", "id": evidence["evidence_id"]}
    subject_fingerprint = evidence_semantic_fingerprint(evidence)
    return subject_ref, subject_fingerprint, None, current_state


def commit_pre_issued_v3_authorities(
    store: FileStateStore,
    ctx: dict[str, Any],
    config: V3TargetConfiguration,
) -> V3LiveWriteAuthorityReferences:
    """For every projection kind, build and Store-commit the real canonical subject (under its
    own canonical record kind -- ``difference``/``change``/``observation_evidence`` -- so it is
    Store-resolvable by exact reference alone, Structural Review Round 11, P14-R11-F1), then
    pre-issue + commit one genuinely Ed25519-signed ``github_projection_grant``/
    ``github_projection_grant_declaration`` pair bound *exactly* to that subject and to
    *config*'s own ``target_repository`` -- externally issued, committed, and Store-resolvable
    before the live execution path is ever invoked (Structural Review Round 10, P14-R10-F1).
    Returns only the project-scoped **references** naming the grant/declaration pairs -- never
    the record bodies themselves, and no separate subject mapping of any kind: every subject is
    Store-resolvable by reference alone, exactly like the grants and declarations that name it,
    and :func:`~tests.fixtures.v3_live_write_authority.resolve_v3_live_write_authority` is the
    one place that ever resolves one."""

    project_id = ctx["project_id"]
    project_binding_id = ctx["project_binding_id"]
    human_authority_ref = ctx["human_authority_ref"]
    current_state = ctx["genesis_state"]

    grant_refs: list[dict[str, str]] = []
    declaration_refs: list[dict[str, str]] = []

    for projection_kind, subject_kind in V3_RUN_PROJECTIONS:
        kind_token = projection_kind.replace("_", "-")
        subject_ref, subject_fingerprint, subject_record, current_state = build_v3_subject(
            store,
            project_id,
            current_state,
            subject_kind,
            transaction_id=f"TX-V3-PREISSUE-SUBJECT-{kind_token}",
        )
        if subject_record is not None:
            # difference/change: build_v3_subject only builds the body in memory --
            # Store-commit it too, under its own real canonical record kind, so it becomes
            # resolvable by exact reference alone (Round 11, P14-R11-F1 §3). observation_evidence
            # is already committed inside build_v3_subject itself (subject_record is None here).
            current_state = commit_v3_test_records(
                store,
                project_id,
                current_state,
                f"TX-V3-PREISSUE-SUBJECT-COMMIT-{kind_token}",
                [(subject_kind, subject_ref["id"], subject_record)],
            )
        payload_fingerprint = projection_payload_fingerprint(
            v3_run_payload(config, projection_kind)
        )

        grant: dict[str, Any] = {
            "schema_version": "0.1",
            "github_projection_grant_id": "",
            "project_id": project_id,
            "subject_ref": dict(subject_ref),
            "subject_fingerprint": subject_fingerprint,
            "projection_kind": projection_kind,
            "target_repository": dict(config.target_repository),
            "payload_fingerprint": payload_fingerprint,
            "permitted_action": V3_PERMITTED_ACTION,
            "status": "ACTIVE",
            "granted_by": dict(human_authority_ref),
        }
        grant["github_projection_grant_id"] = github_projection_grant_id(grant)
        current_state = commit_v3_test_records(
            store,
            project_id,
            current_state,
            f"TX-V3-PREISSUE-GRANT-{kind_token}",
            [("github_projection_grant", grant["github_projection_grant_id"], grant)],
        )
        grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}

        signature = product_binding.sign_github_projection_grant_declaration(
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
            status="ACTIVE",
            declared_at="2026-09-08T00:00:00Z",
        )
        result = declare_github_projection_grant(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            grant_ref=grant_ref,
            status="ACTIVE",
            declared_at="2026-09-08T00:00:00Z",
            signature=signature,
            schema_root=SCHEMA_ROOT,
        )
        declaration = result["github_projection_grant_declaration"]
        current_state = result["committed_state"]

        grant_refs.append(grant_ref)
        declaration_refs.append(
            {
                "kind": "github_projection_grant_declaration",
                "id": declaration["github_projection_grant_declaration_id"],
            }
        )

    ctx["genesis_state"] = current_state
    return V3LiveWriteAuthorityReferences(
        github_projection_grant_refs=tuple(grant_refs),
        github_projection_grant_declaration_refs=tuple(declaration_refs),
    )


def genuine_v3_authority_store_and_material(
    tmp_path: Path, config: V3TargetConfiguration
) -> tuple[FileStateStore, dict[str, Any], V3LiveWriteAuthorityReferences]:
    """One real, committed Store, its ``ctx`` (``project_id``/``project_binding_id``), and the
    project-scoped references naming a genuinely pre-issued, Store-resolvable grant/declaration
    pair per projection kind -- the complete positive-route material
    :func:`~tests.fixtures.v3_live_write_authority.resolve_v3_live_write_authority` accepts.
    Every subject each grant names is itself Store-resolvable by reference alone (Structural
    Review Round 11, P14-R11-F1) -- there is no separate subject value to return here."""

    store, ctx = bind_v3_test_project(tmp_path)
    references = commit_pre_issued_v3_authorities(store, ctx, config)
    return store, ctx, references


def _wrong_signing_private_key() -> Ed25519PrivateKey:
    """A fixed, deterministic Ed25519 private key distinct from
    :func:`tests.fixtures.product_binding`'s own -- test-only, used solely to prove the "wrong
    signer" negative control: a declaration genuinely signed, but not by the real
    project_binding's own registered key, must never authorize."""

    seed = hashlib.sha256(
        b"tests.fixtures.v3_authority_test_material wrong signer -- never the real Project "
        b"Binding's own key"
    ).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def commit_v3_grant_with_declaration_signed_by_the_wrong_key(
    store: FileStateStore,
    ctx: dict[str, Any],
    config: V3TargetConfiguration,
    *,
    projection_kind: str,
    subject_kind: str,
) -> V3LiveWriteAuthorityReferences:
    """Commit one real, Store-resolvable ``github_projection_grant`` for *projection_kind*,
    bound to a real *subject_kind* subject, anchored by a declaration that is genuinely signed
    -- but not by the real project_binding's own registered key. Both records genuinely resolve
    from the Store; only the signature itself is wrong, proving
    :func:`~manosube_agent_civilization.authority.projection_authorization.
    evaluate_projection_authorization`'s own signature check, not mere Store-resolvability, is
    what gates authorization."""

    from manosube_agent_civilization.binding.identity import (
        github_projection_grant_declaration_id,
        github_projection_grant_declaration_signing_payload,
    )

    project_id = ctx["project_id"]
    project_binding_id = ctx["project_binding_id"]
    human_authority_ref = ctx["human_authority_ref"]
    current_state = ctx["genesis_state"]

    subject_ref, subject_fingerprint, subject_record, current_state = build_v3_subject(
        store,
        project_id,
        current_state,
        subject_kind,
        transaction_id="TX-V3-WRONG-SIGNER-SUBJECT-0001",
    )
    if subject_record is not None:
        current_state = commit_v3_test_records(
            store,
            project_id,
            current_state,
            "TX-V3-WRONG-SIGNER-SUBJECT-COMMIT-0001",
            [(subject_kind, subject_ref["id"], subject_record)],
        )
    payload_fingerprint = projection_payload_fingerprint(v3_run_payload(config, projection_kind))

    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": dict(subject_ref),
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(config.target_repository),
        "payload_fingerprint": payload_fingerprint,
        "permitted_action": V3_PERMITTED_ACTION,
        "status": "ACTIVE",
        "granted_by": dict(human_authority_ref),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    current_state = commit_v3_test_records(
        store,
        project_id,
        current_state,
        "TX-V3-WRONG-SIGNER-GRANT-0001",
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}

    declaration: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_declaration_id": "",
        "project_id": project_id,
        "project_binding_id": project_binding_id,
        "grant_ref": grant_ref,
        "declared_by": dict(human_authority_ref),
        "subject_ref": grant["subject_ref"],
        "subject_fingerprint": grant["subject_fingerprint"],
        "projection_kind": grant["projection_kind"],
        "target_repository": grant["target_repository"],
        "payload_fingerprint": grant["payload_fingerprint"],
        "permitted_action": grant["permitted_action"],
        "status": "ACTIVE",
        "declared_at": "2026-09-08T00:00:00Z",
    }
    message = github_projection_grant_declaration_signing_payload(declaration)
    signature_bytes = _wrong_signing_private_key().sign(message)
    declaration["signature"] = {
        "algorithm": "ed25519",
        # Same key_id as the real project_binding's own key -- this negative control proves
        # the *signature bytes* are checked, not merely the declared key_id.
        "key_id": "AUTH-KEY-0001",
        "value": signature_bytes.hex(),
    }
    declaration["github_projection_grant_declaration_id"] = github_projection_grant_declaration_id(
        declaration
    )
    current_state = commit_v3_test_records(
        store,
        project_id,
        current_state,
        "TX-V3-WRONG-SIGNER-DECL-0001",
        [
            (
                "github_projection_grant_declaration",
                declaration["github_projection_grant_declaration_id"],
                declaration,
            )
        ],
    )
    ctx["genesis_state"] = current_state

    return V3LiveWriteAuthorityReferences(
        github_projection_grant_refs=(grant_ref,),
        github_projection_grant_declaration_refs=(
            {
                "kind": "github_projection_grant_declaration",
                "id": declaration["github_projection_grant_declaration_id"],
            },
        ),
    )
