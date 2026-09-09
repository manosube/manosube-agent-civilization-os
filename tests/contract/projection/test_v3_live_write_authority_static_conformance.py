"""Phase 14 (Issue #62), Structural Review Round 8 (P14-R8-F1), Round 9 (P14-R9-F1), Round 10
(P14-R10-F1), and Round 11 (P14-R11-F1): static proof that the V3 live-write gate consumes the
canonical Authority/Binding/Boot/Difference/Change/Evidence owners -- never a parallel,
test-only signing mechanism, a caller-supplied authoritative record body, a caller-selected
Store, or a caller-supplied subject -- holds no private key of its own, and cannot construct a
Store under any circumstance.

A real AST walk over module source -- never a grep, never a hand-maintained assumption -- the
identical technique
``tests/contract/projection/test_projection_static_conformance.py`` and
``tests/contract/independent_verification/test_independent_verification_static_conformance.py``
already establish, applied here to prove:

1. The live gate module (:mod:`tests.fixtures.v3_live_write_authority`) imports and consumes
   the real canonical owners -- ``authority.projection_authorization.
   evaluate_projection_authorization``, ``boot.boot_project``, the Difference/Change/Evidence
   identity owners, and the Difference schema validator -- and never imports the test-only
   material builder (:mod:`tests.fixtures.v3_authority_test_material`),
   ``tests.fixtures.product_binding`` (the repository-held test signer), or
   ``Ed25519PrivateKey``.
2. That live gate module defines no private-key-producing or signature-producing callable of
   its own.
3. The entire shipped Kernel package (``src/manosube_agent_civilization``) contains no
   reference to any V3-specific authority module, constant, or literal, and imports no
   ``Ed25519PrivateKey`` -- the V3 harness never ships.
4. The test-only material builder is never imported by the live gate module.
5. Structural Review Round 9 (P14-R9-F1): the live gate's own authorization entry points
   accept no parameter that could carry an authoritative Project Binding, grant, declaration,
   Authority Decision, or subject **body** -- only a Store instance, project identity strings,
   a configuration, and project-scoped **references**.
6. Structural Review Round 11 (P14-R11-F1): the live gate module never imports
   ``FileStateStore`` at all -- it has no capability to open, select, or construct a Store
   under any circumstance; the Store it operates against is exclusively a caller-injected
   parameter. The now-removed Round 10 trusted-root environment variable and its associated
   type/loader/opener no longer exist. ``resolve_v3_live_write_authority`` accepts no
   ``subjects``/``subject_record``/``subject_records`` parameter of any kind -- every subject
   it consumes is resolved from the Store by reference alone.
7. Structural Review Round 12 (P14-R12-F1): the formal Phase 14 execution interface required
   the opaque context as its own first argument and accepted no Store-selecting field, no
   authoritative body parameter, and no separate subject mapping either -- the identical closed
   shape this file already proves for ``resolve_v3_live_write_authority``, now proved for the
   interface that actually reaches the adapter.
8. Structural Review Round 13 (P14-R13-F1/F2): the opaque context types and the bound-once
   execution capability now live in the shipped ``manosube_agent_civilization.projection``
   package itself -- ``ProjectionExecutionContext``, ``PreIssuedProjectionAuthority``,
   ``execution_context_still_current``, and ``ProjectionExecutionCapability`` -- importable
   from the installed Kernel wheel without importing ``tests`` at all; this file's own
   ``tests.fixtures.v3_live_write_authority`` (the live gate module) names for these types are
   now proved to be plain aliases for the shipped ones, never separate definitions.
   ``ProjectionExecutionCapability.execute``, the shipped capability's own single
   adapter-reaching method, accepts no ``context``, ``store``, ``project_id``, or
   ``project_binding_id`` parameter of any kind on its own signature -- there is no legitimate
   call shape through which a caller could ever substitute a different trust root into a
   capability already bound to one at construction. The entire shipped Kernel package is proved
   to import no ``tests.*`` module anywhere in its own source (not merely the two V3-specific
   literals items 1-4 above already covered), and the integration harness that exercises the
   complete V3 vertical proof is proved to import ``ProjectionExecutionCapability`` from the
   shipped package directly, never through the test-fixture layer.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import pathlib
from types import ModuleType

import tests.fixtures.v3_authority_test_material as test_material_module
import tests.fixtures.v3_live_write_authority as live_gate_module
import tests.integration.projection.test_v3_real_github_vertical_proof as integration_harness_module

import manosube_agent_civilization
import manosube_agent_civilization.projection.execution as shipped_execution_module

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent

#: Literal strings that, if found anywhere in the shipped Kernel package's own source, would
#: mean either V3-specific authority material or Ed25519 private-key-construction capability
#: had leaked into what actually ships in the wheel.
_FORBIDDEN_SHIPPED_LITERALS = (
    "v3_live_write_authority",
    "v3_authority_test_material",
    "Ed25519PrivateKey",
)

#: Parameter names that would signal a caller-supplied authoritative record **body** -- rather
#: than a reference to one already resolved from the caller-injected Store, or the resolved
#: subject a successful authorization itself already produced -- forbidden on every one of the
#: live gate's own authorization entry points (Structural Review Round 9, P14-R9-F1; extended
#: to the subject channel, Structural Review Round 11, P14-R11-F1 §3/§8.4: no caller-supplied
#: subject body and no separate ``subjects`` mapping of any kind).
_FORBIDDEN_BODY_PARAMETER_NAMES = (
    "material",
    "project_binding",
    "grants",
    "grant_declarations",
    "grant_declaration",
    "subjects",
    "subject_record",
    "subject_records",
)

#: Field/parameter names that would signal a caller could select which Store to open --
#: forbidden anywhere in the untrusted references shape or its own loader (Structural Review
#: Round 10, P14-R10-F1; unchanged by Round 11, P14-R11-F1, which removes the Store-selecting
#: surface these names describe from the module's *environment* input entirely, rather than
#: adding it back anywhere else).
_FORBIDDEN_STORE_SELECTING_NAMES = ("store_root", "project_id", "project_binding_id")


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


def test_live_gate_module_never_imports_the_repository_test_signer() -> None:
    """Structural Review Round 10 (P14-R10-F1): the live gate cannot import
    :mod:`tests.fixtures.product_binding`, this repository's own test-only signing helper --
    the live execution path must never be capable of minting a grant/declaration itself, even
    indirectly."""

    imported = _imported_module_names(live_gate_module)
    assert not any("product_binding" in name for name in imported)


def test_live_gate_module_never_imports_ed25519_private_key() -> None:
    imported = _imported_module_names(live_gate_module)
    assert not any("Ed25519PrivateKey" in name for name in imported)
    assert "Ed25519PrivateKey" not in inspect.getsource(live_gate_module)


def test_live_gate_module_never_imports_file_state_store() -> None:
    """Structural Review Round 11 (P14-R11-F1): the live gate module has no capability to
    construct, open, or select a Store under any circumstance -- it never even imports
    ``FileStateStore``, replacing Round 10's weaker "exactly one Store-opening function" proof.
    The Store it operates against is exclusively a caller-injected parameter of
    :func:`~tests.fixtures.v3_live_write_authority.resolve_v3_live_write_authority`."""

    imported = _imported_module_names(live_gate_module)
    assert not any(name.endswith("FileStateStore") for name in imported)


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
    assert any(name.endswith("difference_id") for name in imported)
    assert any(name.endswith("change_id") for name in imported)
    assert any(name.endswith("change_semantic_fingerprint") for name in imported)
    assert any(name.endswith("evidence_semantic_fingerprint") for name in imported)
    assert any(name.endswith("validate_record") for name in imported)


def test_live_gate_module_defines_no_private_key_or_signing_capability() -> None:
    for removed_name in (
        "_signing_private_key",
        "sign_v3_live_write_authority",
        "assemble_v3_live_write_authority",
        "v3_authority_signing_key",
        "V3_LIVE_TRUST_ANCHOR",
        "_verified_project_binding",
        "load_v3_live_write_authority_material",
        "v3_configuration_subject_ref",
        "V3_CONFIGURATION_SUBJECT_KIND",
        "V3TrustedBootRoot",
        "load_v3_trusted_boot_root",
        "open_v3_trusted_store",
        "V3_TRUSTED_BOOT_ROOT_ENV",
        # Structural Review Round 13 (P14-R13-F2): the plain, stateless Round 12 execution
        # entry point is removed outright, replaced by the shipped, bound-once
        # ProjectionExecutionCapability -- this test-fixture module defines no capability of
        # its own.
        "execute_v3_authorized_projection",
        "ProjectionExecutionCapability",
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
# Structural Review Round 11 (P14-R11-F1): the live gate accepts a caller-injected Store and
# project identity, never a Store-selecting reference, and no caller-supplied subject of any
# kind.
# ---------------------------------------------------------------------------


def test_resolve_v3_live_write_authority_accepts_no_authoritative_body_parameter() -> None:
    signature = inspect.signature(live_gate_module.resolve_v3_live_write_authority)
    forbidden = set(_FORBIDDEN_BODY_PARAMETER_NAMES) & set(signature.parameters)
    assert forbidden == set()


def test_resolve_v3_live_write_authority_takes_store_identity_config_and_references() -> None:
    """Structural Review Round 11 (P14-R11-F1): the live gate no longer takes a
    ``trusted_root`` (Round 10's own environment-loaded type, now removed entirely) -- it takes
    the caller-injected Store object itself, plain project identity strings, the frozen V3
    configuration, and the untrusted grant/declaration references, in that order."""

    signature = inspect.signature(live_gate_module.resolve_v3_live_write_authority)
    assert list(signature.parameters) == [
        "store",
        "project_id",
        "project_binding_id",
        "config",
        "references",
    ]


def test_v3_execution_context_still_current_accepts_only_the_opaque_context() -> None:
    signature = inspect.signature(live_gate_module.v3_execution_context_still_current)
    assert list(signature.parameters) == ["context"]


def test_v3_live_write_authority_references_carries_no_store_selecting_field() -> None:
    field_names = {
        field.name for field in dataclasses.fields(live_gate_module.V3LiveWriteAuthorityReferences)
    }
    assert field_names.isdisjoint(_FORBIDDEN_STORE_SELECTING_NAMES)
    assert field_names == {
        "github_projection_grant_refs",
        "github_projection_grant_declaration_refs",
    }


def test_v3_authorized_execution_context_carries_the_caller_injected_store_and_resolved_subjects() -> (
    None
):
    """Structural Review Round 11 (P14-R11-F1): the frozen context carries the exact Store
    object/handle the caller injected, and each :class:`~tests.fixtures.v3_live_write_authority.
    V3PreIssuedProjectionAuthority` carries the resolved subject record itself -- so
    ``project_to_github`` never needs, and this module never offers, a caller-supplied subject
    body or a separate subject mapping of any kind."""

    context_fields = {
        field.name for field in dataclasses.fields(live_gate_module.V3AuthorizedExecutionContext)
    }
    assert "store" in context_fields
    authority_fields = {
        field.name for field in dataclasses.fields(live_gate_module.V3PreIssuedProjectionAuthority)
    }
    assert {"subject_ref", "subject_record"}.issubset(authority_fields)


# ---------------------------------------------------------------------------
# Structural Review Round 13 (P14-R13-F1/F2): the opaque context types and the bound-once
# execution capability now live in the shipped manosube_agent_civilization.projection package
# itself, not in tests.fixtures.v3_live_write_authority -- this file's own live-gate-module names
# for them are proved to be plain aliases, never separate definitions. The shipped capability's
# own single adapter-reaching method accepts no context/store/project-identity-replacing
# parameter of any kind, and the shipped module itself, along with the entire shipped Kernel
# package, is proved to import no tests.* module anywhere.
# ---------------------------------------------------------------------------


def test_v3_context_and_authority_types_are_the_shipped_production_types() -> None:
    """The live gate module defines no separate ``V3AuthorizedExecutionContext``/
    ``V3PreIssuedProjectionAuthority``/``v3_execution_context_still_current`` of its own any
    more -- each is the identical object the shipped
    ``manosube_agent_civilization.projection.execution`` module defines."""

    assert live_gate_module.V3AuthorizedExecutionContext is (
        shipped_execution_module.ProjectionExecutionContext
    )
    assert live_gate_module.V3PreIssuedProjectionAuthority is (
        shipped_execution_module.PreIssuedProjectionAuthority
    )
    assert live_gate_module.v3_execution_context_still_current is (
        shipped_execution_module.execution_context_still_current
    )


def test_shipped_execution_module_imports_no_tests_module() -> None:
    imported = _imported_module_names(shipped_execution_module)
    assert not any(name == "tests" or name.startswith("tests.") for name in imported)


def test_shipped_kernel_package_imports_no_tests_module_anywhere() -> None:
    """Every ``.py`` file in the entire shipped ``manosube_agent_civilization`` package -- what
    actually ends up in the wheel -- is AST-walked for its own ``import``/``from ... import``
    statements; none may name ``tests`` or any ``tests.*`` submodule (Structural Review Round
    13, P14-R13-F1: production code imports no ``tests.*`` module, proved for the whole shipped
    package, not merely the V3-specific literal scan
    ``test_shipped_kernel_package_contains_no_v3_authority_material`` already makes above)."""

    shipped_files = sorted(_SHIPPED_PACKAGE_ROOT.rglob("*.py"))
    assert shipped_files, "expected at least one shipped module to scan"
    offenders: list[tuple[str, str]] = []
    for path in shipped_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "tests" or alias.name.startswith("tests."):
                        offenders.append((str(path.relative_to(_REPO_ROOT)), alias.name))
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module is not None
                and (node.module == "tests" or node.module.startswith("tests."))
            ):
                offenders.append((str(path.relative_to(_REPO_ROOT)), node.module))
    assert offenders == []


def test_projection_execution_capability_constructor_requires_context_as_first_argument() -> None:
    signature = inspect.signature(shipped_execution_module.ProjectionExecutionCapability.__init__)
    parameters = list(signature.parameters)
    assert parameters[:2] == ["self", "context"]
    assert signature.parameters["context"].default is inspect.Parameter.empty


def test_projection_execution_capability_execute_accepts_no_context_replacing_parameter() -> None:
    """Structural Review Round 13 (P14-R13-F2) requirement: the public adapter-reaching method
    has no context-replacement parameter of any kind -- not merely refused if supplied, but
    absent from its own signature entirely, provable by introspection alone, independent of any
    particular constructed instance."""

    signature = inspect.signature(shipped_execution_module.ProjectionExecutionCapability.execute)
    parameter_names = set(signature.parameters) - {"self"}
    assert parameter_names.isdisjoint(
        {"context", "store", "project_id", "project_binding_id"}
        | set(_FORBIDDEN_BODY_PARAMETER_NAMES)
    )
    assert parameter_names == {
        "projection_kind",
        "target_repository",
        "projection_payload",
        "adapter",
        "materialized_at",
        "attempt_claim_token",
    }


def test_integration_harness_imports_the_shipped_capability_directly() -> None:
    """Structural Review Round 13 (P14-R13-F1) requirement: "The final controlled harness MUST
    import and exercise the shipped production interface." -- proved here by AST-walking the
    integration harness module's own import statements for a ``ProjectionExecutionCapability``
    name imported from the shipped ``manosube_agent_civilization.projection`` package, never
    from the test-fixture layer (which defines no such name any more)."""

    tree = ast.parse(inspect.getsource(integration_harness_module))
    found = False
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.startswith("manosube_agent_civilization.projection")
            and any(alias.name == "ProjectionExecutionCapability" for alias in node.names)
        ):
            found = True
    assert found, (
        "expected the integration harness to import ProjectionExecutionCapability from the "
        "shipped manosube_agent_civilization.projection package"
    )
    assert not hasattr(live_gate_module, "ProjectionExecutionCapability")
    assert not hasattr(live_gate_module, "execute_v3_authorized_projection")


def test_load_v3_live_write_authority_references_refuses_smuggled_store_selecting_keys() -> None:
    import json

    for key in _FORBIDDEN_STORE_SELECTING_NAMES:
        payload = {
            "github_projection_grant_refs": [{"kind": "github_projection_grant", "id": "X"}],
            "github_projection_grant_declaration_refs": [
                {"kind": "github_projection_grant_declaration", "id": "Y"}
            ],
            key: "attacker-supplied-value",
        }
        env = {
            live_gate_module.V3_LIVE_WRITE_AUTHORITY_REFERENCES_ENV: json.dumps(payload),
        }
        assert live_gate_module.load_v3_live_write_authority_references(env=env) is None
