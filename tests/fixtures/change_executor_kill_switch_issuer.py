"""The genuinely external issuer of Change Executor's own test kill-switch authority.

Deliberately isolated from :mod:`manosube_agent_civilization.change_executor.kill_switch`, the
shipped module that ever *verifies* a kill switch's own signature
(:func:`~manosube_agent_civilization.change_executor.kill_switch.commit_change_executor_kill_switch`)
-- the identical issuer/verifier separation Phase 17 Round 5 established for URL Boot's own
disposable-local-test authority (``tests/fixtures/url_boot_local_test_issuer.py``). Unlike that
package, ``change_executor.kill_switch`` never hardcodes a trust-anchor public key of its own at
all -- every verifying call site takes ``trust_anchor_public_key_hex`` as an explicit, caller-
supplied parameter (never read from the Store, never baked into shipped source) -- so this module
needs no separate "verifier" fixture module the way URL Boot's own composition boundary does: the
shipped verify-only code already holds no key of its own to duplicate, and this module's own
:func:`issuer_public_key_hex` is simply handed to ``compose_change_executor`` (or
``commit_change_executor_kill_switch``) directly by a test as the trust anchor.

This module holds the one Ed25519 private key that ever signs a genuine test kill-switch record
for this suite. Nothing under ``src/manosube_agent_civilization/change_executor/`` imports this
module, references its key material, or could mint a signature of its own -- ``kill_switch.py``
only ever verifies (see that module's own docstring), a fact this repository's own static
conformance test confirms by AST import inspection.

Mirrors this repository's own established Ed25519-anchored trusted-authority idiom: a
deterministic, fixed, disclosed-as-test-only keypair (``hashlib.sha256(<fixed descriptive
string>).digest()`` seeds ``Ed25519PrivateKey.from_private_bytes``), never
``Ed25519PrivateKey.generate()``, so every test run signs against the identical bytes.
"""

from __future__ import annotations

import hashlib
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

#: Duplicated nowhere else -- see this module's own docstring for why no separate "verifier"
#: constant is needed: the shipped ``kill_switch.py`` never hardcodes a trust anchor of its own.
KEY_ID = "CHANGE-EXECUTOR-KILL-SWITCH-TEST-ISSUER-0001"


def _issuer_private_key() -> Ed25519PrivateKey:
    seed = hashlib.sha256(
        b"tests.fixtures.change_executor_kill_switch_issuer disposable test private key"
    ).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def issuer_public_key_hex() -> str:
    """The one public key this issuer's own private key corresponds to -- the value a test
    hands to ``compose_change_executor``/``commit_change_executor_kill_switch`` as
    ``trust_anchor_public_key_hex`` (or ``kill_switch_trust_anchor_public_key_hex``)."""

    return (
        _issuer_private_key()
        .public_key()
        .public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
        .hex()
    )


def mint_kill_switch_signature(payload: bytes) -> dict[str, Any]:
    """Return a genuine ``{"algorithm", "key_id", "value"}`` signature block -- an Ed25519
    signature, by this module's own private key, over *payload* (the exact canonical bytes
    :func:`~manosube_agent_civilization.change_executor.kill_switch.kill_switch_signing_payload`
    computes for the record being signed). This is the *only* function in this repository able
    to produce a signature ``commit_change_executor_kill_switch`` accepts when verifying against
    :func:`issuer_public_key_hex`."""

    signature = _issuer_private_key().sign(payload)
    return {"algorithm": "ed25519", "key_id": KEY_ID, "value": signature.hex()}


def wrong_kill_switch_signature(payload: bytes) -> dict[str, Any]:
    """Return a structurally genuine, but wrong-key, signature block -- a real Ed25519
    signature over *payload*, by a second, entirely different fixed test keypair, never the one
    :func:`issuer_public_key_hex` names. The one negative-control minter this module carries:
    proves ``commit_change_executor_kill_switch`` refuses a signature that verifies against no
    trust anchor it was ever told to trust, as opposed to merely being malformed."""

    seed = hashlib.sha256(
        b"tests.fixtures.change_executor_kill_switch_issuer WRONG disposable test private key"
    ).digest()
    wrong_key = Ed25519PrivateKey.from_private_bytes(seed)
    signature = wrong_key.sign(payload)
    return {"algorithm": "ed25519", "key_id": KEY_ID, "value": signature.hex()}


__all__ = [
    "KEY_ID",
    "issuer_public_key_hex",
    "mint_kill_switch_signature",
    "wrong_kill_switch_signature",
]
