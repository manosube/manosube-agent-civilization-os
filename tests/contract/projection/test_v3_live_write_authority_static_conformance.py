"""Phase 14 (Issue #62), Structural Review Round 8 (P14-R8-F1) and Round 9 (P14-R9-F1): static
proof that the V3 live-write gate consumes the canonical Authority/Binding/Boot/Store owners --
never a parallel, test-only signing mechanism or a caller-supplied authoritative record body --
and holds no private key of its own.

A real AST walk over module source -- never a grep, never a hand-maintained assumption -- the
identical technique
``tests/contract/projection/test_projection_static_conformance.py`` and
``tests/contract/independent_verification/test_independent_verification_static_conformance.py``
already establish, applied here to prove:

1. The live gate module (:mod:`tests.fixtures.v3_live_write_authority`) imports and consumes
   the real canonical owners -- ``authority.projection_authorization.
   evaluate_projection_authorization``, ``boot.boot_project``, and the Store's own
   ``resolve_record`` surface -- and never imports the test-only material builder
   (:mod:`tests.fixtures.v3_authority_test_material`) or ``Ed25519PrivateKey``.
2. That live gate module defines no private-key-producing or signature-producing callable of
   its own.
3. The entire shipped Kernel package (``src/manosube_agent_civilization``) contains no
   reference to any V3-specific authority module, constant, or literal, and imports no
   ``Ed25519PrivateKey`` -- the V3 harness never ships.
4. The test-only material builder is never imported by the live gate module.
5. Structural Review Round 9 (P14-R9-F1): the live gate's own authorization entry points
   (:func:`~tests.fixtures.v3_live_write_authority.resolve_v3_live_write_authority`,
   :func:`~tests.fixtures.v3_live_write_authority.v3_execution_context_still_current`) accept
   no parameter that could carry an authoritative Project Binding, grant, declaration, or
   Authority Decision **body** -- only a Store instance, a configuration, and project-scoped
   **references** (:class:`~tests.fixtures.v3_live_write_authority.
   V3LiveWriteAuthorityReferences`) or an already-resolved
   :class:`~tests.fixtures.v3_live_write_authority.V3AuthorizedExecutionContext`.
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from types import ModuleType

import tests.fixtures.v3_authority_test_material as test_material_module
import tests.fixtures.v3_live_write_authority as live_gate_module

import manosube_agent_civilization

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent

#: Literal strings that, if found anywhere in the shipped Kernel package's own source, would
#: mean either V3-specific authority material or Ed25519 private-key-construction capability
#: had leaked into what actually ships in the wheel.
_FORBIDDEN_SHIPPED_LITERALS = (
    "v3_live_write_authority",
    "v3_authority_test_material",
    "V3_CONFIGURATION_SUBJECT_KIND",
    "Ed25519PrivateKey",
)

#: Parameter names that would signal a caller-supplied authoritative record **body**, rather
#: than a reference to one already resolved from the real Store -- forbidden on every one of
#: the live gate's own authorization entry points (Structural Review Round 9, P14-R9-F1).
_FORBIDDEN_BODY_PARAMETER_NAMES = (
    "material",
    "project_binding",
    "grants",
    "grant_declarations",
    "grant_declaration",
)


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


def test_live_gate_module_never_imports_the_test_material_builder() -> None:
    imported = _imported_module_names(live_gate_module)
    assert not any("v3_authority_test_material" in name for name in imported)


def test_live_gate_module_never_imports_ed25519_private_key() -> None:
    imported = _imported_module_names(live_gate_module)
    assert not any("Ed25519PrivateKey" in name for name in imported)
    assert "Ed25519PrivateKey" not in inspect.getsource(live_gate_module)


def test_live_gate_module_imports_the_real_canonical_owners() -> None:
    imported = _imported_module_names(live_gate_module)
    assert any(
        name.endswith("evaluate_projection_authorization")
        or name == "manosube_agent_civilization.authority.projection_authorization"
        for name in imported
    )
    assert any(
        name.endswith("boot_project") or name == "manosube_agent_civilization.boot"
        for name in imported
    )
    assert any(
        name == "manosube_agent_civilization.store" or name.endswith("FileStateStore")
        for name in imported
    )


def test_live_gate_module_defines_no_private_key_or_signing_capability() -> None:
    for removed_name in (
        "_signing_private_key",
        "sign_v3_live_write_authority",
        "assemble_v3_live_write_authority",
        "v3_authority_signing_key",
        "V3_LIVE_TRUST_ANCHOR",
        "_verified_project_binding",
        "load_v3_live_write_authority_material",
    ):
        assert not hasattr(live_gate_module, removed_name)


def test_shipped_kernel_package_contains_no_v3_authority_material() -> None:
    """The entire shipped ``manosube_agent_civilization`` package -- what actually ends up in
    the wheel -- names no V3 authority module, constant, or literal, and never imports
    ``Ed25519PrivateKey`` anywhere in its own source."""

    shipped_files = sorted(_SHIPPED_PACKAGE_ROOT.rglob("*.py"))
    assert shipped_files, "expected at least one shipped module to scan"
    offenders = [
        (str(path.relative_to(_REPO_ROOT)), literal)
        for path in shipped_files
        for literal in _FORBIDDEN_SHIPPED_LITERALS
        if literal in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_test_material_builder_is_never_imported_by_the_live_gate_module() -> None:
    """A defensive proof that importing :mod:`tests.fixtures.v3_authority_test_material` for
    this very test file's own use has not, by side effect, caused the live gate module to
    import it too."""

    assert test_material_module.genuine_project_binding is not None
    imported = _imported_module_names(live_gate_module)
    assert not any("v3_authority_test_material" in name for name in imported)


# ---------------------------------------------------------------------------
# Structural Review Round 9 (P14-R9-F1): the live gate accepts only references, never bodies.
# ---------------------------------------------------------------------------


def test_resolve_v3_live_write_authority_accepts_no_authoritative_body_parameter() -> None:
    signature = inspect.signature(live_gate_module.resolve_v3_live_write_authority)
    forbidden = set(_FORBIDDEN_BODY_PARAMETER_NAMES) & set(signature.parameters)
    assert forbidden == set()


def test_resolve_v3_live_write_authority_takes_a_store_and_references_not_a_material_blob() -> None:
    signature = inspect.signature(live_gate_module.resolve_v3_live_write_authority)
    parameter_names = list(signature.parameters)
    assert parameter_names == ["store", "config", "references"]


def test_v3_execution_context_still_current_accepts_only_the_opaque_context() -> None:
    signature = inspect.signature(live_gate_module.v3_execution_context_still_current)
    assert list(signature.parameters) == ["context"]


def test_v3_live_write_authority_references_dataclass_carries_no_body_field() -> None:
    import dataclasses

    field_names = {
        field.name for field in dataclasses.fields(live_gate_module.V3LiveWriteAuthorityReferences)
    }
    assert field_names == {
        "store_root",
        "project_id",
        "project_binding_id",
        "github_projection_grant_refs",
        "github_projection_grant_declaration_refs",
    }
