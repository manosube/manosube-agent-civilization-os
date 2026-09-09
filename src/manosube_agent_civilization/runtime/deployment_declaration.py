"""Human Authority signature verification for a Runtime Deployment Declaration (Phase 15
Structural Review Round 2, Issue #64, P15-R2-F2).

**This module verifies only.** It holds no private key, mints no signature, and reaches no
key server, registry, environment variable, or network of any kind -- exactly the discipline
:mod:`manosube_agent_civilization.binding.signature`'s own module docstring already states for
the two declaration kinds Binding owns. The one public verification key ever consulted is the
one a real, Store-resolved, Boot-restored Project Binding record itself already carries
(``human_authority_signing_key``), passed in by
:mod:`~manosube_agent_civilization.runtime.route` from the Boot context it *itself* just
restored -- never a caller-supplied copy of a key, and never a key read out of the declaration
being checked.

**Why this composition lives here rather than in Binding.** The Ed25519 primitive is *not*
reimplemented: :func:`~manosube_agent_civilization.binding.signature.verify_ed25519_signature`
is the one shared, public, fail-closed-as-a-value primitive this repository owns, and it is
imported and called directly. Only the four-line composition around it
(algorithm match, ``key_id`` match, then the primitive) is restated, because
``binding/signature.py``'s own equivalent composition is module-private and because Runtime is
an adapter layer that depends on Binding, never the reverse -- adding a
``runtime_deployment_declaration``-shaped verifier to ``binding/`` would make the Kernel's own
Binding element import a Phase 15 adapter's record kind and invert that dependency.

Fail-closed as a *value*, never as an exception (the identical convention the primitive itself
uses): this module returns ``False`` on any mismatch and lets its one caller decide what a
``False`` result means for the surrounding decision -- which, in
:func:`~manosube_agent_civilization.runtime.route.observe_runtime_target`, is always a
:class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError` refusal before any
adapter call and with zero commits.
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.binding.signature import (
    SUPPORTED_SIGNATURE_ALGORITHM,
    verify_ed25519_signature,
)

from .identity import runtime_deployment_declaration_signing_payload


def verify_runtime_deployment_declaration_signature(
    declaration: dict[str, Any], *, signing_key: dict[str, Any]
) -> bool:
    """Whether *declaration*'s own ``signature`` is a genuine Ed25519 signature, by the holder
    of *signing_key*, over exactly the canonical payload
    :func:`~manosube_agent_civilization.runtime.identity.
    runtime_deployment_declaration_signing_payload` derives from *declaration*'s own adopted
    semantic fields.

    *signing_key* must always be the ``human_authority_signing_key`` of the Project Binding the
    *calling route's own Boot* just freshly restored -- never a caller-supplied copy, never a
    value read from the declaration itself, and never a key cached from an earlier call.

    ``False`` on any mismatch -- an absent/malformed ``signature`` object, an algorithm this
    repository does not support, an algorithm the signing key itself does not declare, a
    ``key_id`` that does not name *signing_key*'s own, or a signature that does not verify
    against *signing_key*'s own ``public_key`` -- never an exception.
    """

    signature = declaration.get("signature")
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
    return verify_ed25519_signature(
        public_key_hex=public_key_hex,
        message=runtime_deployment_declaration_signing_payload(declaration),
        signature_hex=signature_hex,
    )


__all__ = ["verify_runtime_deployment_declaration_signature"]
