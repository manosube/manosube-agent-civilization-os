"""Every carried record type crosses one typed validation boundary.

Three successive reviews found the same shape of defect: a carried record was accepted
because some check happened to cover the field that was forged. These proofs pin the
boundary itself -- the inventory of accepted types, the gate each one passes, and the
non-claims where a type has no reachable canonical validator in this phase.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest

from manosube_agent_civilization.difference.predecessor import (
    BUNDLE_ENVELOPE_SECTIONS,
    CALLER_ASSIGNED_IDENTITY_SECTIONS,
    CARRIED_TYPES,
    LATER_PHASE_SECTIONS,
    NO_CANONICAL_SCHEMA_SECTIONS,
    PREDECESSOR_SECTIONS,
    REQUIRED_PREDECESSOR_SECTIONS,
    validate_carried_records,
)

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
ENGINE_SOURCE = (
    ROOT / "src" / "manosube_agent_civilization" / "difference" / "engine.py"
).read_text(encoding="utf-8")


def _absorbed_sections() -> set[str]:
    """Every context section the Engine actually merges into the returned bundle."""

    body = ENGINE_SOURCE.split("def _absorb_predecessor_context(")[1].split("\ndef ")[0]
    sections = set(re.findall(r'context\.get\("([a-z_]+)"', body))
    # The generic carried-dependency loop merges every section in _CARRIED_SECTIONS.
    sections |= set(
        re.findall(r'^\s+"([a-z_]+)": "[a-z_]+",$', ENGINE_SOURCE.split("_CARRIED_SECTIONS: dict[str, str] = {")[1].split("}")[0], re.M)
    )
    return sections


# --------------------------------------------------------------------------- #
# The inventory is complete and closed.
# --------------------------------------------------------------------------- #


def test_every_absorbed_section_is_a_declared_carried_type() -> None:
    """No section reaches the returned bundle without a place in the typed table."""

    absorbed = _absorbed_sections()
    assert absorbed, "the absorption inventory could not be read"
    missing = absorbed - set(CARRIED_TYPES)
    assert missing == set(), f"absorbed without a typed validator: {sorted(missing)}"


def test_every_declared_carried_type_is_actually_absorbed() -> None:
    """The table describes the Engine, not an aspiration."""

    unused = set(CARRIED_TYPES) - _absorbed_sections()
    assert unused == set(), f"declared but never absorbed: {sorted(unused)}"


def test_an_unknown_predecessor_section_is_rejected() -> None:
    with pytest.raises(Exception, match="unknown sections"):
        validate_carried_records({"smuggled_records": [{"id": "X"}]})


def test_the_bundle_envelope_is_accepted_and_carries_nothing() -> None:
    """Handing a previous bundle back is canonical usage; its outputs are not carried."""

    validate_carried_records({key: [] for key in BUNDLE_ENVELOPE_SECTIONS})
    assert {"differences", "events", "supersession_relations"} <= BUNDLE_ENVELOPE_SECTIONS
    assert not (BUNDLE_ENVELOPE_SECTIONS & set(CARRIED_TYPES))


def test_the_predecessor_itself_accepts_only_three_keys() -> None:
    """The key set is closed in *both* directions, from one declaration.

    Rejecting unknown sections was the only half stated, so ``predecessor["difference"]``
    indexed a section nothing had established was there. Both halves now read the same
    declaration in the boundary's own module rather than a set literal inlined here.
    """

    assert {"difference", "events", "context"} == PREDECESSOR_SECTIONS
    assert {"difference", "events"} == REQUIRED_PREDECESSOR_SECTIONS
    assert REQUIRED_PREDECESSOR_SECTIONS < PREDECESSOR_SECTIONS
    body = ENGINE_SOURCE.split("def _validate_predecessor(")[1].split("\ndef ")[0]
    assert "unknown = set(predecessor) - PREDECESSOR_SECTIONS" in body
    assert "missing = REQUIRED_PREDECESSOR_SECTIONS - set(predecessor)" in body
    assert "validate_carried_records(predecessor.get(\"context\", {}))" in body
    assert "validate_carried_difference(difference)" in body
    assert "validate_carried_event(event, difference" in body


# --------------------------------------------------------------------------- #
# The coverage matrix: what each type is proven to satisfy.
# --------------------------------------------------------------------------- #


def test_every_carried_type_names_a_schema_that_exists() -> None:
    for section, carried in CARRIED_TYPES.items():
        if carried.schema is None:
            assert section in NO_CANONICAL_SCHEMA_SECTIONS
            continue
        relative = carried.base.split("/v0.1/")[1]
        assert (ROOT / "01_SCHEMA" / relative / carried.schema).is_file(), section


def test_the_no_schema_sections_really_have_no_canonical_schema() -> None:
    """The non-claim is measured against the repository, not asserted."""

    assert {"changes", "reflow_transitions"} == NO_CANONICAL_SCHEMA_SECTIONS
    for directory in ("change", "reflow"):
        assert list((ROOT / "01_SCHEMA" / directory).glob("*.schema.json")) == []


def test_every_later_phase_section_is_declared_as_such() -> None:
    """A type whose semantics this phase does not own is named, not silently trusted."""

    assert {
        "evaluations",
        "reopen_condition_evaluations",
        "candidate_completion_records",
        "candidate_claim_evaluation_events",
        "invariant_evaluations",
        "evidence_sufficiency_results",
        "changes",
        "reflow_transitions",
    } == LATER_PHASE_SECTIONS
    assert NO_CANONICAL_SCHEMA_SECTIONS <= LATER_PHASE_SECTIONS


def test_every_upstream_and_difference_type_recomputes_its_identity() -> None:
    """Types this phase owns or consumes have a content-addressed identity authority."""

    with_authority = set(CARRIED_TYPES) - CALLER_ASSIGNED_IDENTITY_SECTIONS
    assert with_authority == {
        "observations",
        "normalized_facts",
        "fact_observation_bindings",
        "fact_evaluations",
        "negative_observations",
        "negative_observation_evaluations",
        "policies",
        "next_observation_requests",
        "observation_methods",
    }
    # Everything without one is either a caller-assigned canonical id or later-phase.
    for section in CALLER_ASSIGNED_IDENTITY_SECTIONS:
        assert section in LATER_PHASE_SECTIONS or section in {
            "observation_scopes",
            "objective_revisions",
        }


def test_the_coverage_matrix_is_exhaustive() -> None:
    """Every declared type has a decided answer for every column of the matrix."""

    for section, carried in CARRIED_TYPES.items():
        assert isinstance(carried.key, str) and carried.key
        assert (carried.schema is None) == (section in NO_CANONICAL_SCHEMA_SECTIONS)
        assert (carried.identity is None) == (section in CALLER_ASSIGNED_IDENTITY_SECTIONS)
        # `later_phase` is a property of the *section*, not of the canonical record type,
        # since the same type can be carried and emitted on different routes.
        assert (section in LATER_PHASE_SECTIONS) == (
            section
            in {
                "evaluations",
                "reopen_condition_evaluations",
                "candidate_completion_records",
                "candidate_claim_evaluation_events",
                "invariant_evaluations",
                "evidence_sufficiency_results",
                "changes",
                "reflow_transitions",
            }
        )


# --------------------------------------------------------------------------- #
# The lifecycle payload authority is shared, not duplicated.
# --------------------------------------------------------------------------- #


def test_one_lifecycle_payload_authority() -> None:
    import scripts.difference_contract_validator as validator

    from manosube_agent_civilization.difference import predecessor
    from manosube_agent_civilization.difference.lifecycle import (
        blocker_payload_errors,
        next_observation_binding_errors,
    )

    assert vars(validator)["blocker_payload_errors"] is blocker_payload_errors
    assert vars(validator)["next_observation_binding_errors"] is next_observation_binding_errors
    assert vars(predecessor)["blocker_payload_errors"] is blocker_payload_errors
    assert vars(predecessor)["next_observation_binding_errors"] is next_observation_binding_errors

    source = (ROOT / "scripts" / "difference_contract_validator.py").read_text(encoding="utf-8")
    # The rules live in the authority; the validator states none of them itself.
    for rule in (
        "blocker boundary mismatch",
        "blocker condition state mismatch",
        "next observation binding mismatch",
        "non-BLOCKED event carries blocker payload",
    ):
        assert rule not in source, rule


def test_the_blocker_condition_states_match_the_canonical_schema() -> None:
    from manosube_agent_civilization.difference.lifecycle import (
        BLOCKER_CONDITION_EXPECTED_STATE,
    )

    schema = json.loads(
        (
            ROOT / "01_SCHEMA" / "difference" / "difference_lifecycle_event.schema.json"
        ).read_text(encoding="utf-8")
    )
    condition = schema["$defs"]["blocker_resolution_condition"]
    assert set(BLOCKER_CONDITION_EXPECTED_STATE) == set(
        condition["properties"]["condition_code"]["enum"]
    )
    assert set(BLOCKER_CONDITION_EXPECTED_STATE.values()) <= set(
        condition["properties"]["expected_state"]["enum"]
    )
