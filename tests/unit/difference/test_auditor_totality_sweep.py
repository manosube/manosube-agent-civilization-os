"""No emitted bundle may make the independent validator raise instead of report.

The Engine's input surface has been enumerated for several rounds. The auditor's had not
been enumerated at all: its whole negative coverage was the hand-authored invalid-fixture
cases, so a defect class nobody had thought to name was not covered. That asymmetry is what
let an Engine-only rule reach the branch -- the producer rejected a bundle and the auditor
accepted it, and no measurement could have said so.

``validate_bundle`` **returns** violations; it does not raise them. A raw ``KeyError`` or
``TypeError`` out of it is therefore not a rejection, it is the auditor failing to answer,
and an auditor that cannot answer cannot be the independent half of anything. This file
enumerates every reachable location of a real emitted bundle, deletes and retypes each, and
records the three outcomes separately: reported, accepted, or raised. Only the third is a
defect; an accepted mutation may be perfectly legitimate.

The harness is measured before the subject is, for the same reason as the input sweep: a
measurement that cannot fail reports zero.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from scripts.difference_contract_validator import validate_bundle
from tests.difference_helpers import (
    PREDICATE_ID,
    derivation_request,
    negative_claim,
    objective_revision,
    observation_scope,
    observed_bundle,
    raw_fact,
    retained_status_predecessor,
    state_fingerprint,
)
from tests.unit.difference.test_input_totality_sweep import (
    _ACTIONS,
    _MAX_DEPTH,
    _depth_of,
    _locations,
    _mutate,
    _steps,
)

from manosube_agent_civilization.difference import derive_differences


def _fresh_bundle() -> dict[str, Any]:
    """A predecessor-free derivation's emitted bundle."""

    fingerprint = state_fingerprint()
    scope = observation_scope()
    return derive_differences(
        derivation_request(
            objective_revision(),
            [
                {
                    "target_predicate_id": PREDICATE_ID,
                    "observation_scope": scope,
                    "observation_bundle": observed_bundle(
                        scope,
                        [raw_fact(value="NOT-READY")],
                        fingerprint,
                        negative_claims=[negative_claim("NO_RESULT")],
                    ),
                }
            ],
            fingerprint,
        )
    )


def _predecessor_bundle() -> dict[str, Any]:
    """A re-observation's emitted bundle: retained lineage, carried context, events."""

    _baseline, request = retained_status_predecessor("RETAINED")
    return derive_differences(request)


#: Every emitted bundle the auditor sweep walks.
BUNDLES: dict[str, Any] = {
    "fresh": _fresh_bundle,
    "predecessor": _predecessor_bundle,
}

BUILT: dict[str, dict[str, Any]] = {name: build() for name, build in BUNDLES.items()}

CASES: list[tuple[str, str, str]] = sorted(
    {
        (name, path, action)
        for name, built in BUILT.items()
        for path in _locations(built)
        for action in _ACTIONS
    }
)

#: Stated as data so a bundle that silently stops contributing locations fails the
#: measurement rather than shrinking it.
EXPECTED_SPAN: dict[str, int] = {"fresh": 513, "predecessor": 695}

#: Roots that are well-formed JSON but not an emitted bundle.
NON_OBJECT_ROOTS: list[Any] = [None, [], "bundle", 7, True]


def outcome(bundle: Any, validate: Any = validate_bundle) -> str:
    """Classify one audit. The single place this measurement decides an outcome.

    Three outcomes, kept apart on purpose: a reported violation and an accepted bundle are
    both the auditor answering, and only a raised exception is it failing to.
    """

    try:
        errors = validate(bundle)
    except Exception as error:
        return f"RAW:{type(error).__name__}: {error}"
    return "REPORTED" if errors else "ACCEPTED"


def test_the_sweep_covers_a_real_emitted_bundle() -> None:
    """The surface is real, and it is the Engine's own output rather than a hand-built one."""

    assert len(CASES) > 5000
    for name, built in BUILT.items():
        assert built["differences"], name
        assert built["events"], name


