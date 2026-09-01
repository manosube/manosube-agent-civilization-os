"""Mutation coverage for every reference edge kind in the emitted graph.

A carried record used to be admitted on its schema and its identity alone: a schema-valid
Closure Evaluation naming an absent Difference was merged straight into the returned
bundle, because reference resolution only ever looked at the retained Difference and its
events. Every record of every section now crosses the same closure gate, and this suite
mutates each *kind* of edge -- reference-shaped and bare foreign key alike -- rather than
one named field at a time.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import negative_claim, retained_status_predecessor

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.graph import (
    EXTERNAL_KINDS,
    IDENTITY_EDGES,
    REFERENCE_EDGES,
    RESOLVABLE_KINDS,
    reference_closure_errors,
)

_ABSENT = "-ABSENT-0000"


def _request() -> dict[str, Any]:
    _, request = retained_status_predecessor(
        "BLOCKED", negative_claims=[negative_claim("NO_RESULT")], facts=[]
    )
    return request


def _context(request: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = request["bindings"][0]["predecessor"]["context"]
    return context


def test_the_gate_accepts_the_unmutated_lineage() -> None:
    bundle = derive_differences(_request())
    assert reference_closure_errors(bundle) == []
    assert validate_bundle(bundle) == []


def test_a_carried_record_whose_foreign_key_names_no_record_fails_closed() -> None:
    """The reviewed defect: an extra Closure Evaluation naming an absent Difference."""

    request = _request()
    context = _context(request)
    extra = deepcopy(context["evaluations"][0])
    extra["closure_evaluation_id"] = "D-CLOSE-EVAL-" + "B" * 64
    extra["difference_id"] = "D-" + "0" * 64
    context["evaluations"].append(extra)
    before = deepcopy(request)
    with pytest.raises(DifferenceError, match="foreign key does not resolve"):
        derive_differences(request)
    assert request == before


def test_a_carried_record_whose_reference_names_no_record_fails_closed() -> None:
    request = _request()
    context = _context(request)
    extra = deepcopy(context["evaluations"][0])
    extra["closure_evaluation_id"] = "D-CLOSE-EVAL-" + "C" * 64
    extra["policy_ref"] = {
        **deepcopy(extra["policy_ref"]),
        "id": "CP-" + "0" * 64,
    }
    context["evaluations"].append(extra)
    with pytest.raises(DifferenceError, match="reference does not resolve"):
        derive_differences(request)


def test_a_reference_of_the_wrong_kind_fails_closed() -> None:
    request = _request()
    context = _context(request)
    observation = context["observations"][0]
    observation["scope_ref"] = {
        "kind": "observation",
        "id": observation["scope_ref"]["id"],
    }
    with pytest.raises(DifferenceError):
        derive_differences(request)


def test_an_undeclared_reference_kind_fails_closed() -> None:
    """A kind that is neither resolvable nor an enumerated non-claim cannot enter."""

    bundle = derive_differences(_request())
    mutated = deepcopy(bundle)
    mutated["differences"][0]["observation_evidence_refs"][0] = {
        "kind": "invented_kind",
        "id": "X-0001",
    }
    errors = reference_closure_errors(mutated)
    assert any("unknown reference kind" in error for error in errors), errors


def test_an_ambiguous_reference_target_fails_closed() -> None:
    """Two records under one identity make the reference resolve to neither."""

    bundle = derive_differences(_request())
    mutated = deepcopy(bundle)
    duplicate = deepcopy(mutated["observations"][0])
    duplicate["project_id"] = "PRJ-OTHER"
    mutated["observations"].append(duplicate)
    errors = reference_closure_errors(mutated)
    assert any("ambiguous" in error for error in errors), errors


@pytest.mark.parametrize("kind", sorted(RESOLVABLE_KINDS))
def test_every_resolvable_kind_is_rejected_when_its_target_is_absent(kind: str) -> None:
    """One dangling-edge mutation per resolvable reference kind."""

    section = RESOLVABLE_KINDS[kind]
    bundle = {section: [], "differences": [
        {"difference_id": "D-" + "1" * 64},
    ]} if section != "differences" else {"differences": []}
    probe = {
        "observations": [
            {
                "observation_id": "OBS-PROBE",
                "scope_ref": {"kind": kind, "id": "ABSENT" + _ABSENT},
            }
        ]
    }
    merged: dict[str, Any] = {**bundle, **probe}
    errors = reference_closure_errors(merged)
    assert any(
        "does not resolve" in error and "ABSENT" in error for error in errors
    ), (kind, errors)


@pytest.mark.parametrize(
    ("type_name", "field", "section"),
    sorted(
        (type_name, field, section)
        for type_name, edges in IDENTITY_EDGES.items()
        for field, section in edges
    ),
)
def test_every_declared_foreign_key_is_rejected_when_its_target_is_absent(
    type_name: str, field: str, section: str
) -> None:
    """One dangling-key mutation per declared bare foreign key."""

    from manosube_agent_civilization.difference.conformance import (
        EMITTED_SECTIONS,
        RECORD_TYPES,
    )

    holder = next(
        name for name, kind in EMITTED_SECTIONS.items() if kind == type_name
    )
    key = RECORD_TYPES[type_name].key
    bundle: dict[str, Any] = {section: []}
    # A self-referential section (an append-only chain naming its own predecessor) holds
    # the probe itself, so the target section must not be emptied after it is placed.
    bundle[holder] = [{key: "PROBE-IDENTITY", field: "ABSENT" + _ABSENT}]
    errors = reference_closure_errors(bundle)
    assert any(
        "foreign key does not resolve" in error and "ABSENT" in error for error in errors
    ), (type_name, field, errors)


def test_every_permitted_kind_of_every_edge_is_declared_somewhere() -> None:
    """No edge can name a kind the closure gate has no decision for."""

    for type_name, edges in REFERENCE_EDGES.items():
        for edge in edges:
            for kind in edge.kinds:
                assert kind in RESOLVABLE_KINDS or kind in EXTERNAL_KINDS, (
                    f"{type_name}.{edge.path}: {kind}"
                )
