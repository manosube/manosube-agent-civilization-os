"""Unschematized carried records still have their references closed.

``01_SCHEMA/change/`` and ``01_SCHEMA/reflow/`` are empty in v0.1, so those two record types
declare no reference locations. Removing shape-based traversal from the schema-backed gate
therefore left them with *no* closure check at all, and a Change naming an absent Difference
passed both the Engine and the auditor.

The chosen policy is recorded in ``graph.UNSCHEMATIZED_REFERENCE_POLICY``: a conservative
structural traversal applies to these types **only**. Inside a record with no schema nothing
can distinguish a reference from a business value, and the safer reading of an ambiguous
``{"kind", "id"}`` field is that it is a reference which must resolve.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import retained_status_predecessor

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.conformance import (
    CARRIED_SECTIONS,
    RECORD_TYPES,
    UNSCHEMATIZED_SECTIONS,
)
from manosube_agent_civilization.difference.graph import (
    UNSCHEMATIZED_REFERENCE_POLICY,
    UNSCHEMATIZED_TYPES,
    reference_closure_errors,
)

ABSENT_DIFFERENCE = {"kind": "difference", "id": "D-" + "0" * 64}


def _with_change(payload: dict[str, Any]) -> dict[str, Any]:
    _, request = retained_status_predecessor("RETAINED")
    request["bindings"][0]["predecessor"]["context"]["changes"] = [payload]
    return request


def test_the_policy_is_recorded_and_measured_from_schema_absence() -> None:
    assert UNSCHEMATIZED_REFERENCE_POLICY == "STRUCTURAL_CLOSURE_REQUIRED"
    assert {
        name for name, canonical in RECORD_TYPES.items() if canonical.schema is None
    } == UNSCHEMATIZED_TYPES
    assert {CARRIED_SECTIONS[section] for section in UNSCHEMATIZED_SECTIONS} == UNSCHEMATIZED_TYPES


def test_the_unschematized_set_is_measured_against_the_repository() -> None:
    """Not asserted: the schema directories really are empty in v0.1."""

    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "01_SCHEMA"
    for directory in ("change", "reflow"):
        assert list((root / directory).glob("*.json")) == []


@pytest.mark.parametrize(
    "reference",
    [
        ABSENT_DIFFERENCE,
        {"kind": "difference_event", "id": "D-EVT-" + "0" * 64},
        {"kind": "observation", "id": "OBS-ABSENT"},
        {"kind": "closure_policy", "id": "CP-ABSENT"},
    ],
    ids=["difference", "event", "observation", "policy"],
)
def test_a_dangling_reference_in_a_change_fails_closed(reference: dict[str, str]) -> None:
    request = _with_change({"change_id": "CHG-0001", "subject_ref": deepcopy(reference)})
    before = deepcopy(request)
    with pytest.raises(DifferenceError, match="does not resolve"):
        derive_differences(request)
    assert request == before


def test_an_unknown_reference_kind_in_a_change_fails_closed() -> None:
    request = _with_change(
        {"change_id": "CHG-0001", "thing": {"kind": "invented_kind", "id": "X-1"}}
    )
    with pytest.raises(DifferenceError, match="unknown reference kind"):
        derive_differences(request)


def test_a_nested_dangling_reference_is_reached() -> None:
    request = _with_change(
        {
            "change_id": "CHG-0001",
            "payload": {"items": [{"inner": deepcopy(ABSENT_DIFFERENCE)}]},
        }
    )
    with pytest.raises(DifferenceError, match="does not resolve"):
        derive_differences(request)


def test_a_resolving_reference_in_a_change_is_accepted() -> None:
    _, seed = retained_status_predecessor("RETAINED")
    difference_id = seed["bindings"][0]["predecessor"]["difference"]["difference_id"]
    request = _with_change(
        {"change_id": "CHG-0001", "subject_ref": {"kind": "difference", "id": difference_id}}
    )
    bundle = derive_differences(request)
    assert bundle["changes"][0]["change_id"] == "CHG-0001"
    assert validate_bundle(bundle) == []


def test_an_external_kind_in_a_change_is_accepted() -> None:
    """An enumerated non-claim resolves to nothing, and is not required to."""

    request = _with_change(
        {
            "change_id": "CHG-0001",
            "evidence_ref": {"kind": "observation_evidence", "id": "EVID-0001"},
        }
    )
    assert derive_differences(request)["changes"]


def test_a_reflow_transaction_is_gated_the_same_way() -> None:
    _, request = retained_status_predecessor("RETAINED")
    request["bindings"][0]["predecessor"]["context"]["reflow_transitions"] = [
        {"transaction_id": "REFLOW-TX-0002", "subject_ref": deepcopy(ABSENT_DIFFERENCE)}
    ]
    with pytest.raises(DifferenceError, match="does not resolve"):
        derive_differences(request)


def test_a_schema_backed_value_is_never_reinterpreted_by_this_gate() -> None:
    """The structural traversal must not leak back onto schema-backed records."""

    probe = {"fact_id": "FACT-PROBE", "value": {"kind": "difference", "id": "D-ABSENT"}}
    assert reference_closure_errors({"normalized_facts": [probe]}) == []
    # The identical payload inside an unschematized record is gated.
    change = {"change_id": "CHG-1", "value": {"kind": "difference", "id": "D-ABSENT"}}
    assert reference_closure_errors({"changes": [change], "differences": []})


def test_a_new_unschematized_section_cannot_bypass_the_gate() -> None:
    """Coverage follows the record-type table, so a new type is gated on arrival."""

    from manosube_agent_civilization.difference.graph import iter_declared_references

    for type_name in UNSCHEMATIZED_TYPES:
        found = list(
            iter_declared_references({"anything": deepcopy(ABSENT_DIFFERENCE)}, type_name)
        )
        assert found and all(edge is None for _path, edge, _value in found), type_name
