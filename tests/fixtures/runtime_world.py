"""Phase 15 (Issue #64) shared Runtime Observation test world.

Deliberately mirrors ``tests/integration/projection/test_project_to_github.py``'s own
``_bound``/``_commit_records``/``_commit_grant``/``_commit_declaration`` helpers rather than
importing them directly (that module is a test module, never a fixture module other test
modules should import from) -- the identical "self-contained fixture, not cross-test-module
reuse" discipline every other phase's own fixture layer in this repository already keeps.

Structural Review Round 2 (P15-R2-F2) gave this module a deliberately test-confined signing
responsibility: :func:`sign_runtime_deployment_declaration` and the test-only Ed25519 key pairs
(canonical, alternate world, post-re-binding rotation) a ``runtime_deployment_declaration``'s
own Human Authority signature is produced with. Every one is a *test* signer: a real Human's
private key never touches this system, and shipped code only ever verifies.

Structural Review Round 3 (P15-R3-F1/F2) changes two things here:

- ``test_only_trusted_runtime_root`` is gone, and so is the module-private sentinel it reached
  into. Round 3 found that "private" gate to be a naming convention rather than a control (any
  importer could read it), and -- more decisively -- found the framing wrong: a
  :class:`~manosube_agent_civilization.runtime.bootstrap.TrustedRuntimeRoot` now grants nothing
  by itself, so its construction is public, unrestricted shipped API. :func:`trusted_runtime_root`
  below is a one-line convenience over that public constructor, not an issuer of anything.
  What actually admits a root is a canonical, Store-committed ``runtime_root_admission`` record
  verified against an **externally supplied** trust anchor -- :func:`trust_anchor_public_key_hex`
  and :func:`commit_root_admission` here mint and commit one, test-side, exactly as every other
  signing helper in this repository's own fixture layer does.
- :func:`commit_deployment_declaration` now goes through the *shipped* canonical
  commit-and-supersede path (``runtime.commit_runtime_deployment_declaration``) rather than a
  raw fixture-side record insert, so the canonical current-declaration pointer
  (``semantic_state.runtime.claims[<target_key>]``) is genuinely populated for every
  positive-path test -- without which P15-R3-F2's own currency check could not be tested
  meaningfully at all.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from tests.fixtures.product_binding import (
    _signing_private_key as _canonical_signing_private_key,
    bind_project_kwargs,
    genesis_records,
    human_authority_ref as canonical_human_authority_ref,
    human_authority_signing_key,
    sign_github_projection_grant_declaration,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import github_projection_grant_id, rule_id
from manosube_agent_civilization.binding import (
    assemble_project_binding,
    bind_project,
    declare_github_projection_grant,
)
from manosube_agent_civilization.runtime import commit_runtime_deployment_declaration
from manosube_agent_civilization.runtime.bootstrap import TrustedRuntimeRoot
from manosube_agent_civilization.runtime.identity import (
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
    runtime_deployment_declaration_signing_payload,
    runtime_root_admission_id,
    runtime_root_admission_semantic_fingerprint,
    runtime_root_admission_signing_payload,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore

TARGET_REPOSITORY: dict[str, str] = {"host": "github", "owner": "acme", "repo": "widget"}

DEPLOYMENT_DECLARATION_RECORD_KIND = "runtime_deployment_declaration"
ROOT_ADMISSION_RECORD_KIND = "runtime_root_admission"
DEFAULT_DEPLOYMENT_FINGERPRINT = "sha256:" + "a" * 64
#: The default validity window every fixture-issued ``runtime_deployment_declaration`` carries
#: (P15-R3-F2). Deliberately wide enough to contain every ``observed_at`` this repository's own
#: Runtime suites use, so a test that is not *about* the window never trips over it, and every
#: stale/expired/boundary control states its own window explicitly.
DEFAULT_VALID_FROM = "2026-01-01T00:00:00Z"
DEFAULT_VALID_UNTIL = "2026-12-31T23:59:59Z"


# ---------------------------------------------------------------------------
# A TrustedRuntimeRoot is an ordinary public value again (P15-R3-F1)
# ---------------------------------------------------------------------------
#
# Round 1 shipped a public ``provision_trusted_runtime_root`` factory. Round 2 (P15-R2-F1)
# deleted it -- correctly: it accepted exactly the caller-controlled Store/Project/Binding tuple
# the correction existed to stop an untrusted surface from selecting -- and left construction
# behind a module-private sentinel this fixture module imported directly.
#
# Round 3 (P15-R3-F1) found that sentinel to be a naming convention rather than a control, and
# the framing itself wrong: while *holding* a root was sufficient to reach an adapter, "who may
# mint one?" was unanswerable at the library level. So the boundary moved off the type entirely.
# ``bootstrap_projection_execution_capability`` now admits a root only against a canonical,
# Store-committed ``runtime_root_admission`` verified against an externally supplied trust
# anchor, on every call. The type grants nothing, so its constructor is public shipped API and
# this helper is a plain convenience over it -- not an issuer, and not test-privileged in any
# way. Round 2's own mechanical facts are untouched: no shipped function returns this type, no
# shipped module constructs one, and the deleted factory name is reintroduced nowhere.


def trusted_runtime_root(
    store: Any, *, project_id: str, project_binding_id: str
) -> TrustedRuntimeRoot:
    """Return a :class:`~manosube_agent_civilization.runtime.bootstrap.TrustedRuntimeRoot` over
    *store*/*project_id*/*project_binding_id*, through the public shipped constructor.

    Kept as a named helper purely because every call site in this repository passes the same
    three things in the same shape; it confers nothing a caller could not do inline, which is
    exactly Round 3's point.
    """

    return TrustedRuntimeRoot(store, project_id, project_binding_id)


# ---------------------------------------------------------------------------
# The externally controlled trust anchor a Runtime Root Admission is signed by (P15-R3-F1)
# ---------------------------------------------------------------------------
#
# This key pair is deliberately NOT any project's own ``human_authority_signing_key``, and is not
# resolvable from any Store in this repository. It stands in for what a real deployment supplies
# from its own composition-time configuration -- the whole point of the admission record being
# that its trust does not rest on anything the Store being admitted can produce. Only the
# *public* half ever reaches shipped code; the private half exists here, test-side, for the same
# reason every other signing helper in this fixture layer does.


def _trust_anchor_private_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(b"tests.fixtures.runtime_world deployment trust anchor").digest()
    )


def trust_anchor_private_key() -> Ed25519PrivateKey:
    """The deployment trust anchor's own private signing half -- test-side only."""

    return _trust_anchor_private_key()


