"""P15-R4: the one shared monotonic transition-chain mechanism, proved at the rule level.

``transition_chain.py`` exists because Round 4 required the identical lifecycle correction in two
places at once -- a ``runtime_deployment_declaration``'s chain (P15-R4-F2) and a
``runtime_root_admission``'s chain (P15-R4-F1, item 5) -- and writing the
genesis/successor/rotation/revocation/terminality/Compare-And-Swap logic twice would have given
this delivery two chances to drift apart. This file proves the rules themselves, once, over a
deliberately minimal synthetic record kind, so that a rule can never be "proved" only by the
particular record kind that happens to exercise it.

The Store-level controls -- atomic commit, idempotent replay, contention, pointer rollback --
live in ``tests/integration/runtime/test_runtime_declaration_transition_chain.py`` and
``tests/integration/runtime/test_runtime_deployment_authority_composition.py``, against the two
real chains.
"""

from __future__ import annotations

from typing import Any

import pytest

from manosube_agent_civilization.runtime.admission_registry import ROOT_ADMISSION_CHAIN
from manosube_agent_civilization.runtime.deployment_registry import DEPLOYMENT_DECLARATION_CHAIN
from manosube_agent_civilization.runtime.errors import RuntimeRequirementError
from manosube_agent_civilization.runtime.identity import (
    ROOT_ADMISSION_TARGET_KEY_PREFIX,
    runtime_deployment_target_key,
    runtime_root_admission_target_key,
)
from manosube_agent_civilization.runtime.transition_chain import (
    TRANSITION_GENESIS,
    TRANSITION_SUCCESSOR,
    MonotonicChainSpec,
    current_chain_record_id,
    require_legal_transition,
    require_self_consistent_record,
)

_KIND = "synthetic_chained_record"


def _identity(record: dict[str, Any]) -> str:
    """A deliberately trivial "content address": the rules under test are about generation and
    predecessor, never about how a record is hashed, so a synthetic kind proves them without
    borrowing either real record kind's own derivation."""

    return str(record["declared_id"])


def _spec() -> MonotonicChainSpec:
    return MonotonicChainSpec(
        record_kind=_KIND,
        id_field="declared_id",
        semantic_fingerprint_field="declared_fingerprint",
        require_valid=dict,
        recompute_id=_identity,
        recompute_semantic_fingerprint=lambda record: str(record["declared_fingerprint"]),
        chain_key_of=lambda record: str(record["chain"]),
    )


def _record(
    record_id: str,
    *,
    generation: int,
    predecessor: str | None,
    status: str = "ACTIVE",
    chain: str = "CHAIN-A",
) -> dict[str, Any]:
    return {
        "declared_id": record_id,
        "declared_fingerprint": f"fp:{record_id}",
        "project_id": "PRJ-0001",
        "chain": chain,
        "status": status,
        "generation": generation,
        "predecessor_ref": (None if predecessor is None else {"kind": _KIND, "id": predecessor}),
    }


def _legal(proposed: dict[str, Any], current: dict[str, Any] | None) -> str:
    return require_legal_transition(
        _spec(),
        proposed=proposed,
        current_record=current,
        current_id=None if current is None else str(current["declared_id"]),
    )


# ---------------------------------------------------------------------------
# Genesis
# ---------------------------------------------------------------------------


def test_genesis_is_admitted_only_into_an_empty_chain() -> None:
    genesis = _record("R-A", generation=0, predecessor=None)
    assert _legal(genesis, None) == TRANSITION_GENESIS


def test_a_genesis_record_must_be_active() -> None:
    """A chain cannot open with a revocation of something that was never admitted -- the
    resulting head would be terminal without ever having admitted anything, which is a shape
    with no meaning rather than a stricter one."""

    with pytest.raises(RuntimeRequirementError, match="genesis"):
        _legal(_record("R-A", generation=0, predecessor=None, status="REVOKED"), None)


@pytest.mark.parametrize(
    ("generation", "predecessor"),
    [(1, None), (0, "R-OTHER"), (2, "R-OTHER")],
)
def test_a_non_genesis_record_is_refused_into_an_empty_chain(
    generation: int, predecessor: str | None
) -> None:
    with pytest.raises(RuntimeRequirementError, match="genesis"):
        _legal(_record("R-A", generation=generation, predecessor=predecessor), None)


