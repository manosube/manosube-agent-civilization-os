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
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_SHIPPED_PACKAGE_ROOT = pathlib.Path(manosube_agent_civilization.__file__).resolve().parent

#: The trust-root type, and the exact name of the public minting factory Round 1 shipped and
#: Round 2 (P15-R2-F1) deletes. Both are pinned as literals so that reintroducing a minting call
#: site -- or the deleted factory itself, under its own name -- fails this gate immediately.
_TRUSTED_ROOT_TYPE_NAME = "TrustedRuntimeRoot"
_DELETED_MINTING_FACTORY_NAME = "provision_trusted_runtime_root"

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


def _names_the_deleted_factory(node: ast.AST) -> bool:
    """Whether *node* names ``provision_trusted_runtime_root`` in a *code* position -- a
    ``def``, a bare name, an attribute, an import alias, or a string constant equal to it (which
    is how an ``__all__`` re-export would smuggle it back). Prose inside a docstring is
    deliberately not matched: this round's own record has to be able to say what was removed and
    why, and a docstring cannot re-export anything."""

    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return node.name == _DELETED_MINTING_FACTORY_NAME
    if isinstance(node, ast.Name):
        return node.id == _DELETED_MINTING_FACTORY_NAME
    if isinstance(node, ast.Attribute):
        return node.attr == _DELETED_MINTING_FACTORY_NAME
    if isinstance(node, ast.alias):
        return _DELETED_MINTING_FACTORY_NAME in (node.name, node.asname)
    if isinstance(node, ast.Constant):
        return bool(node.value == _DELETED_MINTING_FACTORY_NAME)
    return False


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
    """

    public_callables = {
        name
        for name in runtime_module.__all__
        if callable(getattr(runtime_module, name))
        and not isinstance(getattr(runtime_module, name), type)
    }
    assert public_callables == {
        "bootstrap_projection_execution_capability",
        "commit_runtime_deployment_declaration",
        "observe_runtime_target",
        "route_runtime_observation_to_evidence",
    }


def test_no_shipped_file_constructs_a_trusted_runtime_root() -> None:
    """P15-R2-F1's own decisive static fact.

    Every ``.py`` file in the entire *installed* ``manosube_agent_civilization`` package -- what
    actually ends up in the wheel -- is AST-walked for any ``ast.Call`` whose callee resolves to
    the name ``TrustedRuntimeRoot``. The single admitted site is inside the dataclass's own class
    body in ``bootstrap.py`` (its generated ``__init__``/``__post_init__`` -- and in fact there is
    no literal call there at all, since a frozen dataclass constructs itself). Anywhere else, a
    call site would mean shipped code mints a trust root over some Store, which is exactly the
    defect this round closes.

    Scope, stated exactly: this proves *no shipped minting path exists*, not that a live path
    resists an attacker. There is no live deployment/CLI/agent-runtime composition boundary wired
    to Runtime in this Phase for an attacker to attack. See
    ``tests/integration/runtime/test_runtime_no_shipped_minting_path.py``'s own docstring.
    """

    shipped_files = sorted(_SHIPPED_PACKAGE_ROOT.rglob("*.py"))
    assert shipped_files, "expected at least one shipped module to scan"

    offenders: list[tuple[str, int]] = []
    for path in shipped_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # Every call site that lexically belongs to the TrustedRuntimeRoot class body itself is
        # exempt; every other call site in the shipped package is an offender.
        exempt: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == _TRUSTED_ROOT_TYPE_NAME:
                exempt.update(id(inner) for inner in ast.walk(node) if isinstance(inner, ast.Call))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or id(node) in exempt:
                continue
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else (func.attr if isinstance(func, ast.Attribute) else None)
            )
            if name == _TRUSTED_ROOT_TYPE_NAME:
                offenders.append((str(path.relative_to(_REPO_ROOT)), node.lineno))
    assert offenders == []


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


def test_no_shipped_public_callable_returns_a_trusted_runtime_root() -> None:
    """The shape half of the same fact, proved by introspection rather than by text: a
    same-shaped function reintroduced under some *other* name would still be caught, because no
    public callable this package exports declares ``TrustedRuntimeRoot`` as its return type
    (P15-R2-F1 -- "do not replace it with a same-shaped function under a new name")."""

    for name in runtime_module.__all__:
        member = getattr(runtime_module, name)
        if not callable(member) or isinstance(member, type):
            continue
        annotation = inspect.signature(member).return_annotation
        rendered = (
            annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
        )
        assert _TRUSTED_ROOT_TYPE_NAME not in str(rendered), (
            f"{name} returns a {_TRUSTED_ROOT_TYPE_NAME} -- shipped code must mint none"
        )


def test_bootstrap_accepts_no_store_or_project_selecting_parameter() -> None:
    """P15-R1-F4's own decisive structural fact, proved by introspection rather than by
    behaviour: there is no call shape at all -- not one that is refused at runtime, one that
    does not exist -- through which a caller could hand
    ``bootstrap_projection_execution_capability`` an alternate Store, Project, or Binding.
    The identical technique ``tests/contract/projection/
    test_v3_live_write_authority_static_conformance.py`` already applies to
    ``ProjectionExecutionCapability.execute``."""

    signature = inspect.signature(bootstrap_module.bootstrap_projection_execution_capability)
    assert set(signature.parameters) == {
        "trusted_runtime_root",
        # P15-R3-F1: the two arguments that actually gate this call now. Neither names a Store,
        # a Project, or a Binding -- the admission *reference* is resolved exclusively inside
        # the root's own Store, and the anchor is a bare public key the deployment boundary
        # supplies from its own configuration.
        "runtime_root_admission_ref",
        "trust_anchor_public_key_hex",
        "github_projection_grant_refs",
        "github_projection_grant_declaration_refs",
    }
    for forbidden in ("store", "project_id", "project_binding_id"):
        assert forbidden not in signature.parameters


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


def test_boot_project_is_imported_only_by_route_and_bootstrap() -> None:
    for module in _ALL_PACKAGE_MODULES:
        if module in (route_module, bootstrap_module):
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


def test_the_bootstrap_admission_check_precedes_every_grant_and_authority_call() -> None:
    """P15-R3-F1, proved structurally rather than only dynamically (the zero-call proofs live in
    ``tests/integration/runtime/test_runtime_root_admission.py``).

    Inside ``bootstrap_projection_execution_capability``'s own body, the literal call to
    ``_require_admitted_root`` must appear before the first ``_resolve_grant``,
    ``_resolve_declaration``, or ``evaluate_projection_authorization`` call site -- so no future
    edit can quietly move grant resolution, or an authorization evaluation, in front of the
    admission gate.
    """

    tree = ast.parse(inspect.getsource(bootstrap_module))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "bootstrap_projection_execution_capability"
    )
    admission_lines: list[int] = []
    gated_lines: list[int] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.id
            if isinstance(func, ast.Name)
            else (func.attr if isinstance(func, ast.Attribute) else None)
        )
        if name == "_require_admitted_root":
            admission_lines.append(node.lineno)
        elif name in (
            "_resolve_grant",
            "_resolve_declaration",
            "evaluate_projection_authorization",
        ):
            gated_lines.append(node.lineno)
    assert len(admission_lines) == 1, "exactly one admission call site is expected"
    assert gated_lines, "expected the gated calls to exist at all"
    assert admission_lines[0] < min(gated_lines)


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


def test_only_route_and_the_deployment_registry_call_commit_state_transition() -> None:
    """Runtime Observation commits exactly once per call (no intent/materialize-attempt
    claim pair -- see ``engine.py``'s own module docstring) -- so ``route.py`` calls
    ``commit_state_transition`` from exactly one literal call site.

    Round 3 (P15-R3-F2) admits exactly one more module by name: ``deployment_registry.py``, also
    from exactly one call site, for the single atomic transition that commits a
    ``runtime_deployment_declaration`` **and** moves this target's own current-declaration
    pointer. Two domain reasons for a commit, two transition plans, still one sanctioned
    committer -- the identical discipline ``store/commit.py``'s own module docstring states for
    Reflow and Binding, which are two call sites of it as well. The repository-wide K-003/R-001
    rule is about ``store.commit`` itself, and the test below still proves no module here calls
    that directly.
    """

    for module in _ALL_PACKAGE_MODULES:
        count = _call_site_count(module, "commit_state_transition")
        if module in (route_module, deployment_registry_module):
            assert count == 1, f"{module.__name__} must call commit_state_transition exactly once"
        else:
            assert count == 0, f"{module.__name__} must never call commit_state_transition"


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