def trust_anchor_public_key_hex() -> str:
    """The deployment trust anchor's own public verification half, hex-encoded -- the exact
    value a real deployment would supply to
    ``bootstrap_projection_execution_capability(trust_anchor_public_key_hex=...)`` from its own
    configuration."""

    return (
        _trust_anchor_private_key()
        .public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
        .hex()
    )


def foreign_trust_anchor_private_key() -> Ed25519PrivateKey:
    """A second, genuinely different anchor key pair -- what an attacker who can write Store
    records, or an alternate world signing its own admission record with its own internally
    legitimate key, actually holds. Never the anchor a deployment supplies."""

    return Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(b"tests.fixtures.runtime_world foreign trust anchor").digest()
    )


def sign_runtime_root_admission(
    admission: Mapping[str, Any], *, private_key: Ed25519PrivateKey, key_id: str
) -> dict[str, Any]:
    """Sign the exact canonical payload
    :func:`~manosube_agent_civilization.runtime.identity.runtime_root_admission_signing_payload`
    derives from *admission*'s own adopted semantic fields (P15-R3-F1)."""

    return {
        "algorithm": "ed25519",
        "key_id": key_id,
        "value": private_key.sign(runtime_root_admission_signing_payload(dict(admission))).hex(),
    }


def root_admission_for(
    project_id: str,
    project_binding_id: str,
    *,
    status: str = "ACTIVE",
    declared_at: str = "2026-09-08T00:00:00Z",
    signer: Ed25519PrivateKey | None = None,
    signing_key_id: str = "TRUST-ANCHOR-0001",
) -> dict[str, Any]:
    """Return one real, schema-valid, content-addressed, genuinely signed
    ``runtime_root_admission`` body admitting exactly *project_id*/*project_binding_id*.

    *signer* defaults to the deployment trust anchor's own private key -- the identical
    ``signer``-with-a-canonical-default convention :func:`deployment_declaration_for` already
    uses -- so a test that simply wants a legitimate admission gets one, while every negative
    control passes an attacker's or an alternate world's key explicitly.
    """

    admission: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": project_id,
        "project_binding_ref": {"kind": "project_binding", "id": project_binding_id},
        "status": status,
        "declared_at": declared_at,
    }
    admission["signature"] = sign_runtime_root_admission(
        admission,
        private_key=signer if signer is not None else _trust_anchor_private_key(),
        key_id=signing_key_id,
    )
    admission["runtime_root_admission_id"] = runtime_root_admission_id(admission)
    admission["runtime_root_admission_semantic_fingerprint"] = (
        runtime_root_admission_semantic_fingerprint(admission)
    )
    return admission


