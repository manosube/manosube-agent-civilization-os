"""Phase 14 (Issue #62), Structural Review Round 7 (P14-R7-F1): static proof that the V3 Live
Write Authority's live trust anchor has no matching signing capability reachable from shipped
or live code.

A real AST walk over module source -- never a grep, never a hand-maintained assumption -- the
identical technique
``tests/contract/projection/test_projection_static_conformance.py`` and
``tests/contract/independent_verification/test_independent_verification_static_conformance.py``
already establish, applied here to prove:

1. The live gate module (:mod:`tests.fixtures.v3_live_write_authority`) never imports the
   dedicated test-only signer (:mod:`tests.fixtures.v3_live_write_authority_test_signer`), and
   never imports ``Ed25519PrivateKey`` at all -- so nothing reachable from that module can ever
   construct a private key.
2. That live gate module defines no private-key-producing or signature-producing callable of
   its own (``_signing_private_key``, ``sign_v3_live_write_authority``,
   ``assemble_v3_live_write_authority`` -- Round 6's own names -- all absent).
3. The entire shipped Kernel package (``src/manosube_agent_civilization``) contains no
   reference to "v3" anywhere in its own source -- the whole V3 harness, trust anchor
   included, is confined to ``tests/`` and never ships.
4. The one live call site (``_v3_live_authorized()`` in
   ``tests/integration/projection/test_v3_real_github_vertical_proof.py``) always and only
   passes the fixed :data:`~tests.fixtures.v3_live_write_authority.V3_LIVE_TRUST_ANCHOR` as
   its own ``trust_anchor`` argument -- textually, in its own source -- with no other
   ``trust_anchor=`` binding anywhere in that function.
5. The test-only trust anchor
   (:data:`~tests.fixtures.v3_live_write_authority_test_signer.V3_TEST_TRUST_ANCHOR`) is
   structurally distinct, by both ``key_id`` and ``public_key``, from the live trust anchor.
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from types import ModuleType

import tests.fixtures.v3_live_write_authority as live_gate_module
from tests.fixtures.v3_live_write_authority import V3_LIVE_TRUST_ANCHOR
import tests.fixtures.v3_live_write_authority_test_signer as test_signer_module
from tests.fixtures.v3_live_write_authority_test_signer import V3_TEST_TRUST_ANCHOR
import tests.integration.projection.test_v3_real_github_vertical_proof as integration_module

import manosube_agent_civilization

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent


def _imported_module_names(module: ModuleType) -> set[str]:
    """Every dotted module name *module*'s own source imports, via ``import``/``from ...
    import`` -- an AST walk of the module's own source text, never the live runtime import
    graph (which could include transitively-imported names this module's own source never
    names)."""

    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def test_live_gate_module_never_imports_the_test_signer() -> None:
    imported = _imported_module_names(live_gate_module)
    assert not any("v3_live_write_authority_test_signer" in name for name in imported)


def test_live_gate_module_never_imports_ed25519_private_key() -> None:
    imported = _imported_module_names(live_gate_module)
    assert not any("Ed25519PrivateKey" in name for name in imported)
    assert "Ed25519PrivateKey" not in inspect.getsource(live_gate_module)


def test_live_gate_module_defines_no_private_key_or_signing_capability() -> None:
    """Round 6's own signing helpers (``_signing_private_key``, ``sign_v3_live_write_
    authority``, ``assemble_v3_live_write_authority``, ``v3_authority_signing_key``) must not
    exist on the live gate module at all after this correction."""

    for removed_name in (
        "_signing_private_key",
        "sign_v3_live_write_authority",
        "assemble_v3_live_write_authority",
        "v3_authority_signing_key",
    ):
        assert not hasattr(live_gate_module, removed_name)


#: Literal strings that, if found anywhere in the shipped Kernel package's own source, would
#: mean either V3 authority material or Ed25519 private-key-construction capability had leaked
#: into what actually ships in the wheel. A blanket "v3" substring ban is deliberately *not*
#: used here -- ``github_adapter.py`` legitimately mentions "the V3 harness" in prose
#: describing its own non-shipped test-only consumer, which is not itself a leak of any V3
#: authority material.
_FORBIDDEN_SHIPPED_LITERALS = (
    "v3_live_write_authority",
    "V3_LIVE_TRUST_ANCHOR",
    "MATERIALIZE_V3_PROOF_RUN",
    "Ed25519PrivateKey",
    V3_LIVE_TRUST_ANCHOR["public_key"],
)


def test_shipped_kernel_package_contains_no_v3_authority_material() -> None:
    """The entire shipped ``manosube_agent_civilization`` package -- what actually ends up in
    the wheel -- names no V3 Live Write Authority module, constant, or literal, and never
    imports ``Ed25519PrivateKey`` (the one class capable of constructing a private signing
    key) anywhere in its own source. The V3 harness, including its trust anchor and any
    signing capability, is confined to ``tests/`` and never importable from a plain
    ``pip install`` of this package."""

    shipped_files = sorted(_SHIPPED_PACKAGE_ROOT.rglob("*.py"))
    assert shipped_files, "expected at least one shipped module to scan"
    offenders = [
        (str(path.relative_to(_REPO_ROOT)), literal)
        for path in shipped_files
        for literal in _FORBIDDEN_SHIPPED_LITERALS
        if literal in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_live_call_site_hardcodes_the_live_trust_anchor() -> None:
    """``_v3_live_authorized()``'s own source textually passes ``trust_anchor=V3_LIVE_TRUST_
    ANCHOR`` and nothing else -- no environment variable, no record field, no other caller-
    reachable input can substitute a different trust anchor into this one live call site."""

    source = inspect.getsource(integration_module._v3_live_authorized)
    assert "trust_anchor=V3_LIVE_TRUST_ANCHOR" in source
    assert source.count("trust_anchor=") == 1


def test_test_signer_trust_anchor_is_distinct_from_the_live_trust_anchor() -> None:
    assert V3_TEST_TRUST_ANCHOR["key_id"] != V3_LIVE_TRUST_ANCHOR["key_id"]
    assert V3_TEST_TRUST_ANCHOR["public_key"] != V3_LIVE_TRUST_ANCHOR["public_key"]


def test_live_trust_anchor_constant_is_exactly_the_frozen_literal() -> None:
    """Proves nothing anywhere in this repository's own test run mutates the live module's own
    trust-anchor constant -- a plain equality check against the exact frozen literal, run
    after collection of every other test module in this package (pytest collects the whole
    session before running any test, so this assertion covers the constant as actually
    imported, not merely as originally authored)."""

    assert dict(V3_LIVE_TRUST_ANCHOR) == {
        "algorithm": "ed25519",
        "key_id": "V3-LIVE-TRUST-ANCHOR-0001",
        "public_key": "bc9c2ae0d18920def2125379f70ce6d99eeeaece5d7940a21b0e30d1858016bd",
    }


def test_live_call_site_function_itself_never_references_the_test_signer() -> None:
    """The integration test *file* legitimately imports the test-only signer for its own
    ``test_unauthorized_or_mismatched_human_authority_causes_zero_network_calls`` negative
    control -- but ``_v3_live_authorized()``'s own function body, the one live gate every
    real-adapter test's ``skipif`` marker consults, never references it."""

    source = inspect.getsource(integration_module._v3_live_authorized)
    assert "v3_live_write_authority_test_signer" not in source
    assert "_for_test" not in source


def test_importing_test_signer_module_does_not_alter_the_live_gate_modules_own_import_set() -> None:
    """A defensive proof that importing :mod:`tests.fixtures.v3_live_write_authority_test_
    signer` for this very test file's own use has not, by side effect, caused the live gate
    module to import it too."""

    assert test_signer_module.V3_TEST_TRUST_ANCHOR is not None
    imported = _imported_module_names(live_gate_module)
    assert not any("v3_live_write_authority_test_signer" in name for name in imported)
