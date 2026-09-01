"""The typed scalar wrapper set equals what the Difference Identity Contract declares.

``DIFFERENCE_IDENTITY.md`` states the ``expected_value_type`` derivation as one closed
table. A ``{"value_type": ..., "value": ...}`` wrapper appears in it only for the types
JSON's own shape cannot express; everything else derives from the value itself. Including
``STRUCTURED`` in the unwrap set discarded a Target's outer object, so a Fact carrying only
the inner object satisfied the Target and the required Difference was never derived.

This test reads the rule out of the Kernel document rather than restating it, so the code
constant cannot drift from the contract in either direction.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import scripts.difference_contract_validator as validator

from manosube_agent_civilization.difference.projection import (
    TYPED_SCALAR_WRAPPER_TYPES,
    derived_value_type,
    normalize_objective_value,
)

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "00_KERNEL" / "04_DIFFERENCE" / "DIFFERENCE_IDENTITY.md"
_WRAPPER = re.compile(r'\{"value_type":"([A-Z_]+)"')
_COLLECTION = re.compile(r'\{"collection_kind":"([A-Z_]+)"')


def _contract_text() -> str:
    return CONTRACT.read_text(encoding="utf-8")


def test_the_contract_document_is_present_and_states_the_rule() -> None:
    text = _contract_text()
    assert "expected_value_type" in text
    assert "ordinary JSON object → STRUCTURED" in text
    assert "bare JSON array → REJECT" in text


def test_the_wrapper_set_equals_the_contract_in_both_directions() -> None:
    declared = set(_WRAPPER.findall(_contract_text()))
    assert declared, "the contract table declares no typed wrapper"
    assert declared == set(TYPED_SCALAR_WRAPPER_TYPES)


def test_structured_is_not_a_wrapper_type_in_the_contract() -> None:
    """It is reached by *shape* -- an ordinary JSON object -- never by a wrapper."""

    assert "STRUCTURED" not in set(_WRAPPER.findall(_contract_text()))
    assert "STRUCTURED" not in TYPED_SCALAR_WRAPPER_TYPES


def test_collections_use_the_collection_kind_wrapper_not_value_type() -> None:
    text = _contract_text()
    assert set(_COLLECTION.findall(text)) == {"ORDERED_LIST", "UNORDERED_SET"}
    for collection in ("ORDERED_COLLECTION", "UNORDERED_COLLECTION"):
        assert collection not in TYPED_SCALAR_WRAPPER_TYPES


@pytest.mark.parametrize("value_type", sorted(TYPED_SCALAR_WRAPPER_TYPES))
def test_every_declared_wrapper_unwraps_to_its_declared_type(value_type: str) -> None:
    inner = {"kind": "widget", "id": "W-1"} if value_type == "IDENTITY_REFERENCE" else "1"
    value, declared = normalize_objective_value({"value_type": value_type, "value": inner})
    assert declared == value_type
    assert value == inner


def test_an_ordinary_object_is_never_unwrapped() -> None:
    literal = {"value_type": "STRUCTURED", "value": {"a": 1}}
    value, declared = normalize_objective_value(literal)
    assert value == literal
    assert declared == "STRUCTURED"
    assert derived_value_type(literal) == "STRUCTURED"


def test_a_wrapper_shaped_object_with_an_unknown_type_stays_literal() -> None:
    literal = {"value_type": "WIDGET", "value": {"a": 1}}
    assert normalize_objective_value(literal) == (literal, "STRUCTURED")


def test_a_wrapper_with_extra_fields_stays_literal() -> None:
    """The contract permits the exact fields only."""

    literal = {"value_type": "DECIMAL", "value": "1", "unit": "s"}
    assert normalize_objective_value(literal) == (literal, "STRUCTURED")


def test_the_engine_and_the_auditor_normalize_identically() -> None:
    cases = [
        None,
        True,
        7,
        "1",
        {"a": 1},
        {"value_type": "STRUCTURED", "value": {"a": 1}},
        {"value_type": "DECIMAL", "value": "1.5"},
        {"value_type": "TIMESTAMP", "value": "2026-08-30T09:00:00Z"},
        {"value_type": "DURATION", "value": "PT1S"},
        {"value_type": "IDENTITY_REFERENCE", "value": {"kind": "widget", "id": "W-1"}},
        {"collection_kind": "ORDERED_LIST", "members": ["a", "b"]},
        {"collection_kind": "UNORDERED_SET", "members": ["a", "b"]},
        {"value_type": "ORDERED_COLLECTION", "value": ["a"]},
        {"kind": "widget", "id": "HEAD"},
    ]
    for case in cases:
        assert normalize_objective_value(case) == validator._normalize_objective_value(case), case
