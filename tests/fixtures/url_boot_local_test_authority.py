"""The one trusted, disposable-local-test-only composition boundary for URL Boot's own
loopback-permitting observation path (Structural Review Round 3, P17-R3-F2, extended by
Structural Review Round 4, P17-R4-F2, Issue #69).

**Why this module exists at all, and why it lives here rather than in the shipped package.**
Structural Review Round 2 (P17-R2-F2) moved the loopback exception off every request-facing
value (no Boundary field, no adapter-constructor argument) and into a distinctly-named,
non-``__all__``-exported function inside ``url_boot/route.py`` itself,
``observe_url_source_for_disposable_local_test``. Round 3 correctly found that insufficient:
omitting a name from ``__all__`` is a documentation convention, not access control, and moved the
factory itself here, outside the shipped package -- but left the loopback-permitting
*classifier*'s own body, ``_require_safe_resolved_address_permitting_loopback_only``, still
defined inside ``route.py``, still shipped. **Round 4 found that insufficient in turn**: a caller
who only ever ``pip install``ed this package -- never cloned its test tree -- could still import
``route.py``'s own ``_observe_url_source_impl``, ``_perform_connection_via_trusted_network``, and
``_require_safe_resolved_address_permitting_loopback_only``, and hand-wire the identical
composition this module performs, entirely from shipped ingredients, without ever touching this
file. Structural Review Round 4's own delivery-comment demonstrated this reconstruction attack
explicitly by naming those three importable symbols.

This module is the correction, in three structural moves, none sufficient alone:

1. **The composed capability is a closure, never a class or a named module-level "give me
   loopback" function taking full request-shaped arguments.** :func:`compose_disposable_local_
   test_observer` is a *factory*: it takes the Store/Project/Binding/adapter this one disposable
   test world is bound to, exactly once, and returns the request-facing observation operation
   itself, already closed over all four plus the loopback-permitting classifier
   (:func:`_require_safe_resolved_address_permitting_loopback_only`, defined in *this* module --
   see move 2 below) and the trusted real-network resolver/connector
   (``route._perform_resolution_via_trusted_network``/``route._perform_connection_via_trusted_
   network`` -- the identical ones production ``compose_url_source_observer`` itself uses; only
   the address-safety classifier differs). The returned closure's own call signature carries none
   of them -- only ``(source_identity, boundary, observed_at)``, the genuinely request-facing
   "what to observe" parameters a real V3 test needs to vary between calls. There is no keyword,
   no positional slot, and no attribute on the returned callable through which a caller could
   substitute a different Store, adapter, or classifier after the fact -- the identical "closure,
   not a class; composition chose and closed over the authority before the request boundary
   existed" discipline ``runtime/bootstrap.py``'s own ``compose_trusted_runtime_deployment_
   authority`` already establishes for Runtime's production credential-granting boundary (see
   that module's own Structural Review Round 5, P15-R5-F1, docstring).

2. **The loopback-permitting classifier's own body lives here, never in the shipped package, and
   the factory that wires it in requires a genuine externally held test-harness authority.**
   ``route.py`` no longer defines *any* function, of any name, that classifies a resolved address
   as loopback-safe -- the one classifier it ships,
   ``route._require_safe_resolved_address_production``, always refuses loopback, unconditionally,
   with no parameter through which any caller could change that. ``_require_safe_resolved_
   address_permitting_loopback_only`` is instead defined in *this* module, confirmed absent from
   the distributed wheel (see move 3 below). A caller who only has the shipped wheel therefore has
   no *ready-made* loopback-permitting classifier to import and recombine with ``route.py``'s own
   internal composable engine at all; reconstructing one requires writing an equivalent
   implementation from scratch, which is a categorically different, far weaker act than reusing
   this package's own shipped code -- Python's own dynamism can never be fully closed against a
   caller willing to write arbitrary policy code themselves, and this module does not claim
   otherwise (see the non-claims section below).

   Calling :func:`compose_disposable_local_test_observer` additionally requires a
   *test_harness_authority* value, minted only by :func:`mint_test_harness_authority` -- also
   defined only in this module. :func:`mint_test_harness_authority` returns an HMAC-SHA256 digest
   keyed by a secret generated once, fresh, via :func:`secrets.token_bytes`, at this module's own
   import time -- a value that exists nowhere in the shipped package's own source, is never
   computed by any shipped function, and is not a static, guessable, or reconstructible constant.
   :func:`compose_disposable_local_test_observer` verifies the presented value via
   :func:`hmac.compare_digest` against the identical digest, computed fresh from the same
   in-module secret -- both the minting and the verification live in this one non-shipped module;
   ``route.py`` contains no authority-checking logic of any kind, and never receives, compares, or
   forwards this value. A missing, wrong-typed, or forged *test_harness_authority* is refused
   (:class:`~manosube_agent_civilization.url_boot.errors.UrlBootRequirementError`) before any DNS
   resolution or network connection is ever attempted -- composition itself fails closed.

3. **Neither this module nor the composition it performs is shipped.** This file lives under
   ``tests/``, confirmed by ``pyproject.toml``'s own ``[tool.hatch.build.targets.wheel] packages =
   ["src/manosube_agent_civilization"]`` to be entirely absent from the distributed wheel. A
   caller who has only ``pip install``ed this package, rather than cloned its source tree, cannot
   import this module, its classifier, or its authority-minting function at all: none of them
   exist in what they installed. The two raw ingredients this factory additionally wires in from
   the shipped package -- ``route._observe_url_source_impl`` and ``route._perform_resolution_
   via_trusted_network``/``route._perform_connection_via_trusted_network`` -- remain importable
   from ``route.py`` (Python offers no real way to make a name in an importable module
   unreachable to code that already has source access, and this repository does not pretend
   otherwise), but combined with the strict, always-refuses-loopback production classifier alone
   (the only classifier ``route.py`` itself ships), they yield only production-equivalent,
   loopback-refusing behavior.

**What this is not, disclosed rather than implied.** This is not cryptographic capability
security in the sense ``runtime/bootstrap.py``'s own production credential boundary is: that
boundary anchors trust in a real Ed25519 signature verified against a deployment-configured
public key, because forging it would grant a real, durable, high-value production capability.
This boundary grants something categorically smaller: permission for one disposable,
already-source-visible test process to fetch from ``127.0.0.1`` -- a target every test in this
repository already has unmediated ``socket``/``subprocess`` access to regardless of anything this
module does. The HMAC-verified *test_harness_authority* genuinely closes the specific
reconstruction attack Structural Review Round 4 demonstrated -- recombining *shipped* ``route.py``
private names into a working loopback-permitting request path -- because the secret and the
classifier it gates now exist nowhere a wheel-only caller's own import graph can reach. It does
**not**, and cannot, defend against a fully privileged same-process adversary who already
possesses this repository's own test-suite source: within one Python interpreter, any code that
can import this exact module can read this exact module's own secret, exactly as it could call
:func:`compose_disposable_local_test_observer` directly instead of forging anything. No mechanism
expressible in pure Python, run in the same process as the code it constrains, closes that
residual gap -- true isolation would require a genuinely separate process or credential store,
which this delivery judges disproportionate to a boundary whose entire blast radius is already
inside the caller's own trust domain (loopback access the same test process already has). What
this module's own three moves *do* close is exactly what Round 4 named: the shipped package no
longer contains a ready-made permissive classifier, a ready-made composition wiring it in, or any
value that lets a caller possessing only the installed wheel construct a working loopback-
permitting request path by import and recombination alone.

Every other unsafe address class (private/link-local/multicast/reserved) remains refused
identically to production through this composition -- the loopback exception is the *only* one
:func:`_require_safe_resolved_address_permitting_loopback_only` ever admits -- so even this
trusted composition, correctly authorized, cannot be used to reach anything beyond a disposable
local test target.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hmac
import secrets
from typing import Any

from manosube_agent_civilization.url_boot.errors import UrlBootRequirementError
from manosube_agent_civilization.url_boot.network import require_safe_resolved_address
from manosube_agent_civilization.url_boot.route import (
    _observe_url_source_impl,
    _perform_connection_via_trusted_network,
    _perform_resolution_via_trusted_network,
)

#: Generated fresh, once, at this non-shipped module's own import time -- never a static
#: constant, never computed by any function this repository ships, and never present anywhere in
#: ``route.py``'s own source. Nothing in the shipped package can read, derive, or reconstruct
#: this value.
_TEST_HARNESS_SECRET: bytes = secrets.token_bytes(32)
_TEST_HARNESS_DIGEST_CONTEXT = b"url-boot-disposable-local-test-harness-authority-v1"


def mint_test_harness_authority() -> bytes:
    """Return the one valid *test_harness_authority* value for this process's own test session --
    an HMAC-SHA256 digest keyed by :data:`_TEST_HARNESS_SECRET`. Calling this function is itself
    already only possible for code that can import this non-shipped module; the returned value
    exists to be threaded explicitly into :func:`compose_disposable_local_test_observer`, which
    verifies it structurally before permitting any loopback-classifying composition to be
    returned at all."""

    return hmac.new(_TEST_HARNESS_SECRET, _TEST_HARNESS_DIGEST_CONTEXT, "sha256").digest()


def _require_valid_test_harness_authority(candidate: Any) -> None:
    expected = hmac.new(_TEST_HARNESS_SECRET, _TEST_HARNESS_DIGEST_CONTEXT, "sha256").digest()
    if not isinstance(candidate, bytes | bytearray) or not hmac.compare_digest(
        bytes(candidate), expected
    ):
        raise UrlBootRequirementError(
            "test_harness_authority is missing, the wrong type, or does not match this "
            "process's own minted value -- refusing before any DNS resolution or network "
            "connection is ever attempted"
        )


def _require_safe_resolved_address_permitting_loopback_only(address: str) -> None:
    """The one network-address-safety classifier this repository's own trusted, non-shipped
    disposable-local-test composition closes over -- loopback is the *only* exception ever
    admitted; every other unsafe address class (private/link-local/multicast/reserved) is still
    refused exactly as in production. Defined only in this module (Structural Review Round 4,
    P17-R4-F2) -- ``route.py`` itself ships no loopback-permitting classifier of any kind any
    more, so importing the shipped package alone yields no usable loopback-permitting capability
    regardless of which private names are recombined."""

    require_safe_resolved_address(address, permit_loopback_test_hosts=True)


def compose_disposable_local_test_observer(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    adapter: Any,
    test_harness_authority: bytes,
) -> Callable[[Mapping[str, Any], Mapping[str, Any], str], dict[str, Any]]:
    """Bind one canonical Store, Project, Project Binding, and adapter -- once, and only once a
    genuine *test_harness_authority* (see :func:`mint_test_harness_authority`) has been verified
    -- and return the request-facing observation operation itself, already closed over all four
    plus the loopback-permitting classifier and the trusted real-network resolver/connector.

    *test_harness_authority* is checked structurally, via :func:`hmac.compare_digest` against
    this module's own freshly minted value, before this function returns anything at all -- a
    missing, wrong-typed, or forged value refuses (:class:`~manosube_agent_civilization.url_boot.
    errors.UrlBootRequirementError`) before any DNS resolution or network connection is ever
    attempted (P17-R4-F2's own required decisive control).

    The returned closure's own call signature is exactly ``(source_identity, boundary,
    observed_at)``: no Store, no adapter, no classifier, no resolver, no connector, no policy
    flag, no test-harness authority, and no alternate-world substitution input of any kind
    (P17-R3-F2/P17-R4-F2). Calling this factory again, with a different Store/adapter, produces a
    genuinely independent closure over that different world -- the factory itself does not cache
    or share state across calls -- but no *caller of a returned closure* can redirect it to a
    different world, or a different authority, after the fact.
    """

    _require_valid_test_harness_authority(test_harness_authority)

    def observe(
        source_identity: Mapping[str, Any], boundary: Mapping[str, Any], observed_at: str
    ) -> dict[str, Any]:
        return _observe_url_source_impl(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            source_identity=source_identity,
            boundary=boundary,
            adapter=adapter,
            observed_at=observed_at,
            classify_resolved_address=_require_safe_resolved_address_permitting_loopback_only,
            perform_resolution=_perform_resolution_via_trusted_network,
            perform_connection=_perform_connection_via_trusted_network,
        )

    return observe


__all__ = ["compose_disposable_local_test_observer", "mint_test_harness_authority"]