def commit_root_admission(
    store: FileStateStore, project_id: str, admission: Mapping[str, Any]
) -> dict[str, str]:
    """Commit *admission* (idempotently -- a content address already resolved is the identical
    record, never a second one) and return the reference naming it."""

    admission_id = str(admission["runtime_root_admission_id"])
    if store.resolve_record(project_id, ROOT_ADMISSION_RECORD_KIND, admission_id) is None:
        commit_records(
            store,
            project_id,
            store.load_current(project_id),
            f"TX-RUNTIME-ROOT-ADMISSION-{admission_id[-16:]}",
            [(ROOT_ADMISSION_RECORD_KIND, admission_id, dict(admission))],
        )
    return {"kind": ROOT_ADMISSION_RECORD_KIND, "id": admission_id}


def admitted_root(
    store: FileStateStore, *, project_id: str, project_binding_id: str, **admission_fields: Any
) -> dict[str, Any]:
    """Commit one genuine ``runtime_root_admission`` for *project_id*/*project_binding_id* and
    return the complete ``{trusted_runtime_root, runtime_root_admission_ref,
    trust_anchor_public_key_hex}`` triple every legitimate
    ``bootstrap_projection_execution_capability`` call now needs (P15-R3-F1)."""

    admission = root_admission_for(project_id, project_binding_id, **admission_fields)
    return {
        "trusted_runtime_root": trusted_runtime_root(
            store, project_id=project_id, project_binding_id=project_binding_id
        ),
        "runtime_root_admission_ref": commit_root_admission(store, project_id, admission),
        "trust_anchor_public_key_hex": trust_anchor_public_key_hex(),
        "runtime_root_admission": admission,
    }


def bound(tmp_path: Path) -> tuple[FileStateStore, dict[str, Any]]:
    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
    }


# ---------------------------------------------------------------------------
# A second, fully self-consistent world under its own external Human Authority
# ---------------------------------------------------------------------------
#
# P15-R1-F4's own decisive control needs an alternate Store that is not merely "a different
# temporary directory" but a genuinely complete, internally valid world on its own terms: its
# own Human Authority, its own Ed25519 signing key, its own Project Binding, and its own
# grants/declarations signed by that key and verifiable against that Binding. Anything less
# would prove only that two directories differ, not that a *legitimate* alternate authority
# world cannot be substituted for the canonical one.

ALTERNATE_HUMAN_AUTHORITY_REF: dict[str, str] = {
    "kind": "human_authority",
    "id": "AUTH-ALTERNATE-0001",
}


def _alternate_signing_private_key() -> Ed25519PrivateKey:
    """A second fixed, deterministic, test-only Ed25519 private key -- genuinely different
    from ``tests.fixtures.product_binding``'s own, so the alternate world below is signed by
    an authority the canonical world has never heard of."""

    seed = hashlib.sha256(b"tests.fixtures.runtime_world alternate_human_authority").digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def alternate_signing_private_key() -> Ed25519PrivateKey:
    """The alternate world's own private signing half -- exposed so a negative control can sign
    a *canonical*-world record with a genuinely different, but genuinely legitimate, Human
    Authority's key (P15-R2-F2's own "wrong signer" control)."""

    return _alternate_signing_private_key()


