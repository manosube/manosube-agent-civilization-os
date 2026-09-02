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
    """An unpermitted kind at a declared location cannot enter."""

    bundle = derive_differences(_request())
    mutated = deepcopy(bundle)
    mutated["differences"][0]["observation_evidence_refs"][0] = {
        "kind": "invented_kind",
        "id": "X-0001",
    }
    errors = reference_closure_errors(mutated)
    assert any("reference kind is not permitted here" in error for error in errors), errors


def test_an_ambiguous_reference_target_fails_closed() -> None:
    """Two records under one identity make the reference resolve to neither."""

    bundle = derive_differences(_request())
    mutated = deepcopy(bundle)
    duplicate = deepcopy(mutated["observations"][0])
    duplicate["project_id"] = "PRJ-OTHER"
    mutated["observations"].append(duplicate)
    errors = reference_closure_errors(mutated)
    assert any("ambiguous" in error for error in errors), errors


def _set_path(record: dict[str, Any], path: str, value: Any) -> None:
    """Write *value* at a registry locator, creating the intermediate containers."""

    segments = path.split(".")
    node: Any = record
    for position, segment in enumerate(segments):
        expand = segment.endswith("[]")
        key = segment[:-2] if expand else segment
        last = position == len(segments) - 1
        if last and not expand:
            node[key] = value
            return
        if last and expand:
            node[key] = [value]
            return
        if expand:
            node.setdefault(key, [{}])
            if not node[key]:
                node[key] = [{}]
            node = node[key][0]
        else:
            node = node.setdefault(key, {})


#: Every declared reference edge that can resolve, with the resolvable kind it carries.
_RESOLVING_EDGES = sorted(
    (type_name, edge.path, kind)
    for type_name, edges in REFERENCE_EDGES.items()
    for edge in edges
    for kind in edge.kinds
    if kind in RESOLVABLE_KINDS
)


def test_the_edge_matrix_is_not_vacuous() -> None:
    assert len(_RESOLVING_EDGES) >= 40
    assert len({kind for _, _, kind in _RESOLVING_EDGES}) == len(RESOLVABLE_KINDS)


@pytest.mark.parametrize(
    ("type_name", "path", "kind"),
    _RESOLVING_EDGES,
    ids=[f"{t}.{p}->{k}" for t, p, k in _RESOLVING_EDGES],
)
def test_every_resolving_edge_is_rejected_when_its_target_is_absent(
    type_name: str, path: str, kind: str
) -> None:
    """One dangling-edge mutation per declared edge that can resolve, per kind."""

    from manosube_agent_civilization.difference.conformance import (
        EMITTED_SECTIONS,
        RECORD_TYPES,
    )

    holder = next(name for name, item in EMITTED_SECTIONS.items() if item == type_name)
    key = RECORD_TYPES[type_name].key
    probe: dict[str, Any] = {key: "PROBE-IDENTITY"}
    _set_path(probe, path, {"kind": kind, "id": "ABSENT" + _ABSENT})
    bundle: dict[str, Any] = {RESOLVABLE_KINDS[kind]: []}
    bundle[holder] = [probe]
    errors = reference_closure_errors(bundle)
    assert any(
        "does not resolve" in error and "ABSENT" in error for error in errors
    ), (type_name, path, kind, errors)


@pytest.mark.parametrize(
    ("type_name", "path", "kind"),
    _RESOLVING_EDGES,
    ids=[f"{t}.{p}->{k}" for t, p, k in _RESOLVING_EDGES],
)
def test_every_resolving_edge_rejects_a_reference_of_the_wrong_kind(
    type_name: str, path: str, kind: str
) -> None:
    """A well-formed reference of an unpermitted kind fails closed at every edge."""

    from manosube_agent_civilization.difference.conformance import (
        EMITTED_SECTIONS,
        RECORD_TYPES,
    )
    from manosube_agent_civilization.difference.graph import REFERENCE_EDGES as EDGES

    edge = next(item for item in EDGES[type_name] if item.path == path)
    wrong = next(
        candidate
        for candidate in sorted(RESOLVABLE_KINDS)
        if candidate not in edge.kinds
    )
    holder = next(name for name, item in EMITTED_SECTIONS.items() if item == type_name)
    key = RECORD_TYPES[type_name].key
    probe: dict[str, Any] = {key: "PROBE-IDENTITY"}
    _set_path(probe, path, {"kind": wrong, "id": "WRONG-KIND"})
    bundle: dict[str, Any] = {holder: [probe]}
    errors = reference_closure_errors(bundle)
    assert any("reference kind is not permitted here" in error for error in errors), (
        type_name,
        path,
        errors,
    )


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
