"""The typed reference-edge registry is complete, shared, and crossed exactly once.

Four review rounds closed a record-level escape and found the next one further out. This
suite closes the *inventory*: it proves the edge registry covers every emitted record kind
in both directions, that every reference kind it can meet is either resolvable or an
enumerated non-claim, that the Engine and the independent auditor use the same authority
object rather than two copies, and that no return path can skip the gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import scripts.difference_contract_validator as validator
from tests.difference_helpers import single_binding_request

from manosube_agent_civilization.difference import derive_differences, graph
from manosube_agent_civilization.difference.conformance import (
    EMITTED_SECTIONS,
    RECORD_TYPES,
    merge_records,
)
from manosube_agent_civilization.difference.graph import (
    EXTERNAL_KINDS,
    IDENTITY_EDGES,
    REFERENCE_EDGES,
    RESOLVABLE_KINDS,
    reference_closure_errors,
)

ROOT = Path(__file__).resolve().parents[3]
ENGINE = ROOT / "src" / "manosube_agent_civilization" / "difference" / "engine.py"


def test_the_registry_covers_every_emitted_record_kind_in_both_directions() -> None:
    emitted_kinds = set(EMITTED_SECTIONS.values())
    assert emitted_kinds == set(REFERENCE_EDGES)
    assert emitted_kinds == set(IDENTITY_EDGES)
    # And every emitted kind is a declared canonical record type.
    assert emitted_kinds <= set(RECORD_TYPES)


def test_every_resolvable_kind_names_an_emitted_section() -> None:
    for kind, section in RESOLVABLE_KINDS.items():
        assert section in EMITTED_SECTIONS, kind


def test_every_identity_edge_names_an_emitted_section() -> None:
    for type_name, edges in IDENTITY_EDGES.items():
        for field, section in edges:
            assert section in EMITTED_SECTIONS, f"{type_name}.{field}"


def test_no_reference_kind_is_both_resolvable_and_an_explicit_non_claim() -> None:
    assert not set(RESOLVABLE_KINDS) & EXTERNAL_KINDS


def test_every_declared_edge_kind_is_resolvable_or_an_enumerated_non_claim() -> None:
    for type_name, edges in REFERENCE_EDGES.items():
        for edge in edges:
            unknown = edge.kinds - set(RESOLVABLE_KINDS) - EXTERNAL_KINDS
            assert not unknown, f"{type_name}.{edge.path}: {sorted(unknown)}"


def test_a_resolve_override_never_weakens_a_resolvable_kind() -> None:
    """``resolve`` may only *add* resolution; it can never turn a resolvable kind off."""

    for type_name, edges in REFERENCE_EDGES.items():
        for edge in edges:
            if edge.resolve is False:
                assert not edge.kinds & set(RESOLVABLE_KINDS), f"{type_name}.{edge.path}"
            if edge.resolve:
                for kind in edge.kinds:
                    assert kind in RESOLVABLE_KINDS or kind in graph._FORCED_SECTIONS


def test_the_engine_and_the_auditor_share_one_edge_authority() -> None:
    """Same function object, not a parity claim over two copies."""

    assert vars(validator)["reference_closure_errors"] is reference_closure_errors
    assert vars(graph)["REFERENCE_EDGES"] is REFERENCE_EDGES


def test_the_whole_bundle_gate_is_crossed_exactly_once_on_the_only_return_path() -> None:
    source = ENGINE.read_text(encoding="utf-8")
    body = source.split("def _finalize(")[1].split("\ndef ")[0]
    # One assembly, one gate, one return.
    assert body.count("validate_emitted_bundle(bundle)") == 1
    assert body.count("reference_closure_errors(bundle)") == 1
    assert body.count("relational_errors(bundle)") == 1
    assert body.count("return bundle") == 1
    # The §5 order: schema and identity, then all-record reference closure, then
    # cross-record relational validation -- then, and only then, the return.
    assert (
        body.index("validate_emitted_bundle(bundle)")
        < body.index("reference_closure_errors(bundle)")
        < body.index("relational_errors(bundle)")
        < body.index("return bundle")
    )
    # derive_differences returns only through _finalize, so no partial bundle can escape.
    derivation = source.split("def derive_differences(")[1].split("\ndef ")[0]
    assert derivation.count("return _finalize(") == 1
    assert derivation.count("    return ") == 1


def test_the_engine_holds_no_second_union_and_no_bare_section_assignment() -> None:
    source = ENGINE.read_text(encoding="utf-8")
    assert "merge_records as _merge" in source
    assert "def _merge(" not in source
    assert vars(graph)["reference_closure_errors"] is reference_closure_errors
    assert merge_records.__module__.endswith("difference.conformance")


def test_a_returned_bundle_has_a_closed_reference_graph() -> None:
    assert reference_closure_errors(derive_differences(single_binding_request())) == []


@pytest.mark.parametrize("section", sorted(EMITTED_SECTIONS))
def test_every_emitted_section_is_typed_by_the_registry(section: str) -> None:
    type_name = EMITTED_SECTIONS[section]
    assert type_name in REFERENCE_EDGES
    assert type_name in IDENTITY_EDGES
