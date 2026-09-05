"""Repository-owned static topology inventory for K-001/K-002/K-003/R-001/R-002 (R9-F1,
Phase 7 structural-review round 9; reinforced R10-F2, round 10; reinforced again R11-F2,
round 11).

R8-F1's own module docstring on ``difference/invariant_verifiers.py`` disclosed, honestly,
that K-001/K-002/K-003's ``REQUIRED_EVIDENCE`` names whole-codebase architectural facts --
"dependency graph / kernel entry-point inventory" (K-001), "state owner inventory /
write-path inventory / reconstruction-source inventory" (K-002), "authority resolution
trace / writer identity / transition ownership record" (K-003) -- that no single Candidate's
content can individually falsify or prove, and that this vertical had no owner for them.
SHUKOU's Round 9 adoption settles how to close that gap: a real, reproducible inventory of
the *installed package's own module graph*, using the same functions/classes this vertical
already treats as canonical (``reflow.closure.evaluate_closure``, ``reflow.commit.
commit_reflow``, ``authority.engine.evaluate_authority``, ``store.file_store.
FileStateStore``) -- never a new canonical authority invented for this check alone.

This module lives at the top level, sibling to every domain package, rather than inside
``difference`` (the invariant verifiers' own home) or ``reflow`` (several of the canonical
owners it inventories): the established package layering is ``observation`` independent,
``difference`` depending only on ``observation``/``state``, ``reflow`` depending on
``difference`` -- never the reverse. A module ``difference.invariant_verifiers`` calls that
statically imported anything under ``reflow`` would invert that direction. This module
never does: it names no domain module by static import at all, only by the string
``manosube_agent_civilization`` handed to :func:`pkgutil.walk_packages`, discovering every
canonical owner (``reflow`` and ``store`` included) purely through runtime reflection over
the installed package as a whole -- a cross-cutting introspection utility, not a participant
in the domain dependency graph it inspects.

``KERNEL_INVARIANTS.md`` section 15's own Verification Matrix marks Kernel Identity (and
Reflow/Lineage) invariants ``Static`` *and* ``Natural Cycle`` -- this module supplies the
``Static`` half (computed once, from the actual installed package, independent of any
particular Candidate); :mod:`~manosube_agent_civilization.difference.invariant_verifiers`'s
own per-cycle local-binding checks remain the ``Natural Cycle`` half. Both must hold for
K-001/K-002/K-003/R-001/R-002 to PASS (``K001_K002_K003_PARTIAL_PASS_ACCEPTED=false`` -- a
real topology fact standing in for the whole claim, not the previous round's local-field
proxy).

The inventory is a pure function of the installed package's own source, so it is computed
once and cached: it can never disagree with itself between two calls in the same process,
and a package that genuinely gained a second canonical owner would show it on the very next
(uncached) run in a fresh process, not silently keep passing forever.

**Scope (R11-F2, made explicit):** ``STATIC_TOPOLOGY_SCOPE`` below names exactly what this
module proves anything about -- the installed ``manosube_agent_civilization`` package's own
source, nothing more (``PROOF_SCOPE=INSTALLED_CANONICAL_PACKAGE_SOURCE``). Phase 14's GitHub
Adapter, any external runtime, a future plugin, or an entry point that does not yet exist are
out of Phase 7's scope and this module makes no claim about them
(``UNBOUNDED_EXTERNAL_WORLD_PROOF_REQUIRED=false``). Within that scope, though, every module
that exists must actually be inspected -- no module inside the boundary may be excluded from
the scan merely because its source happens to be unreadable, unparseable, or expressed in a
syntactic form this module's own detectors do not yet recognize by name
(``IN_SCOPE_UNOBSERVED_SOURCE_PASS_ALLOWED=false``). This inventory is a **Verification
Projection** against the existing Contract and implementation, never a second Canonical
Authority in its own right (``TOPOLOGY_INVENTORY_NE_CANONICAL_AUTHORITY=true``): it does not
mint a canonical fact, it checks that exactly one already-canonical owner exists for each
role this vertical's own frozen contract already names, and refuses to answer rather than
guess when it cannot actually see everything in scope.

R10-F2 (SHUKOU Round 10) sharpened two things this module's Round 9 shape left open:

1. ``IMPORT_FAILURE_MUST_NOT_BE_SILENTLY_EXCLUDED=true``. Round 9's own
   :func:`_iter_installed_modules` swallowed any module's import failure
   (``contextlib.suppress(Exception)``) and simply left it out of the scan -- meaning a
   module that fails to import is invisible to this inventory, silently narrowing what the
   scan actually covers rather than making the whole inventory indeterminate. This module no
   longer catches anything there: an import failure anywhere in the installed package now
   propagates out of every ``k00X_...``/``r00X_...`` function, and
   :mod:`~manosube_agent_civilization.difference.invariant_verifiers`'s own
   ``try/except Exception: return "UNKNOWN"`` around each of those calls (already present
   since R9-F1, unchanged this round) turns that into the honest ``UNKNOWN`` this vertical's
   own ``UNPROVEN_INVARIANT_MUST_BE_UNKNOWN=true`` rule already requires -- never a PASS
   computed over an incomplete scan.

2. ``EXPECTED_SYMBOL_NAME_COUNT_NE_CANONICAL_OWNER_COUNT=true``. Round 9's own
   :func:`_functions_named`/:func:`_classes_with_methods` prove uniqueness of a *name* --
   a second implementation under a different function or class name would pass every Round 9
   check unnoticed. Round 10 added real, name-independent content-pattern scans:
   identity-field-assignment sites, direct filesystem write sites, and Reflow transition
   commit sites.

R11-F2 (SHUKOU Round 11) sharpens both of those Round 10 additions further, closing two real
gaps a review of Round 10's own topology reinforcement found:

1. ``SOURCE_READ_FAILURE_MUST_NOT_BE_SILENTLY_EXCLUDED=true`` (and, by the same reasoning,
   ``MODULE_IMPORTED_NE_SOURCE_OBSERVED=true``): Round 10's own :func:`_module_source_trees`
   caught ``inspect.getsource``'s ``(OSError, TypeError)`` and silently ``continue``d past
   that module -- exactly the same silent-exclusion shape R10-F2 already closed one layer up,
   now reopened one layer down. A module that *imports* successfully is not the same fact as
   a module whose *source was actually read and inspected*; this module no longer treats
   the former as sufficient. Source-read failure (and, transitively, a source-parse failure
   -- ``ast.parse`` raising on genuinely malformed text) now propagates identically to an
   import failure, landing on the same ``UNKNOWN`` path.

2. ``AST_PATTERN_NOT_MATCHED_NE_OWNER_ABSENT=true``: Round 10's own content-pattern scans
   recognized exactly one syntactic shape per identity field (a bare ``X["field"] = ...``
   subscript assignment) and exactly one bare-name write primitive (``atomic_write``). A
   second producer expressed as a dict literal, a constructor keyword, an attribute
   assignment, an ``.update(...)``/``.setdefault(...)`` call, or a second writer expressed as
   ``Path.write_text``/``Path.write_bytes``/``open(...).write(...)``/``os.replace``/
   ``os.rename``/``shutil.copy*`` would all have passed unnoticed. This module now recognizes
   all of those forms. Symbol/method *names* still matter (:func:`_functions_named`/
   :func:`_classes_with_methods`, unchanged) but are no longer asked to carry the whole
   uniqueness proof alone -- ``EXPECTED_SYMBOL_NAME_COUNT_NE_CANONICAL_OWNER_COUNT=true``
   holds precisely because the content-pattern side now also holds.

   Deduplication for the identity-field scan happens at the **module**, not the raw
   syntax-site, level (:func:`_site_modules`): a single legitimate producer module may
   express the same identity field through more than one of these recognized forms (this
   vertical's own real producers each do -- an inert ``"field": ""`` dict-literal placeholder
   immediately overwritten by a real subscript assignment, in the same module) without that
   constituting a second producer. What is being counted is "how many distinct *modules* can
   produce this identity", never "how many *lines* mention it" -- a documentation string, a
   schema-key allowlist entry, or a read-only reference to the field is not a production site
   at all (no assignment target, no dict key, no call), and this module's detectors are
   built not to match any of those.
"""