@pytest.mark.parametrize("bundle", sorted(EXPECTED_SPAN))
def test_the_inventory_is_neither_truncated_nor_shrunk(bundle: str) -> None:
    built = BUILT[bundle]
    assert _depth_of(built) <= _MAX_DEPTH, (
        f"{bundle} nests deeper than the sweep walks: the inventory is truncated"
    )
    reached = len(set(_locations(built)))
    assert reached == EXPECTED_SPAN[bundle], (
        f"{bundle} reaches {reached} locations, expected {EXPECTED_SPAN[bundle]}"
    )


def test_every_mutation_applies_or_the_measurement_fails() -> None:
    faults: list[str] = []
    for name, path, action in CASES:
        bundle = deepcopy(BUILT[name])
        try:
            _mutate(bundle, path, action)
        except Exception as error:
            faults.append(f"{name} {path} [{action}]: {type(error).__name__}: {error}")
    assert faults == [], f"{len(faults)} mutations could not be applied: {faults[:5]}"


def test_every_path_round_trips_through_the_parser() -> None:
    unreachable: list[str] = []
    for name, built in BUILT.items():
        for path in _locations(built):
            node: Any = built
            try:
                for _kind, step in _steps(path):
                    node = node[step]
            except Exception as error:
                unreachable.append(f"{name} {path}: {type(error).__name__}: {error}")
    assert unreachable == [], f"{len(unreachable)} paths do not resolve: {unreachable[:5]}"


def test_the_classifier_tells_the_three_outcomes_apart() -> None:
    """Positive control: a measurement that cannot fail proves nothing."""

    def raises_raw(_bundle: Any) -> list[str]:
        empty: dict[str, str] = {}
        empty["absent"]  # a deliberate KeyError: the exact shape being detected
        return []

    assert outcome(None, raises_raw).startswith("RAW:KeyError")
    assert outcome(None, lambda _bundle: ["a violation"]) == "REPORTED"
    assert outcome(None, lambda _bundle: []) == "ACCEPTED"


def test_the_auditor_accepts_every_clean_emitted_bundle() -> None:
    """Positive control, known good: what the Engine emits, the auditor accepts."""

    for name, built in BUILT.items():
        assert outcome(deepcopy(built)) == "ACCEPTED", (
            f"{name}: {validate_bundle(deepcopy(built))[:3]}"
        )


@pytest.mark.parametrize(
    ("path", "action"),
    [
        ("differences[0].difference_id", "retype:str"),
        ("events[0].difference_event_id", "retype:str"),
        ("differences[0].closure_policy.id", "retype:str"),
    ],
)
def test_the_auditor_reports_a_known_bad_mutation(path: str, action: str) -> None:
    """Positive control, known bad: a forged identity is reported, not accepted.

    Without this, an auditor that returned ``[]`` for everything would make the whole sweep
    green. The sweep proves it does not raise; this proves it still answers.
    """

    bundle = deepcopy(BUILT["fresh"])
    _mutate(bundle, path, action)
    assert outcome(bundle) == "REPORTED", f"{action} {path} was not reported"


@pytest.mark.parametrize("root", NON_OBJECT_ROOTS)
def test_a_non_object_bundle_is_reported_not_raised(root: Any) -> None:
    assert outcome(root) == "REPORTED"


@pytest.mark.parametrize(("bundle", "path", "action"), CASES, ids=lambda item: str(item))
def test_no_emitted_bundle_mutation_makes_the_auditor_raise(
    bundle: str, path: str, action: str
) -> None:
    """Report, or accept. Never raise.

    Accepting is a legitimate outcome: many locations are unconstrained payload, and the
    auditor is not required to have an opinion about every byte. What it is required to do
    is answer.
    """

    mutated = deepcopy(BUILT[bundle])
    _mutate(mutated, path, action)
    result = outcome(mutated)
    assert not result.startswith("RAW:"), f"{action} {path} produced {result}"
