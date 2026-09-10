"""Phase 17 (Issue #69) URL Boot: static conformance proofs.

A real AST walk over the ``url_boot`` package's own module source -- never a grep, never a
hardcoded name list -- the identical technique ``tests/contract/runtime/
test_runtime_static_conformance.py`` already establishes, scaled down to this package's own
deliberately simpler shape: no deployment declaration, no root admission, no signing, no
composition step. Two routes only (P17-C8): :func:`observe_url_source` and
:func:`route_url_observation_to_evidence`.

P17-C5's own network-safety requirement is proved here structurally: ``network.py`` is the one
and only module in this package permitted to import ``socket``/``http.client``/``ssl``/
``ipaddress`` -- every other module, ``adapter.py`` included, reaches a real socket only through
that one owner's own :func:`~manosube_agent_civilization.url_boot.network.
perform_admitted_connection`.

Structural Review Round 3 (P17-R3-F1/F2) adds three further proofs: the
:class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter` Protocol declares no
connect-capable method at all; ``route.py`` itself never binds the loopback-permitting classifier
to anything; and this shipped package defines no second, loopback-permitting entry point under
any name.
"""

from __future__ import annotations

import ast
import inspect
import pathlib
from types import ModuleType

import manosube_agent_civilization
import manosube_agent_civilization.url_boot as url_boot_module
import manosube_agent_civilization.url_boot.adapter as adapter_module
import manosube_agent_civilization.url_boot.engine as engine_module
import manosube_agent_civilization.url_boot.errors as errors_module
import manosube_agent_civilization.url_boot.evidence_handoff as evidence_handoff_module
import manosube_agent_civilization.url_boot.identity as identity_module
import manosube_agent_civilization.url_boot.network as network_module
import manosube_agent_civilization.url_boot.route as route_module
import manosube_agent_civilization.url_boot.types as types_module

_ALL_PACKAGE_MODULES = (
    route_module,
    engine_module,
    identity_module,
    types_module,
    errors_module,
    adapter_module,
    evidence_handoff_module,
    network_module,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent
_URL_BOOT_PACKAGE_ROOT = _SHIPPED_PACKAGE_ROOT / "url_boot"

#: The transport-opening standard-library surfaces P17-C5's own resolve-once-connect-to-that-
#: address technique requires -- confined to exactly one module (this package's own deliberate
#: departure from Runtime's I/O-free ``network.py`` precedent, disclosed in ``network.py``'s own
#: module docstring).
_NETWORK_OPENING_MODULES = ("socket", "http.client", "ssl", "ipaddress")

_FORBIDDEN_OWNER_MODULE_PREFIXES = (
    "manosube_agent_civilization.reflow",
    "manosube_agent_civilization.independent_verification",
    "manosube_agent_civilization.authority",
    "manosube_agent_civilization.projection",
    "manosube_agent_civilization.model_runtime",
    "manosube_agent_civilization.agent_runtime",
    "manosube_agent_civilization.change",
)


def _imported_module_names(module: ModuleType) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def _call_site_count(module: ModuleType, name: str) -> int:
    tree = ast.parse(inspect.getsource(module))
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Name) and func.id == name) or (
            isinstance(func, ast.Attribute) and func.attr == name
        ):
            count += 1
    return count


def test_url_boot_package_exports_exactly_two_routes() -> None:
    """``PUBLIC_URL_BOOT_ENTRY_POINT_COUNT=2`` (module docstring): the observation route and its
    single Evidence hand-off, and nothing else callable."""

    public_callables = {
        name
        for name in url_boot_module.__all__
        if callable(getattr(url_boot_module, name))
        and not isinstance(getattr(url_boot_module, name), type)
    }
    assert public_callables == {"observe_url_source", "route_url_observation_to_evidence"}


#: ``adapter.py`` imports ``socket`` for exactly one narrow purpose: classifying the one typed
#: exception a genuine DNS lookup lets escape (``socket.gaierror``) into
#: :data:`~manosube_agent_civilization.url_boot.types.URL_HOP_RESOLVE_OUTCOMES`'s own
#: ``DNS_FAILURE`` -- never to open a socket itself, which stays exclusively ``network.py``'s own
#: job. Since Structural Review Round 3 (P17-R3-F1), ``adapter.py`` no longer imports ``ssl`` at
#: all: ``LocalHttpUrlSourceAdapter`` performs no connection of any kind any more, so it has no TLS
#: exception left to classify. Proved by the accompanying source-level check that no
#: socket-opening/TLS-wrapping call appears in this module.
_ADAPTER_ADMITTED_EXCEPTION_CLASSIFICATION_SURFACES = ("socket",)
_SOCKET_OPENING_CALL_NAMES = (
    "socket",
    "create_connection",
    "wrap_socket",
    "create_default_context",
    "HTTPConnection",
    "HTTPSConnection",
)


