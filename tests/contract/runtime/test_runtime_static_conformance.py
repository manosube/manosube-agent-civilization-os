"""Phase 15 (Issue #64) Runtime: static conformance proofs.

A real AST walk over the ``runtime`` package's own module source -- never a grep, never a
hardcoded name list -- mirroring ``tests/contract/projection/
test_projection_static_conformance.py``'s own technique exactly, adapted to Runtime's own
disclosed architectural divergences from Projection:

- Runtime Observation is bounded by its own closed Observation Boundary, never by an
  Authority Decision -- so ``authority``/``evaluate_projection_authorization`` is legitimately
  imported and called only by ``bootstrap.py`` (V5's own trusted-provisioning concern),
  never by ``route.py`` at all (unlike Projection's own ``route.py``, which is the one and
  only Authority call site in that package).
- ``bootstrap.py`` legitimately imports the shipped ``manosube_agent_civilization.projection``
  package (the Phase 14 execution interface it provisions), ``binding.identity`` (declaration
  signature reverification), and ``difference``/``change`` identity utilities (subject
  reverification) -- none of which any other module in this package may import.
- ``boot_project`` has two legitimate call sites in this package (``route.py`` and
  ``bootstrap.py``), never a single one the way Projection's own package requires.

Structural Review Round 1 (P15-R1) changed four of the facts this file pins, each recorded at
the test that pins it:

- ``network.py`` exists (P15-R1-F1) and is the *second* module in this package naming
  ``urllib`` -- admitted here for exactly one import, the pure, parse-only ``urllib.parse``,
  and additionally proved to open nothing at all.
- ``route.py`` still has exactly one literal ``boot_project`` call site, but now reaches it
  from three points per observation (P15-R1-F5) through one private helper.
- ``engine.py`` additionally imports ``difference.errors`` (P15-R1-F2), to translate the
  canonical schema validator's own failure into this package's own refusal vocabulary.
- the package exported a fourth public callable, ``provision_trusted_runtime_root``
  (P15-R1-F4) -- a provisioning entry point, not a fourth route. **Round 2 (P15-R2-F1) deletes
  that callable outright**; see the two facts below.

Structural Review Round 2 (P15-R2) changes two further facts this file pins:

- ``provision_trusted_runtime_root`` no longer exists anywhere in the shipped package, and no
  shipped file constructs a ``TrustedRuntimeRoot`` at all -- proved by an AST walk over every
  ``.py`` file in the *installed* package, the identical technique
  ``tests/contract/projection/test_v3_live_write_authority_static_conformance.py`` already uses
  for "no shipped file may contain this forbidden material" (P15-R2-F1).
- ``deployment_declaration.py`` exists (P15-R2-F2) and is the *second* module in this package
  importing ``binding`` -- admitted here for exactly one import, ``binding.signature``, whose
  shared Ed25519 primitive it composes rather than reimplements.

Structural Review Round 3 (P15-R3) changes four further facts this file pins:

- ``root_admission.py`` exists (P15-R3-F1) and is the *third* module importing ``binding`` --
  again for exactly one import, ``binding.signature``, again composed rather than reimplemented,
  and again verification-only. The three Round 2 facts about the deleted minting factory are
  **unchanged and still asserted**: reintroducing public construction of a ``TrustedRuntimeRoot``
  is safe precisely because the type stopped being a capability, so none of those assertions had
  to be weakened, and keeping them is what proves this round is not a quiet restoration of
  Round 1's factory.
- ``bootstrap_projection_execution_capability`` takes two further keyword arguments
  (``runtime_root_admission_ref``, ``trust_anchor_public_key_hex``) and still takes no
  ``store``/``project_id``/``project_binding_id`` (P15-R3-F1).
- ``deployment_registry.py`` exists (P15-R3-F2) and is the *second* module in this package
  calling ``commit_state_transition`` -- admitted here by name, for exactly one call site, for
  the one atomic commit-the-record-and-move-the-pointer transition that makes revocation
  genuinely effective. No module in this package calls a ``store`` object's own ``.commit``
  directly, unchanged.
- the package exports a fourth public callable, ``commit_runtime_deployment_declaration``
  (P15-R3-F2) -- a canonical committer, not a fourth route, exactly as
  ``PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3`` continues to say.

Structural Review Round 4 (P15-R4) changes six further facts this file pins:

- ``TrustedRuntimeRoot`` is **gone**. Rounds 2 and 3 could assert only that no shipped callable
  returned one and no shipped module constructed one; the assertion here is now strictly
  stronger -- the name occurs in no code position anywhere in the shipped tree. The deleted Round
  1 minting factory is still absent by name, unchanged (P15-R4-F1).
- ``bootstrap_projection_execution_capability`` takes exactly three parameters, and **none** of
  ``store``/``project_id``/``project_binding_id``/``runtime_root_admission_ref``/
  ``trust_anchor_public_key_hex``. Round 3 could only rule out the first three; ruling out the
  last two is the whole Round 4 correction (P15-R4-F1).
- ``compose_trusted_runtime_deployment_authority`` is the one shipped composition entry point,
  and a raw trust anchor is named as a parameter in exactly three shipped places -- that entry
  point, the root-admission committer, and the pure verification wrapper -- none of them
  request-facing (P15-R4-F1).
- ``transition_chain.py`` exists (P15-R4-F1/F2) and is now the *second* module calling
  ``commit_state_transition``, taking that role over from ``deployment_registry.py``: both chains
  share one mechanism, so the package still admits exactly two call sites in total rather than
  growing one per chain kind.
- ``admission_registry.py`` exists (P15-R4-F1) and is the *fourth* module importing
  ``manosube_agent_civilization.boot``, alongside ``route.py``, ``bootstrap.py`` and
  ``deployment_registry.py`` -- each committer freshly Boots to verify who may move its own
  chain, and ``bootstrap.py`` still reaches Boot through exactly one literal call site even
  though it now Boots from two points (composition and the request-facing call).
- the package exports two further public callables, ``commit_runtime_root_admission`` and
  ``compose_trusted_runtime_deployment_authority`` -- a committer and a composition step, neither
  a route, so ``PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3`` still holds.

Structural Review Round 5 (P15-R5) changes five further facts this file pins:

- ``RuntimeDeploymentAuthority`` is **gone**, on exactly the precedent Round 4 set for
  ``TrustedRuntimeRoot``: it was an ordinary public frozen dataclass with an ordinary public
  constructor, so "possessing an authority" was reproducible by any caller who could import the
  module, and an ``isinstance`` check over it was never a trust control. The name now occurs in no
  code position anywhere in the shipped tree (P15-R5-F1).
- ``bootstrap_projection_execution_capability`` is no longer a module-level function. It is the
  **closure** ``compose_trusted_runtime_deployment_authority`` returns, defined inside that
  function's own body, so exactly one ``def`` anywhere in the shipped tree carries the name and it
  is nested inside the composition entry point. Its parameter list is now exactly two names, and
  ruling out ``deployment_authority`` -- the last world-bearing parameter Round 4 itself
  introduced -- is the Round 5 correction (P15-R5-F1).
- the package therefore exports one public callable fewer for this mechanism:
  ``compose_trusted_runtime_deployment_authority`` alone, whose declared return type is a
  ``Callable[..., ProjectionExecutionCapability]``. ``PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3`` is
  unchanged -- none of these was ever a route (P15-R5-F1).
- the request-facing operation performs a per-call currency recheck,
  ``_require_bound_admission_still_current``, which composition itself does not call and which
  precedes every gated grant/authorization call (P15-R5-F2).
- ``engine.py`` owns the one instant parser in this package, ``parse_utc_instant``, and is the
  only module here that imports ``datetime`` or calls ``fromisoformat`` at all: ``route.py``'s own
  private ``_instant`` moved there unchanged and ``deployment_registry.py`` reuses it rather than
  ordering two timestamp *strings*, which is what P15-R5-F3 found unsound. No second timestamp
  grammar and no Runtime-specific time owner exists (P15-R5-F3).
"""