from __future__ import annotations

import ast
from functools import lru_cache
import importlib
import inspect
import pkgutil
from typing import Any

_PACKAGE_NAME = "manosube_agent_civilization"

#: R11-F2: the explicit, named boundary of everything this module proves anything about --
#: see the module docstring's own "Scope" section.
STATIC_TOPOLOGY_SCOPE = _PACKAGE_NAME

#: The exact (module, name) this vertical already treats as the one canonical producer/
#: owner for each role K-001/K-002/K-003/R-001/R-002 name -- used only to describe the
#: inventory below, never to pre-select or filter what the scan actually finds.
CANONICAL_CLOSURE_PRODUCER = (f"{_PACKAGE_NAME}.reflow.closure", "evaluate_closure")
CANONICAL_STATE_STORE = (f"{_PACKAGE_NAME}.store.file_store", "FileStateStore")
CANONICAL_AUTHORITY_PRODUCER = (f"{_PACKAGE_NAME}.authority.engine", "evaluate_authority")
CANONICAL_REFLOW_COMMITTER = (f"{_PACKAGE_NAME}.reflow.commit", "commit_reflow")
#: R10-F2: the real composed Kernel entry point -- distinct from
#: ``CANONICAL_CLOSURE_PRODUCER`` above, which is only the Closure-Evaluation-producer stage
#: inside it (``EVALUATE_CLOSURE_NE_WHOLE_KERNEL_ENTRYPOINT=true``).
CANONICAL_KERNEL_ENTRY_POINT = (f"{_PACKAGE_NAME}.reflow.route", "reflow")

