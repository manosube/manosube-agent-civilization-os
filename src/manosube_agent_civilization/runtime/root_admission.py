"""Trust-anchor signature verification for a Runtime Root Admission (Phase 15 Structural
Review Round 3, Issue #64, P15-R3-F1).

**This module verifies only.** It holds no private key, mints no signature, and reaches no key
server, registry, environment variable, or network of any kind -- the identical discipline
:mod:`manosube_agent_civilization.runtime.deployment_declaration` already states, and which
:mod:`manosube_agent_civilization.binding.signature` established before both of them. The
Ed25519 primitive is *not* reimplemented:
:func:`~manosube_agent_civilization.binding.signature.verify_ed25519_signature` is the one
shared, public, fail-closed-as-a-value primitive this repository owns, and it is imported and
called directly; only the same four-line composition around it (algorithm match, then the
primitive) is restated locally, for the identical dependency-direction reason
``deployment_declaration.py``'s own docstring gives -- Runtime depends on the Kernel's Binding
element, never the reverse.

**Why this verifier's parameter is a bare public key hex string, and not a ``signing_key``
mapping resolved from a Store.** The sibling verifier for a
``runtime_deployment_declaration`` takes the ``human_authority_signing_key`` the *calling
route's own Boot* just restored from the current Project Binding -- which is exactly right
there, because that declaration is a statement *by* the project's own Human Authority *about*
one of the project's own deployments, and the question being asked is "did this project's own
Authority really say this?".

A Runtime Root Admission asks a different question, and it must be answered from outside:
"is this Store, this Project, and this Project Binding the one the deployment boundary
actually admits?" A key resolved from inside the Store being admitted cannot answer that. An
attacker's fully self-consistent alternate world -- its own Human Authority, its own Ed25519
signing key, its own Project Binding, every record internally valid on its own terms -- would
simply self-sign a matching admission record with its *own* internally-legitimate key and pass.
The record therefore carries no ``human_authority_ref`` field at all (see
:data:`~manosube_agent_civilization.runtime.identity.ROOT_ADMISSION_SEMANTIC_FIELDS`), and this
function verifies against a ``trust_anchor_public_key_hex`` its caller supplies:

```text
trust_anchor_public_key_hex   MUST come from deployment/composition-time configuration --
                              the boundary that decides which world is canonical at all.
                              NEVER from the Store being admitted, never derived from
                              anything on the request path, and never hardcoded as a
                              specific real-world key inside shipped source.
```

Who supplies it, and how, is a genuine deployment's own responsibility; this repository ships
the mechanism, not a live invocation of it (``10_RUNTIME/RUNTIME_CONTRACT.md`` §12.1).

Fail-closed as a *value*, never as an exception (the identical convention the primitive itself
uses): this module returns ``False`` on any mismatch and lets its one caller decide what a
``False`` result means -- which, in
:func:`~manosube_agent_civilization.runtime.bootstrap.
compose_trusted_runtime_deployment_authority`,
is always a :class:`~manosube_agent_civilization.runtime.errors.RuntimeRequirementError`
refusal reached before any grant resolution, before
``evaluate_projection_authorization`` is ever called, and therefore with zero adapter calls.
"""

from __future__ import annotations

from typing import Any

from manosube_agent_civilization.binding.signature import (
    SUPPORTED_SIGNATURE_ALGORITHM,
    verify_ed25519_signature,
)

from .identity import runtime_root_admission_signing_payload


def verify_runtime_root_admission_signature(
    admission: dict[str, Any], *, trust_anchor_public_key_hex: str
) -> bool:
    """Whether *admission*'s own ``signature`` is a genuine Ed25519 signature, by the holder of
    the private key matching *trust_anchor_public_key_hex*, over exactly the canonical payload
    :func:`~manosube_agent_civilization.runtime.identity.runtime_root_admission_signing_payload`
    derives from *admission*'s own adopted semantic fields.

    *trust_anchor_public_key_hex* is a raw 32-byte Ed25519 **public** key, hex-encoded, and must
    always come from deployment/composition-time configuration -- never from the Store being
    admitted, never derived from anything on the request path, and never a constant baked into
    shipped source. See this module's own docstring for why that independence is the entire
    point of this record kind.

    ``False`` on any mismatch -- an absent/malformed ``signature`` object, an algorithm this
    repository does not support, a non-string signature value or anchor key, or a signature that
    does not verify against the anchor -- never an exception.

    Deliberately **no** ``key_id`` cross-check: unlike a declaration signed by a Human Authority
    whose own declared ``key_id`` a Boot-restored Project Binding independently carries, there is
    no second, independent statement of the trust anchor's own ``key_id`` to compare against
    here -- the record's own ``signature.key_id`` is written by whoever wrote the record, so
    requiring it to equal itself would prove nothing. The cryptographic check against the
    externally supplied anchor is the whole control, and it is not weakened by an absent
    self-comparison.
    """

    signature = admission.get("signature")
    if not isinstance(signature, dict):
        return False
    if signature.get("algorithm") != SUPPORTED_SIGNATURE_ALGORITHM:
        return False
    signature_hex = signature.get("value")
    if not isinstance(signature_hex, str) or not isinstance(trust_anchor_public_key_hex, str):
        return False
    return verify_ed25519_signature(
        public_key_hex=trust_anchor_public_key_hex,
        message=runtime_root_admission_signing_payload(admission),
        signature_hex=signature_hex,
    )


__all__ = ["verify_runtime_root_admission_signature"]
