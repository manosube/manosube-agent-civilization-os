"""The genuinely external issuer of this repository's own disposable-local-test URL Boot
authority (Structural Review Round 5, P17-R5-F2, Issue #69).

Deliberately isolated from ``tests/fixtures/url_boot_local_test_authority.py`` -- the verifier
and composer that consumes this authority's own minted credential -- so that importing the
verifier/composer module alone can never yield a minting capability. This module holds the one
Ed25519 private key that ever signs a genuine local-test-harness credential; the verifier module
holds only the corresponding public key, a literal constant it carries independently, never
derived by importing this module at all. Neither module imports the other; a caller who imports
only ``url_boot_local_test_authority`` finds no mint function, no secret, and no way to reach one
through that module's own import graph.

Mirrors this repository's own established Ed25519-anchored trusted-authority idiom
(``runtime/bootstrap.py``'s own trust-anchor pattern, ``binding/signature.py``'s own
``verify_ed25519_signature``, reused directly by the verifier) rather than inventing a new scheme:
a deterministic, fixed, disclosed-as-test-only keypair
(``hashlib.sha256(<fixed descriptive string>).digest()`` seeds ``Ed25519PrivateKey.
from_private_bytes``), never ``Ed25519PrivateKey.generate()``, so every test run signs against the
identical bytes -- and, symmetrically, the verifier's own hardcoded public-key constant is exactly
this keypair's own public half (confirmed by this repository's own test suite, which imports both
modules together purely to assert that non-vacuous fact -- production code never does).

This closes the exact gap Structural Review Round 5 found in the prior HMAC-based design: minting
and verifying lived in the same module, sharing the same symmetric secret, so any caller able to
import the composer could mint valid authority for itself. Asymmetric signing genuinely separates
the two roles -- the verifier can confirm a credential without ever holding anything that could
produce one.
"""

from __future__ import annotations

import hashlib
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

#: The exact message every genuine local-test-harness credential is a signature over -- a fixed,
#: non-secret, public constant (never derived from caller-supplied data of any kind). Duplicated
#: verbatim, not imported, in the verifier module -- see that module's own docstring for why an
#: import edge between the two would undermine the separation this file exists to provide.
TEST_HARNESS_AUTHORITY_SIGNING_PAYLOAD: bytes = (
    b"url-boot-disposable-local-test-harness-authority-v2-ed25519"
)

#: Duplicated verbatim in the verifier module's own ``signature.key_id`` check.
TEST_HARNESS_AUTHORITY_KEY_ID = "URL-BOOT-LOCAL-TEST-AUTHORITY-0001"


def _issuer_private_key() -> Ed25519PrivateKey:
    seed = hashlib.sha256(
        b"tests.fixtures.url_boot_local_test_issuer disposable-local-test-harness private key"
    ).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def issuer_public_key_hex() -> str:
    """The one public key this issuer's own private key corresponds to. Present here only so this
    repository's own test suite can assert the verifier module's hardcoded constant equals it (a
    non-vacuity control proving the two modules' keys genuinely match rather than each silently
    trusting a different one) -- never consulted by the verifier itself at runtime, which carries
    its own independent, hardcoded copy of the same hex string rather than importing this
    function."""

    return (
        _issuer_private_key()
        .public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
        .hex()
    )


def mint_test_harness_authority() -> dict[str, Any]:
    """Return one genuine local-test-harness authority credential -- an Ed25519 signature, by
    this module's own private key, over :data:`TEST_HARNESS_AUTHORITY_SIGNING_PAYLOAD`.

    This is the *only* function in this repository able to produce a credential
    ``tests/fixtures/url_boot_local_test_authority.py``'s own verifier accepts; that module
    imports nothing from this one and cannot mint on its own. A test that wants to exercise the
    disposable-local-test composition legitimately must import *this* module -- a genuinely
    separate file from the one it then hands the resulting credential to -- the "genuine external
    issuer positive control" Structural Review Round 5 requires."""

    signature = _issuer_private_key().sign(TEST_HARNESS_AUTHORITY_SIGNING_PAYLOAD)
    return {
        "algorithm": "ed25519",
        "key_id": TEST_HARNESS_AUTHORITY_KEY_ID,
        "value": signature.hex(),
    }


__all__ = ["issuer_public_key_hex", "mint_test_harness_authority"]