def test_a_genesis_record_is_refused_once_a_chain_exists() -> None:
    """The ancestor-replay case in its purest form: a perfectly genuine genesis record, proposed
    again against a chain that has moved on. Round 3's committer accepted exactly this and moved
    the pointer straight back."""

    current = _record("R-B", generation=1, predecessor="R-A")
    with pytest.raises(RuntimeRequirementError, match="ancestor-replay"):
        _legal(_record("R-A", generation=0, predecessor=None), current)


# ---------------------------------------------------------------------------
# Succession
# ---------------------------------------------------------------------------


def test_a_successor_naming_the_exact_head_and_the_next_generation_is_admitted() -> None:
    current = _record("R-A", generation=0, predecessor=None)
    successor = _record("R-B", generation=1, predecessor="R-A")
    assert _legal(successor, current) == TRANSITION_SUCCESSOR


def test_an_active_rotation_and_a_revocation_follow_the_identical_successor_rule() -> None:
    """Rotation is not a separate rule -- it is the successor rule with ``status="ACTIVE"``, and
    revocation is the successor rule with ``status="REVOKED"``. Keeping them one rule is why a
    revocation cannot be smuggled past a check a rotation would fail, or the reverse."""

    current = _record("R-A", generation=0, predecessor=None)
    for status in ("ACTIVE", "REVOKED"):
        successor = _record("R-B", generation=1, predecessor="R-A", status=status)
        assert _legal(successor, current) == TRANSITION_SUCCESSOR


def test_a_successor_naming_the_wrong_predecessor_is_refused() -> None:
    current = _record("R-B", generation=1, predecessor="R-A")
    with pytest.raises(RuntimeRequirementError, match="predecessor_ref"):
        _legal(_record("R-C", generation=2, predecessor="R-A"), current)


def test_a_successor_skipping_a_generation_is_refused() -> None:
    current = _record("R-A", generation=0, predecessor=None)
    with pytest.raises(RuntimeRequirementError, match="one past"):
        _legal(_record("R-C", generation=2, predecessor="R-A"), current)


def test_a_duplicate_generation_with_a_different_body_is_refused() -> None:
    """Two different records both claiming generation 1 from the same predecessor: whichever
    lands second is refused, because by then the pointer no longer names that predecessor."""

    current = _record("R-B", generation=1, predecessor="R-A")
    with pytest.raises(RuntimeRequirementError, match="predecessor_ref"):
        _legal(_record("R-B-PRIME", generation=1, predecessor="R-A"), current)


def test_a_rewound_generation_is_refused() -> None:
    current = _record("R-C", generation=2, predecessor="R-B")
    with pytest.raises(RuntimeRequirementError, match="one past"):
        _legal(_record("R-B", generation=1, predecessor="R-C"), current)


def test_a_record_from_a_different_chain_can_never_supersede_this_one() -> None:
    current = _record("R-A", generation=0, predecessor=None, chain="CHAIN-A")
    with pytest.raises(RuntimeRequirementError, match="different chain"):
        _legal(_record("R-B", generation=1, predecessor="R-A", chain="CHAIN-B"), current)


# ---------------------------------------------------------------------------
# Terminality
# ---------------------------------------------------------------------------


def test_a_revoked_head_admits_no_successor_ever() -> None:
    """Permanent terminality, and stated as such: after a revocation, no same-chain successor and
    no ancestor replay is ever admitted again. Any later reactivation requires a separately
    adopted new target epoch/chain, which this round deliberately does not build -- see
    ``10_RUNTIME/RUNTIME_CONTRACT.md`` §13.5, item 8."""

    revoked_head = _record("R-B", generation=1, predecessor="R-A", status="REVOKED")
    for proposed in (
        _record("R-C", generation=2, predecessor="R-B"),
        _record("R-C", generation=2, predecessor="R-B", status="REVOKED"),
        _record("R-A", generation=0, predecessor=None),
        _record("R-B", generation=1, predecessor="R-A"),
    ):
        with pytest.raises(RuntimeRequirementError, match="terminal"):
            _legal(proposed, revoked_head)


