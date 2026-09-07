"""Ed25519 signature verification for Human Grant Declarations (Structural Review Round
5-R1, Issue #51, P13-R5-R1: ``CANONICAL_HUMAN_DECLARATION_ANCHOR``).

Binding owns this verification. Binding -- and this whole vertical -- never *generates* a
signature: the Human's own private key never touches this system at all, only the public
verification key a real, already-committed Project Binding canonically holds
(``human_authority_signing_key``). This module only verifies, read-only, that a caller-
supplied signature actually validates against that exact public key, over the exact
canonical bytes of the declaration's own adopted payload
(:func:`~manosube_agent_civilization.binding.identity.human_grant_declaration_signing_
payload`) -- never a looser check, never trusting the caller's own claim that a signature is
valid. Authority re-verifies the identical signature the identical way, imported lazily for
the same circular-import reason ``authority/conformance.py`` already documents for
``human_grant_declaration_id`` (P13-R5).

No network, no external key server, no hidden registry: the one public key ever consulted is
the one the real, Store-resolved Project Binding record itself already carries.
"""

from __future__ import annotations

from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .identity import human_grant_declaration_signing_payload

SUPPORTED_SIGNATURE_ALGORITHM = "ed25519"


def verify_ed25519_signature(*, public_key_hex: str, message: bytes, signature_hex: str) -> bool:
    """Whether *signature_hex* (a raw 64-byte Ed25519 signature, hex-encoded) is a genuine
    signature over *message* by the holder of the private key matching *public_key_hex* (a
    raw 32-byte Ed25519 public key, hex-encoded).

    Never raises on a bad signature or malformed key/signature material -- returns ``False``,
    the same fail-closed-as-a-value convention this Kernel's own verifier functions already
    use, so a caller can compose this into a total decision without a try/except of its own.
    """

    try:
        public_key_bytes = bytes.fromhex(public_key_hex)
        signature_bytes = bytes.fromhex(signature_hex)
    except ValueError:
        return False
    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature_bytes, message)
    except (InvalidSignature, ValueError):
        return False
    return True


def verify_declaration_signature(record: dict[str, Any], *, signing_key: dict[str, Any]) -> bool:
    """Whether *record*'s own ``signature`` is a genuine signature, by the holder of
    *signing_key* (a real Project Binding's own ``human_authority_signing_key`` -- never a
    caller-supplied copy), over exactly the canonical payload
    :func:`~manosube_agent_civilization.binding.identity.human_grant_declaration_signing_
    payload` derives from *record*'s own fields.

    ``False`` on any mismatch -- an unsigned/malformed ``signature`` object, an algorithm this
    module does not support, a ``key_id`` that does not name *signing_key*'s own, a signature
    that does not verify against *signing_key*'s own ``public_key``, or a payload that has
    been altered since it was signed -- never an exception; the caller decides what a
    ``False`` result means for the surrounding decision.
    """

    signature = record.get("signature")
    if not isinstance(signature, dict):
        return False
    algorithm = signature.get("algorithm")
    if algorithm != SUPPORTED_SIGNATURE_ALGORITHM or signing_key.get("algorithm") != algorithm:
        return False
    if signature.get("key_id") != signing_key.get("key_id"):
        return False
    signature_hex = signature.get("value")
    public_key_hex = signing_key.get("public_key")
    if not isinstance(signature_hex, str) or not isinstance(public_key_hex, str):
        return False
    message = human_grant_declaration_signing_payload(record)
    return verify_ed25519_signature(
        public_key_hex=public_key_hex, message=message, signature_hex=signature_hex
    )
