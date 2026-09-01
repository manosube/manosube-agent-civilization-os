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
from tests.difference_helpers import negative_claim, retained_status_predecessor

from manosube_agent_civilization.difference import DifferenceError, derive_differences
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
