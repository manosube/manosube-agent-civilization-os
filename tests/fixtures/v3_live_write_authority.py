"""Genuine, verified SHUKOU/Human Authority for V3 live-write execution (Structural Review
Round 6, Issue #62, P14-R6-F2).

Round 5's own ``v3_live_write_authorized`` required only that a caller-supplied environment
variable equal :attr:`~tests.fixtures.v3_target_configuration.V3TargetConfiguration.
configuration_fingerprint` -- a value any caller can itself compute from the frozen
configuration alone, with no Human Authority behind it at all. Structural Review Round 6
requires the genuine article: a signed **V3 Live Write Authority** record, binding the exact
configuration fingerprint, target repository, permitted action, authorized artifact kinds and
count, and the cleanup/no-merge boundary, verified against one fixed, non-caller-controlled
public key -- the identical Ed25519 verification primitive
(:func:`~manosube_agent_civilization.binding.signature.verify_ed25519_signature`) this
repository's own signed Human Grant Declarations already use, applied here to a distinct
record shape this V3 harness alone needs.

**A caller-computable digest, a bare credential, an environment-variable's mere presence, or
network capability alone never grants this authority.** :func:`v3_live_write_authorized`
performs pure comparison plus one signature verification -- no I/O of its own, and in
particular no network access -- so an unauthorized or mismatched authority record is refused
before this harness could ever reach a live call on its strength.

This record is a harness-execution permission, never a canonical Kernel record: it is never
persisted through the Store, never a Difference/Change/Evidence/Authority Decision, and this
module is deliberately test-only, exactly as :mod:`tests.fixtures.v3_target_configuration`
already is for the configuration it binds.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import os
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from manosube_agent_civilization.binding.signature import verify_ed25519_signature
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .v3_target_configuration import V3TargetConfiguration

#: The one closed permitted-action literal a genuine V3 Live Write Authority record may name
#: -- never left open-ended, so a record naming any other action can never be silently
#: accepted as authorizing this harness's own live execution.
V3_LIVE_WRITE_PERMITTED_ACTION = "MATERIALIZE_V3_PROOF_RUN"

#: The one status literal that counts as a currently-granted authority -- anything else
#: (``"REVOKED"``, a typo, an absent field) refuses.
_ACTIVE_STATUS = "ACTIVE"

#: The environment variable carrying the complete, JSON-encoded V3 Live Write Authority
#: record -- deliberately distinct from every :data:`~tests.fixtures.v3_target_configuration.
#: ALL_V3_ENV_VARS` name, so configuration validity and this authority remain two
#: independently-gated inputs, exactly as Structural Review Round 4 (P14-R4-F3) already
#: established for the (now superseded) unscoped boolean.
V3_LIVE_WRITE_AUTHORITY_RECORD_ENV = "MANOSUBE_P14_V3_LIVE_WRITE_AUTHORITY_RECORD"

#: Every field a V3 Live Write Authority record's own signature covers, in the exact order
#: the canonical signing payload restates them -- one dedicated signing-payload function per
#: signed record shape, the identical convention
#: ``binding/identity.py``'s own ``github_projection_grant_declaration_signing_payload`` and
#: ``human_grant_declaration_signing_payload`` already establish (never one shared generic
#: function two differently-shaped records both feed).
_SIGNED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "configuration_fingerprint",
    "target_repository",
    "permitted_action",
    "authorized_artifact_kinds",
    "authorized_artifact_count",
    "cleanup_confirmed",
    "no_merge_confirmed",
    "status",
    "valid_from",
    "valid_until",
)


class V3LiveWriteAuthorityError(RuntimeError):
    """Raised only by this module's own test-side signing helpers on a malformed input --
    never by :func:`v3_live_write_authorized` itself, which always fails closed as a plain
    ``False`` rather than raising (the identical "fail closed as a value" convention this
    Kernel's own verifier functions already use, so a caller can compose it into a total
    decision without a try/except of its own)."""


def v3_live_write_authority_signing_payload(record: Mapping[str, Any]) -> bytes:
    """The exact canonical bytes a V3 Live Write Authority record's own signature covers --
    every bound field, canonically serialized, deliberately excluding ``signature`` itself (a
    signature can never cover its own bytes)."""

    payload: dict[str, Any] = {}
    for field in _SIGNED_FIELDS:
        if field not in record:
            raise V3LiveWriteAuthorityError(f"record is missing required field {field!r}")
        payload[field] = record[field]
    kinds = payload["authorized_artifact_kinds"]
    if isinstance(kinds, frozenset | set):
        payload["authorized_artifact_kinds"] = sorted(kinds)
    return canonical_json_bytes(payload)


def _signing_private_key() -> Ed25519PrivateKey:
    """A fixed, deterministic, test-only Ed25519 private key for the dedicated V3 Live Write
    Authority signer -- a distinct key from the Project Binding's own
    ``human_authority_signing_key`` (``tests/fixtures/product_binding.py``), since V3
    live-write authority is a harness-execution permission bound to one exact configuration
    and target, never a Project-scoped projection grant. Never a real Human's private key,
    which never touches this system's production code at all -- this module, like
    ``binding.signature``, only ever verifies in any path a real caller reaches."""

    seed = hashlib.sha256(b"tests.fixtures.v3_live_write_authority signing_key").digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def v3_authority_signing_key() -> dict[str, str]:
    """The real, fixed, non-caller-controlled public verification key a genuine V3 Live
    Write Authority record must be signed by -- the one value :func:`v3_live_write_authorized`
    ever trusts, never itself supplied or computed by whatever is requesting live-write
    authority."""

    public_bytes = (
        _signing_private_key()
        .public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    )
    return {
        "algorithm": "ed25519",
        "key_id": "V3-AUTHORITY-KEY-0001",
        "public_key": public_bytes.hex(),
    }


def sign_v3_live_write_authority(record: Mapping[str, Any]) -> dict[str, str]:
    """Sign *record*'s own canonical payload with the dedicated V3 authority private key --
    test-only; the private key never touches production code (see the module docstring)."""

    message = v3_live_write_authority_signing_payload(record)
    signature_bytes = _signing_private_key().sign(message)
    return {
        "algorithm": "ed25519",
        "key_id": v3_authority_signing_key()["key_id"],
        "value": signature_bytes.hex(),
    }


def assemble_v3_live_write_authority(
    *,
    configuration_fingerprint: str,
    target_repository: Mapping[str, str],
    authorized_artifact_kinds: frozenset[str],
    authorized_artifact_count: int,
    cleanup_confirmed: bool = True,
    no_merge_confirmed: bool = True,
    status: str = _ACTIVE_STATUS,
    valid_from: str,
    valid_until: str,
    permitted_action: str = V3_LIVE_WRITE_PERMITTED_ACTION,
) -> dict[str, Any]:
    """Assemble and sign one complete V3 Live Write Authority record -- test-only, since
    genuine authority is never self-issued by a caller of :func:`v3_live_write_authorized`.
    *permitted_action* defaults to the one closed literal this mechanism ever authorizes;
    callers proving the wrong-action negative control pass a different value explicitly."""

    record: dict[str, Any] = {
        "schema_version": "0.1",
        "configuration_fingerprint": configuration_fingerprint,
        "target_repository": dict(target_repository),
        "permitted_action": permitted_action,
        "authorized_artifact_kinds": sorted(authorized_artifact_kinds),
        "authorized_artifact_count": authorized_artifact_count,
        "cleanup_confirmed": cleanup_confirmed,
        "no_merge_confirmed": no_merge_confirmed,
        "status": status,
        "valid_from": valid_from,
        "valid_until": valid_until,
    }
    record["signature"] = sign_v3_live_write_authority(record)
    return record


def load_v3_live_write_authority_record(
    env: Mapping[str, str] | None = None,
) -> Mapping[str, Any] | None:
    """Read and JSON-decode :data:`V3_LIVE_WRITE_AUTHORITY_RECORD_ENV`, or return ``None`` if
    unset, unparseable, or not a JSON object -- the identical "malformed input is simply no
    authority, never an exception" discipline every other check here applies. *env* defaults
    to :data:`os.environ`; performs no network access, identically to
    :mod:`tests.fixtures.v3_target_configuration`."""

    source = env if env is not None else os.environ
    raw = source.get(V3_LIVE_WRITE_AUTHORITY_RECORD_ENV)
    if raw is None:
        return None
    try:
        record = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def v3_live_write_authorized(
    config: V3TargetConfiguration | None,
    authority_record: Mapping[str, Any] | None,
    *,
    evaluation_time: str,
) -> bool:
    """Return whether *authority_record* is a genuine, currently-valid SHUKOU/Human Authority
    grant of live-write execution for *config* (Structural Review Round 6, Issue #62,
    P14-R6-F2) -- the complete configuration-fingerprint, target-repository, permitted-action,
    artifact-kinds/count, cleanup/no-merge, and validity binding this finding requires, never
    a caller-computable digest or a bare environment-variable's presence.

    Performs no I/O of its own -- pure comparison plus one Ed25519 signature verification
    (:func:`~manosube_agent_civilization.binding.signature.verify_ed25519_signature`) against
    the one fixed, non-caller-controlled public key (:func:`v3_authority_signing_key`).
    ``config=None``, ``authority_record=None``, or *authority_record* not even being a mapping
    (e.g. a bare digest string a caller computed themselves) all return ``False`` immediately,
    with zero further comparison and zero signature verification. *evaluation_time* is always an
    explicit caller-supplied input, never a wall-clock read inside this function -- the
    identical discipline ``authority/engine.py``'s own ``evaluate_authority`` already applies
    for its own ``evaluation_time``."""

    if config is None or authority_record is None or not isinstance(authority_record, Mapping):
        return False

    if authority_record.get("permitted_action") != V3_LIVE_WRITE_PERMITTED_ACTION:
        return False
    if authority_record.get("status") != _ACTIVE_STATUS:
        return False
    valid_from = authority_record.get("valid_from")
    valid_until = authority_record.get("valid_until")
    if not isinstance(valid_from, str) or not isinstance(valid_until, str):
        return False
    if not (valid_from <= evaluation_time <= valid_until):
        return False

    if authority_record.get("configuration_fingerprint") != config.configuration_fingerprint:
        return False
    if authority_record.get("target_repository") != config.target_repository:
        return False
    record_kinds = authority_record.get("authorized_artifact_kinds")
    if not isinstance(record_kinds, list):
        return False
    if frozenset(record_kinds) != config.authorized_artifact_kinds:
        return False
    if authority_record.get("authorized_artifact_count") != config.authorized_artifact_count:
        return False
    if authority_record.get("cleanup_confirmed") is not True:
        return False
    if authority_record.get("no_merge_confirmed") is not True:
        return False

    signature = authority_record.get("signature")
    if not isinstance(signature, dict):
        return False
    signing_key = v3_authority_signing_key()
    if signature.get("algorithm") != signing_key["algorithm"]:
        return False
    if signature.get("key_id") != signing_key["key_id"]:
        return False
    signature_hex = signature.get("value")
    if not isinstance(signature_hex, str):
        return False
    try:
        message = v3_live_write_authority_signing_payload(authority_record)
    except V3LiveWriteAuthorityError:
        return False
    return verify_ed25519_signature(
        public_key_hex=signing_key["public_key"], message=message, signature_hex=signature_hex
    )