from __future__ import annotations

import ast
import inspect
import pathlib
import re
from types import ModuleType

import manosube_agent_civilization
import manosube_agent_civilization.runtime as runtime_module
import manosube_agent_civilization.runtime.adapter as adapter_module
import manosube_agent_civilization.runtime.admission_registry as admission_registry_module
import manosube_agent_civilization.runtime.bootstrap as bootstrap_module
import manosube_agent_civilization.runtime.deployment_declaration as deployment_declaration_module
import manosube_agent_civilization.runtime.deployment_registry as deployment_registry_module
import manosube_agent_civilization.runtime.engine as engine_module
import manosube_agent_civilization.runtime.errors as errors_module
import manosube_agent_civilization.runtime.evidence_handoff as evidence_handoff_module
import manosube_agent_civilization.runtime.identity as identity_module
import manosube_agent_civilization.runtime.network as network_module
import manosube_agent_civilization.runtime.root_admission as root_admission_module
import manosube_agent_civilization.runtime.route as route_module
import manosube_agent_civilization.runtime.transition_chain as transition_chain_module
import manosube_agent_civilization.runtime.types as types_module

_ALL_PACKAGE_MODULES = (
    route_module,
    engine_module,
    identity_module,
    types_module,
    errors_module,
    adapter_module,
    evidence_handoff_module,
    bootstrap_module,
    network_module,
    deployment_declaration_module,
    root_admission_module,
    deployment_registry_module,
    admission_registry_module,
    transition_chain_module,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent

#: The trust-root type Rounds 1-3 carried and Round 4 (P15-R4-F1) removes outright, and the exact
#: name of the public minting factory Round 1 shipped and Round 2 (P15-R2-F1) deletes. Both are
#: pinned as literals so that reintroducing either -- under its own name, anywhere in the shipped
#: tree -- fails this gate immediately.
_TRUSTED_ROOT_TYPE_NAME = "TrustedRuntimeRoot"
_DELETED_MINTING_FACTORY_NAME = "provision_trusted_runtime_root"

#: The composition-owned capability type Round 4 introduced and Round 5 (P15-R5-F1) removes on
#: the identical precedent -- a public dataclass with a public constructor is not a trust control.
#: Pinned as a literal so that reintroducing it, anywhere shipped, fails this gate immediately.
_DEPLOYMENT_AUTHORITY_TYPE_NAME = "RuntimeDeploymentAuthority"

#: The one shipped composition entry point, and the name of the request-facing operation it now
#: *returns* -- a closure defined inside it, never a module-level function (P15-R5-F1).
_COMPOSITION_ENTRY_POINT_NAME = "compose_trusted_runtime_deployment_authority"
_REQUEST_FACING_OPERATION_NAME = "bootstrap_projection_execution_capability"

#: The one instant-parsing owner this package may have (P15-R5-F3).
_INSTANT_PARSER_NAME = "parse_utc_instant"

#: The raw trust-anchor parameter name. It may appear on exactly three shipped functions, all of
#: them composition-side or pure verification, and on no request-facing one (P15-R4-F1).
_TRUST_ANCHOR_PARAMETER_NAME = "trust_anchor_public_key_hex"

#: Existing canonical owners no module in this package may ever import, in whole or in part --
#: Runtime is read-only and mints no Authority/Reflow decision of its own, and never reaches
#: Independent Verification's own machinery.
_FORBIDDEN_OWNER_MODULE_PREFIXES = (
    "manosube_agent_civilization.reflow",
    "manosube_agent_civilization.independent_verification",
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


def _names_identifier(node: ast.AST, identifier: str) -> bool:
    """Whether *node* names *identifier* in a *code* position -- a ``def``, a ``class``, a bare
    name, an attribute, an import alias, or a string constant equal to it (which is how an
    ``__all__`` re-export would smuggle one back). Prose inside a docstring is deliberately not
    matched: each round's own record has to be able to say what was removed and why, and a
    docstring cannot re-export anything."""

    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return node.name == identifier
    if isinstance(node, ast.Name):
        return node.id == identifier
    if isinstance(node, ast.Attribute):
        return node.attr == identifier
    if isinstance(node, ast.alias):
        return identifier in (node.name, node.asname)
    if isinstance(node, ast.Constant):
        return bool(node.value == identifier)
    return False


def _function_defs(module: ModuleType) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every ``def`` in *module*, nested ones included, keyed by name.

    P15-R5-F1 makes this necessary: the request-facing operation is no longer a module-level
    function but a closure defined inside ``compose_trusted_runtime_deployment_authority``. Keying
    by name is sound here precisely because the tests below also prove the name is unique across
    the entire shipped tree.
    """

    tree = ast.parse(inspect.getsource(module))
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            assert node.name not in found, f"two functions named {node.name!r} in {module.__name__}"
            found[node.name] = node
    return found


def _called_names_excluding_nested_defs(node: ast.AST) -> set[str]:
    """Names called *directly* in this function's own body -- deliberately not descending into a
    nested ``def``, whose calls belong to that function rather than to this one.

    ``ast.walk`` would happily walk into the closure and attribute its calls to the enclosing
    composition step, which is exactly the distinction the ordering fact below rests on."""

    names: set[str] = set()

    def _visit(current: ast.AST, *, root: bool) -> None:
        if not root and isinstance(current, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            return
        if isinstance(current, ast.Call):
            func = current.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
        for child in ast.iter_child_nodes(current):
            _visit(child, root=False)

    _visit(node, root=True)
    return names


def _parameter_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    arguments = node.args
    return {
        argument.arg
        for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
    }


def _names_the_deleted_factory(node: ast.AST) -> bool:
    """Whether *node* names ``provision_trusted_runtime_root`` in a *code* position -- one
    binding of :func:`_names_identifier`, kept under its own name because the fact it pins
    (P15-R2-F1) is cited by name in three rounds' records."""

    return _names_identifier(node, _DELETED_MINTING_FACTORY_NAME)


def test_runtime_package_exports_exactly_three_routes_and_one_capability_bootstrap() -> None:
    """``PUBLIC_RUNTIME_ENTRY_POINT_COUNT=3`` is unchanged: the three *routes* this package owns
    are exactly the three it always owned, alongside the one capability bootstrap and -- since
    Round 3 (P15-R3-F2) -- one canonical committer.

    Structural Review Round 1 (P15-R1-F4) had added a fourth public callable that was not a
    route -- ``provision_trusted_runtime_root``. Round 2 (P15-R2-F1) removes it: that factory
    accepted exactly the caller-controlled Store/Project/Binding tuple the correction existed to
    stop an untrusted surface from selecting, so it relocated the trust decision rather than
    removing it, and it is **not** reintroduced by Round 3 (see the three tests below, which
    Round 3 leaves fully intact).

    Round 3 adds ``commit_runtime_deployment_declaration``: the one sanctioned path that commits
    a deployment declaration *and* moves this target's own current-declaration pointer in a
    single atomic State transition. It is a committer, not a route -- it reaches no adapter,
    observes nothing, and mints no Authority -- so ``PUBLIC_RUNTIME_ENTRY_POINT_COUNT`` stays
    ``3``, exactly as Round 1 declared ``TRUSTED_RUNTIME_ROOT_PROVISIONING_ENTRY_POINT_COUNT``
    separately rather than inflating the route count (``10_RUNTIME/RUNTIME_CONTRACT.md`` §12).

    Round 5 (P15-R5-F1) *removes* one: ``bootstrap_projection_execution_capability`` is no longer
    a module-level callable at all, because the composition step now returns it. The capability
    bootstrap this test is named for still exists -- it is exactly what
    ``compose_trusted_runtime_deployment_authority`` hands back -- and
    ``PUBLIC_RUNTIME_ENTRY_POINT_COUNT`` is unchanged at ``3``, since neither the removed name nor
    the surviving one was ever a route.
    """

    public_callables = {
        name
        for name in runtime_module.__all__
        if callable(getattr(runtime_module, name))
        and not isinstance(getattr(runtime_module, name), type)
    }
    assert public_callables == {
        "commit_runtime_deployment_declaration",
        "commit_runtime_root_admission",
        _COMPOSITION_ENTRY_POINT_NAME,
        "observe_runtime_target",
        "route_runtime_observation_to_evidence",
    }
    # P15-R5-F1: one public callable fewer than Round 4 exported for this mechanism. The
    # request-facing operation is no longer a module-level name at all -- it is the closure the
    # composition entry point returns -- so exporting it would be exporting something a caller
    # could not legitimately obtain any other way than by composing.
    assert _REQUEST_FACING_OPERATION_NAME not in runtime_module.__all__
    assert not hasattr(runtime_module, _REQUEST_FACING_OPERATION_NAME)
    assert not hasattr(bootstrap_module, _REQUEST_FACING_OPERATION_NAME)


def test_the_removed_trust_root_type_appears_in_no_shipped_code_position() -> None:
    """P15-R2-F1's own decisive static fact, in the strictly stronger form Round 4 permits.

    Rounds 2 and 3 could assert only that no shipped ``.py`` file *called* ``TrustedRuntimeRoot``
    outside its own class body, and that no shipped callable declared it as a return type -- the
    type still existed, so nothing stronger was available. Round 4 (P15-R4-F1) removes it, because
    naming a world is now the composition step's own job and an inert value beside the new
    authority would give a future reader two handles with one purpose. The honest assertion is
    therefore the absolute one: every ``.py`` file in the entire *installed* package -- what
    actually ends up in the wheel -- is AST-walked, and the name occurs in no code position at
    all.

    Prose inside a docstring is deliberately not matched (see :func:`_names_the_deleted_factory`
    for the identical reasoning): each round's own record has to be able to say what was removed
    and why, and a docstring re-exports nothing.

    Scope, stated exactly: this proves *no shipped minting path exists*, not that a live path
    resists an attacker. There is no live deployment/CLI/agent-runtime composition boundary wired
    to Runtime in this Phase for an attacker to attack. See
    ``tests/integration/runtime/test_runtime_no_shipped_minting_path.py``'s own docstring.
    """

    shipped_files = sorted(_SHIPPED_PACKAGE_ROOT.rglob("*.py"))
    assert shipped_files, "expected at least one shipped module to scan"

    offenders: list[tuple[str, int]] = []
    for path in shipped_files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if _names_identifier(node, _TRUSTED_ROOT_TYPE_NAME):
                offenders.append((str(path.relative_to(_REPO_ROOT)), getattr(node, "lineno", -1)))
    assert offenders == []
    assert not hasattr(bootstrap_module, _TRUSTED_ROOT_TYPE_NAME)
    assert not hasattr(runtime_module, _TRUSTED_ROOT_TYPE_NAME)


def test_the_removed_deployment_authority_type_appears_in_no_shipped_code_position() -> None:
    """P15-R5-F1's own decisive static fact, in exactly the form Round 4 established for
    ``TrustedRuntimeRoot`` -- and for the identical reason.

    Round 4 carried its ownership boundary on a value: an opaque, frozen, slotted
    ``RuntimeDeploymentAuthority``, obtainable "only" from the composition step. Round 5 found
    that "only" was a convention rather than a control -- the type was public, its constructor was
    public, and the free request-facing function's sole defence was an ``isinstance`` check, so any
    caller able to import the module could construct their own authority over an alternate
    Store/Project/Binding and pass. The review rules out a sentinel, a private constructor, a
    leading-underscore field, an opaque ``repr`` and an ``isinstance`` check as trust controls, so
    the type is deleted rather than hidden, exactly as Round 2 deleted the minting factory and
    Round 4 deleted the trust root.

    Prose inside a docstring is deliberately not matched (see :func:`_names_the_deleted_factory`
    for the identical reasoning): each round's own record has to be able to say what was removed
    and why, and a docstring re-exports nothing.
    """

    shipped_files = sorted(_SHIPPED_PACKAGE_ROOT.rglob("*.py"))
    assert shipped_files, "expected at least one shipped module to scan"

    offenders: list[tuple[str, int]] = []
    for path in shipped_files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if _names_identifier(node, _DEPLOYMENT_AUTHORITY_TYPE_NAME):
                offenders.append((str(path.relative_to(_REPO_ROOT)), getattr(node, "lineno", -1)))
    assert offenders == []
    assert not hasattr(bootstrap_module, _DEPLOYMENT_AUTHORITY_TYPE_NAME)
    assert not hasattr(runtime_module, _DEPLOYMENT_AUTHORITY_TYPE_NAME)


def test_the_request_facing_operation_is_a_closure_owned_by_the_composition_entry_point() -> None:
    """The Round 5 replacement for Round 4's "exactly one module defines the authority, exactly
    one call site constructs it" fact (P15-R5-F1).

    What has to be unique now is not a type but the *operation*: exactly one ``def`` anywhere in
    the shipped tree carries the request-facing name, it lives in ``bootstrap.py``, and it is
    **nested inside** ``compose_trusted_runtime_deployment_authority`` rather than being a
    module-level function. A second definition anywhere -- or the same one hoisted back to module
    level -- would mean a working request-facing operation could be obtained without passing the
    composition step's own admission gate, which is precisely the class of defect Rounds 1-5 have
    each closed one layer at a time.
    """

    shipped_files = sorted(_SHIPPED_PACKAGE_ROOT.rglob("*.py"))
    definitions: list[tuple[str, int]] = []
    for path in shipped_files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
                and node.name == _REQUEST_FACING_OPERATION_NAME
            ):
                definitions.append((str(path.relative_to(_REPO_ROOT)), node.lineno))
    assert len(definitions) == 1, definitions
    assert definitions[0][0] == "src/manosube_agent_civilization/runtime/bootstrap.py"

    # ...and that one definition is lexically inside the composition entry point, not beside it.
    tree = ast.parse(inspect.getsource(bootstrap_module))
    module_level = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    assert _REQUEST_FACING_OPERATION_NAME not in module_level
    assert _COMPOSITION_ENTRY_POINT_NAME in module_level
    composing = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == _COMPOSITION_ENTRY_POINT_NAME
    )
    nested = [
        node
        for node in ast.walk(composing)
        if isinstance(node, ast.FunctionDef) and node.name == _REQUEST_FACING_OPERATION_NAME
    ]
    assert len(nested) == 1
    # ...and composition genuinely hands it back, so the only way to hold one is to compose.
    assert any(
        isinstance(node, ast.Return)
        and isinstance(node.value, ast.Name)
        and node.value.id == _REQUEST_FACING_OPERATION_NAME
        for node in ast.walk(composing)
    )


