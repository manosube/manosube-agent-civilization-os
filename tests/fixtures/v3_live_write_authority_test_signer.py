"""Test-only signer for the V3 Live Write Authority record shape (Structural Review Round 7,
Issue #62, P14-R7-F1).

This is the dedicated, clearly test-only counterpart to
:mod:`tests.fixtures.v3_live_write_authority`, which -- as of Structural Review Round 7 -- is a
pure verifier holding only a fixed public trust anchor
(:data:`~tests.fixtures.v3_live_write_authority.V3_LIVE_TRUST_ANCHOR`) with no matching private
key. Exercising :func:`~tests.fixtures.v3_live_write_authority.v3_live_write_authorized`'s own
verification logic offline still requires *some* genuinely signed record to check it against;
this module supplies that, under an entirely distinct keypair
(:data:`V3_TEST_TRUST_ANCHOR`, ``key_id="V3-TEST-TRUST-ROOT-0001"``) that can never be mistaken
for, and can never verify against, the live trust anchor
(``key_id="V3-LIVE-TRUST-ANCHOR-0001"``).

**This module is never imported by** :mod:`tests.fixtures.v3_live_write_authority` **or by the
one live call site** (``_v3_live_authorized()`` in
``tests/integration/projection/test_v3_real_github_vertical_proof.py``) -- a static conformance
test (``tests/contract/projection/test_v3_live_write_authority_static_conformance.py``) proves
this by AST-walking both modules' own import statements. A record this module signs, even one naming
every bound field byte-for-byte identically to a genuine live grant, is verified only against
:data:`V3_TEST_TRUST_ANCHOR` -- passing it (or its signature) to the live verifier under
:data:`~tests.fixtures.v3_live_write_authority.V3_LIVE_TRUST_ANCHOR` always fails, because no
signature this module ever produces can validate against a public key it holds no matching
private key for.

The private key here is a fixed, deterministic, test-only value -- never a real Human's
private key, which never touches this system at all (see
:mod:`manosube_agent_civilization.binding.signature`'s own docstring for the identical
production discipline this module mirrors for offline testing purposes only).
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from .v3_live_write_authority import (
    V3_LIVE_WRITE_PERMITTED_ACTION,
    v3_live_write_authority_signing_payload,
)

#: The one status literal that counts as a currently-granted authority -- mirrors
#: :mod:`tests.fixtures.v3_live_write_authority`'s own identical private constant; duplicated
#: rather than imported across the module boundary since it is a plain literal, not shared
#: behavior.
_ACTIVE_STATUS = "ACTIVE"


def _test_signing_private_key() -> Ed25519PrivateKey:
    """A fixed, deterministic, test-only Ed25519 private key -- distinct from every other
    fixed test keypair this repository defines (Project Binding's own
    ``tests/fixtures/product_binding.py``'s ``human_authority_signing_key``, and any future
    signer), and, critically, distinct from and never able to produce a signature accepted by
    :data:`~tests.fixtures.v3_live_write_authority.V3_LIVE_TRUST_ANCHOR`. Never reachable from
    :mod:`tests.fixtures.v3_live_write_authority` or the live call site -- this module exists
    solely so offline tests can exercise genuine Ed25519 verification without ever holding the
    live trust anchor's own (nonexistent, in this repository) private key."""

    seed = hashlib.sha256(
        b"tests.fixtures.v3_live_write_authority_test_signer TEST-ONLY signing_key "
        b"-- never the live trust anchor, never reachable from the live gate"
    ).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def _test_trust_anchor() -> dict[str, str]:
    public_bytes = (
        _test_signing_private_key()
        .public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    )
    return {
        "algorithm": "ed25519",
        "key_id": "V3-TEST-TRUST-ROOT-0001",
        "public_key": public_bytes.hex(),
    }


#: The test-only trust anchor a caller must explicitly inject
#: (:func:`~tests.fixtures.v3_live_write_authority.v3_live_write_authorized`'s own
#: ``trust_anchor`` keyword argument) to verify a record this module signs. Structurally
#: distinct from :data:`~tests.fixtures.v3_live_write_authority.V3_LIVE_TRUST_ANCHOR` by both
#: ``key_id`` and ``public_key`` -- proven by a dedicated equality-refusal test.
V3_TEST_TRUST_ANCHOR: dict[str, str] = _test_trust_anchor()


def sign_v3_live_write_authority_for_test(record: Mapping[str, Any]) -> dict[str, str]:
    """Sign *record*'s own canonical payload with the test-only private key -- test-only; the
    resulting signature verifies only against :data:`V3_TEST_TRUST_ANCHOR`, never against the
    live trust anchor."""

    message = v3_live_write_authority_signing_payload(record)
    signature_bytes = _test_signing_private_key().sign(message)
    return {
        "algorithm": "ed25519",
        "key_id": V3_TEST_TRUST_ANCHOR["key_id"],
        "value": signature_bytes.hex(),
    }


def assemble_v3_live_write_authority_for_test(
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
    """Assemble and sign one complete V3 Live Write Authority record under the test-only
    trust anchor -- test-only, since genuine authority is never self-issued by a caller of
    :func:`~tests.fixtures.v3_live_write_authority.v3_live_write_authorized`.
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
    record["signature"] = sign_v3_live_write_authority_for_test(record)
    return record
