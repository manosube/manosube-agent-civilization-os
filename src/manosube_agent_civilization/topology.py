"""Repository-owned static topology inventory for K-001/K-002/K-003/R-001/R-002 (R9-F1,
Phase 7 structural-review round 9; reinforced R10-F2, round 10).

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

R10-F2 (SHUKOU Round 10) sharpens two things this module's Round 9 shape left open:

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
   a second implementation under a different function or class name (e.g. a second
   ``evaluate_closure``-shaped gate engine literally called ``run_closure_gates``, or a
   second Store literally writing through its own bespoke ``open(...).write(...)`` rather
   than a method named ``commit``) would pass every Round 9 check unnoticed. This module now
   also scans the actual installed source for three *content patterns*, entirely independent
   of what any function or class happens to be named:

   - **Identity-field-assignment sites** (:func:`_identity_field_assignment_sites`): every
     ``X["closure_evaluation_id"] = ...``/``X["authority_decision_id"] = ...`` assignment in
     the installed tree -- a real second Closure-Evaluation or Authority-Decision producer
     must mint that same identity field somewhere, regardless of what its own function is
     named.
   - **Direct filesystem write sites** (:func:`_call_sites` against ``atomic_write``,
     excluding ``store/file_store.py`` and ``store/atomic_write.py`` themselves): any other
     module in the tree calling the one raw, atomic write primitive directly is a second,
     unsanctioned write path into the on-disk Store -- ``DIRECT_FILESYSTEM_WRITE_PATH``.
   - **Reflow transition commit sites** (:func:`_call_sites` against ``commit``, excluding
     ``reflow/commit.py`` itself): any other module calling *some* object's ``.commit(...)``
     is a second Reflow transition committer wrapper, regardless of what function or class it
     lives inside -- ``REFLOW_TRANSITION_COMMITTER``.

   K-001's own ``kernel entry-point inventory`` evidence is also widened past
   ``evaluate_closure`` alone: ``EVALUATE_CLOSURE_NE_WHOLE_KERNEL_ENTRYPOINT=true`` --
   ``evaluate_closure`` is this vertical's one Closure-Evaluation-producer (the G1-G22 gate
   engine), never itself the whole composed Kernel entry point a caller actually drives a
   cycle through. That composed entry point is :func:`~manosube_agent_civilization.reflow.
   route.reflow` (``reflow.route.reflow`` obtains the canonical State, resolves base Kernel
   provenance, calls ``evaluate_closure``, mints the lifecycle event and commits the State
   transition -- ``evaluate_closure`` is one stage inside it, not a synonym for it). Nothing
   in the frozen ``00_KERNEL/KERNEL_INVARIANTS.md`` text names one specific function for
   "kernel entry-point inventory", so this is a code-level resolution of an
   otherwise-open contract phrase, not a contract rewrite: K-001's Static half now also
   requires exactly one function named ``reflow`` in the installed package (this module adds
   no ninth Kernel element and no second Kernel dispatcher -- ``reflow.route.reflow`` already
   is, and remains, the sole function this vertical calls to drive a cycle).
"""

from __future__ import annotations

import ast
from functools import lru_cache
import importlib
import inspect
import pkgutil
from typing import Any

_PACKAGE_NAME = "manosube_agent_civilization"

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

#: R10-F2: modules sanctioned to call the raw ``atomic_write`` primitive directly -- the one
#: file that defines it, and the one Store implementation that calls it. Any other module
#: in the installed tree calling it directly is a second, unsanctioned write path.
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


def _module_source_trees() -> list[tuple[str, ast.Module]]:
    """``(module_name, parsed_ast)`` for every installed module whose own source is
    readable -- the shared basis for every content-pattern scan below, so each one parses
    the tree exactly once per :func:`kernel_topology_inventory` call rather than
    independently."""

    trees: list[tuple[str, ast.Module]] = []
    for module in _iter_installed_modules():
        try:
            source = inspect.getsource(module)
        except (OSError, TypeError):
            continue
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


def _identity_field_assignment_sites(field_name: str) -> list[str]:
    """R10-F2: every real source location where some subscripted target is assigned via a
    string-literal key exactly *field_name* (e.g. ``record["closure_evaluation_id"] =
    closure_evaluation_id(record)``) -- found by walking each installed module's own parsed
    source, never by the name of the enclosing function or class. A second producer of this
    identity field shows here even if it is never named ``evaluate_closure``/
    ``evaluate_authority`` (or anything else this module already scans for by name) at all.
    """

    found: list[str] = []
    for module_name, tree in _module_source_trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.slice, ast.Constant)
                    and target.slice.value == field_name
                ):
                    found.append(f"{module_name}:{node.lineno}")
    return sorted(found)