def test_the_raw_trust_anchor_is_named_only_by_composition_side_functions() -> None:
    """P15-R4-F1, item 2, proved structurally: the raw anchor is admitted at the trusted
    composition step and is absent from every request-facing execution signature.

    Every ``def`` in the shipped ``runtime`` package is AST-walked for a parameter literally named
    ``trust_anchor_public_key_hex``. Exactly three may carry it, and each is either the
    composition boundary itself or an act *of* that boundary:

    ```text
    compose_trusted_runtime_deployment_authority   the one trusted composition entry point
    commit_runtime_root_admission                  issuing/rotating/revoking an admission IS the
                                                   deployment boundary acting
    verify_runtime_root_admission_signature        the pure verification wrapper both call
    _require_currently_admitted                    composition's own private helper
    ```

    Anything else -- and in particular anything reachable from a request path -- fails this gate.
    """

    permitted = {
        _COMPOSITION_ENTRY_POINT_NAME,
        "commit_runtime_root_admission",
        "verify_runtime_root_admission_signature",
        "_require_currently_admitted",
    }
    carriers: set[str] = set()
    for path in sorted((_SHIPPED_PACKAGE_ROOT / "runtime").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            arguments = node.args
            names = {
                argument.arg
                for argument in (
                    *arguments.posonlyargs,
                    *arguments.args,
                    *arguments.kwonlyargs,
                )
            }
            if _TRUST_ANCHOR_PARAMETER_NAME in names:
                carriers.add(node.name)
    assert carriers == permitted, carriers


def test_no_shipped_file_defines_imports_or_exports_the_deleted_minting_factory() -> None:
    """The deleted factory is gone by *name* as well as by shape (P15-R2-F1).

    Every shipped ``.py`` file is AST-walked for that name appearing in any *code* position --
    see :func:`_names_the_deleted_factory` for exactly which positions count and why prose does
    not.
    """

    shipped_files = sorted(_SHIPPED_PACKAGE_ROOT.rglob("*.py"))
    assert shipped_files, "expected at least one shipped module to scan"

    offenders: list[tuple[str, int]] = []
    for path in shipped_files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if _names_the_deleted_factory(node):
                offenders.append((str(path.relative_to(_REPO_ROOT)), getattr(node, "lineno", -1)))
    assert offenders == []
    assert not hasattr(bootstrap_module, _DELETED_MINTING_FACTORY_NAME)
    assert not hasattr(runtime_module, _DELETED_MINTING_FACTORY_NAME)


def test_exactly_one_shipped_public_callable_returns_a_bound_request_facing_bootstrap() -> None:
    """The shape half of the same fact, proved by introspection rather than by text.

    Rounds 2 and 3 asserted that *no* public callable returned the trust root, because a
    mechanism with no legitimate producer was the position of the day. Round 3 itself rejected
    that position -- a bootstrap with no production-legitimate way to obtain its first argument
    does not satisfy this Phase's own V5 requirement -- so Round 4's honest form was that exactly
    one callable produced the composition-owned authority. Round 5 removes that type, so the same
    control is stated over what composition returns instead: a callable producing a
    ``ProjectionExecutionCapability``. A same-shaped producer reintroduced under some *other* name
    would still be caught here, and so would a reintroduced authority type.
    """

    producers = []
    for name in runtime_module.__all__:
        member = getattr(runtime_module, name)
        if not callable(member) or isinstance(member, type):
            continue
        annotation = inspect.signature(member).return_annotation
        rendered = str(
            annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
        )
        assert _DEPLOYMENT_AUTHORITY_TYPE_NAME not in rendered, name
        if "Callable" in rendered and "ProjectionExecutionCapability" in rendered:
            producers.append(name)
    assert producers == [_COMPOSITION_ENTRY_POINT_NAME]


def test_the_request_facing_bootstrap_accepts_no_trust_deciding_parameter() -> None:
    """P15-R5-F1's own decisive structural fact, proved over the operation's own ``def`` rather
    than by behaviour: there is no call shape at all -- not one that is refused at runtime, one
    that does not exist -- through which a caller could hand the request-facing bootstrap an
    alternate Store, Project, Binding, root admission, trust anchor, **or authority object**.

    Round 1 (P15-R1-F4) removed the first three. Round 3 (P15-R3-F1) *added* the last two as
    required keyword arguments, which is exactly what Round 4 found still open. Round 4 removed
    those but introduced a sixth, ``deployment_authority``, carrying a public dataclass any caller
    could construct -- which is exactly what Round 5 found still open. All six are now absent, and
    the request-facing signature carries exactly two parameters, both operation-scoped references.

    Read from the AST rather than through ``inspect.signature`` because the operation is now a
    closure: obtaining a live one requires composing against a real world, which the integration
    suite does (``tests/integration/runtime/
    test_runtime_deployment_authority_composition.py`` introspects the genuinely returned object).
    This is the static half, over what the shipped source actually declares.
    """

    request_facing = _function_defs(bootstrap_module)[_REQUEST_FACING_OPERATION_NAME]
    assert _parameter_names(request_facing) == {
        "github_projection_grant_refs",
        "github_projection_grant_declaration_refs",
    }
    # Keyword-only, so not even a positional world-bearing argument can be attempted.
    assert request_facing.args.args == []
    assert request_facing.args.posonlyargs == []
    for forbidden in (
        "deployment_authority",
        "store",
        "project_id",
        "project_binding_id",
        "runtime_root_admission_ref",
        _TRUST_ANCHOR_PARAMETER_NAME,
    ):
        assert forbidden not in _parameter_names(request_facing)


def test_the_composition_entry_point_owns_every_trust_deciding_parameter() -> None:
    """The other half of the ownership boundary (P15-R4-F1): what the request-facing call may not
    name, the composition step must -- otherwise the values would have to come from somewhere
    else, and "somewhere else" is exactly what this correction forbids."""

    signature = inspect.signature(getattr(bootstrap_module, _COMPOSITION_ENTRY_POINT_NAME))
    assert set(signature.parameters) == {
        "store",
        "project_id",
        "project_binding_id",
        "runtime_root_admission_ref",
        _TRUST_ANCHOR_PARAMETER_NAME,
    }


def test_no_shipped_runtime_module_reads_configuration_at_all() -> None:
    """P15-R4-F1, item 7: no request-path code may read an environment variable, a file, or a
    registry to choose a different trust root. Deployment configuration is resolved *before* the
    request boundary and injected only as the already-bound authority.

    Proved for the whole shipped package rather than only the request path, which is stronger and
    simpler to keep true: no module here imports ``os`` or ``pathlib``, names ``environ`` or
    ``getenv``, or calls ``open``. Every value any of them uses is passed in by its caller.
    """

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
            # A bare ``open(...)`` reads a file; ``adapter.py``'s own ``self._opener.open(...)``
            # is the HTTP opener this package's network boundary already owns and bounds, and is
            # deliberately not what this control is about.
            if isinstance(func, ast.Name):
                assert func.id != "open", f"{module.__name__} reads a file at {node.lineno}"
            elif isinstance(func, ast.Attribute):
                assert func.attr not in ("read_text", "read_bytes"), (
                    f"{module.__name__} reads a file at {node.lineno}"
                )


def test_no_module_imports_a_forbidden_existing_owner() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        for forbidden_prefix in _FORBIDDEN_OWNER_MODULE_PREFIXES:
            assert not any(
                name == forbidden_prefix or name.startswith(forbidden_prefix + ".")
                for name in imported
            ), f"{module.__name__} imports forbidden owner prefix {forbidden_prefix!r}: {imported}"


def test_evidence_is_imported_only_by_evidence_handoff_and_bootstrap() -> None:
    """``evidence_handoff.py`` is the one caller of ``derive_evidence`` itself; ``bootstrap.py``
    additionally imports the read-only ``evidence.identity.evidence_semantic_fingerprint`` to
    reverify an ``EVIDENCE_ARTIFACT``-kind subject's own real fingerprint (the identical
    narrow reuse Projection's own ``route.py`` already makes of the same function) -- no other
    module in this package imports ``evidence`` in any form."""

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
        elif module is bootstrap_module:
            assert evidence_imports == {"manosube_agent_civilization.evidence.identity"}
        else:
            assert not evidence_imports, f"{module.__name__} imports evidence: {evidence_imports}"


def test_evidence_handoff_calls_derive_evidence_exactly_once() -> None:
    assert _call_site_count(evidence_handoff_module, "derive_evidence") == 1


def test_boot_project_is_imported_only_by_the_route_the_bootstrap_and_the_two_committers() -> None:
    """Four modules, and each for a reason it can state.

    ``route.py`` Boots to decide who may observe; ``bootstrap.py`` Boots at composition (to prove
    the world being bound is genuinely restorable) and again, freshly, on every request-facing
    call. Round 4 adds the two chain committers (P15-R4-F1/F2): each must freshly Boot to verify
    who may *move its own chain* -- the declaration committer against the Boot-restored Human
    Authority key, the admission committer to prove the Project Binding an admission names is
    genuinely this project's own.
    """

    for module in (
        route_module,
        bootstrap_module,
        deployment_registry_module,
        admission_registry_module,
    ):
        assert any(
            name == "manosube_agent_civilization.boot"
            or name.startswith("manosube_agent_civilization.boot.")
            for name in _imported_module_names(module)
        ), f"{module.__name__} is expected to import boot"
    for module in _ALL_PACKAGE_MODULES:
        if module in (
            route_module,
            bootstrap_module,
            deployment_registry_module,
            admission_registry_module,
        ):
            continue
        imported = _imported_module_names(module)
        assert not any(
            name == "manosube_agent_civilization.boot"
            or name.startswith("manosube_agent_civilization.boot.")
            for name in imported
        ), f"{module.__name__} imports manosube_agent_civilization.boot: {imported}"


def test_route_has_exactly_one_boot_project_call_site() -> None:
    """One literal call site, reached from three points per observation (P15-R1-F5).

    Round 1 required the authority-defining context to be re-proved immediately before the
    adapter is reached, and again on every commit attempt -- so a single observation now Boots
    up to three times. All three go through ``route.py``'s own single private helper, so this
    module still contains exactly one literal ``boot_project`` call site and no second,
    drifting way of restoring a project can ever appear beside it.
    """

    assert _call_site_count(route_module, "boot_project") == 1


def test_bootstrap_calls_boot_project_exactly_once() -> None:
    """One literal call site, reached from two points since Round 4 (P15-R4-F1) -- once at
    composition, once per request-facing call -- through this module's own single private helper,
    exactly the discipline ``route.py`` already keeps for its own three."""

    assert _call_site_count(bootstrap_module, "boot_project") == 1


def test_authority_is_never_imported_by_route() -> None:
    """Runtime Observation is bounded by its own closed Observation Boundary, never by an
    Authority Decision -- this package's own disclosed judgment call
    (``10_RUNTIME/RUNTIME_CONTRACT.md`` §4)."""

    imported = _imported_module_names(route_module)
    assert not any(
        name == "manosube_agent_civilization.authority"
        or name.startswith("manosube_agent_civilization.authority.")
        for name in imported
    ), f"route.py imports manosube_agent_civilization.authority: {imported}"


def test_authority_is_imported_only_by_bootstrap() -> None:
    for module in _ALL_PACKAGE_MODULES:
        if module is bootstrap_module:
            continue
        imported = _imported_module_names(module)
        assert not any(
            name == "manosube_agent_civilization.authority"
            or name.startswith("manosube_agent_civilization.authority.")
            for name in imported
        ), f"{module.__name__} imports manosube_agent_civilization.authority: {imported}"


def test_bootstrap_calls_evaluate_projection_authorization_exactly_once() -> None:
    assert _call_site_count(bootstrap_module, "evaluate_projection_authorization") == 1


def test_projection_package_is_imported_only_by_bootstrap() -> None:
    """The shipped Phase 14 execution interface this delivery provisions (V5) -- imported
    exclusively by ``bootstrap.py``, never by any other module in this package."""

    for module in _ALL_PACKAGE_MODULES:
        if module is bootstrap_module:
            continue
        imported = _imported_module_names(module)
        assert not any(
            name == "manosube_agent_civilization.projection"
            or name.startswith("manosube_agent_civilization.projection.")
            for name in imported
        ), f"{module.__name__} imports manosube_agent_civilization.projection: {imported}"


def test_binding_is_imported_only_for_declaration_identity_and_signature_verification() -> None:
    """Two modules, one import each, both read-only reverification of a declaration a Human
    Authority already issued.

    ``bootstrap.py`` imports ``binding.identity`` (grant-declaration identity reverification).
    Round 2 (P15-R2-F2) adds ``deployment_declaration.py``, which imports exactly
    ``binding.signature`` -- the shared, public, fail-closed-as-a-value Ed25519 primitive
    (``verify_ed25519_signature``) plus the supported-algorithm constant, *composed* here rather
    than reimplemented. Binding is deliberately not made to import anything from ``runtime/``:
    Runtime is an adapter layer that depends on the Kernel's Binding element, never the reverse.
    """

    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        binding_imports = {
            name
            for name in imported
            if name == "manosube_agent_civilization.binding"
            or name.startswith("manosube_agent_civilization.binding.")
        }
        if module is bootstrap_module:
            assert binding_imports == {"manosube_agent_civilization.binding.identity"}
        elif module in (deployment_declaration_module, root_admission_module):
            assert binding_imports == {"manosube_agent_civilization.binding.signature"}
        else:
            assert not binding_imports, f"{module.__name__} imports binding: {binding_imports}"


def test_the_signature_verifiers_reimplement_no_cryptography() -> None:
    """P15-R2-F2 and P15-R3-F1: both verification wrappers compose the shared primitive and own
    no cryptography of their own -- neither imports ``cryptography`` (or an Ed25519 type)
    directly, neither names a private key, and neither signs anything. Verification only; no
    private key of any kind -- a Human Authority's or a deployment trust anchor's -- ever touches
    this system."""

    for module in (deployment_declaration_module, root_admission_module):
        imported = _imported_module_names(module)
        assert not any("cryptography" in name or "ed25519" in name.lower() for name in imported)
        source = inspect.getsource(module)
        for forbidden in ("Ed25519PrivateKey", "from_private_bytes", "def sign", ".sign("):
            assert forbidden not in source, (
                f"{module.__name__} names {forbidden!r} -- it may only ever verify"
            )
        assert _call_site_count(module, "verify_ed25519_signature") == 1


def test_no_shipped_module_hardcodes_a_trust_anchor_public_key() -> None:
    """P15-R3-F1: ``trust_anchor_public_key_hex`` is supplied by the deployment/composition
    boundary, never baked into shipped source. Proved by an AST walk over every ``.py`` file in
    the installed *runtime* package for any string constant that could *be* a raw Ed25519 public
    key -- 64 hex characters -- so a "temporary" real key pasted anywhere in this package fails
    this gate immediately, whatever it is named.

    Scoped to this package deliberately: elsewhere in the installed tree, 64-hex string constants
    are legitimate and numerous (canonical record digests in Reflow's own invariant registry, for
    one), so a repository-wide version of this scan would be noise rather than a control. This
    package is where an anchor key would plausibly be pasted, and this package contains none.
    """

    offenders: list[tuple[str, int]] = []
    for path in sorted((_SHIPPED_PACKAGE_ROOT / "runtime").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if re.fullmatch(r"[0-9a-fA-F]{64}", node.value):
                offenders.append((str(path.relative_to(_REPO_ROOT)), node.lineno))
    assert offenders == []


def test_the_admission_gate_precedes_every_grant_and_authority_call_by_construction() -> None:
    """P15-R3-F1's own structural ordering fact, in the stronger form Rounds 4 and 5 make
    available (the zero-call proofs live in ``tests/integration/runtime/``).

    Round 3 could only assert an *ordering within one function body*: the literal
    ``_require_admitted_root`` call had to appear before the first ``_resolve_grant``,
    ``_resolve_declaration``, or ``evaluate_projection_authorization`` call site, so that no
    future edit could quietly move grant resolution in front of the admission gate.

    Round 4 made the ordering structural instead of positional: the admission check lives in a
    *different function* that must complete before a request-facing operation exists at all.
    Round 5 keeps that and adds the per-call half (P15-R5-F2): the request-facing operation itself
    now names ``_require_bound_admission_still_current``, and names it before the first gated call
    in its own body -- so a rotated or revoked composition authority is refused with zero grant
    resolutions and zero authorization evaluations.

    Calls are collected without descending into nested ``def``s: the request-facing operation is
    now lexically inside the composition entry point, and attributing its calls to its enclosing
    function would silently destroy the very separation this test asserts.
    """

    functions = _function_defs(bootstrap_module)
    gated = ("_resolve_grant", "_resolve_declaration", "evaluate_projection_authorization")

    composing = _called_names_excluding_nested_defs(functions[_COMPOSITION_ENTRY_POINT_NAME])
    assert "_require_currently_admitted" in composing
    assert not composing & set(gated), composing
    assert "_require_bound_admission_still_current" not in composing

    request_facing_node = functions[_REQUEST_FACING_OPERATION_NAME]
    request_facing = _called_names_excluding_nested_defs(request_facing_node)
    assert set(gated) <= request_facing, request_facing
    assert "_require_currently_admitted" not in request_facing
    assert "_require_bound_admission_still_current" in request_facing
    assert _TRUST_ANCHOR_PARAMETER_NAME not in _parameter_names(request_facing_node)

    # ...and the currency recheck genuinely precedes every gated call in that body, positionally,
    # so no future edit can move grant resolution in front of it (Round 3's own technique, kept).
    def _first_line(name: str) -> int:
        return min(
            node.lineno
            for node in ast.walk(request_facing_node)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == name)
                or (isinstance(node.func, ast.Attribute) and node.func.attr == name)
            )
        )

    recheck_line = _first_line("_require_bound_admission_still_current")
    for gated_name in gated:
        assert recheck_line < _first_line(gated_name), gated_name


