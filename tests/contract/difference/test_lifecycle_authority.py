"""The executable lifecycle table is the contract's table, and there is only one.

``LEGAL_TRANSITIONS`` lives in ``manosube_agent_civilization.difference.lifecycle`` and is
imported by the independent cross-record validator, so no second table exists. These
proofs pin it to the transition table in ``00_KERNEL/04_DIFFERENCE/DIFFERENCE_LIFECYCLE.md``
so the code cannot drift from the contract.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import scripts.difference_contract_validator as validator

from manosube_agent_civilization.difference.lifecycle import (
    LEGAL_TRANSITIONS,
    NEXT_OBSERVATION_REASON,
    OBSERVATION_BOUND_FORBIDDEN,
    REQUIRES_NEXT_OBSERVATION,
    TERMINAL_STATUSES,
    is_legal_transition,
    legal_supersession_sources,
)

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "00_KERNEL" / "04_DIFFERENCE" / "DIFFERENCE_LIFECYCLE.md"
_ROW = re.compile(r"^\|\s*`(\w+)`\s*\|\s*`(\w+)`\s*\|", re.MULTILINE)


def _contract_transitions() -> set[tuple[str | None, str]]:
    """Parse only the section 3 transition table, not other two-column tables."""

    source = CONTRACT.read_text(encoding="utf-8")
    start = source.index("# 3. Legal Transitions")
    end = source.index("\n# ", start)
    return {
        (None if left == "null" else left, right)
        for left, right in _ROW.findall(source[start:end])
    }


def test_the_executable_table_is_the_contract_table() -> None:
    parsed = _contract_transitions()
    assert parsed, "the lifecycle contract transition table could not be parsed"
    assert set(LEGAL_TRANSITIONS) == parsed


def test_exactly_one_transition_table_exists() -> None:
    """The independent validator imports the table; it does not define its own."""

    # The validator holds the imported object itself, not a copy or a second table.
    assert vars(validator)["LEGAL_TRANSITIONS"] is LEGAL_TRANSITIONS
    assert "LEGAL_TRANSITIONS = {" not in (
        ROOT / "scripts" / "difference_contract_validator.py"
    ).read_text(encoding="utf-8")


def test_terminal_statuses_have_no_outgoing_transition() -> None:
    for status in TERMINAL_STATUSES:
        assert not [target for source, target in LEGAL_TRANSITIONS if source == status]


def test_closed_is_not_terminal() -> None:
    assert "CLOSED" not in TERMINAL_STATUSES
    assert is_legal_transition("CLOSED", "REOPENED")
    assert is_legal_transition("CLOSED", "SUPERSEDED")


def test_observation_bound_forbidden_statuses_are_closed_or_terminal() -> None:
    assert TERMINAL_STATUSES | {"CLOSED"} == OBSERVATION_BOUND_FORBIDDEN


def test_every_status_requiring_a_next_observation_has_a_reason_code() -> None:
    assert set(NEXT_OBSERVATION_REASON) == REQUIRES_NEXT_OBSERVATION
    assert {"BLOCKED", "RETAINED", "REOPENED"} == REQUIRES_NEXT_OBSERVATION


def test_supersession_sources_are_derived_from_the_table() -> None:
    assert legal_supersession_sources() == {
        source for source, target in LEGAL_TRANSITIONS if target == "SUPERSEDED" and source
    }


# --------------------------------------------------------------------------- #
# The Fact effective-boundary matching rule is also a single authority.
# --------------------------------------------------------------------------- #


def test_exactly_one_fact_boundary_authority_exists() -> None:
    """The Observation owner defines it; the Engine and the auditor delegate to it."""

    from manosube_agent_civilization.observation import engine as observation_engine
    from manosube_agent_civilization.observation.boundary import fact_boundary_observed

    assert vars(observation_engine)["fact_boundary_observed"] is fact_boundary_observed
    assert vars(validator)["fact_boundary_observed"] is fact_boundary_observed
    source = (ROOT / "src" / "manosube_agent_civilization" / "difference" / "engine.py").read_text(
        encoding="utf-8"
    )
    assert "fact_boundary_observed(" in source


def test_fact_boundary_authority_covers_every_schema_kind() -> None:
    """The matcher handles exactly the kinds the Normalized Fact schema declares."""

    import json

    from manosube_agent_civilization.observation.boundary import FACT_BOUNDARY_KINDS

    schema = json.loads(
        (
            ROOT / "01_SCHEMA" / "observation" / "normalized_fact.schema.json"
        ).read_text(encoding="utf-8")
    )
    declared = set(
        schema["properties"]["effective_boundary"]["properties"]["kind"]["enum"]
    )
    assert declared == FACT_BOUNDARY_KINDS
    assert declared == {"SOURCE_SNAPSHOT", "TIME_INTERVAL", "STATE_REVISION"}


def test_one_fact_identity_authority_is_shared_with_normalization() -> None:
    """`normalize_fact` and the verifier use the same semantic projection."""

    from manosube_agent_civilization.observation import normalization
    from manosube_agent_civilization.observation.identity import (
        fact_identity,
        fact_semantic_projection,
    )

    assert vars(normalization)["fact_semantic_projection"] is fact_semantic_projection
    assert vars(normalization)["fact_identity"] is fact_identity


def test_one_observation_record_verification_authority() -> None:
    """Schema and cross-record evaluation rules exist once, owned by Observation."""


    from manosube_agent_civilization.observation import engine as observation_engine
    from manosube_agent_civilization.observation.verification import (
        RECORD_SCHEMAS,
        observation_record_errors,
    )

    assert vars(observation_engine)["observation_record_errors"] is observation_record_errors

    from manosube_agent_civilization.difference import engine as difference_engine

    assert vars(difference_engine)["observation_record_errors"] is observation_record_errors

    # The Observation Engine keeps no ruleset of its own: its record validation is one
    # delegating call, and the Difference Engine states no evaluation rule at all.
    observation_source = (
        ROOT / "src" / "manosube_agent_civilization" / "observation" / "engine.py"
    ).read_text(encoding="utf-8")
    body = observation_source.split("def _validate_records(")[1].split("\ndef ")[0]
    assert "errors.append" not in body
    assert body.count("observation_record_errors(") == 1

    difference_source = (
        ROOT / "src" / "manosube_agent_civilization" / "difference" / "engine.py"
    ).read_text(encoding="utf-8")
    assert "observation_record_errors(bundle)" in difference_source
    # The Difference Engine reads an evaluation status; it never names the conflict
    # payload, and never validates an upstream evaluation against a schema of its own.
    for owned_by_observation in (
        "conflict_fact_refs",
        "conflict_negative_observation_refs",
        "fact_evaluation.schema.json",
        "negative_observation_evaluation.schema.json",
    ):
        assert owned_by_observation not in difference_source

    # The authority validates exactly the six canonical Observation record schemas -- the
    # Observation *bundle*'s own carried record kinds. ``source_snapshot`` (R6-F1a) is a
    # real Observation-owned schema too, but it is never a bundle section (no
    # ``bundle["source_snapshots"]`` list exists anywhere): it is resolved standalone, by
    # Reflow, from a caller-supplied pool, the same way ``observation_scope``/
    # ``observation_method`` already sit outside this bundle-validation authority.
    declared = set(RECORD_SCHEMAS.values())
    on_disk = {
        path.name
        for path in (ROOT / "01_SCHEMA" / "observation").glob("*.schema.json")
        if path.name
        not in {
            "observation_scope.schema.json",
            "observation_method.schema.json",
            "source_snapshot.schema.json",
        }
    }
    assert declared == on_disk


def test_the_difference_engine_validates_the_upstream_payload_before_projection() -> None:
    """Payload validation and identity recomputation are distinct, ordered obligations."""

    source = (
        ROOT / "src" / "manosube_agent_civilization" / "difference" / "engine.py"
    ).read_text(encoding="utf-8")
    verify = source.split("def _verify_upstream_records(")[1].split("\ndef ")[0]
    assert "fact_identity(fact)" in verify
    assert "binding_identity(binding)" in verify
    assert "fact_evaluation_identity(evaluation)" in verify
    assert "observation_record_errors(bundle)" in verify
    # It runs before any observed candidate is projected.
    assert source.index("_verify_upstream_records(observation, bundle") < source.index(
        "value_candidate(fact, boundary)"
    )


def test_one_observation_identity_authority() -> None:
    """The Observation Engine mints and every consumer re-derives one closed projection."""

    from manosube_agent_civilization.observation import engine as observation_engine, verification
    from manosube_agent_civilization.observation.identity import (
        OBSERVATION_SEMANTIC_FIELDS,
        observation_identity,
    )

    assert vars(observation_engine)["observation_identity"] is observation_identity
    assert vars(verification)["observation_identity"] is observation_identity

    from manosube_agent_civilization.difference import engine as difference_engine

    assert vars(difference_engine)["observation_identity"] is observation_identity

    # The Observation Engine mints through the shared projection rather than assembling a
    # second identity input of its own.
    source = (
        ROOT / "src" / "manosube_agent_civilization" / "observation" / "engine.py"
    ).read_text(encoding="utf-8")
    assert 'deterministic_id("OBS"' not in source
    assert "observation_identity(observation_identity_payload)" in source

    assert set(OBSERVATION_SEMANTIC_FIELDS) == {
        "project_id",
        "state_revision_observed",
        "state_fingerprint_observed",
        "target_identity",
        "scope_id",
        "method_ref",
        "time_boundary",
        "source_snapshot_refs",
        "normalization_profile",
    }


def test_one_time_boundary_containment_authority() -> None:
    """The Scope containment rule lives once, in the Observation element."""

    from manosube_agent_civilization.observation import engine as observation_engine
    from manosube_agent_civilization.observation.boundary import time_boundary_within_scope

    assert vars(observation_engine)["time_boundary_within_scope"] is time_boundary_within_scope

    from manosube_agent_civilization.difference import engine as difference_engine

    assert vars(difference_engine)["time_boundary_within_scope"] is time_boundary_within_scope


def test_the_engine_and_the_observation_owner_agree_on_observation_identity() -> None:
    """Every Observation the Engine returns recomputes under the Observation authority."""

    from tests.difference_helpers import reobservation_pair

    from manosube_agent_civilization.difference import derive_differences
    from manosube_agent_civilization.observation.identity import observation_identity
    from manosube_agent_civilization.observation.verification import observation_record_errors

    _, later_request = reobservation_pair()
    source = later_request["bindings"][0]["observation_bundle"]
    assert observation_record_errors(source) == []

    bundle = derive_differences(later_request)
    assert len(bundle["observations"]) == 2
    for observation in bundle["observations"]:
        assert observation["observation_id"] == observation_identity(observation)


def test_one_next_observation_request_derivation_path() -> None:
    """A single call site mints Next Observation Requests for appended events."""

    source = (
        ROOT / "src" / "manosube_agent_civilization" / "difference" / "engine.py"
    ).read_text(encoding="utf-8")
    body = source.split("def derive_differences(")[1]
    assert body.count("_next_observation_request(") == 1
    # And it refuses to derive a second request for an event that already carries one.
    assert 'if head["next_observation_ref"] is not None:' in body


def test_one_carried_observation_verification_pass() -> None:
    """Every Observation in a returned bundle is verified by one owner, before return."""

    source = (
        ROOT / "src" / "manosube_agent_civilization" / "difference" / "engine.py"
    ).read_text(encoding="utf-8")
    body = source.split("def derive_differences(")[1].split("\ndef ")[0]
    assert body.count("_validate_carried_observations(") == 1
    assert source.index("_validate_carried_observations(\n") < source.index(
        "    return _finalize("
    )
    pass_body = source.split("def _validate_carried_observations(")[1].split("\ndef ")[0]
    for obligation in (
        "_validate_observation_boundary(observation, _own_scope(observation, scopes)",
        "observation_record_errors(",
    ):
        assert obligation in pass_body, obligation

    # One resolver decides which Scope an Observation is verified against, and both the
    # append-only context closure and the final pass call it -- so no route can substitute
    # the current derivation Scope for a historical Observation's own Scope.
    resolver = source.split("def _own_scope(")[1].split("\ndef ")[0]
    for obligation in (
        'observation.get("scope_ref")',
        "names a Scope absent from the bundle",
        'validate_record(scope, "observation_scope.schema.json"',
        "does not name its own id",
    ):
        assert obligation in resolver, obligation
    assert source.count("def _own_scope(") == 1
    assert source.count("_own_scope(") == 3
    closure = source.split("def _absorb_observation_context(")[1].split("\ndef ")[0]
    assert "_validate_observation_boundary(current, _own_scope(current, scopes)" in closure


def test_every_returned_observation_recomputes_and_resolves_its_scope() -> None:
    from tests.difference_helpers import reobservation_pair

    from manosube_agent_civilization.difference import derive_differences
    from manosube_agent_civilization.observation.boundary import time_boundary_within_scope
    from manosube_agent_civilization.observation.identity import observation_identity

    _, later_request = reobservation_pair()
    bundle = derive_differences(later_request)
    scopes = {item["scope_id"]: item for item in bundle["observation_scopes"]}
    assert bundle["observations"]
    for observation in bundle["observations"]:
        assert observation["observation_id"] == observation_identity(observation)
        scope = scopes[observation["scope_ref"]["id"]]
        assert time_boundary_within_scope(observation, scope)