#: R10-F2/R11-F2: modules sanctioned to perform a direct filesystem write -- the one file
#: that defines the raw atomic-write primitive, and the one Store implementation that calls
#: it (and, internally, appends to its own lineage log the identical way). Any other module
#: in the installed tree performing a direct write of any recognized shape is a second,
#: unsanctioned write path.
_SANCTIONED_DIRECT_WRITE_MODULES = frozenset(
    {f"{_PACKAGE_NAME}.store.file_store", f"{_PACKAGE_NAME}.store.atomic_write"}
)
#: R10-F2: the one module sanctioned to call some object's ``.commit(...)`` -- Reflow's own
#: atomic-commit orchestrator. Any other module doing so is a second transition committer.
_SANCTIONED_COMMIT_CALL_MODULES = frozenset({f"{_PACKAGE_NAME}.reflow.commit"})


def _iter_installed_modules() -> list[Any]:
    """Every module in the installed package, imported fresh.

    R10-F2: an import failure anywhere in the tree now propagates out of this function (and
    therefore out of every inventory function built on it) rather than being silently
    swallowed and excluded -- ``IMPORT_FAILURE_MUST_NOT_BE_SILENTLY_EXCLUDED=true``. A module
    this scan cannot even import is not proof of "nothing to see here"; it is proof the scan
    itself is incomplete, and every caller of this function already turns that propagated
    exception into the honest ``UNKNOWN`` a topology fact this vertical cannot currently
    compute must report (see :mod:`~manosube_agent_civilization.difference.
    invariant_verifiers`'s own ``try/except Exception: return "UNKNOWN"`` around each
    ``k00X_...``/``r00X_...`` call, unchanged since R9-F1).
    """

    package = importlib.import_module(_PACKAGE_NAME)
    return [
        importlib.import_module(info.name)
        for info in pkgutil.walk_packages(package.__path__, prefix=_PACKAGE_NAME + ".")
    ]


def _module_source_trees(modules: list[Any] | None = None) -> list[tuple[str, ast.Module]]:
    """``(module_name, parsed_ast)`` for every module in *modules* (defaulting to
    :func:`_iter_installed_modules`'s own real scan) -- the shared basis for every
    content-pattern scan below, so each one parses the tree exactly once per
    :func:`kernel_topology_inventory` call rather than independently.

    R11-F2: ``inspect.getsource`` failing on an installed, successfully-imported module (or
    ``ast.parse`` failing on what it returns) now propagates instead of being silently
    excluded -- ``MODULE_IMPORTED_NE_SOURCE_OBSERVED=true``/``SOURCE_READ_FAILURE_MUST_NOT_
    BE_SILENTLY_EXCLUDED=true``. A module this scan cannot actually read the source of is not
    proof there is nothing to see there; every caller already turns the propagated exception
    into ``UNKNOWN`` the identical way an import failure does. *modules* is exposed as a
    parameter so a caller (this module's own test suite included) can hand this function a
    real module object whose ``inspect.getsource`` genuinely fails, or genuinely-malformed
    real source text run through the identical, real ``ast.parse`` this function itself
    calls, without needing to physically alter the installed package on disk for every case
    -- the acquisition-failure boundary this parameter exercises is the same one the default,
    unparameterized call already relies on.
    """

    trees: list[tuple[str, ast.Module]] = []
    for module in modules if modules is not None else _iter_installed_modules():
        source = inspect.getsource(module)
        trees.append((module.__name__, ast.parse(source, filename=module.__name__)))
    return trees


def _functions_named(name: str) -> list[str]:
    """Every module-level function literally named *name*, defined (not merely imported)
    in the module it is found on -- ``f"{module}.{name}"`` per match, deduplicated by
    identity so a re-export of the same function object is not counted twice."""

    found: dict[int, str] = {}
    for module in _iter_installed_modules():
        obj = getattr(module, name, None)
        if inspect.isfunction(obj) and obj.__module__ == module.__name__:
            found[id(obj)] = f"{module.__name__}.{name}"
    return sorted(found.values())