def test_the_admission_barrier_runs_again_immediately_before_the_capability_is_constructed() -> (
    None
):
    """P15-R6-F1, items 3, 4 and 6, proved structurally over the shipped source.

    Round 5's single barrier ran at the start of the request-facing call, and the capability was
    then constructed from that same original Boot snapshot after every grant, declaration and
    subject had been resolved and every Authority decision evaluated. A rotation or revocation
    committing in that window was still followed by a newly issued capability. Round 6 adds a
    second barrier, and this is its positional half -- the deterministic race controls live in
    ``tests/integration/runtime/test_runtime_deployment_authority_composition.py``.

    Three facts, over the request-facing operation's own body:

    1. ``_require_bound_admission_still_current`` is called **twice**, and ``_boot`` twice with it,
       so the second barrier reads a freshly Booted State rather than rechecking the snapshot the
       first barrier already read;
    2. the **last** such call comes after every gated call (the pre-issuance barrier is genuinely
       after all resolution and Authority evaluation) and before the one
       ``ProjectionExecutionContext`` construction, so no future edit can quietly move issuance in
       front of it;
    3. **item 6, the closed request signature**: none of this bought a new request-facing
       parameter. The operation's own ``def`` still declares exactly the two operation-scoped
       reference parameters Round 5 closed it at, keyword-only, with nothing positional --
       restated here rather than left implicit, because "no new public request parameter of any
       kind" is an adopted condition of this round in its own right and must fail this gate if a
       later edit relaxes it.
    """

    functions = _function_defs(bootstrap_module)
    request_facing_node = functions[_REQUEST_FACING_OPERATION_NAME]

    def _call_lines(name: str) -> list[int]:
        return sorted(
            node.lineno
            for node in ast.walk(request_facing_node)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == name)
                or (isinstance(node.func, ast.Attribute) and node.func.attr == name)
            )
        )

    barriers = _call_lines("_require_bound_admission_still_current")
    boots = _call_lines("_boot")
    assert len(barriers) == 2, barriers
    assert len(boots) == 2, boots
    # Each barrier is preceded by its own Boot: the second one never rechecks the first snapshot.
    assert boots[0] < barriers[0] < boots[1] < barriers[1]

    for gated_name in (
        "_resolve_grant",
        "_resolve_declaration",
        "evaluate_projection_authorization",
    ):
        assert max(_call_lines(gated_name)) < barriers[1], gated_name

    context_lines = _call_lines("ProjectionExecutionContext")
    assert len(context_lines) == 1, context_lines
    assert barriers[1] < context_lines[0]

    # Item 6: the Round 5 request signature is unchanged, and carries no new parameter at all.
    assert _parameter_names(request_facing_node) == {
        "github_projection_grant_refs",
        "github_projection_grant_declaration_refs",
    }
    assert request_facing_node.args.args == []
    assert request_facing_node.args.posonlyargs == []
    assert request_facing_node.args.vararg is None
    assert request_facing_node.args.kwarg is None