def test_network_opening_surfaces_are_confined_to_network_py() -> None:
    """P17-C5's own structural proof: no module besides ``network.py`` may import ``http.client``
    or ``ipaddress`` at all, and only ``network.py``/``adapter.py`` may import ``socket``/``ssl``
    -- ``adapter.py``'s own use is narrowed to exception-type classification alone by the
    accompanying source-level check, never to opening a socket or wrapping TLS itself."""

    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        offending = {
            name
            for name in imported
            if any(
                name == surface or name.startswith(surface + ".")
                for surface in _NETWORK_OPENING_MODULES
            )
        }
        if module is network_module:
            assert offending == set(_NETWORK_OPENING_MODULES), offending
        elif module is adapter_module:
            assert offending == set(_ADAPTER_ADMITTED_EXCEPTION_CLASSIFICATION_SURFACES), offending
        else:
            assert not offending, (
                f"{module.__name__} imports a network-opening surface: {offending}"
            )


def test_adapter_never_opens_a_socket_or_wraps_tls_itself() -> None:
    """The narrowing half of the exception above: ``adapter.py`` may name ``socket`` only to catch
    its exception type -- it must call none of the actual socket-opening or TLS-wrapping
    primitives that module or ``ssl`` expose. Every real connection is made exclusively through
    :func:`~manosube_agent_civilization.url_boot.network.perform_admitted_connection`, called
    directly by ``route.py`` (P17-R3-F1) -- never through any adapter method at all."""

    source = inspect.getsource(adapter_module)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            assert name not in _SOCKET_OPENING_CALL_NAMES, f"adapter.py calls {name!r} directly"


def test_no_module_imports_a_forbidden_existing_owner() -> None:
    """URL Boot mints no Authority, no Reflow/Change/Model-Runtime decision, and reaches no
    Independent Verification, Projection, or Agent Runtime machinery of its own (P17-C4)."""

    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        for forbidden_prefix in _FORBIDDEN_OWNER_MODULE_PREFIXES:
            assert not any(
                name == forbidden_prefix or name.startswith(forbidden_prefix + ".")
                for name in imported
            ), f"{module.__name__} imports forbidden owner prefix {forbidden_prefix!r}: {imported}"


def test_evidence_is_imported_only_by_evidence_handoff() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        evidence_imports = {
            name
            for name in imported
            if name == "manosube_agent_civilization.evidence"
            or name.startswith("manosube_agent_civilization.evidence.")
        }
        if module is evidence_handoff_module:
            assert evidence_imports == {"manosube_agent_civilization.evidence"}
        else:
            assert not evidence_imports, f"{module.__name__} imports evidence: {evidence_imports}"


def test_evidence_handoff_calls_derive_evidence_exactly_once() -> None:
    assert _call_site_count(evidence_handoff_module, "derive_evidence") == 1


def test_boot_project_is_imported_and_called_only_by_route() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        names_boot = any(
            name == "manosube_agent_civilization.boot"
            or name.startswith("manosube_agent_civilization.boot.")
            for name in imported
        )
        if module is route_module:
            assert names_boot, "route.py is expected to import boot"
        else:
            assert not names_boot, f"{module.__name__} imports manosube_agent_civilization.boot"
    assert _call_site_count(route_module, "boot_project") == 1


def test_store_is_committed_to_only_by_route() -> None:
    """``commit_state_transition`` -- the one existing canonical persistence boundary -- is
    called from exactly one place in this package."""

    for module in _ALL_PACKAGE_MODULES:
        if module is route_module:
            continue
        assert _call_site_count(module, "commit_state_transition") == 0, module.__name__
    assert _call_site_count(route_module, "commit_state_transition") == 1


def test_no_shipped_url_boot_module_reads_configuration_or_a_filesystem_path() -> None:
    """No request-path code may read an environment variable, a file, or a registry to choose a
    different network scope, mirroring ``runtime/test_runtime_static_conformance.py``'s own
    identical control."""

    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        assert not any(
            name == "os" or name.startswith("os.") or name in ("pathlib", "configparser")
            for name in imported
        ), f"{module.__name__} imports a configuration surface: {imported}"
        source = inspect.getsource(module)
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Name):
                assert node.id not in ("environ", "getenv", "expanduser"), (
                    f"{module.__name__} names {node.id!r} at {node.lineno}"
                )
            if isinstance(node, ast.Attribute):
                assert node.attr not in ("environ", "getenv", "expanduser"), (
                    f"{module.__name__} names {node.attr!r} at {node.lineno}"
                )
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id != "open", f"{module.__name__} reads a file at {node.lineno}"
            elif isinstance(func, ast.Attribute):
                assert func.attr not in ("read_text", "read_bytes"), (
                    f"{module.__name__} reads a file at {node.lineno}"
                )


