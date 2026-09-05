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

import hashlib
import json
from pathlib import Path
from typing import Any

from tests.fixtures import vertical_proof as fx
from tests.natural_cycle.proof import assemble_vertical_proof_route, run_vertical_proof
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.store import FileStateStore

#: The exact placeholder id (P8-R2-F1, SHUKOU Phase 8 structural-review round 2): a bare
#: string-``count`` scan over serialized JSON would also match ``NEG-EVID-VP8-0001`` (this
#: proof's own, separate, deliberately-fixed ``NEGATIVE_EVIDENCE_REF`` fixture value) as a
#: false positive, so this scans for exact leaf-value equality against the Observation
#: Evidence placeholder id alone, never a substring match.
_PLACEHOLDER_EVIDENCE_ID = "EVID-VP8-0001"


def _leaf_matches(obj: Any, target: Any) -> list[str]:
    """Every path at which some leaf value of *obj* equals *target* exactly."""

    hits: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            hits.extend(f".{key}{path}" for path in _leaf_matches(value, target))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            hits.extend(f"[{index}]{path}" for path in _leaf_matches(value, target))
    elif obj == target:
        hits.append("")
    return hits


def test_the_source_snapshot_fixtures_are_truthful_not_arbitrary() -> None:
    """P8-R1 Source Snapshot fixture truthfulness (SHUKOU Phase 8 structural-review round
    1): both the before- and after-world ``source_locator``s name a real file this
    repository actually ships, and both ``content_digest``s are the real ``sha256`` of that
    exact file's own on-disk bytes -- never an arbitrary digest asserted for content nobody
    checked."""

    for locator, snapshot in (
        (fx.BEFORE_SOURCE_WORLD_LOCATOR, fx.BEFORE_SOURCE_SNAPSHOT),
        (fx.AFTER_SOURCE_WORLD_LOCATOR, fx.AFTER_SOURCE_SNAPSHOT),
    ):
        path = fx.ROOT / locator
        assert path.is_file(), f"source_locator does not name a real file: {locator}"
        real_digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        assert snapshot["content_digest"] == real_digest
        assert snapshot["source_locator"] == locator


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


def test_the_difference_actually_consumes_the_real_observation_evidence(tmp_path: Path) -> None:
    """P8-R1-F1 (SHUKOU Phase 8 structural-review round 1): the Difference's own
    ``observation_evidence_refs`` field names the real, already-derived Observation
    Evidence id -- never a bare, unresolved placeholder. ``difference.engine._evidence_
    union`` copies this field straight from the before-Observation's own declared
    ``observation_evidence_refs``, so this also proves :func:`observe_before`'s two-pass
    correction actually reached the Observation the Difference was derived from, not only
    the one used to seed the Evidence derivation."""

    result = run_vertical_proof(tmp_path)
    ledger = result["identity_ledger"]
    real_ref = {"kind": "observation_evidence", "id": ledger["observation_evidence_id"]}
    assert real_ref in result["difference"]["observation_evidence_refs"]
    placeholder_ref = {"kind": "observation_evidence", "id": "EVID-VP8-0001"}
    assert placeholder_ref not in result["difference"]["observation_evidence_refs"]


def test_the_evidence_fixed_point_closes_across_the_full_accepted_request_graph(
    tmp_path: Path,
) -> None:
    """P8-R2-F1 (SHUKOU Phase 8 structural-review round 2): P8-R1-F1 only proved the final
    Difference's own ``observation_evidence_refs`` was placeholder-free -- the *accepted*
    request graph reaching Sufficiency, Closure and Reflow (``before["observation_evidence_
    request"]``, ``closure_request``, ``reflow_kwargs``) still carried the provisional,
    placeholder-seeded requests. ``FULL_ACCEPTED_REQUEST_GRAPH_PLACEHOLDER_COUNT=0`` is
    proven here, mechanically, by an exact leaf-value scan over the real assembled
    route -- not by checking one field and inferring the rest -- and again over every real
    record this run actually persisted, resolved straight from the committed transaction
    manifest, never from an in-process object this test could be fooled by.
    """

    assembly = assemble_vertical_proof_route(tmp_path / "assembly")
    before = assembly["before"]

    # CORRECTED_OBSERVATION_RETAINS_EXPECTED_OBSERVATION_ID / CORRECTED_EVIDENCE_REQUEST_
    # REDERIVES_SAME_EVIDENCE_ID: the fixed point in :func:`observe_before` already asserts
    # this internally (raising rather than silently substituting on divergence) -- proven
    # here from the outside too, against the real returned artifacts.
    assert before["observation_evidence_request"]["observation_request"][
        "observation_evidence_refs"
    ] == [{"kind": "observation_evidence", "id": before["observation_evidence"]["evidence_id"]}]

    for label, graph in (
        ("before.observation_evidence_request", before["observation_evidence_request"]),
        ("sufficiency.request", assembly["sufficiency"]["request"]),
        ("closure_request", assembly["closure_request"]),
        ("reflow_kwargs", assembly["reflow_kwargs"]),
    ):
        hits = _leaf_matches(graph, _PLACEHOLDER_EVIDENCE_ID)
        assert hits == [], f"placeholder Evidence id survives in {label}: {hits}"

    result = run_vertical_proof(tmp_path / "run")
    assert _leaf_matches(result["difference"], _PLACEHOLDER_EVIDENCE_ID) == []
    assert _leaf_matches(result["closure_request"], _PLACEHOLDER_EVIDENCE_ID) == []

    # PLACEHOLDER_IN_PERSISTED_RECORDS=false: resolve every record this run's own committed
    # transaction manifest names, straight from the Store's own recovery journal, and scan
    # each one -- not merely the records this test happens to already hold references to.
    store = result["store"]
    tx_root = store.root / "projects" / fx.PROJECT_ID / "state" / "recovery"
    total_hits = 0
    for tx_dir in tx_root.iterdir():
        manifest = json.loads((tx_dir / "manifest.json").read_text())
        for kind, record_id in manifest:
            record = store.resolve_record(fx.PROJECT_ID, kind, record_id)
            hits = _leaf_matches(record, _PLACEHOLDER_EVIDENCE_ID)
            assert hits == [], (
                f"placeholder Evidence id survives in persisted {kind}/{record_id}: {hits}"
            )
            total_hits += len(hits)
    assert total_hits == 0


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