def alternate_human_authority_signing_key() -> dict[str, Any]:
    public_bytes = (
        _alternate_signing_private_key()
        .public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    )
    return {
        "algorithm": "ed25519",
        "key_id": "AUTH-KEY-ALTERNATE-0001",
        "public_key": public_bytes.hex(),
    }


def _rebind_authority(value: Any) -> Any:
    """Recursively replace every appearance of the canonical fixture Human Authority reference
    with :data:`ALTERNATE_HUMAN_AUTHORITY_REF` -- the three-way cross-match ``bind_project``
    enforces (Binding, Objective Revision, Authority Rule) means all of them must move
    together or the alternate world would not be internally valid at all."""

    canonical = canonical_human_authority_ref()
    if isinstance(value, dict):
        if value == canonical:
            return dict(ALTERNATE_HUMAN_AUTHORITY_REF)
        return {key: _rebind_authority(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind_authority(item) for item in value]
    return value


def alternate_bound(tmp_path: Path) -> tuple[FileStateStore, dict[str, Any]]:
    """Bind one complete alternate world -- its own external Human Authority, its own signing
    key, its own Project Binding -- through the identical real ``bind_project`` route, and
    return it exactly as :func:`bound` returns the canonical one."""

    store_root = tmp_path / "alternate-backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = deepcopy(bind_project_kwargs())
    kwargs = _rebind_authority(kwargs)
    kwargs["human_authority_signing_key"] = alternate_human_authority_signing_key()
    kwargs["authority_rule"]["authority_rule_id"] = rule_id(kwargs["authority_rule"])
    kwargs["authority_policy_ref"] = {
        "kind": "authority_rule",
        "id": kwargs["authority_rule"]["authority_rule_id"],
    }
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
    }


# ---------------------------------------------------------------------------
# A legitimate Human Authority signing-key re-binding, inside one project
# ---------------------------------------------------------------------------
#
# P15-R2-F2 requires proving that a declaration signed under a *previous* Project Binding is
# refused once the project has legitimately been re-bound, and that a newly issued, newly signed
# one succeeds. This repository has no separate "re-bind" route: ``bind_project`` owns genesis
# and genesis is strictly one-shot. A re-binding here is therefore exactly what it is in this
# Kernel -- a genuinely new ``project_binding`` record, assembled through the *real* Binding
# producer (``assemble_project_binding``, the identical function ``bind_project`` itself calls),
# carrying a rotated ``human_authority_signing_key`` under the identical Human Authority, and
# committed into the identical project. Because a Project Binding is content-addressed over its
# own ``human_authority_ref``/``human_authority_signing_key``, that rotation necessarily mints a
# new ``project_binding_id``, and Boot restores it exactly as it restores the original.

REBOUND_SIGNING_KEY_ID = "AUTH-KEY-REBOUND-0001"


def _rebound_signing_private_key() -> Ed25519PrivateKey:
    """A third fixed, deterministic, test-only Ed25519 private key -- the one a legitimate
    signing-key rotation of the *canonical* Human Authority moves to, generated exactly the way
    :func:`_alternate_signing_private_key` above already generates its own."""

    seed = hashlib.sha256(b"tests.fixtures.runtime_world rebound_human_authority").digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def rebound_signing_private_key() -> Ed25519PrivateKey:
    """The post-re-binding private signing half -- what a newly issued declaration must be
    signed with once :func:`rebind_with_rotated_signing_key` has run."""

    return _rebound_signing_private_key()


def rebound_human_authority_signing_key() -> dict[str, Any]:
    public_bytes = (
        _rebound_signing_private_key()
        .public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    )
    return {
        "algorithm": "ed25519",
        "key_id": REBOUND_SIGNING_KEY_ID,
        "public_key": public_bytes.hex(),
    }