def test_no_shipped_url_boot_module_names_a_dynamic_tool_dispatch_or_subprocess_surface() -> None:
    """P17's own explicit non-claim: fetched content is never trusted to mean anything on its
    own (P17-C4) -- no module in this package may import ``subprocess``, ``eval``, ``exec``, or a
    browser-automation surface."""

    forbidden_modules = ("subprocess", "playwright", "selenium", "webbrowser")
    forbidden_calls = ("eval", "exec", "compile", "__import__")
    for path in sorted(_URL_BOOT_PACKAGE_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not any(
            name == forbidden or name.startswith(forbidden + ".")
            for forbidden in forbidden_modules
            for name in imported
        ), f"{path} imports a forbidden dynamic-execution surface"
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in forbidden_calls, f"{path} calls {node.func.id!r}"


def test_the_url_source_adapter_protocol_declares_no_connect_capable_method() -> None:
    """Structural Review Round 3 (P17-R3-F1): the replaceable
    :class:`~manosube_agent_civilization.url_boot.types.UrlSourceAdapter` Protocol must carry no
    method through which a caller-supplied adapter implementation could ever be asked to perform a
    network connection -- ``resolve_hop`` (a bounded DNS lookup, independently safety-classified by
    the route before its result is ever used) is the only method this Protocol declares."""

    from manosube_agent_civilization.url_boot.types import UrlSourceAdapter

    declared_methods = {
        name
        for name, value in vars(UrlSourceAdapter).items()
        if not name.startswith("_") and callable(value)
    }
    assert declared_methods == {"resolve_hop"}, declared_methods
    assert not hasattr(UrlSourceAdapter, "connect_hop")


def test_local_http_url_source_adapter_declares_no_connect_capable_method() -> None:
    """The shipped real-network adapter implementation mirrors the narrowed Protocol exactly
    (P17-R3-F1): it carries no ``connect_hop`` or other connect-capable method of its own -- every
    real connection is made by ``route.py`` calling
    :func:`~manosube_agent_civilization.url_boot.network.perform_admitted_connection` directly."""

    assert not hasattr(adapter_module.LocalHttpUrlSourceAdapter, "connect_hop")


def test_route_py_never_binds_the_loopback_permitting_classifier_to_anything() -> None:
    """Structural Review Round 3 (P17-R3-F2): ``route.py`` still defines
    ``_require_safe_resolved_address_permitting_loopback_only`` (a raw Python name in an
    importable module cannot be made truly unreachable), but no function *defined in this module*
    may reference it anywhere except its own definition -- the one place that classifier is ever
    bound to a request-facing operation is this repository's own trusted, non-shipped
    disposable-local-test composition, entirely outside this module and outside the distributed
    package."""

    classifier_name = "_require_safe_resolved_address_permitting_loopback_only"
    tree = ast.parse(inspect.getsource(route_module))
    reference_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == classifier_name:
            continue
        if isinstance(node, ast.Name) and node.id == classifier_name:
            reference_count += 1
    assert reference_count == 0, (
        f"route.py itself references {classifier_name!r} {reference_count} time(s) outside its "
        "own definition"
    )


def test_route_py_defines_no_second_loopback_permitting_entry_point() -> None:
    """Structural Review Round 3 (P17-R3-F2): ``route.py`` no longer defines
    ``observe_url_source_for_disposable_local_test`` (Round 2's own since-removed second entry
    point), and defines no other module-level function whose own name suggests it either."""

    assert not hasattr(route_module, "observe_url_source_for_disposable_local_test")
    forbidden_substrings = ("disposable_local_test", "permit_loopback", "permitting_loopback")
    exempt_prefixes = ("_require_safe_resolved_address", "_perform_connection")
    for name in vars(route_module):
        if name.startswith(exempt_prefixes):
            continue
        assert not any(substring in name for substring in forbidden_substrings), name


def test_route_py_public_surface_is_exactly_one_entry_point() -> None:
    """``route.py``'s own ``__all__`` names exactly the one schema-base constant and the one
    public, request-facing entry point -- unchanged in shape since before Round 3, but now the
    *only* function in this module callable with a caller-supplied Store/adapter/Boundary that
    can ever reach genuine network I/O with the loopback exception admitted."""

    assert route_module.__all__ == ["URL_BOOT_SCHEMA_BASE", "observe_url_source"]


def test_no_shipped_url_boot_module_hardcodes_a_credential_looking_constant() -> None:
    """No API key, bearer token, or password constant anywhere in this package -- every Boundary
    this package ever fetches through carries ``credentials_permitted: false`` (schema-enforced),
    so shipped source should never carry one either."""

    forbidden_names = {"api_key", "apikey", "password", "secret", "bearer_token", "access_token"}
    for path in sorted(_URL_BOOT_PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assert target.id.lower() not in forbidden_names, f"{path}:{node.lineno}"


__all__: list[str] = []