def _classes_with_methods(*method_names: str) -> list[str]:
    """Every concrete (non-``typing.Protocol``) class defined in the installed package that
    implements every one of *method_names* -- an interface declaration (a ``Protocol``) is
    not a second implementation, only a second concrete class actually providing the full
    surface counts."""

    found: dict[int, str] = {}
    for module in _iter_installed_modules():
        for cls_name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__:
                continue
            if getattr(obj, "_is_protocol", False):
                continue
            if all(callable(getattr(obj, method, None)) for method in method_names):
                found[id(obj)] = f"{module.__name__}.{cls_name}"
    return sorted(found.values())


def _site_modules(sites: list[str]) -> set[str]:
    """The distinct module names named by a ``"module:lineno"``-shaped site list -- R11-F2's
    own module-level deduplication (see the module docstring). Counting *modules*, not raw
    syntax sites, is what makes "a legitimate producer expresses this field through two
    recognized forms in the same module" and "two different modules each express it once"
    distinguishable, which raw site counting is not."""

    return {site.rsplit(":", 1)[0] for site in sites}


def _identity_field_assignment_sites(
    field_name: str, *, trees: list[tuple[str, ast.Module]] | None = None
) -> list[str]:
    """R10-F2, widened R11-F2: every real source location in *trees* (defaulting to
    :func:`_module_source_trees`'s own real scan) where a recognized production form could
    mint the identity field *field_name* -- e.g. ``record["closure_evaluation_id"] =
    closure_evaluation_id(record)``, ``record.closure_evaluation_id = ...``, a dict literal
    ``{"closure_evaluation_id": ..., ...}`` (placeholder or real value alike -- see below),
    ``record.update({"closure_evaluation_id": ...})``/``record.update(closure_evaluation_id=
    ...)``, ``record.setdefault("closure_evaluation_id", ...)``, or any call supplying
    ``closure_evaluation_id=...`` as a keyword argument (a constructor, a dataclass, or an
    ordinary function alike -- AST cannot distinguish "class constructor" from "function
    call" by syntax shape alone, so this deliberately treats every keyword-argument match as
    a candidate production site rather than guessing which calls are constructors).

    Found by walking each module's own parsed source, never by the name of the enclosing
    function or class -- a second producer of this identity field shows here even if it is
    never named ``evaluate_closure``/``evaluate_authority`` (or anything else this module
    already scans for by name) at all.

    A read (``record["closure_evaluation_id"]`` used as a value, not assigned to), a
    documentation string, or a schema-key allowlist entry (``"closure_evaluation_id"``
    appearing as a tuple/list element or as a dict *value* rather than *key*) matches none
    of these node shapes and is correctly never counted -- this module's own real production
    sites (``reflow/closure.py``'s and ``authority/engine.py``'s each pairing a placeholder
    dict-literal key with a later subscript-assignment recompute in the same module) are the
    positive proof that both forms coexisting in one legitimate producer module do not
    inflate its own count; :func:`_site_modules` is what a caller must use to turn this
    site list into a *producer-module* count, not ``len()`` of the raw list.
    """

    found: list[str] = []
    for module_name, tree in trees if trees is not None else _module_source_trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Subscript)
                        and isinstance(target.slice, ast.Constant)
                        and target.slice.value == field_name
                    ) or (isinstance(target, ast.Attribute) and target.attr == field_name):
                        found.append(f"{module_name}:{node.lineno}")
            elif isinstance(node, ast.AnnAssign):
                target = node.target
                if (isinstance(target, ast.Attribute) and target.attr == field_name) or (
                    isinstance(target, ast.Name) and target.id == field_name
                ):
                    found.append(f"{module_name}:{node.lineno}")
            elif isinstance(node, ast.Dict):
                for key in node.keys:
                    if isinstance(key, ast.Constant) and key.value == field_name:
                        found.append(f"{module_name}:{node.lineno}")
                        break
            elif isinstance(node, ast.Call):
                # Any call's own keyword argument named *field_name* -- a constructor, a
                # dataclass, an ordinary function, or ``.update(field_name=...)`` alike (AST
                # cannot distinguish "class constructor" from "function call" by syntax shape
                # alone, so every keyword-argument match is a candidate production site).
                # This deliberately does NOT also scan positional arguments in general: an
                # arbitrary bare-name call passing *field_name*'s own string as one of many
                # positional arguments (a schema-key reference, a validator invocation) is
                # exactly the "string exists as a reference" case that must never count as
                # production -- only ``.setdefault(field_name, ...)`` below, where the first
                # positional argument is unambiguously the dict key itself, is a real
                # production site expressed positionally.
                for kw in node.keywords:
                    if kw.arg == field_name:
                        found.append(f"{module_name}:{node.lineno}")
                        break
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "setdefault"
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value == field_name
                ):
                    found.append(f"{module_name}:{node.lineno}")
    return sorted(found)