def rebind_with_rotated_signing_key(
    store: FileStateStore, project_id: str, *, transaction_id: str = "TX-RUNTIME-REBIND-0001"
) -> dict[str, Any]:
    """Commit one genuinely new, real ``project_binding`` for *project_id* under the identical
    Human Authority but a rotated ``human_authority_signing_key``, and return that new record.

    Assembled through the real Binding producer
    (:func:`~manosube_agent_civilization.binding.assemble_project_binding`) -- never a hand-built
    dict -- so the resulting record is schema-valid, content-addressed, and restorable by the
    real ``boot_project`` exactly as the original is.
    """

    kwargs = deepcopy(bind_project_kwargs())
    rebound = assemble_project_binding(
        project_id=kwargs["project_id"],
        objective_revision_ref={
            "kind": "objective_revision",
            "id": kwargs["objective_revision"]["objective_revision_id"],
        },
        boundary=kwargs["boundary"],
        authority_policy_ref=kwargs["authority_policy_ref"],
        source_registrations=kwargs["source_registrations"],
        command_policy=kwargs["command_policy"],
        secret_exclusion_policy=kwargs["secret_exclusion_policy"],
        human_authority_ref=kwargs["human_authority_ref"],
        human_authority_signing_key=rebound_human_authority_signing_key(),
        bound_at=kwargs["bound_at"],
        schema_root=SCHEMA_ROOT,
    )
    commit_records(
        store,
        project_id,
        store.load_current(project_id),
        transaction_id,
        [("project_binding", rebound["project_binding_id"], rebound)],
    )
    return rebound


def sign_alternate_github_projection_grant_declaration(**payload_fields: Any) -> dict[str, Any]:
    """Sign the identical canonical declaration payload
    :func:`tests.fixtures.product_binding.sign_github_projection_grant_declaration` signs, with
    the alternate world's own private key -- so the alternate world's declarations are
    genuinely valid *there*, and genuinely foreign everywhere else."""

    from manosube_agent_civilization.binding.identity import (
        github_projection_grant_declaration_signing_payload,
    )

    payload_record = {"schema_version": "0.1", **payload_fields}
    message = github_projection_grant_declaration_signing_payload(payload_record)
    return {
        "algorithm": "ed25519",
        "key_id": alternate_human_authority_signing_key()["key_id"],
        "value": _alternate_signing_private_key().sign(message).hex(),
    }


def commit_records(
    store: FileStateStore,
    project_id: str,
    current_state: dict[str, Any],
    transaction_id: str,
    records: list[tuple[str, str, Mapping[str, Any]]],
    *,
    committed_at: str = "2026-09-09T00:00:00Z",
) -> dict[str, Any]:
    """Commit *records* over *current_state* and return the resulting next State -- the
    identical shared shape every fixture-side commit in this repository's own test suite
    uses (deliberately bypasses :func:`~manosube_agent_civilization.runtime.route.
    observe_runtime_target`'s own single sanctioned committer, since this helper exists only
    to seed pre-existing world state a real route call then observes/consumes)."""

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


def canonical_signing_private_key() -> Ed25519PrivateKey:
    """The canonical fixture Human Authority's own fixed, deterministic, test-only Ed25519
    private key -- the private half of ``tests.fixtures.product_binding``'s own
    :func:`~tests.fixtures.product_binding.human_authority_signing_key`, and therefore the one
    key a canonical world's own Boot-restored Project Binding actually verifies against.

    A real Human's private key never touches this system (see
    ``manosube_agent_civilization.binding.signature``'s own module docstring, which only ever
    verifies); this is a test signer, exactly as every other signing helper in this repository's
    own fixture layer is.
    """

    return _canonical_signing_private_key()


