"""The reference-edge registry equals what the canonical schemas declare.

Reference completeness used to come from a shape heuristic: any nested object carrying
string ``kind`` and ``id`` was treated as a graph edge. That is unsound, because
``IDENTITY_REFERENCE`` is a declared canonical value type -- a schema-valid Fact value can
*be* ``{"kind": "widget", "id": "abc"}`` -- so legitimate domain payload was rejected as an
unresolvable reference.

Completeness now comes from this comparison instead: ``tests/schema_reference_paths.py``
derives every identity-bearing reference location from ``01_SCHEMA``, and the registry must
equal it, modulo two reviewed and documented lists.
"""

from __future__ import annotations

from typing import Any

import pytest
from tests.schema_reference_paths import reference_paths

from manosube_agent_civilization.difference.conformance import (
    EMITTED_SECTIONS,
    RECORD_TYPES,
)
from manosube_agent_civilization.difference.graph import (
    EXCLUDED_REFERENCE_SUBTREES,
    EXTERNAL_KINDS,
    NON_IDENTITY_POINTERS,
    REFERENCE_EDGES,
    RESOLVABLE_KINDS,
    reference_closure_errors,
)

SCHEMA_BACKED = sorted(
    type_name
    for type_name in set(EMITTED_SECTIONS.values())
    if RECORD_TYPES[type_name].schema is not None
)


def _declared_inventory(type_name: str) -> set[str]:
    canonical = RECORD_TYPES[type_name]
    base = canonical.base.rstrip("/").rsplit("/", 1)[-1]
    assert canonical.schema is not None
    paths = reference_paths(base, canonical.schema)
    excluded = EXCLUDED_REFERENCE_SUBTREES.get(type_name, ())
    return {
        path
        for path in paths
        if not any(
            path == prefix or path.startswith((f"{prefix}.", f"{prefix}["))
            for prefix in excluded
        )
    }


def test_the_inventory_is_not_vacuous() -> None:
    """The schemas really do declare references, so the comparison below has content."""

    total = sum(len(_declared_inventory(type_name)) for type_name in SCHEMA_BACKED)
    assert total >= 60


@pytest.mark.parametrize("type_name", SCHEMA_BACKED)
def test_every_schema_declared_reference_location_is_in_the_registry(type_name: str) -> None:
    missing = sorted(_declared_inventory(type_name) - {e.path for e in REFERENCE_EDGES[type_name]})
    assert not missing, missing


@pytest.mark.parametrize("type_name", SCHEMA_BACKED)
def test_the_registry_declares_no_location_the_schemas_do_not(type_name: str) -> None:
    declared = {edge.path for edge in REFERENCE_EDGES[type_name]}
    pointers = set(NON_IDENTITY_POINTERS.get(type_name, ()))
    extra = sorted(declared - _declared_inventory(type_name) - pointers)
    assert not extra, extra


def test_a_type_with_no_canonical_schema_declares_no_edge() -> None:
    """Change and Reflow have no schema in v0.1, so no edge can be declared for them."""

    for type_name, canonical in RECORD_TYPES.items():
        if canonical.schema is None and type_name in REFERENCE_EDGES:
            assert REFERENCE_EDGES[type_name] == ()


def test_every_non_identity_pointer_can_never_resolve() -> None:
    """A pointer without an identity adds no resolution obligation, only a kind."""

    for type_name, paths in NON_IDENTITY_POINTERS.items():
        for path in paths:
            edge = next(
                (item for item in REFERENCE_EDGES[type_name] if item.path == path), None
            )
            assert edge is not None, f"{type_name}.{path}"
            assert edge.kinds <= EXTERNAL_KINDS, f"{type_name}.{path}: {sorted(edge.kinds)}"


def test_every_excluded_subtree_is_a_real_schema_location() -> None:
    """An exclusion must name something the schemas actually declare, or it is dead text."""

    for type_name, prefixes in EXCLUDED_REFERENCE_SUBTREES.items():
        canonical = RECORD_TYPES[type_name]
        assert canonical.schema is not None
        base = canonical.base.rstrip("/").rsplit("/", 1)[-1]
        found = reference_paths(base, canonical.schema)
        for prefix in prefixes:
            assert any(
                path == prefix or path.startswith((f"{prefix}.", f"{prefix}["))
                for path in found
            ), f"{type_name}: {prefix}"


def test_every_resolvable_kind_is_reachable_from_a_declared_edge() -> None:
    """A resolvable kind no edge can carry would be an obligation nothing bears."""

    carried = {
        kind
        for edges in REFERENCE_EDGES.values()
        for edge in edges
        for kind in edge.kinds
    }
    assert set(RESOLVABLE_KINDS) <= carried


def test_the_gate_reads_no_field_it_did_not_declare() -> None:
    """A reference-shaped canonical *value* is payload, and is never traversed."""

    probe: dict[str, Any] = {
        "fact_id": "FACT-PROBE",
        # IDENTITY_REFERENCE is a declared canonical value type, so this is legal payload.
        "value": {"kind": "widget", "id": "abc"},
    }
    assert reference_closure_errors({"normalized_facts": [probe]}) == []
    registered_lookalike = {
        "fact_id": "FACT-PROBE",
        "value": {"kind": "difference", "id": "D-" + "0" * 64},
    }
    assert reference_closure_errors({"normalized_facts": [registered_lookalike]}) == []
    nested = {
        "fact_id": "FACT-PROBE",
        "value": {
            "collection_kind": "ORDERED_LIST",
            "members": [{"kind": "observation", "id": "OBS-ABSENT"}],
        },
    }
    assert reference_closure_errors({"normalized_facts": [nested]}) == []


def test_shape_based_reference_detection_is_gone() -> None:
    """The heuristic that misread canonical values as edges must not come back."""

    from pathlib import Path

    from manosube_agent_civilization.difference import graph

    source = Path(graph.__file__).read_text(encoding="utf-8")
    assert "_is_reference" not in source
    assert "_structural_errors" not in source
    # Traversal reads declared locators only.
    body = source.split("def reference_closure_errors(")[1].split("\ndef ")[0]
    assert "REFERENCE_EDGES[type_name]" in body
    assert "IDENTITY_EDGES[type_name]" in body
