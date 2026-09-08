"""Genuine, verified SHUKOU/Human Authority for V3 live-write execution (Structural Review
Round 6, Issue #62, P14-R6-F2; external trust anchor, Structural Review Round 7, P14-R7-F1).

Round 5's own ``v3_live_write_authorized`` required only that a caller-supplied environment
variable equal :attr:`~tests.fixtures.v3_target_configuration.V3TargetConfiguration.
configuration_fingerprint` -- a value any caller can itself compute from the frozen
configuration alone, with no Human Authority behind it at all. Structural Review Round 6
replaced that with a genuine Ed25519-signed record, verified with the identical
:func:`~manosube_agent_civilization.binding.signature.verify_ed25519_signature` primitive this
repository's own signed Human Grant Declarations already use.

Round 6's own implementation, however, kept the matching **private** signing key in the same
importable module as the verifier (:func:`v3_live_write_authorized`) and exposed a public
``assemble_v3_live_write_authority`` capable of minting a fully ``ACTIVE`` record for any
caller-selected configuration/target/boundary -- a caller-computable *signature* in place of
Round 5's caller-computable *digest*, without changing who actually controls authorization.
Structural Review Round 7 (P14-R7-F1) corrects this: **this module now contains only
verification** -- a fixed, non-caller-controlled public trust anchor
(:data:`V3_LIVE_TRUST_ANCHOR`) and the pure comparison/signature-check logic
(:func:`v3_live_write_authorized`) -- and defines no private key, no signing helper, and no
authority-issuance capability of any kind. Nothing this module exports, and nothing any shipped
module (``src/manosube_agent_civilization``) exports, can mint a record this module's own live
call site (``_v3_live_authorized()`` in
``tests/integration/projection/test_v3_real_github_vertical_proof.py``) would ever accept.

The genuinely signed article a live V3 gate would consume must therefore be issued entirely
outside this repository, through the existing canonical Authority/Binding route SHUKOU already
uses for real Human declarations -- exactly as :mod:`manosube_agent_civilization.binding.
signature`'s own docstring already states for Project Binding's Human Authority key: "the
Human's own private key never touches this system at all, only the public verification key."
This module applies the identical discipline to the V3 harness's own bounded execution
permission.

A dedicated, clearly test-only signer
(:mod:`tests.fixtures.v3_live_write_authority_test_signer`) exists purely so this module's own
verification logic can be exercised offline, under an explicitly injected *test* trust anchor
distinct from :data:`V3_LIVE_TRUST_ANCHOR` -- this module never imports that signer, and
:func:`v3_live_write_authorized` never falls back to any trust anchor other than the one its
caller explicitly supplies, so a test-signed record can never be silently accepted by the one
live call site, which always supplies :data:`V3_LIVE_TRUST_ANCHOR` and nothing else.

This record is a harness-execution permission, never a canonical Kernel record: it is never
persisted through the Store, never a Difference/Change/Evidence/Authority Decision, and this
module is deliberately test-only, exactly as :mod:`tests.fixtures.v3_target_configuration`
already is for the configuration it binds.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import os
from typing import Any

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

#: The fixed, non-caller-controlled public verification key the one live call site
#: (``_v3_live_authorized()``) always and only consults (Structural Review Round 7,
#: P14-R7-F1). No private key matching this public key exists anywhere in this repository,
#: its runtime package, or any importable module -- it was generated once, outside any
#: persisted process, and the private key was discarded; nothing in this codebase can produce
#: a signature this trust anchor would accept. A genuine V3 Live Write Authority artifact must
#: be issued entirely outside this repository, through the existing canonical Authority/
#: Binding route, and handed to this harness only via :data:`V3_LIVE_WRITE_AUTHORITY_RECORD_
#: ENV` -- this constant is never itself sufficient to construct one.
V3_LIVE_TRUST_ANCHOR: Mapping[str, str] = {
    "algorithm": "ed25519",
    "key_id": "V3-LIVE-TRUST-ANCHOR-0001",
    "public_key": "bc9c2ae0d18920def2125379f70ce6d99eeeaece5d7940a21b0e30d1858016bd",
}

#: Every field a V3 Live Write Authority record's own signature covers, in the exact order
#: the canonical signing payload restates them -- one dedicated signing-payload function per
#: signed record shape, the identical convention
#: ``binding/identity.py``'s own ``github_projection_grant_declaration_signing_payload`` and
#: ``human_grant_declaration_signing_payload`` already establish (never one shared generic
#: function two differently-shaped records both feed). Shared, read-only, and used identically
#: by both this module's verifier and the test-only signer -- constructing this payload never
#: requires possessing any private key.
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
    """Raised only by :func:`v3_live_write_authority_signing_payload` on a malformed input --
    never by :func:`v3_live_write_authorized` itself, which always fails closed as a plain
    ``False`` rather than raising (the identical "fail closed as a value" convention this
    Kernel's own verifier functions already use, so a caller can compose it into a total
    decision without a try/except of its own)."""


def v3_live_write_authority_signing_payload(record: Mapping[str, Any]) -> bytes:
    """The exact canonical bytes a V3 Live Write Authority record's own signature covers --
    every bound field, canonically serialized, deliberately excluding ``signature`` itself (a
    signature can never cover its own bytes). Pure and read-only: constructing this payload
    requires no private key and grants no authority by itself -- both the live verifier here
    and the dedicated test-only signer (:mod:`tests.fixtures.v3_live_write_authority_test_
    signer`) call this identical function so the two sides can never silently diverge on what
    a signature actually covers."""

    payload: dict[str, Any] = {}
    for field in _SIGNED_FIELDS:
        if field not in record:
            raise V3LiveWriteAuthorityError(f"record is missing required field {field!r}")
        payload[field] = record[field]
    kinds = payload["authorized_artifact_kinds"]
    if isinstance(kinds, frozenset | set):
        payload["authorized_artifact_kinds"] = sorted(kinds)
    return canonical_json_bytes(payload)


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
    trust_anchor: Mapping[str, str],
) -> bool:
    """Return whether *authority_record* is a genuine, currently-valid SHUKOU/Human Authority
    grant of live-write execution for *config*, verified against *trust_anchor* (Structural
    Review Round 6, Issue #62, P14-R6-F2; external trust anchor, Structural Review Round 7,
    P14-R7-F1) -- the complete configuration-fingerprint, target-repository, permitted-action,
    artifact-kinds/count, cleanup/no-merge, and validity binding this finding requires, never
    a caller-computable digest or a bare environment-variable's presence.

    *trust_anchor* is a required, explicit keyword-only argument, never a module-level default
    silently consulted -- this is the one structural property that makes "caller-selected
    trust roots on the live path" impossible: the one live call site
    (``_v3_live_authorized()``) always and only passes :data:`V3_LIVE_TRUST_ANCHOR`, hardcoded,
    with no environment variable, record field, or other caller-reachable input able to
    substitute a different value for it. A test explicitly passing its own test-only trust
    anchor (:data:`~tests.fixtures.v3_live_write_authority_test_signer.V3_TEST_TRUST_ANCHOR`)
    is exercising this same pure function with different, legitimately injected inputs --
    exactly how any pure verifier is unit tested -- never a change to what the live path itself
    consults.

    Performs no I/O of its own -- pure comparison plus one Ed25519 signature verification
    (:func:`~manosube_agent_civilization.binding.signature.verify_ed25519_signature`) against
    *trust_anchor*. ``config=None``, ``authority_record=None``, or *authority_record* not even
    being a mapping (e.g. a bare digest string a caller computed themselves) all return
    ``False`` immediately, with zero further comparison and zero signature verification.
    *evaluation_time* is always an explicit caller-supplied input, never a wall-clock read
    inside this function -- the identical discipline ``authority/engine.py``'s own
    ``evaluate_authority`` already applies for its own ``evaluation_time``."""

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
    if signature.get("algorithm") != trust_anchor["algorithm"]:
        return False
    if signature.get("key_id") != trust_anchor["key_id"]:
        return False
    signature_hex = signature.get("value")
    if not isinstance(signature_hex, str):
        return False
    try:
        message = v3_live_write_authority_signing_payload(authority_record)
    except V3LiveWriteAuthorityError:
        return False
    return verify_ed25519_signature(
        public_key_hex=trust_anchor["public_key"], message=message, signature_hex=signature_hex
    )
