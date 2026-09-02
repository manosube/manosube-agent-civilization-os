"""An Objective revision is individually valid; a history is not individually anything.

Revision numbering, the immediate-predecessor binding and the base fingerprint are relations
between records, so every revision of a discontinuous Human Objective history passes its own
schema and the history is still broken. The independent validator already computed this
condition — and spent it only on deciding whether to *trust* an Objective head, never
reporting it. So the discontinuity did not fail; it silently changed what other rules
concluded, and what surfaced was an unrelated evaluation head mismatch.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
import scripts.difference_contract_validator as validator_module
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import (
    negative_claim,
    objective_revision,
    retained_status_predecessor,
)

from manosube_agent_civilization.difference import DifferenceError, derive_differences
from manosube_agent_civilization.difference.graph import (
    EXTERNAL_KINDS,
    REFERENCE_EDGES,
    RESOLVABLE_KINDS,
)
from manosube_agent_civilization.difference.identity import objective_semantic_fingerprint
from manosube_agent_civilization.difference.objective import objective_chain_errors


def _successor(base: dict[str, Any]) -> dict[str, Any]:
    """A well-formed revision 1 over *base*: numbering, binding and base digest all sound."""

    head = deepcopy(base)
    head["objective_revision_id"] = "OBJ-REV-0002"
    head["revision"] = base["revision"] + 1
    head["previous_objective_ref"] = {
        "kind": "objective_revision", "id": base["objective_revision_id"]
    }
    head["status"] = "SUPERSEDED"
    head["change_reason"] = "second revision"
    head["semantic_change_summary"] = "refined"
    head["base_semantic_fingerprint"] = {
        "profile": "MANOSUBE-STATE-SHA256-0.1",
        "digest": objective_semantic_fingerprint(base).removeprefix("sha256:"),
    }
    return head


def _request(mutate: Any = None) -> dict[str, Any]:
    _, request = retained_status_predecessor(
        "BLOCKED",
        "BLOCKER_REOBSERVATION",
        negative_claims=[negative_claim("NO_RESULT")],
        facts=[],
    )
    context = request["bindings"][0]["predecessor"]["context"]
    base = deepcopy(context["objective_revisions"][0])
    head = _successor(base)
    if mutate is not None:
        mutate(head, base)
    context["objective_revisions"].append(head)
    return request


def test_the_continuous_chain_is_accepted() -> None:
    """The control: two revisions, sound history, both emitted and cross-record valid."""

    bundle = derive_differences(_request())
    assert [
        (revision["objective_revision_id"], revision["revision"])
        for revision in bundle["objective_revisions"]
    ] == [("OBJ-REV-0001", 0), ("OBJ-REV-0002", 1)]
    assert validate_bundle(bundle) == []


def test_a_forged_base_fingerprint_fails_closed() -> None:
    def mutate(head: dict[str, Any], _base: dict[str, Any]) -> None:
        head["base_semantic_fingerprint"] = {
            "profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64
        }

    with pytest.raises(
        DifferenceError, match="Objective base fingerprint does not match its predecessor"
    ):
        derive_differences(_request(mutate))


def test_a_null_base_fingerprint_past_revision_zero_fails_closed() -> None:
    def mutate(head: dict[str, Any], _base: dict[str, Any]) -> None:
        head["base_semantic_fingerprint"] = None

    with pytest.raises(
        DifferenceError, match="Objective base fingerprint does not match its predecessor"
    ):
        derive_differences(_request(mutate))


def test_discontinuous_numbering_fails_closed() -> None:
    def mutate(head: dict[str, Any], _base: dict[str, Any]) -> None:
        head["revision"] = 2

    with pytest.raises(DifferenceError, match="Objective revision numbering is discontinuous"):
        derive_differences(_request(mutate))


def test_a_predecessor_binding_that_skips_a_revision_fails_closed() -> None:
    """The reference still resolves; what it names is not the immediate predecessor."""

    def mutate(head: dict[str, Any], base: dict[str, Any]) -> None:
        head["previous_objective_ref"] = {
            "kind": "objective_revision", "id": head["objective_revision_id"]
        }
        head["base_semantic_fingerprint"] = {
            "profile": "MANOSUBE-STATE-SHA256-0.1",
            "digest": objective_semantic_fingerprint(base).removeprefix("sha256:"),
        }

    with pytest.raises(
        DifferenceError, match="does not bind its immediate predecessor"
    ):
        derive_differences(_request(mutate))


# --------------------------------------------------------------------------- #
# A reference is typed: the id alone is not the binding
# --------------------------------------------------------------------------- #


def test_a_predecessor_of_the_wrong_kind_fails_closed() -> None:
    """A schema-valid reference at the wrong kind, carrying the right id.

    Reading the ``id`` and discarding the ``kind`` accepted a well-formed pointer at
    something else that happens to share an identifier. ``objective`` was permitted on this
    edge *and* is an external kind, so reference closure passed too without ever
    establishing a revision edge.
    """

    def mutate(head: dict[str, Any], base: dict[str, Any]) -> None:
        head["previous_objective_ref"] = {
            "kind": "objective", "id": base["objective_revision_id"]
        }

    with pytest.raises(DifferenceError, match="previous_objective_ref"):
        derive_differences(_request(mutate))


def test_the_edge_permits_only_the_revision_kind() -> None:
    """The structural half: closure now requires an actual objective_revision edge."""

    edges = {edge.path: edge for edge in REFERENCE_EDGES["objective_revision"]}
    assert edges["previous_objective_ref"].kinds == {"objective_revision"}
    assert "objective_revision" in RESOLVABLE_KINDS


def test_objective_stays_an_external_kind() -> None:
    """Removing the edge does not remove the kind: it has a second consumer.

    ``EXTERNAL_KINDS`` also governs the structural traversal of unschematized Change and
    Reflow records, where a reference to an Objective is legitimate provenance this phase
    does not own. Narrowing the set would reject that.
    """

    assert "objective" in EXTERNAL_KINDS
    assert "objective" not in RESOLVABLE_KINDS


def _chain(head_mutation: Any = None) -> dict[str, dict[str, Any]]:
    base = objective_revision()
    head = _successor(base)
    if head_mutation is not None:
        head_mutation(head, base)
    return {
        base["objective_revision_id"]: base,
        head["objective_revision_id"]: head,
    }


def test_the_owner_accepts_the_sound_chain() -> None:
    """So the rejections below are the kind check, not the fixture."""

    errors, intact = objective_chain_errors(_chain())
    assert errors == []
    assert intact == {"OBJ-0001"}


@pytest.mark.parametrize("kind", ["objective", "difference", "state", "human_authority"])
def test_the_owner_rejects_every_wrong_kind_on_its_own(kind: str) -> None:
    """The rule does not lean on the edge registry to hold: it checks the kind itself."""

    def mutate(head: dict[str, Any], base: dict[str, Any]) -> None:
        head["previous_objective_ref"] = {
            "kind": kind, "id": base["objective_revision_id"]
        }

    errors, intact = objective_chain_errors(_chain(mutate))
    assert any("does not bind its immediate predecessor" in error for error in errors)
    assert intact == set()


def test_revision_zero_may_not_declare_a_predecessor() -> None:
    chain = _chain()
    chain["OBJ-REV-0001"]["previous_objective_ref"] = {
        "kind": "objective_revision", "id": "OBJ-REV-0002"
    }
    errors, intact = objective_chain_errors(chain)
    assert any("revision zero declares a predecessor" in error for error in errors)
    assert intact == set()


def test_an_incomplete_predecessor_is_reported_not_raised() -> None:
    """Total: the auditor runs this over records it has not yet proven schema-valid."""

    chain = _chain()
    del chain["OBJ-REV-0001"]["target_predicates"]
    errors, intact = objective_chain_errors(chain)
    assert any("not complete enough to recompute" in error for error in errors)
    assert intact == set()


# --------------------------------------------------------------------------- #
# The rule is reported, not merely spent on trust
# --------------------------------------------------------------------------- #


def test_the_auditor_reports_the_chain_rather_than_a_consequence() -> None:
    """Before this round the same bundle produced an unrelated head mismatch instead."""

    request = _request(
        lambda head, _base: head.__setitem__(
            "base_semantic_fingerprint",
            {"profile": "MANOSUBE-STATE-SHA256-0.1", "digest": "0" * 64},
        )
    )
    context = request["bindings"][0]["predecessor"]["context"]
    base = deepcopy(context["objective_revisions"][0])
    forged = deepcopy(context["objective_revisions"][1])
    errors, intact = objective_chain_errors(
        {
            base["objective_revision_id"]: base,
            forged["objective_revision_id"]: forged,
        }
    )
    assert errors == [
        "Objective base fingerprint does not match its predecessor: OBJ-0001.OBJ-REV-0002"
    ]
    assert intact == set()


def test_the_auditor_holds_no_chain_rule_of_its_own() -> None:
    assert vars(validator_module)["objective_chain_errors"] is objective_chain_errors


def test_an_intact_chain_is_still_trusted_for_the_active_head() -> None:
    """The boolean the validator used to compute is returned by the same reading."""

    request = _request()
    context = request["bindings"][0]["predecessor"]["context"]
    revisions = {
        revision["objective_revision_id"]: revision
        for revision in context["objective_revisions"]
    }
    errors, intact = objective_chain_errors(revisions)
    assert errors == []
    assert intact == {"OBJ-0001"}
