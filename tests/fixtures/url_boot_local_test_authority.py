"""The one trusted, disposable-local-test-only composition boundary for URL Boot's own
loopback-permitting observation path (Structural Review Round 3, P17-R3-F2, Issue #69).

**Why this module exists at all, and why it lives here rather than in the shipped package.**
Structural Review Round 2 (P17-R2-F2) moved the loopback exception off every request-facing
value (no Boundary field, no adapter-constructor argument) and into a distinctly-named,
non-``__all__``-exported function inside ``url_boot/route.py`` itself,
``observe_url_source_for_disposable_local_test``. Structural Review Round 3 correctly found that
insufficient: omitting a name from ``__all__`` is a documentation convention, not access control.
Any caller able to import ``manosube_agent_civilization.url_boot.route`` -- which is not a
restricted operation; it is the same shipped module ``observe_url_source`` itself lives in --
could import that exact name directly and call it with its own Store, Project, Binding, adapter
and Boundary, reaching the loopback-permitting classifier with the same one-function-call ease
public ``observe_url_source`` offers.

This module is the correction. Two structural moves, both required, neither sufficient alone:

1. **The composed capability is a closure, never a class or a named module-level "give me
   loopback" function taking full request-shaped arguments.** :func:`compose_disposable_local_
   test_observer` is a *factory*: it takes the Store/Project/Binding/adapter this one disposable
   test world is bound to, exactly once, and returns the request-facing observation operation
   itself, already closed over all four plus the loopback-permitting classifier
   (``route._require_safe_resolved_address_permitting_loopback_only``) and the trusted real-network
   connector (``route._perform_connection_via_trusted_network`` -- the identical one production
   ``observe_url_source`` itself uses; only the address-safety classifier differs). The returned
   closure's own call signature carries none of them -- only ``(source_identity, boundary,
   observed_at)``, the genuinely request-facing "what to observe" parameters a real V3 test needs
   to vary between calls. There is no keyword, no positional slot, and no attribute on the
   returned callable through which a caller could substitute a different Store, adapter, or
   classifier after the fact -- the identical "closure, not a class; composition chose and closed
   over the authority before the request boundary existed" discipline
   ``runtime/bootstrap.py``'s own ``compose_trusted_runtime_deployment_authority`` already
   establishes for Runtime's production credential-granting boundary (see that module's own
   Structural Review Round 5, P15-R5-F1, docstring).

2. **The factory itself is not shipped.** ``route.py`` no longer defines *any* function, of any
   name, that both (a) is reachable by importing the shipped package and (b) permits loopback for
   a caller-supplied Store/adapter/Boundary in one call. The two raw ingredients this factory
   wires together -- ``route._observe_url_source_impl`` and ``route._require_safe_resolved_
   address_permitting_loopback_only`` -- remain importable from ``route.py`` (Python offers no
   real way to make a name in an importable module unreachable to code that already has source
   access, and this repository does not pretend otherwise), but ``route.py`` itself never wires
   them together for a request-facing caller: no function defined *there* ever binds the
   loopback-permitting classifier to anything at all any more. This module -- under ``tests/``,
   confirmed by ``pyproject.toml``'s own ``[tool.hatch.build.targets.wheel] packages =
   ["src/manosube_agent_civilization"]`` to be entirely absent from the distributed wheel -- is
   the one place in this entire repository that performs that wiring. A caller who has only
   ``pip install``ed this package, rather than cloned its source tree, cannot import this module
   at all: it does not exist in what they installed.

**What this is not, disclosed rather than implied.** This is not cryptographic capability
security, and it is not claimed to be. ``runtime/bootstrap.py``'s own production credential
boundary anchors trust in a real Ed25519 signature verified against a deployment-configured
public key, because forging that boundary would grant a real, durable, high-value production
capability. This boundary grants something categorically smaller: permission for one disposable,
already-source-visible test process to fetch from ``127.0.0.1`` -- a target every test in this
repository already has unmediated ``socket``/``subprocess`` access to regardless of anything this
module does. Requiring a real cryptographic anchor here would be security theater over a boundary
whose entire blast radius is already inside the caller's own trust domain. What this module
*does* close, and what Round 3 asked for, is structural: there is no longer a single, stably
named, request-shaped function anywhere in the *shipped* package through which a production
caller -- someone who imported this library as a dependency, never cloned its test tree -- could
reach loopback. Reaching it now requires being this repository's own test suite, not merely being
able to `import manosube_agent_civilization.url_boot.route`.

Every other unsafe address class (private/link-local/multicast/reserved) remains refused
identically to production through this composition -- the loopback exception is the *only* one
``_require_safe_resolved_address_permitting_loopback_only`` ever admits -- so even this trusted
composition cannot be used to reach anything beyond a disposable local test target.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from manosube_agent_civilization.url_boot.route import (
    _observe_url_source_impl,
    _perform_connection_via_trusted_network,
    _require_safe_resolved_address_permitting_loopback_only,
)


def compose_disposable_local_test_observer(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    adapter: Any,
) -> Callable[[Mapping[str, Any], Mapping[str, Any], str], dict[str, Any]]:
    """Bind one canonical Store, Project, Project Binding, and adapter -- once -- and return the
    request-facing observation operation itself, already closed over all four plus the
    loopback-permitting classifier and the trusted real-network connector.

    The returned closure's own call signature is exactly ``(source_identity, boundary,
    observed_at)``: no Store, no adapter, no classifier, no policy flag, and no alternate-world
    substitution input of any kind (P17-R3-F2). Calling this factory again, with a different
    Store/adapter, produces a genuinely independent closure over that different world -- the
    factory itself does not cache or share state across calls -- but no *caller of a returned
    closure* can redirect it to a different world after the fact.
    """

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
            perform_connection=_perform_connection_via_trusted_network,
        )

    return observe


__all__ = ["compose_disposable_local_test_observer"]