def sign_runtime_deployment_declaration(
    declaration: Mapping[str, Any], *, private_key: Ed25519PrivateKey, key_id: str
) -> dict[str, Any]:
    """Sign the exact canonical payload
    :func:`~manosube_agent_civilization.runtime.identity.
    runtime_deployment_declaration_signing_payload` derives from *declaration*'s own adopted
    semantic fields (Phase 15 Structural Review Round 2, P15-R2-F2) -- the identical sibling of
    ``tests.fixtures.product_binding``'s own ``sign_github_projection_grant_declaration``, over
    a Runtime Deployment Declaration's own restated fields instead.
    """

    message = runtime_deployment_declaration_signing_payload(dict(declaration))
    return {
        "algorithm": "ed25519",
        "key_id": key_id,
        "value": private_key.sign(message).hex(),
    }


def deployment_declaration_for(
    project_id: str,
    project_binding_id: str,
    human_authority_ref: Mapping[str, Any],
    *,
    provider: str = "local",
    deployment_id: str = "widget-service",
    instance_identity: str = "widget-service-1",
    deployment_fingerprint: str = DEFAULT_DEPLOYMENT_FINGERPRINT,
    status: str = "ACTIVE",
    declared_at: str = "2026-09-08T00:00:00Z",
    valid_from: str = DEFAULT_VALID_FROM,
    valid_until: str = DEFAULT_VALID_UNTIL,
    signer: Ed25519PrivateKey | None = None,
    signing_key_id: str | None = None,
) -> dict[str, Any]:
    """Return one real, schema-valid, content-addressed, genuinely Ed25519-signed
    ``runtime_deployment_declaration`` body (Round 1, P15-R1-F6; signed and status-bound by
    Round 2, P15-R2-F2) -- the canonical record a target's own declared
    ``deployment_fingerprint`` must now match, minted through the real identity owner exactly as
    every other fixture in this repository mints a content-addressed record.

    *signer*/*signing_key_id* default to the canonical fixture Human Authority's own key pair --
    the identical ``signer``-with-a-canonical-default convention :func:`commit_declaration`
    already uses in this same module -- so a test that simply wants a legitimate declaration
    gets one, while a negative control passes an attacker's, an alternate world's, or a
    pre-re-binding key explicitly.

    The signature is produced over the body *before* either digest field exists (a signature
    cannot cover its own value; an identity cannot be computed over itself), and both digests
    are then computed over the identical payload the signature covers -- the shared-derivation
    discipline ``binding/identity.py``'s own declaration payloads already establish.
    """

    declaration: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": project_id,
        "project_binding_ref": {"kind": "project_binding", "id": project_binding_id},
        "provider": provider,
        "deployment_id": deployment_id,
        "instance_identity": instance_identity,
        "deployment_fingerprint": deployment_fingerprint,
        "human_authority_ref": dict(human_authority_ref),
        "status": status,
        "declared_at": declared_at,
        "valid_from": valid_from,
        "valid_until": valid_until,
    }
    declaration["signature"] = sign_runtime_deployment_declaration(
        declaration,
        private_key=signer if signer is not None else canonical_signing_private_key(),
        key_id=(
            signing_key_id
            if signing_key_id is not None
            else str(human_authority_signing_key()["key_id"])
        ),
    )
    declaration["runtime_deployment_declaration_id"] = runtime_deployment_declaration_id(
        declaration
    )
    declaration["runtime_deployment_declaration_semantic_fingerprint"] = (
        runtime_deployment_declaration_semantic_fingerprint(declaration)
    )
    return declaration


def commit_deployment_declaration(
    store: FileStateStore,
    project_id: str,
    declaration: Mapping[str, Any],
    *,
    committed_at: str = "2026-09-09T00:00:00Z",
) -> dict[str, str]:
    """Commit *declaration* through the **shipped** canonical commit-and-supersede path and
    return the reference naming it (P15-R3-F2).

    Before Round 3 this helper inserted the record with a raw fixture-side
    :func:`commit_records`. It now calls
    :func:`~manosube_agent_civilization.runtime.commit_runtime_deployment_declaration`, which
    commits the immutable record **and** moves this target's own current-declaration pointer
    (``semantic_state.runtime.claims[<target_key>]``) in one atomic State transition -- so every
    positive-path test in this repository genuinely populates the pointer the route now requires,
    and every negative control that deliberately bypasses this path (a forged, tampered, or
    never-registered record inserted with :func:`commit_records`) is refused for exactly the
    reason its own name claims.

    Issuing any *later* declaration for the same target through this same helper supersedes this
    one, whatever either record's own ``status`` says -- which is the entire mechanism the
    revoked-after-issuance and superseded controls exercise.
    """

    result = commit_runtime_deployment_declaration(
        store, project_id, dict(declaration), committed_at=committed_at
    )
    return dict(result["runtime_deployment_declaration_ref"])