def test_this_package_has_exactly_one_instant_parsing_owner() -> None:
    """P15-R5-F3: "No second timestamp grammar or Runtime-specific time owner may be created."

    Round 1 (P15-R1-F2) established that lexicographic comparison is unsound over this
    repository's own canonical timestamp grammar, and put a real parser in ``route.py``. Round 5
    found ``deployment_registry.py`` still ordering a declaration's own ``valid_from``/
    ``valid_until`` as **strings**, which accepted an inverted window and refused a genuine
    fractional-second one. The correction moved the existing parser to ``engine.py`` and made both
    sites read through it, rather than adding a second one.

    So the honest static fact is a uniqueness one: exactly one module in this package imports
    ``datetime`` at all, exactly one function anywhere in it calls ``fromisoformat``, and that
    function is ``engine.parse_utc_instant``.
    """

    datetime_importers = {
        module.__name__
        for module in _ALL_PACKAGE_MODULES
        if any(
            name == "datetime" or name.startswith("datetime.")
            for name in _imported_module_names(module)
        )
    }
    assert datetime_importers == {engine_module.__name__}, datetime_importers

    parsers: list[tuple[str, str]] = []
    for path in sorted((_SHIPPED_PACKAGE_ROOT / "runtime").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if "fromisoformat" in _called_names_excluding_nested_defs(node):
                parsers.append((str(path.relative_to(_REPO_ROOT)), node.name))
    assert parsers == [
        ("src/manosube_agent_civilization/runtime/engine.py", _INSTANT_PARSER_NAME)
    ], parsers

    # ...and both windowing sites genuinely reach it, rather than one of them keeping a private
    # copy under another name.
    assert _call_site_count(route_module, _INSTANT_PARSER_NAME) >= 1
    assert _call_site_count(deployment_registry_module, _INSTANT_PARSER_NAME) == 2
    assert hasattr(engine_module, _INSTANT_PARSER_NAME)


def test_the_declaration_committer_orders_its_validity_window_as_instants_not_strings() -> None:
    """P15-R5-F3, stated over the exact site the review named.

    ``_require_declaration_shape_and_signature`` must compare *parsed instants*, never the two
    raw ``valid_from``/``valid_until`` strings. Proved structurally: every comparison in that
    function whose operands are plain names compares names that came out of
    ``parse_utc_instant``, and the raw string names are never themselves compared with an ordering
    operator.
    """

    functions = _function_defs(deployment_registry_module)
    node = functions["_require_declaration_shape_and_signature"]
    raw_names = {"valid_from", "valid_until"}
    for compare in ast.walk(node):
        if not isinstance(compare, ast.Compare):
            continue
        if not all(
            isinstance(operator, ast.Lt | ast.LtE | ast.Gt | ast.GtE) for operator in compare.ops
        ):
            continue
        operands = [compare.left, *compare.comparators]
        named = {operand.id for operand in operands if isinstance(operand, ast.Name)}
        assert not (named & raw_names), (
            "the declaration committer orders raw timestamp strings -- lexicographic order and "
            f"chronological order genuinely disagree over this grammar: {sorted(named)}"
        )
    assert "parse_utc_instant" in _called_names_excluding_nested_defs(node)


def test_only_bootstrap_imports_difference_and_change_identity() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        difference_or_change = {
            name
            for name in imported
            if name.startswith(
                ("manosube_agent_civilization.difference.", "manosube_agent_civilization.change.")
            )
        }
        if module is bootstrap_module:
            assert difference_or_change == {
                "manosube_agent_civilization.difference.identity",
                "manosube_agent_civilization.difference.validation",
                "manosube_agent_civilization.change.identity",
            }
        elif module is engine_module:
            # P15-R1-F2: engine.py now additionally imports ``difference.errors``, solely to
            # translate the canonical schema validator's own DifferenceValidationError into
            # this package's own RuntimeRequirementError -- a read of an error type, never a
            # second validator or a second Difference owner.
            assert difference_or_change == {
                "manosube_agent_civilization.difference.validation",
                "manosube_agent_civilization.difference.errors",
            }
        else:
            assert not difference_or_change, f"{module.__name__}: {difference_or_change}"


def test_only_route_and_the_shared_transition_chain_call_commit_state_transition() -> None:
    """Runtime Observation commits exactly once per call (no intent/materialize-attempt
    claim pair -- see ``engine.py``'s own module docstring) -- so ``route.py`` calls
    ``commit_state_transition`` from exactly one literal call site.

    Round 3 (P15-R3-F2) admitted one more module by name for the declaration chain's own
    commit-the-record-and-move-the-pointer transition. Round 4 (P15-R4-F1/F2) adds a *second*
    chain kind -- root admissions -- and yet the admitted count is still two, not three: both
    chains parameterize one shared mechanism, so ``transition_chain.py`` now owns that single call
    site and ``deployment_registry.py`` has none of its own. That is exactly the shape the review
    asked for; a second, independently written committer would have shown up here as a third call
    site and as two chances to drift apart.

    Two domain reasons for a commit, one shared plan builder, still one sanctioned committer --
    the identical discipline ``store/commit.py``'s own module docstring states for Reflow and
    Binding. The repository-wide K-003/R-001 rule is about ``store.commit`` itself, and the test
    below still proves no module here calls that directly.
    """

    for module in _ALL_PACKAGE_MODULES:
        count = _call_site_count(module, "commit_state_transition")
        if module in (route_module, transition_chain_module):
            assert count == 1, f"{module.__name__} must call commit_state_transition exactly once"
        else:
            assert count == 0, f"{module.__name__} must never call commit_state_transition"


def test_both_chain_committers_share_one_mechanism_and_restate_no_rule_of_their_own() -> None:
    """P15-R4: the shared-mechanism requirement, proved rather than asserted in prose.

    Both committers must reach the chain through ``commit_chain_transition``, and neither may
    contain a genesis/successor/terminality rule of its own -- the words that would give it one
    (``generation``-arithmetic, a predecessor comparison, a REVOKED-terminality branch) belong to
    ``transition_chain.py`` alone.
    """

    for module in (deployment_registry_module, admission_registry_module):
        assert _call_site_count(module, "commit_chain_transition") == 1, module.__name__
        tree = ast.parse(inspect.getsource(module))
        docstrings = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        }
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
            ):
                assert node.value not in ("ACTIVE", "REVOKED"), (
                    f"{module.__name__} names a chain status literal in a code position -- the "
                    "closed status vocabulary and every rule over it belong to "
                    "transition_chain.py, so that one mechanism cannot drift into two"
                )
        assert _call_site_count(module, "require_legal_transition") == 0, (
            f"{module.__name__} must not evaluate transition legality itself"
        )


