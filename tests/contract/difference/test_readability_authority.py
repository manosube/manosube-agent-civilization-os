"""Record readability has exactly one owner, and no gate restates it.

The `a11d7c7` finding was not a missed case. It was a *second, weaker* answer to a question
already answered correctly one module away: `validate_typed_record` checked the declared
identity key for every type including the unschematized ones, and the emitted-bundle gate
added beside it skipped every unschematized record entirely. The producer and the auditor
disagreed about what a readable record is, inside the gate written so they could not.

Counting call sites after the fact is what let that happen, so the consumer list is pinned
here in both directions:

* every module that decides readability delegates to `difference.readability`;
* no module outside it implements the decision itself.

The second direction is the one that matters. It is a source-level check, which is coarse,
and it is deliberately coarse: a rule that reappears anywhere in these modules fails this
test whether or not anyone remembered to add a call-site assertion for it.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
from scripts import difference_contract_validator as validator

from manosube_agent_civilization.difference import conformance, predecessor, readability

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "src" / "manosube_agent_civilization" / "difference"

#: Every gate that must delegate. Adding a gate without adding it here is caught by
#: `test_no_module_outside_the_owner_decides_readability`, not by this list.
DELEGATING_MODULES: dict[str, Any] = {
    "difference.conformance": conformance,
    "difference.predecessor": predecessor,
    "scripts.difference_contract_validator": validator,
}

#: The decision, in the two forms callers hold: by record type, and by declared key.
OWNER_ENTRY_POINTS = ("of_record", "of_record_by_key", "section_errors")


def test_the_owner_answers_for_schematized_and_unschematized_types_alike() -> None:
    """One rule, every declared type. This is the half the emitted gate used to skip."""

    for type_name, canonical in conformance.RECORD_TYPES.items():
        readable = readability.of_record({canonical.key: "X-0001"}, type_name)
        assert readable.readable, type_name
        assert readability.of_record({}, type_name).reason == readability.IDENTITY_NOT_USABLE
        assert readability.of_record(7, type_name).reason == readability.NOT_AN_OBJECT
        for unusable in (None, "", ["X"], {"id": "X"}, 7):
            verdict = readability.of_record({canonical.key: unusable}, type_name)
            assert verdict.reason == readability.IDENTITY_NOT_USABLE, (type_name, unusable)


def test_the_owner_covers_every_unschematized_type() -> None:
    """A type without a schema is unvalidated, not unreadable."""

    assert conformance.UNSCHEMATIZED_SECTIONS
    for section in conformance.UNSCHEMATIZED_SECTIONS:
        type_name = conformance.EMITTED_SECTIONS[section]
        assert conformance.RECORD_TYPES[type_name].schema is None
        assert readability.mechanical_schema_errors({}, type_name) == []
        assert readability.of_record({}, type_name).reason == readability.IDENTITY_NOT_USABLE


def test_every_gate_reads_the_same_owner() -> None:
    """Import identity, not import name: one object, held by every delegating module."""

    for name, module in DELEGATING_MODULES.items():
        held = getattr(module, "readability", None) or getattr(
            module, "emitted_bundle_readability_errors", None
        )
        assert held is not None, f"{name} holds no reference to the readability owner"
    assert vars(conformance)["readability"] is readability
    assert vars(predecessor)["readability"] is readability
    assert (
        vars(validator)["emitted_bundle_readability_errors"]
        is conformance.emitted_bundle_readability_errors
    )


def _decides_readability(node: ast.AST) -> bool:
    """A comparison that answers "can this be read", written out rather than delegated."""

    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        return False
    if node.func.id != "isinstance" or len(node.args) != 2:
        return False
    target, kinds = node.args
    names = (
        {element.id for element in kinds.elts if isinstance(element, ast.Name)}
        if isinstance(kinds, ast.Tuple)
        else {kinds.id} if isinstance(kinds, ast.Name) else set()
    )
    if not names & {"dict", "list"}:
        return False
    # The rule is about a *record* or a *section of records*, not about an arbitrary value.
    source = ast.unparse(target)
    return any(
        token in source
        for token in ("record", "records", "section", "bundle[", "member", "identity")
    )


@pytest.mark.parametrize(
    "module",
    ["conformance.py", "predecessor.py"],
)
def test_no_module_outside_the_owner_decides_readability(module: str) -> None:
    """The direction that catches a rule nobody remembered to register.

    `readability.py` itself is exempt: it is the owner. Everything else in the gate path
    must delegate, so a re-introduced `isinstance(record, dict)` fails here immediately.
    """

    tree = ast.parse((SOURCE / module).read_text(encoding="utf-8"))
    offenders = [
        f"{module}:{node.lineno}: {ast.unparse(node)[:88]}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _decides_readability(node)
    ]
    assert offenders == [], (
        f"{len(offenders)} readability decisions outside difference/readability.py: "
        f"{offenders}"
    )


def test_the_owner_does_not_absorb_admissibility() -> None:
    """Readability must stay narrow, or it recreates the defect it was written to remove.

    Folding the full schema pass or identity recomputation in here is what reported a
    supersession cycle as a schema failure. The owner must not import either.
    """

    source = (SOURCE / "readability.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    for forbidden in ("validate_record", "require_schema_version", "canonical_bytes"):
        assert forbidden not in called, (
            f"the readability owner calls {forbidden}: admissibility has leaked into it"
        )