def target_identity_for(
    project_binding_id: str,
    *,
    deployment_declaration_ref: Mapping[str, str],
    provider: str = "local",
    deployment_id: str = "widget-service",
    instance_identity: str = "widget-service-1",
    deployment_fingerprint: str = DEFAULT_DEPLOYMENT_FINGERPRINT,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "deployment_id": deployment_id,
        "instance_identity": instance_identity,
        "project_binding_ref": {"kind": "project_binding", "id": project_binding_id},
        "deployment_declaration_ref": dict(deployment_declaration_ref),
        "deployment_fingerprint": deployment_fingerprint,
    }


def commit_target_identity(
    store: FileStateStore,
    project_id: str,
    project_binding_id: str,
    human_authority_ref: Mapping[str, Any],
    *,
    provider: str = "local",
    deployment_id: str = "widget-service",
    instance_identity: str = "widget-service-1",
    deployment_fingerprint: str = DEFAULT_DEPLOYMENT_FINGERPRINT,
    status: str = "ACTIVE",
    declared_at: str = "2026-09-08T00:00:00Z",
    valid_from: str = DEFAULT_VALID_FROM,
    valid_until: str = DEFAULT_VALID_UNTIL,
    signer: Ed25519PrivateKey | None = None,
    signing_key_id: str | None = None,
) -> dict[str, Any]:
    """Commit the canonical, ACTIVE, genuinely signed, in-window ``runtime_deployment_declaration``
    anchoring this target -- through the shipped commit-and-supersede path, so it is also this
    target's own *current* declaration -- and return the matching ``target_identity``
    referencing it. The one helper every V1-V5 test uses now that
    ``deployment_declaration_ref`` is a required, Store-resolved, Authority-bound,
    signature-verified, in-window, currently-registered field (P15-R1-F6, P15-R2-F2,
    P15-R3-F2)."""

    declaration = deployment_declaration_for(
        project_id,
        project_binding_id,
        human_authority_ref,
        provider=provider,
        deployment_id=deployment_id,
        instance_identity=instance_identity,
        deployment_fingerprint=deployment_fingerprint,
        status=status,
        declared_at=declared_at,
        valid_from=valid_from,
        valid_until=valid_until,
        signer=signer,
        signing_key_id=signing_key_id,
    )
    ref = commit_deployment_declaration(store, project_id, declaration)
    return target_identity_for(
        project_binding_id,
        deployment_declaration_ref=ref,
        provider=provider,
        deployment_id=deployment_id,
        instance_identity=instance_identity,
        deployment_fingerprint=deployment_fingerprint,
    )


def boundary_for(
    *,
    base_url: str = "http://127.0.0.1:1",
    path: str = "/health",
    permitted_fields: list[str] | None = None,
    issued_at: str = "2026-01-01T00:00:00Z",
    expires_at: str = "2026-01-01T01:00:00Z",
    allowed_hosts: list[str] | None = None,
    timeout_seconds: int = 5,
    redaction_fields: list[str] | None = None,
    expected_field: str | None = None,
    expected_value: Any = None,
) -> dict[str, Any]:
    boundary: dict[str, Any] = {
        "observation_method": "HTTP_GET_BOUNDED",
        "endpoint": {"base_url": base_url, "path": path},
        "permitted_fields": list(permitted_fields if permitted_fields is not None else ["status"]),
        "time_window": {"issued_at": issued_at, "expires_at": expires_at},
        "network_scope": {
            "allowed_hosts": list(allowed_hosts if allowed_hosts is not None else ["127.0.0.1"])
        },
        "timeout_seconds": timeout_seconds,
        "redaction_fields": list(redaction_fields if redaction_fields is not None else []),
    }
    if expected_field is not None:
        boundary["expected_field"] = expected_field
        boundary["expected_value"] = expected_value
    return boundary


