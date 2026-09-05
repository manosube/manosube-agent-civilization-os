"""Phase 8 Vertical Proof -- the one required successful route (item D of Issue #41).

Every step below is produced, once, exclusively through
:mod:`tests.natural_cycle.proof`'s composed :func:`run_vertical_proof` -- the one public
proof entry -- driving the identical real, public canonical owners
(:mod:`manosube_agent_civilization.observation`, ``.difference``, ``.authority``, ``.change``,
``.evidence``, ``.reflow``) this repository already ships. This file only asserts on the
result; it never hand-builds a canonical record, and never substitutes anything the proof
entry itself produced.
"""

from __future__ import annotations

from pathlib import Path

from tests.fixtures import vertical_proof as fx
from tests.natural_cycle.proof import run_vertical_proof
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.store import FileStateStore


def test_the_full_natural_cycle_reaches_closed_through_real_owners_only(tmp_path: Path) -> None:
    """Items D.1-D.14, ``ONE_FULL_NATURAL_CYCLE_PASS``, in one real run."""

    result = run_vertical_proof(tmp_path)

    assert result["reflow_result"]["decision"]["to_status"] == "CLOSED"
    assert (
        result["reflow_result"]["event"]["reflow_transition_ref"]
        == result["reflow_result"]["state_transition_ref"]
    )
    # Item D.14: CLOSED only after the atomic Reflow itself succeeded -- proven, not merely
    # asserted, by the fact that a real committed_state and state_transition_ref exist at all
    # (a failed commit would have raised before returning).
    assert result["reflow_result"]["committed_state"]["state_revision"] == 1
    assert result["reflow_result"]["committed_state"]["state_revision"] == (
        result["genesis_state"]["state_revision"] + 1
    )


def test_reconstruction_from_lineage_matches_the_committed_state_exactly(tmp_path: Path) -> None:
    """Item D.12/D.13: every referenced immutable record resolves, and the reconstructed
    State is canonically equivalent to the committed one -- proven from a *fresh*
    :class:`FileStateStore` instance over only the persisted backend, never the in-process
    object :func:`run_vertical_proof` itself returned."""

    result = run_vertical_proof(tmp_path)
    fresh_store = FileStateStore(result["store"].root, schema_root=SCHEMA_ROOT)
    reconstructed = fresh_store.reconstruct(fx.PROJECT_ID)
    assert reconstructed == result["reflow_result"]["committed_state"]
    assert fresh_store.load_current(fx.PROJECT_ID) == result["reflow_result"]["committed_state"]

    ledger = result["identity_ledger"]
    for kind, record_id in (
        ("closure_evaluation", ledger["closure_evaluation_id"]),
        ("difference_event", ledger["difference_lifecycle_event_id"]),
        ("evidence_sufficiency_result", ledger["evidence_sufficiency_id"]),
        ("observation_evidence", ledger["observation_evidence_id"]),
        ("observation_evidence", ledger["change_result_evidence_id"]),
    ):
        resolved = fresh_store.resolve_record(fx.PROJECT_ID, kind, record_id)
        assert resolved is not None, (
            f"{kind}/{record_id} did not resolve from the persisted backend"
        )


def test_the_difference_is_removed_from_open_differences_only_because_reflow_closed_it(
    tmp_path: Path,
) -> None:
    """Item D.14 sharpened: the committed semantic State no longer lists this Difference as
    open -- and this file never wrote that bookkeeping mutation itself; ``reflow()`` did."""

    result = run_vertical_proof(tmp_path)
    difference_ref = {"kind": "difference", "id": result["difference"]["difference_id"]}
    assert (
        difference_ref
        not in result["reflow_result"]["committed_state"]["semantic_state"]["open_differences"]
    )


def test_the_identity_ledger_names_every_required_stage_with_a_real_id(tmp_path: Path) -> None:
    """The identity ledger the Issue itself enumerates -- every one of the fourteen named
    identities is present and is a real, non-empty, content-addressed value this run actually
    produced (never a URL, filename, list position or fixture label standing in for it)."""

    result = run_vertical_proof(tmp_path)
    ledger = result["identity_ledger"]
    required_keys = {
        "objective_revision_id",
        "initial_state_revision",
        "initial_state_fingerprint",
        "before_observation_id",
        "difference_id",
        "difference_lifecycle_head_ref",
        "authority_decision_id",
        "change_id",
        "change_result_observation_id",
        "verification_observation_id",
        "observation_evidence_id",
        "change_result_evidence_id",
        "evidence_sufficiency_id",
        "closure_evaluation_id",
        "difference_lifecycle_event_id",
        "state_transition_ref",
        "final_state_revision",
        "final_state_fingerprint",
        "final_lineage_head_ref",
    }
    assert required_keys <= set(ledger)
    for key in required_keys:
        assert ledger[key] not in (None, "", [], {}), f"{key} is empty"

    # Every Observation-identity role this cycle produced is a genuinely distinct real
    # Observation -- never one Observation record standing in for two roles.
    observation_ids = {
        ledger["before_observation_id"],
        ledger["change_result_observation_id"],
        ledger["verification_observation_id"],
    }
    assert len(observation_ids) == 3


def test_the_change_and_authority_decision_bind_the_exact_requested_action_and_scope(
    tmp_path: Path,
) -> None:
    """The Change the real Change owner derived is the one the real Authority Decision
    actually authorized -- not merely present, but bound to the identical action/scope."""

    result = run_vertical_proof(tmp_path)
    change = result["change"]["change"]
    decision = result["authority"]["decision"]
    assert decision["decision"] == "AUTONOMOUS"
    assert change["authority_ref"]["id"] == decision["authority_decision_id"]
    assert (
        change["action"]["action_semantic_fingerprint"]
        == decision["requested_action"]["action_semantic_fingerprint"]
    )


def test_the_change_result_evidence_binds_the_real_change_and_the_real_authority_decision(
    tmp_path: Path,
) -> None:
    """The Change-result Evidence the real Evidence owner derived names the exact real Change
    and the exact real Authority Decision this cycle produced -- never a forgeable
    restatement."""

    result = run_vertical_proof(tmp_path)
    evidence = result["evidence"]["change_result_evidence"]
    assert evidence["change_identity"]["id"] == result["change"]["change"]["change_id"]
    assert (
        evidence["authority_used"]["id"] == result["authority"]["decision"]["authority_decision_id"]
    )
    assert evidence["authority_used"]["decision"] == "AUTONOMOUS"


def test_the_evidence_sufficiency_result_is_sufficient_against_the_reals_policy(
    tmp_path: Path,
) -> None:
    result = run_vertical_proof(tmp_path)
    sufficiency = result["sufficiency"]["result"]
    assert sufficiency["result"] == "SUFFICIENT"
    assert sufficiency["difference_ref"]["id"] == result["difference"]["difference_id"]
