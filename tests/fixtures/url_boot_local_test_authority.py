"""The one trusted, disposable-local-test-only composition boundary for URL Boot's own
loopback-permitting observation path (Structural Review Round 3, P17-R3-F2, extended by
Structural Review Round 4, P17-R4-F2, and Structural Review Round 5, P17-R5-F2, Issue #69).

**Why this module exists at all, and why it lives here rather than in the shipped package.**
Structural Review Round 2 (P17-R2-F2) moved the loopback exception off every request-facing
value (no Boundary field, no adapter-constructor argument) and into a distinctly-named,
non-``__all__``-exported function inside ``url_boot/route.py`` itself,
``observe_url_source_for_disposable_local_test``. Round 3 correctly found that insufficient:
omitting a name from ``__all__`` is a documentation convention, not access control, and moved the
factory itself here, outside the shipped package -- but left the loopback-permitting
*classifier*'s own body, ``_require_safe_resolved_address_permitting_loopback_only``, still
defined inside ``route.py``, still shipped. Round 4 found that insufficient in turn: a caller who
only ever ``pip install``ed this package -- never cloned its test tree -- could still import
``route.py``'s own generic ``_observe_url_source_impl``, ``_perform_connection_via_trusted_
network``, and ``_require_safe_resolved_address_permitting_loopback_only``, and hand-wire the
identical composition this module performs, entirely from shipped ingredients, without ever
touching this file.

**Round 5 found the deeper structural gap those three moves alone still left open
(P17-R5-F2).** The shipped ``route.py`` still carried the *generic*, dependency-injected
orchestration itself (the pre-Round-5 ``_observe_url_source_impl``, accepting
``classify_resolved_address``/``perform_resolution``/``perform_connection`` as ordinary function
parameters) -- so a caller able to import ``route.py`` directly could call that generic function
with the genuine, shipped trusted-network resolver/connector *and* an ordinary permissive lambda
as ``classify_resolved_address``, reconstructing a working loopback-admitting path from shipped
code alone, no adapter object and no import of this module required at all. Round 5's correction
has two parts, both reflected in this module:

1. **The generic engine itself no longer ships.** ``route.py`` now ships only a fixed,
   non-parameterized production pipeline (``_fetch_with_route_owned_redirects_production``,
   ``_observe_url_source_impl_production``) whose classifier/resolver/connector calls are
   hardcoded, direct calls -- there is no parameter list anywhere in the shipped package through
   which a caller could substitute any of the three. The generic, dependency-injected form this
   module's own composition still genuinely needs now lives in
   ``tests/fixtures/url_boot_test_engine.py`` -- confirmed absent from the distributed wheel by the
   identical packaging fact already established for this module -- and this module delegates to
   *that* module's own ``observe_url_source_for_internal_testing``, never to anything in
   ``route.py`` beyond the fixed production primitives it still legitimately reuses
   (``route._perform_resolution_via_trusted_network``/``route._perform_connection_via_trusted_
   network``, themselves fixed functions, not a generic engine).

2. **The test-harness authority is now issuer/verifier-separated, not a single shared secret
   (P17-R5-F2).** Round 4's HMAC design kept the minting secret and the verifying logic in this
   one module -- anyone able to import this module could both mint and verify, so the "genuine
   external authority" property rested entirely on this module's own non-shipped status, not on
   any structural separation of roles. Structural Review Round 5 found that insufficient: an
   authority whose verifier can also mint is not genuinely a *verifier* at all. This module now
   holds **only** a hardcoded Ed25519 public-key hex literal
   (:data:`_TRUSTED_LOCAL_TEST_AUTHORITY_PUBLIC_KEY_HEX`) and verifies a presented credential
   against it via this repository's own established
   :func:`~manosube_agent_civilization.binding.signature.verify_ed25519_signature` -- the
   identical verifier ``runtime/bootstrap.py``'s own production trust-anchor already uses. It
   holds no private key, no minting function, and imports nothing from
   ``tests/fixtures/url_boot_local_test_issuer.py`` -- the one module that *can* mint a genuine
   credential. A caller who wants to exercise this composition legitimately must obtain a
   credential from that genuinely separate module; this module cannot manufacture one for itself.

**Neither this module, ``url_boot_test_engine.py``, nor ``url_boot_local_test_issuer.py`` is
shipped.** All three live under ``tests/``, confirmed by ``pyproject.toml``'s own
``[tool.hatch.build.targets.wheel] packages = ["src/manosube_agent_civilization"]`` to be entirely
absent from the distributed wheel. A caller who has only ``pip install``ed this package cannot
import any of them, their classifier, or their authority material at all: none of it exists in
what they installed. What remains importable from the shipped ``route.py`` --
``_perform_resolution_via_trusted_network``/``_perform_connection_via_trusted_network`` -- are
fixed, non-generic functions; combined with the strict, always-refuses-loopback production
classifier alone (the only classifier ``route.py`` itself ships) and no generic orchestration to
thread them through, they yield only production-equivalent, loopback-refusing behavior.

**What this is not, disclosed rather than implied.** This boundary's blast radius, exactly as
Round 4 disclosed, is permission for one disposable, already-source-visible test process to fetch
from ``127.0.0.1`` -- a target every test in this repository already has unmediated
``socket``/``subprocess`` access to regardless of anything this module does. Asymmetric,
issuer/verifier-separated signing closes the specific gap Round 5 named (a shared secret whose
holder could both mint and verify) but, like Round 4's HMAC design before it, cannot defend
against a fully privileged same-process adversary who already possesses this repository's own test
suite source: within one Python interpreter, any code that can import ``url_boot_local_test_
issuer.py`` can mint a genuine credential exactly as it could call
:func:`compose_disposable_local_test_observer` directly instead. No mechanism expressible in pure
Python, run in the same process as the code it constrains, closes that residual gap -- true
isolation would require a genuinely separate process or credential store, which this delivery
judges disproportionate to a boundary whose entire blast radius is already inside the caller's own
trust domain.

Every other unsafe address class (private/link-local/multicast/reserved) remains refused
identically to production through this composition -- the loopback exception is the *only* one
:func:`_require_safe_resolved_address_permitting_loopback_only` ever admits -- so even this
trusted composition, correctly authorized, cannot be used to reach anything beyond a disposable
local test target.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from tests.fixtures.url_boot_test_engine import observe_url_source_for_internal_testing

from manosube_agent_civilization.binding.signature import verify_ed25519_signature
from manosube_agent_civilization.url_boot.errors import UrlBootRequirementError
from manosube_agent_civilization.url_boot.network import require_safe_resolved_address
from manosube_agent_civilization.url_boot.route import (
    _perform_connection_via_trusted_network,
    _perform_resolution_via_trusted_network,
)

#: This composition's own hardcoded trust anchor -- the public half of the one Ed25519 keypair
#: ``tests/fixtures/url_boot_local_test_issuer.py`` alone holds the private half of. A literal
#: constant, duplicated here rather than imported from the issuer module, deliberately: importing
#: the issuer module from this one would give this module's own import graph a path to the
#: private key it exists to never hold (Structural Review Round 5, P17-R5-F2). This repository's
#: own test suite asserts, separately, that this literal equals the issuer module's own
#: ``issuer_public_key_hex()`` -- a non-vacuity control confirming the two modules' keys genuinely
#: match, never consulted by this module itself at runtime.
_TRUSTED_LOCAL_TEST_AUTHORITY_PUBLIC_KEY_HEX = (
    "201ad69ba2630ad78e40925737b0fb9afb8e450d77de9a223a6fd6d17a498a67"
)

#: Duplicated verbatim from ``url_boot_local_test_issuer.py``'s own identically-named constant --
#: not imported, for the same reason the public-key literal above is not imported. Both modules
#: must agree on the exact bytes a genuine credential is a signature over; this repository's own
#: test suite asserts that agreement independently.
_TEST_HARNESS_AUTHORITY_SIGNING_PAYLOAD: bytes = (
    b"url-boot-disposable-local-test-harness-authority-v2-ed25519"
)

#: Duplicated verbatim from ``url_boot_local_test_issuer.py``'s own identically-named constant.
_TEST_HARNESS_AUTHORITY_KEY_ID = "URL-BOOT-LOCAL-TEST-AUTHORITY-0001"


def _require_valid_test_harness_authority(candidate: Any) -> None:
    """Structurally verify *candidate* is a genuine credential minted by
    ``url_boot_local_test_issuer.py``'s own ``mint_test_harness_authority`` -- an Ed25519
    signature, by that module's own private key, over
    :data:`_TEST_HARNESS_AUTHORITY_SIGNING_PAYLOAD`. This module holds no private key and cannot
    mint one itself; it can only confirm one presented to it. A missing, wrong-shaped, wrong
    ``key_id``, or cryptographically invalid *candidate* is refused
    (:class:`~manosube_agent_civilization.url_boot.errors.UrlBootRequirementError`) before any
    DNS resolution or network connection is ever attempted -- composition itself fails closed."""

    if not isinstance(candidate, Mapping):
        raise UrlBootRequirementError(
            "test_harness_authority is missing or not a mapping -- refusing before any DNS "
            "resolution or network connection is ever attempted"
        )
    algorithm = candidate.get("algorithm")
    key_id = candidate.get("key_id")
    value = candidate.get("value")
    if algorithm != "ed25519":
        raise UrlBootRequirementError(
            f"test_harness_authority declares an unsupported algorithm: {algorithm!r}"
        )
    if key_id != _TEST_HARNESS_AUTHORITY_KEY_ID:
        raise UrlBootRequirementError(
            f"test_harness_authority declares an unrecognized key_id: {key_id!r}"
        )
    if not isinstance(value, str) or not value:
        raise UrlBootRequirementError(
            "test_harness_authority does not declare a readable signature value"
        )
    if not verify_ed25519_signature(
        public_key_hex=_TRUSTED_LOCAL_TEST_AUTHORITY_PUBLIC_KEY_HEX,
        message=_TEST_HARNESS_AUTHORITY_SIGNING_PAYLOAD,
        signature_hex=value,
    ):
        raise UrlBootRequirementError(
            "test_harness_authority's own signature does not verify against this composition's "
            "own trusted local-test-authority public key -- forged, corrupted, or signed by a "
            "different key entirely"
        )


def _require_safe_resolved_address_permitting_loopback_only(address: str) -> None:
    """The one network-address-safety classifier this repository's own trusted, non-shipped
    disposable-local-test composition closes over -- loopback is the *only* exception ever
    admitted; every other unsafe address class (private/link-local/multicast/reserved) is still
    refused exactly as in production. Defined only in this module -- ``route.py`` itself ships no
    loopback-permitting classifier of any kind, and no generic orchestration to thread one
    through even if it did (Structural Review Round 4/Round 5, P17-R4-F2/P17-R5-F2)."""

    require_safe_resolved_address(address, permit_loopback_test_hosts=True)


def compose_disposable_local_test_observer(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    adapter_identity: Any,
    test_harness_authority: Any,
) -> Callable[[Mapping[str, Any], Mapping[str, Any], str], dict[str, Any]]:
    """Bind one canonical Store, Project, Project Binding, and adapter identity -- once, and only
    once a genuine *test_harness_authority* (minted only by
    ``tests/fixtures/url_boot_local_test_issuer.py``'s own ``mint_test_harness_authority``) has
    been verified -- and return the request-facing observation operation itself, already closed
    over all of them plus the loopback-permitting classifier and the trusted real-network
    resolver/connector (:func:`~manosube_agent_civilization.url_boot.route.
    _perform_resolution_via_trusted_network`/:func:`~manosube_agent_civilization.url_boot.route.
    _perform_connection_via_trusted_network` -- the identical fixed, non-parameterized primitives
    production's own :func:`~manosube_agent_civilization.url_boot.route.
    compose_url_source_observer` uses; only the address-safety classifier differs). Real
    resolution and connection are created and controlled entirely by the trusted network layer,
    never by any adapter -- this factory carries no adapter *object* parameter at all, mirroring
    production's own Round 5 boundary exactly.

    *adapter_identity* is, exactly like production's own :func:`~manosube_agent_civilization.
    url_boot.route.compose_url_source_observer`, already-realized plain data -- canonicalized
    once, here, at composition time, via :func:`~manosube_agent_civilization.url_boot.route.
    _canonicalize_inert_adapter_identity` (Structural Review Round 5, P17-R5-F1).

    *test_harness_authority* is checked structurally and cryptographically before this function
    returns anything at all -- a missing, wrong-shaped, wrong-``key_id``, or forged value refuses
    (:class:`~manosube_agent_civilization.url_boot.errors.UrlBootRequirementError`) before any DNS
    resolution or network connection is ever attempted (P17-R4-F2/P17-R5-F2's own required
    decisive control).

    The returned closure's own call signature is exactly ``(source_identity, boundary,
    observed_at)``: no Store, no adapter, no adapter identity, no classifier, no resolver, no
    connector, no policy flag, no test-harness authority, and no alternate-world substitution
    input of any kind (P17-R3-F2/P17-R4-F2/P17-R5-F1/F2). Calling this factory again, with a
    different Store/adapter identity, produces a genuinely independent closure over that different
    world -- the factory itself does not cache or share state across calls -- but no *caller of a
    returned closure* can redirect it to a different world, or a different authority, after the
    fact.
    """

    _require_valid_test_harness_authority(test_harness_authority)
    canonical_adapter_identity = _canonicalize_adapter_identity_via_route(adapter_identity)

    def observe(
        source_identity: Mapping[str, Any], boundary: Mapping[str, Any], observed_at: str
    ) -> dict[str, Any]:
        return observe_url_source_for_internal_testing(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            source_identity=source_identity,
            boundary=boundary,
            adapter_identity=canonical_adapter_identity,
            observed_at=observed_at,
            classify_resolved_address=_require_safe_resolved_address_permitting_loopback_only,
            perform_resolution=lambda _adapter, current_identity: (
                _perform_resolution_via_trusted_network(current_identity)
            ),
            perform_connection=lambda _adapter, current_identity, admitted_address, boundary_: (
                _perform_connection_via_trusted_network(
                    current_identity, admitted_address, boundary_
                )
            ),
        )

    return observe


def _canonicalize_adapter_identity_via_route(value: Any) -> Mapping[str, Any]:
    """Reuse ``route.py``'s own single canonicalizer rather than duplicating its validation
    logic -- imported lazily, by attribute access on the already-imported module object, to keep
    this module's own top-level import list limited to the two fixed production primitives it
    genuinely composes with."""

    from manosube_agent_civilization.url_boot import route as route_module

    result: Mapping[str, Any] = route_module._canonicalize_inert_adapter_identity(value)
    return result


__all__ = ["compose_disposable_local_test_observer"]
