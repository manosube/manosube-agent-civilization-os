"""The Scope time-boundary predicate is one rule, and it carries every obligation.

Covers the independent review finding on `56a204a`: extracting `_time_boundary_complete`
from `observation/engine.py` into the shared boundary authority silently dropped the
canonical Scope freshness limit, so a source snapshot older than the Scope permits could
still be reported time-boundary complete.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import scripts.difference_contract_validator as validator
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_request,
    observation_scope,
    raw_fact,
    state_fingerprint,
    target_predicate,
)

from manosube_agent_civilization.difference import BoundaryViolationError, derive_differences
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.observation.boundary import instant, time_boundary_within_scope
from manosube_agent_civilization.observation.errors import ObservationError

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]

# The helper Scope: observation window 09:00-09:01, effective window 08:00-09:00,
# cutoff 09:00:00Z, freshness limit 300 seconds.
_SCOPE = observation_scope()
_LIMIT = _SCOPE["freshness_limit_seconds"]


def _boundary(snapshot: Any = "2026-08-30T08:59:00Z", **overrides: Any) -> dict[str, Any]:
    boundary = {
        "observation_started_at": "2026-08-30T09:00:00Z",
        "observation_ended_at": "2026-08-30T09:01:00Z",
        "target_effective_start": "2026-08-30T08:00:00Z",
        "target_effective_end": "2026-08-30T09:00:00Z",
        "source_snapshot_time": snapshot,
    }
    boundary.update(overrides)
    return {"time_boundary": boundary}


# --------------------------------------------------------------------------- #
# The freshness limit itself.
# --------------------------------------------------------------------------- #


def test_the_helper_scope_states_the_limit_under_test() -> None:
    assert _LIMIT == 300
    assert _SCOPE["cutoff"] == "2026-08-30T09:00:00Z"


def test_a_snapshot_exactly_at_the_freshness_limit_is_accepted() -> None:
    """cutoff - snapshot == limit, so the boundary is inclusive."""

    at_limit = "2026-08-30T08:55:00Z"
    assert (instant(_SCOPE["cutoff"]) - instant(at_limit)).total_seconds() == _LIMIT
    assert time_boundary_within_scope(_boundary(at_limit), _SCOPE) is True


def test_a_snapshot_one_second_beyond_the_limit_is_rejected() -> None:
    beyond = "2026-08-30T08:54:59Z"
    assert (instant(_SCOPE["cutoff"]) - instant(beyond)).total_seconds() == _LIMIT + 1
    assert time_boundary_within_scope(_boundary(beyond), _SCOPE) is False


def test_a_fresh_pre_cutoff_snapshot_is_accepted() -> None:
    assert time_boundary_within_scope(_boundary("2026-08-30T08:59:00Z"), _SCOPE) is True


def test_a_snapshot_at_the_cutoff_is_accepted() -> None:
    """Zero age is the freshest possible snapshot, not a degenerate case."""

    assert time_boundary_within_scope(_boundary("2026-08-30T09:00:00Z"), _SCOPE) is True


def test_a_zero_freshness_limit_admits_only_the_cutoff_instant() -> None:
    scope = deepcopy(_SCOPE)
    scope["freshness_limit_seconds"] = 0
    assert time_boundary_within_scope(_boundary("2026-08-30T09:00:00Z"), scope) is True
    assert time_boundary_within_scope(_boundary("2026-08-30T08:59:59Z"), scope) is False


# --------------------------------------------------------------------------- #
# Every other obligation the predicate carries, each independently.
# --------------------------------------------------------------------------- #

_REJECTED: list[tuple[str, dict[str, Any]]] = [
    # A snapshot after the cutoff is never accepted, however fresh.
    ("after cutoff", _boundary("2026-08-30T09:00:30Z")),
    # A future snapshot beyond the observation window.
    ("after the observed interval", _boundary("2026-08-30T09:05:00Z")),
    # Before the Target effective window opens: negative age against effective_start.
    ("before the effective window", _boundary("2026-08-30T07:00:00Z")),
    # Reversed observation window.
    (
        "reversed observation window",
        _boundary(observation_started_at="2026-08-30T09:01:00Z", observation_ended_at="2026-08-30T09:00:00Z"),
    ),
    # Reversed effective window.
    (
        "reversed effective window",
        _boundary(target_effective_start="2026-08-30T09:00:00Z", target_effective_end="2026-08-30T08:00:00Z"),
    ),
    # Observation window outside the Scope's own.
    ("observation window escapes scope", _boundary(observation_started_at="2026-08-30T08:30:00Z")),
    ("observation window overruns scope", _boundary(observation_ended_at="2026-08-30T10:00:00Z")),
    # Effective window outside the Scope's own.
    ("effective window escapes scope", _boundary(target_effective_start="2026-08-30T07:00:00Z")),
    ("effective window overruns scope", _boundary(target_effective_end="2026-08-30T09:30:00Z")),
    # Unparseable, naive and non-string instants all fail closed.
    ("unparseable instant", _boundary("not-a-timestamp")),
    ("naive instant", _boundary("2026-08-30T08:59:00")),
    ("null instant", _boundary(None)),
    ("numeric instant", _boundary(12345)),
    ("missing field", {"time_boundary": {"observation_started_at": "2026-08-30T09:00:00Z"}}),
    ("missing time boundary", {}),
]


@pytest.mark.parametrize(
    ("label", "observation"), _REJECTED, ids=[case[0] for case in _REJECTED]
)
def test_every_boundary_violation_fails_closed(label: str, observation: dict[str, Any]) -> None:
    assert time_boundary_within_scope(observation, _SCOPE) is False


_BAD_SCOPES: list[tuple[str, dict[str, Any]]] = [
    ("missing freshness limit", {"freshness_limit_seconds": None}),
    ("boolean freshness limit", {"freshness_limit_seconds": True}),
    ("string freshness limit", {"freshness_limit_seconds": "300"}),
    ("naive cutoff", {"cutoff": "2026-08-30T09:00:00"}),
    ("unparseable cutoff", {"cutoff": "never"}),
]


@pytest.mark.parametrize(
    ("label", "override"), _BAD_SCOPES, ids=[case[0] for case in _BAD_SCOPES]
)
def test_a_malformed_scope_fails_closed(label: str, override: dict[str, Any]) -> None:
    scope = deepcopy(_SCOPE)
    scope.update(override)
    assert time_boundary_within_scope(_boundary(), scope) is False


def test_a_scope_missing_a_window_fails_closed() -> None:
    scope = deepcopy(_SCOPE)
    del scope["observation_window"]
    assert time_boundary_within_scope(_boundary(), scope) is False


# --------------------------------------------------------------------------- #
# The three consumers provably agree.
# --------------------------------------------------------------------------- #


def _parity_matrix() -> list[tuple[dict[str, Any], dict[str, Any]]]:
    cases: list[tuple[dict[str, Any], dict[str, Any]]] = [
        (_boundary(snapshot), deepcopy(_SCOPE))
        for snapshot in (
            "2026-08-30T09:00:00Z",
            "2026-08-30T08:59:00Z",
            "2026-08-30T08:55:00Z",
            "2026-08-30T08:54:59Z",
            "2026-08-30T08:50:00Z",
            "2026-08-30T09:00:30Z",
            "2026-08-30T07:00:00Z",
            "2026-08-30T08:59:00",
            "not-a-timestamp",
        )
    ]
    cases.extend((observation, deepcopy(_SCOPE)) for _, observation in _REJECTED)
    for _, override in _BAD_SCOPES:
        scope = deepcopy(_SCOPE)
        scope.update(override)
        cases.append((_boundary(), scope))
    for limit in (0, 1, 60, 300, 301, 100000):
        scope = deepcopy(_SCOPE)
        scope["freshness_limit_seconds"] = limit
        for snapshot in ("2026-08-30T09:00:00Z", "2026-08-30T08:55:00Z", "2026-08-30T08:50:00Z"):
            cases.append((_boundary(snapshot), scope))
    return cases


def test_the_shared_authority_and_the_independent_validator_agree_everywhere() -> None:
    """The auditor keeps its own derivation; a parity matrix proves they cannot drift."""

    matrix = _parity_matrix()
    assert len(matrix) >= 40
    verdicts = set()
    for observation, scope in matrix:
        shared = time_boundary_within_scope(observation, scope)
        independent = validator._observation_time_boundary_complete(observation, scope)
        assert shared == independent, (observation, scope["freshness_limit_seconds"])
        verdicts.add(shared)
    # The matrix exercises both verdicts, so agreement is not agreement-on-False.
    assert verdicts == {True, False}


def test_the_observation_owner_holds_the_shared_authority() -> None:
    from manosube_agent_civilization.difference import engine as difference_engine
    from manosube_agent_civilization.observation import engine as observation_engine

    assert vars(observation_engine)["time_boundary_within_scope"] is time_boundary_within_scope
    assert vars(difference_engine)["time_boundary_within_scope"] is time_boundary_within_scope


def test_the_predicate_carries_every_pre_extraction_obligation() -> None:
    """A regression test against the predicate this authority was extracted from.

    `_time_boundary_complete` lived in `observation/engine.py` before the extraction. Each
    obligation it stated is named here, so a future extraction cannot quietly drop one the
    way the freshness limit was dropped.
    """

    source = (
        ROOT / "src" / "manosube_agent_civilization" / "observation" / "boundary.py"
    ).read_text(encoding="utf-8")
    body = source.split("def time_boundary_within_scope(")[1]
    for obligation in (
        "observed_start <= observed_end",
        "effective_start <= effective_end",
        "scope_observed_start <= observed_start <= observed_end <= scope_observed_end",
        "scope_effective_start <= effective_start <= effective_end <= scope_effective_end",
        "effective_start <= snapshot <= observed_end",
        "snapshot <= cutoff",
        "(cutoff - snapshot).total_seconds() <= freshness_limit",
    ):
        assert obligation in body, obligation

    # And the canonical Scope contract's own time-boundary vocabulary is all consumed.
    for field in (
        "observation_window",
        "target_effective_window",
        "freshness_limit_seconds",
        "cutoff",
    ):
        assert field in body, field
    contract = (
        ROOT / "00_KERNEL" / "03_OBSERVATION" / "OBSERVATION_SCOPE.md"
    ).read_text(encoding="utf-8")
    section = contract.split("# 5. Time Boundary")[1].split("\n# ")[0]
    for named in ("observation_window", "target_effective_window", "freshness_limit", "cutoff"):
        assert named in section, named


# --------------------------------------------------------------------------- #
# End to end: a stale snapshot reaches nothing.
# --------------------------------------------------------------------------- #

_STALE = "2026-08-30T08:50:00Z"


def _stale_request(
    facts: list[dict[str, Any]], negatives: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    request = observation_request(_SCOPE, facts, state_fingerprint())
    if negatives is not None:
        request["negative_claims"] = negatives
    request["time_boundary"]["source_snapshot_time"] = _STALE
    return request


def test_a_stale_snapshot_cannot_produce_a_complete_observation() -> None:
    bundle = observe(_stale_request([raw_fact()]))
    assert bundle["observations"][0]["status"] == "INCOMPLETE"


def test_a_fresh_snapshot_still_produces_a_complete_observation() -> None:
    bundle = observe(observation_request(_SCOPE, [raw_fact()], state_fingerprint()))
    assert bundle["observations"][0]["status"] == "COMPLETE"


def test_a_stale_snapshot_cannot_produce_bounded_absence() -> None:
    with pytest.raises(ObservationError, match="complete bounded absence gate"):
        observe(_stale_request([], [negative_claim("ABSENT")]))


def test_a_stale_snapshot_cannot_produce_a_difference() -> None:
    bundle = observe(_stale_request([raw_fact()]))
    with pytest.raises(BoundaryViolationError, match="time boundary escapes the resolved Scope"):
        derive_differences(
            derivation_request(
                objective_revision([target_predicate()]),
                [
                    {
                        "target_predicate_id": PREDICATE_ID,
                        "observation_scope": _SCOPE,
                        "observation_bundle": bundle,
                    }
                ],
                state_fingerprint(),
            )
        )