def test_the_two_chain_key_spaces_are_structurally_disjoint() -> None:
    """P15-R4-F1: both chains record their pointers in the identical
    ``semantic_state.runtime.claims`` map, so their key spaces must be provably disjoint rather
    than observed not to collide.

    A deployment target key is ``RUNTIME-DEPLOYMENT-TARGET-`` plus 64 uppercase hex characters --
    an alphabet that contains no ``":"`` at any position -- while every admission chain key
    carries one at a fixed offset. This is the structural statement; the exhaustive
    alphabet-level proof is in ``tests/unit/runtime/test_runtime_transition_chain.py``.
    """

    assert ":" in identity_module.ROOT_ADMISSION_TARGET_KEY_PREFIX
    sample = identity_module.runtime_deployment_target_key(
        {
            "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-0001"},
            "provider": "local",
            "deployment_id": "widget-service",
            "instance_identity": "widget-service-1",
        }
    )
    assert ":" not in sample
    assert not sample.startswith(identity_module.ROOT_ADMISSION_TARGET_KEY_PREFIX)


def test_no_module_calls_store_commit_directly() -> None:
    """The sanctioned single committer is ``store.commit.commit_state_transition`` -- no
    module in this package may call a ``store`` object's own ``.commit(...)`` method
    directly (K-003/R-001, ``topology.py``'s own static scan enforces the identical rule
    package-wide; this is the package-local proof that this package's own source agrees)."""

    for module in _ALL_PACKAGE_MODULES:
        tree = ast.parse(inspect.getsource(module))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "commit":
                continue
            assert isinstance(node.func.value, ast.Name) and node.func.value.id != "store", (
                f"{module.__name__} appears to call store.commit(...) directly, bypassing "
                "commit_state_transition"
            )