def test_terminality_is_checked_before_the_successor_rule() -> None:
    """A perfectly well-formed successor to a revoked head must be refused *as terminal*, which
    is the true reason, rather than as some accidental mismatch -- otherwise the message would
    mislead whoever reads it, and a future edit could "fix" the wrong thing."""

    revoked_head = _record("R-B", generation=1, predecessor="R-A", status="REVOKED")
    with pytest.raises(RuntimeRequirementError) as raised:
        _legal(_record("R-C", generation=2, predecessor="R-B"), revoked_head)
    assert "terminal" in str(raised.value)
    assert "one past" not in str(raised.value)


# ---------------------------------------------------------------------------
# Record self-consistency
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "generation",
    [-1, "1", 1.0, True, None],
)
def test_a_malformed_generation_is_refused(generation: Any) -> None:
    """``True`` is included deliberately: Python would otherwise let a ``bool`` through as an
    ``int``, and a chain whose generation could be ``True`` is not a chain."""

    record = _record("R-A", generation=0, predecessor=None)
    record["generation"] = generation
    with pytest.raises(RuntimeRequirementError, match="generation"):
        require_self_consistent_record(_spec(), record)


@pytest.mark.parametrize(
    "predecessor_ref",
    [
        {"kind": "some_other_kind", "id": "R-A"},
        {"kind": _KIND},
        {"kind": _KIND, "id": ""},
        "R-A",
        [],
    ],
)
def test_a_malformed_predecessor_reference_is_refused(predecessor_ref: Any) -> None:
    record = _record("R-B", generation=1, predecessor="R-A")
    record["predecessor_ref"] = predecessor_ref
    with pytest.raises(RuntimeRequirementError, match="predecessor_ref"):
        require_self_consistent_record(_spec(), record)


def test_a_record_whose_own_identity_does_not_reproduce_is_refused() -> None:
    record = _record("R-A", generation=0, predecessor=None)
    record["declared_id"] = "R-SOMETHING-ELSE"
    record["declared_fingerprint"] = "fp:R-A"
    spec = MonotonicChainSpec(
        record_kind=_KIND,
        id_field="declared_id",
        semantic_fingerprint_field="declared_fingerprint",
        require_valid=dict,
        recompute_id=lambda _record: "R-A",
        recompute_semantic_fingerprint=lambda record: str(record["declared_fingerprint"]),
        chain_key_of=lambda record: str(record["chain"]),
    )
    with pytest.raises(RuntimeRequirementError, match="recomputed identity"):
        require_self_consistent_record(spec, record)


@pytest.mark.parametrize("status", ["PENDING", "", None, "active"])
def test_a_record_carrying_an_unrecognized_status_is_refused(status: Any) -> None:
    record = _record("R-A", generation=0, predecessor=None)
    record["status"] = status
    with pytest.raises(RuntimeRequirementError, match="status"):
        require_self_consistent_record(_spec(), record)


# ---------------------------------------------------------------------------
# Pointer reads
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "state",
    [
        {},
        {"semantic_state": None},
        {"semantic_state": {}},
        {"semantic_state": {"runtime": None}},
        {"semantic_state": {"runtime": {}}},
        {"semantic_state": {"runtime": {"claims": None}}},
        {"semantic_state": {"runtime": {"claims": {}}}},
        {"semantic_state": {"runtime": {"claims": {"CHAIN-A": 7}}}},
    ],
)
def test_an_unreadable_or_absent_pointer_reads_as_none_rather_than_raising(
    state: dict[str, Any],
) -> None:
    """A missing pointer is an ordinary state of the world -- nothing has been made current yet
    -- and deciding what it *means* belongs to the caller. Every caller in this package treats it
    as a refusal, which is exactly why the read itself must not pre-empt that decision."""

    assert current_chain_record_id(state, "CHAIN-A") is None


def test_a_present_pointer_reads_back_exactly() -> None:
    state = {"semantic_state": {"runtime": {"claims": {"CHAIN-A": "R-B", "CHAIN-B": "R-Z"}}}}
    assert current_chain_record_id(state, "CHAIN-A") == "R-B"
    assert current_chain_record_id(state, "CHAIN-B") == "R-Z"