def _open_call_is_write_mode(node: ast.Call) -> bool:
    """Whether a bare ``open(...)`` call's own *mode* argument is anything other than the
    default read-only ``"r"`` -- a non-literal (computed) mode cannot be proven read-only
    from syntax alone and is conservatively treated as a write candidate
    (``unknown or unclassified mutation site causes UNKNOWN/FAIL``, per SHUKOU's own Round
    11 text)."""

    mode_node = node.args[1] if len(node.args) >= 2 else None
    for kw in node.keywords:
        if kw.arg == "mode":
            mode_node = kw.value
    if mode_node is None:
        return False
    if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
        return any(ch in "wax+" for ch in mode_node.value)
    return True


def _call_sites(
    names: frozenset[str],
    *,
    exclude_modules: frozenset[str],
    required_receiver: str | None = None,
    trees: list[tuple[str, ast.Module]] | None = None,
) -> list[str]:
    """R10-F2, widened R11-F2: every call site in *trees* (defaulting to
    :func:`_module_source_trees`'s own real scan), outside *exclude_modules*, whose called
    function is a bare name or an attribute literally named one of *names* -- e.g.
    ``atomic_write(...)`` or ``store.commit(...)``.

    *required_receiver*, when given, restricts an attribute-form match to calls on that
    exact bare receiver name (e.g. ``"os"`` for ``os.replace``/``os.rename``, ``"shutil"``
    for ``shutil.copy*``) -- ``replace``/``rename``/``copy`` are also ordinary ``str``/
    ``dict``/``list`` method names in wide, legitimate use throughout this codebase (string
    timestamp normalization, dict/list copies) that share no relationship at all with a
    filesystem write; matching those names unqualified would flag every one of them as a
    false "second write path". Requiring the literal ``os``/``shutil`` receiver is what
    keeps this scan aimed at the actual filesystem primitive rather than any object that
    happens to expose a same-named method.

    A second writer or committer shows here regardless of what class, method name, or
    wrapper function it is reached through."""

    found: list[str] = []
    for module_name, tree in trees if trees is not None else _module_source_trees():
        if module_name in exclude_modules:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):
                if required_receiver is not None:
                    continue
                name = func.id
            elif isinstance(func, ast.Attribute):
                if required_receiver is not None and not (
                    isinstance(func.value, ast.Name) and func.value.id == required_receiver
                ):
                    continue
                name = func.attr
            else:
                continue
            if name in names:
                found.append(f"{module_name}:{node.lineno}")
    return sorted(found)


def _open_write_call_sites(
    *, exclude_modules: frozenset[str], trees: list[tuple[str, ast.Module]] | None = None
) -> list[str]:
    """R11-F2: every bare ``open(...)`` call in *trees*, outside *exclude_modules*, whose
    own mode argument is not provably read-only (:func:`_open_call_is_write_mode`) -- the
    ``open(..., "wb").write(...)``-shaped direct write path SHUKOU's own Round 11 text names
    explicitly, caught regardless of what object the returned file handle is bound to or what
    that handle's own ``.write(...)`` call is later reached through."""

    found: list[str] = []
    for module_name, tree in trees if trees is not None else _module_source_trees():
        if module_name in exclude_modules:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "open"
                and _open_call_is_write_mode(node)
            ):
                found.append(f"{module_name}:{node.lineno}")
    return sorted(found)


def _direct_filesystem_write_sites() -> list[str]:
    """R10-F2, widened R11-F2: every recognized direct-filesystem-write call site in the
    installed package, outside the two sanctioned Store modules -- the union of the raw
    atomic-write primitive, ``pathlib.Path``'s own ``write_text``/``write_bytes``, a bare
    file object's ``.write(...)``, ``os.replace``/``os.rename``, ``shutil.copy``/
    ``copyfile``/``copy2``, and a write-mode ``open(...)`` call. A caller mutating
    ``lineage``/``current``/``records``/``recovery`` paths through any of these primitives
    is caught here regardless of which specific primitive it happens to use -- this module
    does not need to separately special-case those path names, since any real mutation of
    them necessarily goes through one of these calls."""

    trees = _module_source_trees()
    return sorted(
        set(
            _call_sites(
                frozenset({"atomic_write"}),
                exclude_modules=_SANCTIONED_DIRECT_WRITE_MODULES,
                trees=trees,
            )
        )
        | set(
            _call_sites(
                frozenset({"write_text", "write_bytes", "write"}),
                exclude_modules=_SANCTIONED_DIRECT_WRITE_MODULES,
                trees=trees,
            )
        )
        | set(
            _call_sites(
                frozenset({"replace", "rename"}),
                exclude_modules=_SANCTIONED_DIRECT_WRITE_MODULES,
                required_receiver="os",
                trees=trees,
            )
        )
        | set(
            _call_sites(
                frozenset({"copy", "copyfile", "copy2"}),
                exclude_modules=_SANCTIONED_DIRECT_WRITE_MODULES,
                required_receiver="shutil",
                trees=trees,
            )
        )
        | set(_open_write_call_sites(exclude_modules=_SANCTIONED_DIRECT_WRITE_MODULES, trees=trees))
    )