def test_only_adapter_module_imports_a_network_or_transport_surface() -> None:
    """``adapter.py`` is the only module that may import a surface which actually *opens*
    anything; ``network.py`` (P15-R1-F1) may import exactly ``urllib.parse`` and nothing else.

    Round 1 required the Boundary's own declared ``network_scope`` to be enforced *before* any
    connection exists, structurally, for every adapter implementation -- which means the
    route's own Boundary validation must be able to parse and canonicalize an endpoint URL.
    ``urllib.parse`` is a pure string-parsing surface (never ``urllib.request``), so one more
    file in this package needs a network-surface-*adjacent* but genuinely I/O-free import.
    That file is ``network.py``, it is admitted here by name for exactly that one import, and
    the next test additionally proves it opens nothing at all -- ``route.py`` itself still
    imports no ``urllib`` of any kind.
    """

    forbidden_substrings = ("urllib", "requests", "http.client", "socket", "subprocess")
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        hits = {
            name
            for name in imported
            if any(substring in name for substring in forbidden_substrings)
        }
        if module is adapter_module:
            assert hits, "adapter.py is expected to import a network/transport surface"
        elif module is network_module:
            assert hits == {"urllib.parse"}, (
                "network.py may import exactly urllib.parse -- a parse-only surface -- and "
                f"nothing else: {hits}"
            )
        else:
            assert not hits, f"{module.__name__} imports a network/transport surface: {hits}"