def commit_grant(
    store: FileStateStore,
    project_id: str,
    human_authority_ref: dict[str, Any],
    transaction_id: str,
    *,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any] | None = None,
    payload_fingerprint: str,
    permitted_action: str = "MATERIALIZE_PROJECTION",
    status: str = "ACTIVE",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Commit one real, genuine, Store-resolvable ``github_projection_grant`` and return
    ``(ref, grant)`` -- needed by V5's own bootstrap continuity proof, mirroring
    ``test_project_to_github.py``'s own identical helper exactly."""

    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "github_projection_grant_id": "",
        "project_id": project_id,
        "subject_ref": dict(subject_ref),
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": dict(target_repository or TARGET_REPOSITORY),
        "payload_fingerprint": payload_fingerprint,
        "permitted_action": permitted_action,
        "status": status,
        "granted_by": dict(human_authority_ref),
    }
    grant["github_projection_grant_id"] = github_projection_grant_id(grant)
    current_state = store.load_current(project_id)
    commit_records(
        store,
        project_id,
        current_state,
        transaction_id,
        [("github_projection_grant", grant["github_projection_grant_id"], grant)],
    )
    return {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}, grant


def commit_declaration(
    store: FileStateStore,
    project_id: str,
    project_binding_id: str,
    human_authority_ref: dict[str, Any],
    grant: dict[str, Any],
    *,
    status: str = "ACTIVE",
    declared_at: str = "2026-09-08T00:00:00Z",
    signer: Any = None,
) -> dict[str, Any]:
    """Declare and commit one real, genuinely Ed25519-signed
    ``github_projection_grant_declaration`` through the real, fail-closed committing route
    -- never a raw record insert, mirroring ``test_project_to_github.py``'s own identical
    helper exactly.

    *signer* defaults to the canonical fixture Human Authority's own signing helper; the
    alternate world (P15-R1-F4) passes
    :func:`sign_alternate_github_projection_grant_declaration` instead, so its declarations
    are signed by its own genuinely different key.
    """

    sign = signer or sign_github_projection_grant_declaration
    grant_ref = {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}
    signature = sign(
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
        status=status,
        declared_at=declared_at,
    )
    result = declare_github_projection_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        status=status,
        declared_at=declared_at,
        signature=signature,
        schema_root=SCHEMA_ROOT,
    )
    declaration = result["github_projection_grant_declaration"]
    return {
        "kind": "github_projection_grant_declaration",
        "id": declaration["github_projection_grant_declaration_id"],
    }


__all__ = [
    "ALTERNATE_HUMAN_AUTHORITY_REF",
    "DEFAULT_DEPLOYMENT_FINGERPRINT",
    "DEFAULT_VALID_FROM",
    "DEFAULT_VALID_UNTIL",
    "DEPLOYMENT_DECLARATION_RECORD_KIND",
    "REBOUND_SIGNING_KEY_ID",
    "ROOT_ADMISSION_RECORD_KIND",
    "TARGET_REPOSITORY",
    "admitted_root",
    "alternate_bound",
    "alternate_human_authority_signing_key",
    "alternate_signing_private_key",
    "bound",
    "boundary_for",
    "canonical_signing_private_key",
    "commit_declaration",
    "commit_deployment_declaration",
    "commit_grant",
    "commit_records",
    "commit_root_admission",
    "commit_target_identity",
    "deployment_declaration_for",
    "foreign_trust_anchor_private_key",
    "human_authority_signing_key",
    "rebind_with_rotated_signing_key",
    "rebound_human_authority_signing_key",
    "rebound_signing_private_key",
    "root_admission_for",
    "sign_alternate_github_projection_grant_declaration",
    "sign_runtime_deployment_declaration",
    "sign_runtime_root_admission",
    "target_identity_for",
    "trust_anchor_private_key",
    "trust_anchor_public_key_hex",
    "trusted_runtime_root",
]