#: R12-F2 (SHUKOU Phase 7 Final Closure): the exact ``"module.function"`` pairs authorized
#: to write to the Lineage log, keyed by the semantic role each one fulfills --
#: ``AUTHORIZED_LINEAGE_WRITE_PATHS_EXPLICIT=true``. Any *other* function anywhere in the
#: installed package whose own body both references the Lineage-path accessor
#: (:meth:`FileStateStore._lineage`) and calls a recognized write primitive is a second,
#: unauthorized Lineage writer -- ``UNCLASSIFIED_LINEAGE_WRITE_PATHS=0`` is this vertical's
#: own claim, checked against this exact set, never against a bare count alone (a rogue
#: writer could otherwise coincide in number with a removed legitimate one).
_AUTHORIZED_LINEAGE_WRITE_FUNCTIONS = frozenset(
    {
        f"{_PACKAGE_NAME}.store.file_store._append",
        f"{_PACKAGE_NAME}.store.file_store.initialize",
    }
)
#: Recognized write/read primitive names for the Lineage-specific scan below -- the same
#: vocabulary :func:`_direct_filesystem_write_sites` already uses, reused rather than
#: reinvented for this narrower, Lineage-path-specific question.
_LINEAGE_WRITE_PRIMITIVE_NAMES = frozenset({"atomic_write", "write_text", "write_bytes", "write"})
_LINEAGE_READ_PRIMITIVE_NAMES = frozenset({"read_text", "read_bytes"})
_LINEAGE_ACCESSOR_NAME = "_lineage"
#: R13-F1 (SHUKOU post-Final-Closure correction): ``LINEAGE_OWNER_PROOF_MUST_COVER_CREATE_
#: APPEND_REWRITE_AND_DESTRUCTIVE_MUTATION=true`` -- R12-F2's own primitive vocabulary above
#: recognized only the raw atomic-write/``write_text``/``write_bytes``/bare-``.write()``
#: shapes :func:`_direct_filesystem_write_sites` already used for the *general* filesystem
#: scan, but never that scan's own write-mode-``open``/``os.replace``/``os.rename``/
#: ``shutil.copy*`` widening (R11-F2) -- a rogue Lineage rewrite expressed through any of
#: those forms was invisible to the Lineage-specific inventory even though the general scan
#: already recognizes the identical primitive shape. Receiver-qualified to the literal
#: ``os``/``shutil`` module for the identical reason Round 11 already established:
#: ``replace``/``rename``/``copy`` are also ordinary ``str``/``dict``/``list`` method names
#: in wide, unrelated use, and bare-name matching would flag every one of those as a false
#: Lineage write.
_LINEAGE_OS_PRIMITIVE_NAMES = frozenset({"replace", "rename"})
_LINEAGE_SHUTIL_PRIMITIVE_NAMES = frozenset({"copy", "copyfile", "copy2"})