# ---------------------------------------------------------------------------
# The two shipped chains' key spaces are structurally disjoint
# ---------------------------------------------------------------------------


def test_the_two_chain_key_spaces_cannot_collide_by_construction() -> None:
    """P15-R4-F1: both shipped chains record their pointers in the identical
    ``semantic_state.runtime.claims`` map, so their key spaces must be *provably* disjoint rather
    than observed not to collide over whatever inputs a test happens to try.

    The proof is over the alphabets themselves, not over samples. A deployment target key is
    exactly the literal ``RUNTIME-DEPLOYMENT-TARGET-`` followed by 64 characters drawn from
    ``[0-9A-F]`` -- ``hashlib.sha256(...).hexdigest().upper()`` can emit nothing else -- and
    neither the prefix nor that alphabet contains ``":"``. Every admission chain key contains one,
    at the fixed offset the literal prefix puts it at. No string can therefore be a member of
    both sets, whatever the inputs.
    """

    deployment_alphabet = set("0123456789ABCDEF")
    deployment_prefix = "RUNTIME-DEPLOYMENT-TARGET-"
    separator = ":"
    assert separator in ROOT_ADMISSION_TARGET_KEY_PREFIX
    assert separator not in deployment_prefix
    assert separator not in deployment_alphabet
    # ...and the prefixes disagree before the separator is even reached.
    assert not ROOT_ADMISSION_TARGET_KEY_PREFIX.startswith(deployment_prefix)
    assert not deployment_prefix.startswith(ROOT_ADMISSION_TARGET_KEY_PREFIX)


def test_the_two_shipped_key_derivations_agree_with_that_structural_claim() -> None:
    """The empirical companion to the structural proof above: the real derivations really do
    produce keys of the shapes the argument assumes."""

    deployment_key = runtime_deployment_target_key(
        {
            "project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-0001"},
            "provider": "local",
            "deployment_id": "widget-service",
            "instance_identity": "widget-service-1",
        }
    )
    admission_key = runtime_root_admission_target_key(
        {"project_binding_ref": {"kind": "project_binding", "id": "PROJBIND-0001"}}
    )
    assert deployment_key.startswith("RUNTIME-DEPLOYMENT-TARGET-")
    assert set(deployment_key.removeprefix("RUNTIME-DEPLOYMENT-TARGET-")) <= set("0123456789ABCDEF")
    assert ":" not in deployment_key
    assert admission_key == ROOT_ADMISSION_TARGET_KEY_PREFIX + "PROJBIND-0001"
    assert deployment_key != admission_key


def test_an_admission_chain_key_cannot_be_derived_without_a_binding_reference() -> None:
    for admission in ({}, {"project_binding_ref": None}, {"project_binding_ref": {"kind": "x"}}):
        with pytest.raises(RuntimeRequirementError, match="project_binding_ref"):
            runtime_root_admission_target_key(dict(admission))


# ---------------------------------------------------------------------------
# The two shipped specs bind the identical mechanism
# ---------------------------------------------------------------------------


def test_both_shipped_chains_use_the_identical_field_names_and_status_vocabulary() -> None:
    """The specs differ only in what is genuinely record-kind-specific -- the record kind, its two
    digest field names, its validator, its derivations, and its chain key. Everything a *rule*
    reads is identical, which is what makes "one mechanism" a fact rather than an intention."""

    for spec in (DEPLOYMENT_DECLARATION_CHAIN, ROOT_ADMISSION_CHAIN):
        assert spec.generation_field == "generation"
        assert spec.predecessor_field == "predecessor_ref"
        assert spec.status_field == "status"
        assert spec.active_status == "ACTIVE"
        assert spec.revoked_status == "REVOKED"
    assert DEPLOYMENT_DECLARATION_CHAIN.record_kind == "runtime_deployment_declaration"
    assert ROOT_ADMISSION_CHAIN.record_kind == "runtime_root_admission"
    assert DEPLOYMENT_DECLARATION_CHAIN.chain_key_of is runtime_deployment_target_key
    assert ROOT_ADMISSION_CHAIN.chain_key_of is runtime_root_admission_target_key