def test_the_network_scope_module_performs_no_io_of_any_kind() -> None:
    """P15-R1-F1: ``network.py`` decides, from strings alone, whether a declared endpoint
    falls inside a declared network scope. It must never resolve a name, open a socket, read a
    file, or reach anything -- proved by an AST walk for any call to a name that could."""

    tree = ast.parse(inspect.getsource(network_module))
    forbidden_callables = {
        "urlopen",
        "open",
        "build_opener",
        "connect",
        "create_connection",
        "getaddrinfo",
        "gethostbyname",
        "read_text",
        "read_bytes",
        "run",
        "Popen",
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.id
            if isinstance(func, ast.Name)
            else (func.attr if isinstance(func, ast.Attribute) else None)
        )
        assert name not in forbidden_callables, (
            f"network.py calls {name!r} -- it must remain entirely I/O-free"
        )


def test_no_module_imports_a_scheduler_or_multi_agent_surface() -> None:
    forbidden_substrings = (
        "threading",
        "asyncio",
        "sched",
        "multiprocessing",
        "openai",
        "anthropic",
    )
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        hits = {
            name
            for name in imported
            if any(substring in name for substring in forbidden_substrings)
        }
        assert not hits, f"{module.__name__} imports a forbidden surface: {hits}"


def test_shipped_kernel_package_imports_no_tests_module_anywhere() -> None:
    for module in _ALL_PACKAGE_MODULES:
        imported = _imported_module_names(module)
        assert not any(name == "tests" or name.startswith("tests.") for name in imported), (
            f"{module.__name__} imports a tests module: {imported}"
        )