def _lineage_reference_and_primitive_functions(
    *, trees: list[tuple[str, ast.Module]] | None = None
) -> tuple[list[str], list[str]]:
    """R12-F2, widened R13-F1: independently inventory every function/method in the
    installed package whose own body references the Lineage-path accessor
    (``self._lineage(...)``) -- Round 10's own ``_direct_filesystem_write_sites`` proves no
    *unsanctioned module* writes a file directly, but a rogue write added *inside* an
    already-sanctioned module (``store.file_store`` itself) is invisible to that check by
    construction (``REFLOW_COMMIT_OWNER_COUNT_NE_LINEAGE_WRITE_PATH_COUNT=true`` -- R-001's
    own "one commit path" fact says nothing about how many functions touch the Lineage log
    specifically). This closes that gap by classifying every function that references the
    Lineage path *by what it actually does with it*, never by which module it happens to
    live in (``SAME_MODULE_NE_AUTOMATICALLY_AUTHORIZED=true``).

    R13-F1 widens *what counts as doing something with it* to match every create/append/
    replace/rename/copy/truncate-shaped mutation primitive the *general* filesystem scan
    already recognizes (``LINEAGE_PATH_REFERENCE_PLUS_MUTATION_PRIMITIVE_IS_A_LINEAGE_
    WRITER=true``, ``UNCLASSIFIED_LINEAGE_MUTATION_PATHS_ALLOWED=false``): a write-mode
    ``open(...)`` call, ``os.replace``/``os.rename``, and ``shutil.copy``/``copyfile``/
    ``copy2`` now count as writers here too, not only the four raw primitive names R12-F2
    itself recognized. No statically-visible mutation path a function reaches while also
    referencing the Lineage accessor may go unclassified
    (``STATICALLY_VISIBLE_MUTATION_PATH_MUST_NOT_BE_MISSED=true``); a call reached only
    through a runtime-constructed name remains the same disclosed, bounded detection
    boundary this module's own docstring already names for every one of its content-pattern
    scans (``DYNAMICALLY_CONSTRUCTED_CALL_NAME_STATIC_PROOF_REQUIRED=false``).

    Returns ``(write_functions, read_functions)`` -- ``"module.function"`` entries. A
    function referencing the accessor whose own body also calls a recognized write
    primitive is a writer; failing that, one that calls a recognized read primitive is a
    reader; a function that merely checks ``.exists()`` on the path (``initialize``'s own
    ``AlreadyInitializedError`` guard, shared by both its branches) is neither, and is
    correctly excluded from both lists -- existence-checking is not itself reading or
    writing the Lineage log's own content.
    """

    write_functions: list[str] = []
    read_functions: list[str] = []
    for module_name, tree in trees if trees is not None else _module_source_trees():
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            references_lineage = False
            has_write = False
            has_read = False
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Call):
                    continue
                func = inner.func
                if isinstance(func, ast.Attribute):
                    name = func.attr
                elif isinstance(func, ast.Name):
                    name = func.id
                else:
                    continue
                if name == _LINEAGE_ACCESSOR_NAME:
                    references_lineage = True
                elif name in _LINEAGE_WRITE_PRIMITIVE_NAMES:
                    has_write = True
                elif name in _LINEAGE_READ_PRIMITIVE_NAMES:
                    has_read = True
                elif (
                    isinstance(func, ast.Name)
                    and name == "open"
                    and _open_call_is_write_mode(inner)
                ) or (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and (
                        (name in _LINEAGE_OS_PRIMITIVE_NAMES and func.value.id == "os")
                        or (name in _LINEAGE_SHUTIL_PRIMITIVE_NAMES and func.value.id == "shutil")
                    )
                ):
                    has_write = True
            if not references_lineage:
                continue
            qualname = f"{module_name}.{node.name}"
            if has_write:
                write_functions.append(qualname)
            elif has_read:
                read_functions.append(qualname)
    return sorted(write_functions), sorted(read_functions)


@lru_cache(maxsize=1)
def kernel_topology_inventory() -> dict[str, list[str]]:
    """Return the real, reproducible inventory this module's own docstring names -- every
    ``evaluate_closure`` (Closure-Evaluation producer), every ``reflow`` function under
    ``reflow.route`` (the real composed Kernel entry point, R10-F2), every concrete class
    implementing the full canonical-State surface (``commit``/``load_current``/
    ``reconstruct``/``resolve_record`` -- write path, reconstruction source and persistence
    owner together), every ``evaluate_authority`` (Authority owner), every ``commit_reflow``
    (Reflow transition owner), and every name-independent identity-field-assignment or
    write/commit call site actually found in the installed package (R10-F2, widened R11-F2).
    Exactly one *module* producing each named role, and zero unsanctioned call sites, is this
    vertical's own claim; anything else is a real, reproducible violation, not a proxy for
    one. Use :func:`_site_modules` on the ``*_identity_sites`` entries to get a producer-
    module count rather than a raw site count (see that function's own docstring).
    """

    lineage_write_functions, lineage_read_functions = _lineage_reference_and_primitive_functions()
    return {
        "closure_producers": _functions_named("evaluate_closure"),
        "kernel_entry_points": _functions_named("reflow"),
        "state_stores": _classes_with_methods(
            "commit", "load_current", "reconstruct", "resolve_record"
        ),
        "authority_producers": _functions_named("evaluate_authority"),
        "reflow_committers": _functions_named("commit_reflow"),
        "closure_evaluation_identity_sites": _identity_field_assignment_sites(
            "closure_evaluation_id"
        ),
        "authority_decision_identity_sites": _identity_field_assignment_sites(
            "authority_decision_id"
        ),
        "direct_filesystem_write_sites": _direct_filesystem_write_sites(),
        "reflow_transition_commit_sites": _call_sites(
            frozenset({"commit"}), exclude_modules=_SANCTIONED_COMMIT_CALL_MODULES
        ),
        "lineage_write_functions": lineage_write_functions,
        "lineage_read_functions": lineage_read_functions,
    }