def _call_sites(call_name: str, *, exclude_modules: frozenset[str]) -> list[str]:
    """R10-F2: every call site in the installed package (outside *exclude_modules*) whose
    called function is a bare name or an attribute literally named *call_name* -- e.g.
    ``atomic_write(...)`` or ``store.commit(...)`` -- found by walking each module's own
    parsed source. A second writer or committer shows here regardless of what class, method
    name, or wrapper function it is reached through."""

    found: list[str] = []
    for module_name, tree in _module_source_trees():
        if module_name in exclude_modules:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            else:
                name = None
            if name == call_name:
                found.append(f"{module_name}:{node.lineno}")
    return sorted(found)


@lru_cache(maxsize=1)
def kernel_topology_inventory() -> dict[str, list[str]]:
    """Return the real, reproducible inventory this module's own docstring names -- every
    ``evaluate_closure`` (Closure-Evaluation producer), every ``reflow`` function under
    ``reflow.route`` (the real composed Kernel entry point, R10-F2), every concrete class
    implementing the full canonical-State surface (``commit``/``load_current``/
    ``reconstruct``/``resolve_record`` -- write path, reconstruction source and persistence
    owner together), every ``evaluate_authority`` (Authority owner), every ``commit_reflow``
    (Reflow transition owner), and (R10-F2) every name-independent identity-field-assignment
    or write/commit call site actually found in the installed package. Exactly one of each
    named role, and zero of each unsanctioned call-site list, is this vertical's own claim;
    anything else is a real, reproducible violation, not a proxy for one.
    """

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
        "direct_filesystem_write_sites": _call_sites(
            "atomic_write", exclude_modules=_SANCTIONED_DIRECT_WRITE_MODULES
        ),
        "reflow_transition_commit_sites": _call_sites(
            "commit", exclude_modules=_SANCTIONED_COMMIT_CALL_MODULES
        ),
    }


def k001_single_kernel_entry_point() -> bool:
    """K-001 EXACTLY_ONE_CANONICAL_KERNEL, its Static half: exactly one ``evaluate_closure``
    (the Closure-Evaluation-producer stage) *and* exactly one ``reflow`` function under
    ``reflow.route`` (the real composed Kernel entry point, R10-F2) *and* exactly one
    real content-addressed-identity-field-assignment site for ``closure_evaluation_id`` --
    proof, by both name and by what the code actually does, that only one Kernel
    implementation exists in the tree, not merely the one this call happened to import."""

    inventory = kernel_topology_inventory()
    return (
        len(inventory["closure_producers"]) == 1
        and len(inventory["kernel_entry_points"]) == 1
        and len(inventory["closure_evaluation_identity_sites"]) == 1
    )


def k002_single_canonical_state_owner() -> bool:
    """K-002 (State ownership), its Static half: exactly one concrete class in the installed
    package implements the full canonical-State surface, *and* (R10-F2) no other module
    calls the raw ``atomic_write`` primitive directly -- no parallel State owner, named or
    unnamed, exists to consult or write through instead."""

    inventory = kernel_topology_inventory()
    return len(inventory["state_stores"]) == 1 and not inventory["direct_filesystem_write_sites"]


def k003_single_authority_and_transition_owner() -> bool:
    """K-003 (Authority/transition/persistence ownership, absence of parallel canonical
    authority): exactly one ``evaluate_authority`` Authority producer, exactly one real
    ``authority_decision_id``-assignment site (R10-F2), exactly one ``commit_reflow`` Reflow
    transition committer with no other module calling any object's ``.commit(...)`` (R10-F2),
    and the same single canonical State owner K-002 already proved -- no second, competing
    canonical authority for any of the three roles this Invariant names, by name or by what
    the code actually does."""

    inventory = kernel_topology_inventory()
    return (
        len(inventory["authority_producers"]) == 1
        and len(inventory["authority_decision_identity_sites"]) == 1
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
    """R-002 LINEAGE_APPEND_ONLY, its Static half: identical to R-001 -- the single canonical
    State owner is also the sole lineage-append path (``reconstruct``, the same method
    K-002's own inventory already required that owner to implement), with no second,
    unsanctioned direct write path into it."""

    return r001_single_atomic_committer()