def k001_single_kernel_entry_point() -> bool:
    """K-001 EXACTLY_ONE_CANONICAL_KERNEL, its Static half: exactly one ``evaluate_closure``
    (the Closure-Evaluation-producer stage), exactly one ``reflow`` function under
    ``reflow.route`` (the real composed Kernel entry point, R10-F2), and exactly one
    *module* producing a real content-addressed ``closure_evaluation_id`` (R10-F2, module-
    level per R11-F2) -- proof, by both name and by what the code actually does, that only
    one Kernel implementation exists in the tree, not merely the one this call happened to
    import."""

    inventory = kernel_topology_inventory()
    return (
        len(inventory["closure_producers"]) == 1
        and len(inventory["kernel_entry_points"]) == 1
        and len(_site_modules(inventory["closure_evaluation_identity_sites"])) == 1
    )


def k002_single_canonical_state_owner() -> bool:
    """K-002 (State ownership), its Static half: exactly one concrete class in the installed
    package implements the full canonical-State surface, *and* (R10-F2, widened R11-F2) no
    other module performs any recognized direct filesystem write -- no parallel State owner,
    named or unnamed, exists to consult or write through instead."""

    inventory = kernel_topology_inventory()
    return len(inventory["state_stores"]) == 1 and not inventory["direct_filesystem_write_sites"]


def k003_single_authority_and_transition_owner() -> bool:
    """K-003 (Authority/transition/persistence ownership, absence of parallel canonical
    authority): exactly one ``evaluate_authority`` Authority producer, exactly one *module*
    producing a real ``authority_decision_id`` (R10-F2, module-level per R11-F2), exactly one
    ``commit_reflow`` Reflow transition committer with no other module calling any object's
    ``.commit(...)`` (R10-F2), and the same single canonical State owner K-002 already
    proved -- no second, competing canonical authority for any of the three roles this
    Invariant names, by name or by what the code actually does."""

    inventory = kernel_topology_inventory()
    return (
        len(inventory["authority_producers"]) == 1
        and len(_site_modules(inventory["authority_decision_identity_sites"])) == 1
        and len(inventory["reflow_committers"]) == 1
        and not inventory["reflow_transition_commit_sites"]
        and k002_single_canonical_state_owner()
    )


def r001_single_atomic_committer() -> bool:
    """R-001 REFLOW_ATOMIC, its Static half: the same single canonical State owner K-002
    already proved is the one and only place an atomic commit can happen through, *and*
    (R10-F2) no other module calls any object's ``.commit(...)`` at all -- there is no
    second commit path, named or unnamed, a caller could reach instead."""

    inventory = kernel_topology_inventory()
    return k002_single_canonical_state_owner() and not inventory["reflow_transition_commit_sites"]


def r002_single_lineage_owner() -> bool:
    """R-002 LINEAGE_APPEND_ONLY, its Static half -- R12-F2 (SHUKOU Phase 7 Final Closure):
    no longer a bare proxy of R-001 (``R002_NE_R001_PROXY=true``/``R002_INDEPENDENT_OF_
    R001=true``). R-001's own "one commit path" fact says nothing about how many functions
    actually touch the Lineage log (``REFLOW_COMMIT_OWNER_COUNT_NE_LINEAGE_WRITE_PATH_
    COUNT=true``) -- a second Lineage writer added *inside* the already-sanctioned
    ``store.file_store`` module would pass R-001 unnoticed, since R-001 never inspects
    Lineage-path-specific call sites at all. This Invariant now has its own, independent
    inventory (:func:`_lineage_reference_and_primitive_functions`): the set of functions
    that actually write to the Lineage path must equal exactly the two explicitly-named,
    authorized roles (:data:`_AUTHORIZED_LINEAGE_WRITE_FUNCTIONS` --
    ``AUTHORIZED_BARE_GENESIS_CREATE``/``AUTHORIZED_TRANSACTION_APPEND``; recovery
    completion reuses the identical authorized append function rather than writing
    directly, so it needs no third entry), and the single canonical State owner K-002
    already proved must still hold -- Lineage stays owned by the one ``FileStateStore``
    this vertical has, just no longer trusted merely for living inside it
    (``SAME_MODULE_NE_AUTOMATICALLY_AUTHORIZED=true``)."""

    inventory = kernel_topology_inventory()
    return (
        k002_single_canonical_state_owner()
        and set(inventory["lineage_write_functions"]) == _AUTHORIZED_LINEAGE_WRITE_FUNCTIONS
    )
