"""Phase 8 Vertical Proof -- persisted-reference-graph closure proof (P8-R3-F1/P8-R4-F1/
P8-R4-F2/P8-R4-F3, SHUKOU Phase 8 final-closure rounds 3-4).

Round 2 proved the *accepted request graph* carried no placeholder Evidence id
(``test_vertical_proof.py::test_the_evidence_fixed_point_closes_across_the_full_accepted_
request_graph``). Round 3 closed the persisted-graph gap for ``observation``/
``observation_evidence`` records specifically, but scoped its own closure check to an
opt-in caller keyword and its own test vocabulary to two record kinds, omitting
``source_snapshot`` (P8-R4-F2), and left the Difference's own genesis lifecycle event
unpersisted and therefore unresolvable (P8-R4-F3). Round 4 (SHUKOU's own explicit reversal
of Round 3's opt-in scoping decision) makes Reference Closure an unconditional invariant of
every ``reflow()`` call, walked through the single production reference-edge registry
(:mod:`manosube_agent_civilization.reflow.reference_registry`) this file imports directly
rather than maintaining a second, duplicate vocabulary
(``PRODUCTION_AND_TEST_REFERENCE_VOCABULARY_MUST_MATCH=true``,
``DUPLICATE_TEST_REFERENCE_REGISTRY=false``).

This file proves ``PERSISTED_REFERENCE_GRAPH_CLOSED=true`` /
``UNRESOLVED_STORE_OWNED_REFERENCE_COUNT=0`` over every Store-owned reference edge the
production registry recognizes: an ``observation`` record's own ``source_snapshot_refs``
and ``observation_evidence_refs``; an ``observation_evidence`` record's own
``observed_result.observation_ref``, ``lineage.derived_from`` (``observation``-kind members
only), and ``lineage.predecessor_evidence_refs``; a ``closure_evaluation`` record's own
``difference_event_head_ref``; and a ``difference_event`` record's own
``previous_event_id`` (including the Difference's own genesis lifecycle event, now
atomically persisted alongside the first real Reflow-minted event, P8-R4-F3). References
this Kernel names but never gives a Store-owned producer of its own -- ``difference``,
``change``, ``authority_decision``, ``artifact``, ``negative_evidence`` (no second
canonical owner is created for any of them here, or anywhere else in this vertical) --
remain out of this proof's scope, not silently treated as resolved.

The recognition rule for a reference is structural, not a text search over key names: a
dict shaped like ``common/reference.schema.json`` (``kind``+``id``, both non-empty
strings), with ``kind`` restricted to the production registry's own
:data:`~manosube_agent_civilization.reflow.reference_registry.STORE_OWNED_REFERENCE_KINDS`
-- explicit and reviewed, never "any key ending in ``_ref``/``_refs``".

Idempotent replay over this Finding's own larger record set (SHUKOU's required item 12) is
not duplicated here: ``test_vertical_proof_negative_routes.py::test_p8r1f3_the_full_
vertical_transaction_record_set_replays_as_a_true_no_op`` already reads the real committed
transaction's own manifest dynamically and replays every record it names, so it already
covers the additional records this Finding admits, with no change of its own required.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import textwrap
from typing import Any

import pytest
from tests.fixtures import vertical_proof as fx
from tests.natural_cycle.proof import assemble_vertical_proof_route, run_vertical_proof
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.reflow.errors import ReflowValidationError
from manosube_agent_civilization.reflow.reference_registry import (
    STORE_OWNED_REFERENCE_KINDS,
    reference_edges,
)
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.store import STAGES, FileStateStore
from manosube_agent_civilization.store.errors import CorruptStoreError, SimulatedCrash


def _manifest_records(store: Any, project_id: str) -> list[tuple[str, str, dict[str, Any]]]:
    """Every immutable record a real committed transaction's own manifest names, resolved
    through the public :meth:`~manosube_agent_civilization.store.file_store.FileStateStore.
    resolve_record` -- never read directly off disk."""

    tx_root = store.root / "projects" / project_id / "state" / "recovery"
    records: list[tuple[str, str, dict[str, Any]]] = []
    for tx_dir in sorted(p for p in tx_root.iterdir() if p.is_dir()):
        manifest = json.loads((tx_dir / "manifest.json").read_text())
        for kind, record_id in manifest:
            body = store.resolve_record(project_id, kind, record_id)
            assert body is not None, f"manifest names {kind}/{record_id} but it does not resolve"
            records.append((kind, record_id, body))
    return records


def _closure_report(store: Any, project_id: str) -> dict[str, Any]:
    """Walk every manifest record's own in-scope reference edges (via the production
    registry, :func:`reference_edges`) and resolve each -- ``PLACEHOLDER_STRING_ABSENCE``
    alone is not completion; every real, in-scope reference this committed graph declares
    must resolve through the public Store API."""

    manifest_records = _manifest_records(store, project_id)
    edges_checked: set[tuple[str, str]] = set()
    unresolved: list[tuple[str, str, str, str]] = []
    for kind, record_id, body in manifest_records:
        for ref_kind, ref_id in reference_edges(kind, body):
            edges_checked.add((ref_kind, ref_id))
            if store.resolve_record(project_id, ref_kind, ref_id) is None:
                unresolved.append((kind, record_id, ref_kind, ref_id))
    return {
        "manifest_records": manifest_records,
        "edges_checked": edges_checked,
        "unresolved": unresolved,
    }


# --- positive closure proof ---------------------------------------------------------------- #


def test_the_full_persisted_reference_graph_closes_with_zero_unresolved_edges(
    tmp_path: Path,
) -> None:
    """Item 1/2/8: the real vertical proof's own committed transaction manifest is read,
    every record it names is resolved, every in-scope reference edge those records declare
    is recursively walked, and every one of them resolves -- ``PERSISTED_REFERENCE_GRAPH_
    CLOSED=true``, ``UNRESOLVED_STORE_OWNED_REFERENCE_COUNT=0``."""

    result = run_vertical_proof(tmp_path)
    report = _closure_report(result["store"], fx.PROJECT_ID)
    assert report["unresolved"] == []
    assert len(report["edges_checked"]) > 0
    kinds_seen = {kind for kind, _, _ in report["manifest_records"]}
    assert {
        "observation",
        "observation_evidence",
        "closure_evaluation",
        "difference_event",
    } <= kinds_seen
    # P8-R4-F2: the production registry actually walks source_snapshot edges now -- a
    # vacuously-passing empty scan (no source_snapshot-kind edge ever checked) would not
    # prove anything about them.
    assert any(ref_kind == "source_snapshot" for ref_kind, _ in report["edges_checked"])
    # P8-R4-F1: the registry-driven walk also covers a difference_event's own
    # previous_event_id -- the genesis event's own resolvability, in particular.
    assert any(ref_kind == "difference_event" for ref_kind, _ in report["edges_checked"])


def test_the_verification_observation_resolves_its_own_auxiliary_evidence(
    tmp_path: Path,
) -> None:
    """Item 3: the persisted verification Observation's own ``observation_evidence_refs``
    entry -- the auxiliary Change-Free Verification Evidence P8-R3-F1 is about -- resolves."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    ledger = result["identity_ledger"]
    verification_observation = store.resolve_record(
        fx.PROJECT_ID, "observation", ledger["verification_observation_id"]
    )
    assert verification_observation is not None
    refs = verification_observation["observation_evidence_refs"]
    assert refs
    for ref in refs:
        assert store.resolve_record(fx.PROJECT_ID, ref["kind"], ref["id"]) is not None


def test_the_observation_evidence_resolves_the_before_observation_it_names(
    tmp_path: Path,
) -> None:
    """Item 4: Observation Evidence's own ``observed_result.observation_ref`` names the
    real before-Observation, and it now resolves."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    ledger = result["identity_ledger"]
    observation_evidence = store.resolve_record(
        fx.PROJECT_ID, "observation_evidence", ledger["observation_evidence_id"]
    )
    ref = observation_evidence["observed_result"]["observation_ref"]
    assert ref["id"] == ledger["before_observation_id"]
    assert store.resolve_record(fx.PROJECT_ID, ref["kind"], ref["id"]) is not None


def test_the_change_result_evidence_resolves_the_before_observation_it_names(
    tmp_path: Path,
) -> None:
    """Item 5: Change-result Evidence's own ``lineage.derived_from`` names the identical
    real before-Observation, and it now resolves."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    ledger = result["identity_ledger"]
    change_result_evidence = store.resolve_record(
        fx.PROJECT_ID, "observation_evidence", ledger["change_result_evidence_id"]
    )
    members = change_result_evidence["lineage"]["derived_from"]["members"]
    before_refs = [
        m
        for m in members
        if m["kind"] == "observation" and m["id"] == ledger["before_observation_id"]
    ]
    assert before_refs
    assert (
        store.resolve_record(fx.PROJECT_ID, "observation", ledger["before_observation_id"])
        is not None
    )


def test_the_change_result_evidence_resolves_the_post_change_observation_it_names(
    tmp_path: Path,
) -> None:
    """Item 6: Change-result Evidence's own ``observed_result.observation_ref`` names the
    real post-change Observation, and it now resolves."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    ledger = result["identity_ledger"]
    change_result_evidence = store.resolve_record(
        fx.PROJECT_ID, "observation_evidence", ledger["change_result_evidence_id"]
    )
    ref = change_result_evidence["observed_result"]["observation_ref"]
    assert ref["id"] == ledger["change_result_observation_id"]
    assert store.resolve_record(fx.PROJECT_ID, ref["kind"], ref["id"]) is not None


def test_the_independent_verification_observation_resolves(tmp_path: Path) -> None:
    """Item 7: the independent re-observation Reflow's own G8 gate verifies is itself a
    real, resolvable persisted record (unchanged from Round 1/2; re-asserted here as this
    Finding's own required row)."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    ledger = result["identity_ledger"]
    assert (
        store.resolve_record(fx.PROJECT_ID, "observation", ledger["verification_observation_id"])
        is not None
    )


# --- negative controls ----------------------------------------------------------------------- #


def test_missing_auxiliary_verification_evidence_fails_closed(tmp_path: Path) -> None:
    """Item 9: omitting the provenance-only Evidence request the persisted verification
    Observation's own reference needs fails the whole route closed, before any
    State/Lineage/record/manifest mutation -- never a silently-dangling reference."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["provenance_only_evidence_requests"] = []
    with pytest.raises(ReflowValidationError, match="unresolved reference"):
        reflow(assembly["store"], **kwargs)

    fresh = FileStateStore(assembly["store"].root, schema_root=SCHEMA_ROOT)
    current = fresh.load_current(fx.PROJECT_ID)
    assert current["state_revision"] == assembly["genesis_state"]["state_revision"]
    assert fresh.reconstruct(fx.PROJECT_ID) == current


def test_a_tampered_referenced_body_is_detected_on_resolution(tmp_path: Path) -> None:
    """Item 10: a persisted record whose bytes are altered after commit -- naming an
    identity its own content no longer produces -- is detected the moment anything asks
    the Store to resolve it (the identical mechanism item E12 already proves, re-asserted
    here for the specific before-Observation this Finding newly persists)."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    ledger = result["identity_ledger"]
    before_id = ledger["before_observation_id"]
    record_path = (
        store.root / "projects" / fx.PROJECT_ID / "records" / "observation" / f"{before_id}.json"
    )
    assert record_path.is_file()
    body = json.loads(record_path.read_text(encoding="utf-8"))
    body["time_boundary"]["observation_started_at"] = "2020-01-01T00:00:00Z"
    record_path.write_text(json.dumps(body), encoding="utf-8")

    fresh = FileStateStore(store.root, schema_root=SCHEMA_ROOT)
    with pytest.raises(CorruptStoreError):
        fresh.resolve_record(fx.PROJECT_ID, "observation", before_id)


def test_same_kind_id_different_body_candidates_are_rejected() -> None:
    """Item 11: two independent reproduction paths that both claim the identical
    ``(kind, id)`` but disagree on body fail closed --
    ``SAME_KIND_ID_DIFFERENT_BODY=CORRUPTION_OR_VALIDATION_ERROR``, neither
    ``FIRST_BODY_WINS`` nor ``LAST_BODY_WINS``. This is the exact mechanism P8-R3-F1's own
    ``_admitted_observations_from_evidence_requests``/``_admitted_provenance_only_evidence``
    rely on whenever two Evidence requests independently reproduce the identical
    Observation or Evidence id (real content-addressed identities never collide by
    accident, so this is tested directly against the merge primitive itself, the way this
    codebase already unit-tests other pure content-address helpers, rather than contrived
    through the full ``reflow()`` route)."""

    from manosube_agent_civilization.reflow.route import _merge_verified_record

    records: dict[tuple[str, str], dict[str, Any]] = {}
    _merge_verified_record(records, "observation", {"observation_id": "OBS-X", "value": 1}, "OBS-X")
    with pytest.raises(ReflowValidationError):
        _merge_verified_record(
            records, "observation", {"observation_id": "OBS-X", "value": 2}, "OBS-X"
        )
    # The refusal raises before touching *records* at all -- the caller's own transaction
    # aborts and nothing commits, rather than silently keeping whichever body arrived
    # first (records["observation", "OBS-X"] is unchanged only because the merge attempt
    # never reaches the assignment, not because a resolution policy chose it).
    assert records[("observation", "OBS-X")]["value"] == 1


def test_fresh_file_state_store_reconstructs_the_identical_reference_closure(
    tmp_path: Path,
) -> None:
    """Item 13: a brand-new :class:`FileStateStore` instance, over only the persisted
    backend, reproduces the identical closure report -- never the in-process store object
    :func:`run_vertical_proof` itself returned."""

    result = run_vertical_proof(tmp_path)
    fresh = FileStateStore(result["store"].root, schema_root=SCHEMA_ROOT)
    original_report = _closure_report(result["store"], fx.PROJECT_ID)
    fresh_report = _closure_report(fresh, fx.PROJECT_ID)
    assert fresh_report["unresolved"] == []
    assert fresh_report["edges_checked"] == original_report["edges_checked"]


def test_a_fresh_python_process_reconstructs_the_identical_reference_closure(
    tmp_path: Path,
) -> None:
    """Item 14: process isolation is feasible here (a plain ``subprocess`` of the same
    interpreter) -- a brand-new Python process, holding none of this test's own in-process
    objects, reproduces the identical closure report over a pipe."""

    result = run_vertical_proof(tmp_path)
    store_root = str(result["store"].root)

    script = textwrap.dedent(
        f"""
        import json, pathlib, sys
        sys.path.insert(0, {str(Path.cwd())!r})
        from tests.fixtures import vertical_proof as fx
        from tests.natural_cycle.test_vertical_proof_reference_closure import _closure_report
        from manosube_agent_civilization.store import FileStateStore
        from tests.state_helpers import SCHEMA_ROOT
        store = FileStateStore(pathlib.Path({store_root!r}), schema_root=SCHEMA_ROOT)
        report = _closure_report(store, fx.PROJECT_ID)
        print(json.dumps({{"unresolved": report["unresolved"], "edge_count": len(report["edges_checked"])}}))
        """
    )
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=str(Path.cwd()),
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["unresolved"] == []
    assert payload["edge_count"] > 0


@pytest.mark.parametrize("stage", STAGES)
def test_crash_at_every_stage_never_exposes_a_partial_reference_graph_as_canonical(
    stage: str, tmp_path: Path
) -> None:
    """Item 15: the existing crash-injection stages (E8/E9's own mechanism) never expose a
    partially-admitted reference graph as canonical -- recovery converges to exactly
    genesis (no new records at all) or the one fully-closed successor (this Finding's own
    complete reference graph), never a State advanced without its own supporting records."""

    from tests.natural_cycle.proof import build_store

    def fault(current: str, _stage: str = stage) -> None:
        if current == _stage:
            raise SimulatedCrash(_stage)

    with pytest.raises(SimulatedCrash):
        run_vertical_proof(tmp_path, fault=fault)

    store = build_store(tmp_path)
    store.recover(fx.PROJECT_ID)
    current = store.load_current(fx.PROJECT_ID)
    if current["state_revision"] == 0:
        return
    report = _closure_report(store, fx.PROJECT_ID)
    assert report["unresolved"] == []


def test_provenance_only_evidence_never_changes_sufficiency_or_resolution_mode(
    tmp_path: Path,
) -> None:
    """Item 16: admitting the auxiliary provenance-only Evidence changes nothing about the
    real Sufficiency verdict or the Candidate's own resolution_mode -- it is reproduced and
    persisted entirely outside evaluate_closure/evaluate_sufficiency."""

    result = run_vertical_proof(tmp_path)
    assert result["sufficiency"]["result"]["result"] == "SUFFICIENT"
    assert result["reflow_result"]["evaluation"]["resolution_mode"] == "CHANGE_BOUND"


def test_the_successful_route_still_reaches_closed(tmp_path: Path) -> None:
    """Item 17: the required successful route (Issue #41 item D) still reaches CLOSED with
    this Finding's own additional persistence in place."""

    result = run_vertical_proof(tmp_path)
    assert result["reflow_result"]["decision"]["to_status"] == "CLOSED"


def test_a_real_non_closed_route_still_persists_and_reconstructs(tmp_path: Path) -> None:
    """Item 18: the real, committed non-CLOSED (RETAINED) route P8-R1-F2 proved still
    commits and reconstructs identically with this Finding's own additional persistence in
    place."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    closure_request = dict(kwargs["closure_request"])
    sufficiency_request = dict(closure_request["evidence_sufficiency_request"])
    sufficiency_request["evidence_requests"] = []
    closure_request["evidence_sufficiency_request"] = sufficiency_request
    closure_request["proposed_terminal_status"] = "RETAINED"
    closure_request["terminal_reason_evidence_refs"] = [
        {
            "kind": "observation_evidence",
            "id": assembly["before"]["observation_evidence"]["evidence_id"],
        }
    ]
    closure_request["terminal_reason_evidence_requests"] = [
        assembly["before"]["observation_evidence_request"]
    ]
    kwargs["closure_request"] = closure_request
    kwargs["next_observation_ref"] = {
        "kind": "observation",
        "id": assembly["verification_observation_id"],
    }

    result = reflow(assembly["store"], **kwargs)
    assert result["decision"]["to_status"] == "RETAINED"

    fresh = FileStateStore(assembly["store"].root, schema_root=SCHEMA_ROOT)
    assert fresh.reconstruct(fx.PROJECT_ID) == fresh.load_current(fx.PROJECT_ID)


# --- P8-R4-F1: unconditional Reference Closure (no opt-in) ----------------------------------- #


def test_reference_closure_is_unconditional_no_opt_in_keyword_needed(tmp_path: Path) -> None:
    """P8-R4-F1 item: omitting ``provenance_only_evidence_requests``/``auxiliary_source_
    snapshots`` entirely (never opting in at all) still fails the route closed on the same
    unresolved auxiliary references -- ``REFERENCE_CLOSURE_OPT_IN_ALLOWED=false``: the
    invariant holds by default, not only when a caller opts into it by passing the keyword."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs.pop("provenance_only_evidence_requests", None)
    kwargs.pop("auxiliary_source_snapshots", None)
    with pytest.raises(ReflowValidationError, match="unresolved"):
        reflow(assembly["store"], **kwargs)


def test_reference_closure_still_holds_with_an_explicitly_empty_provenance_list(
    tmp_path: Path,
) -> None:
    """An emptied ``provenance_only_evidence_requests=[]`` does not weaken the invariant --
    the same unresolved-reference refusal fires whether the keyword is omitted or passed
    empty, proving the gate is not merely toggled by the keyword's own presence."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["provenance_only_evidence_requests"] = []
    with pytest.raises(ReflowValidationError, match="unresolved reference"):
        reflow(assembly["store"], **kwargs)


# --- P8-R4-F2: Source Snapshot reference closure ---------------------------------------------- #


def test_source_snapshot_edges_are_actually_emitted_by_the_production_registry() -> None:
    """P8-R4-F2 item: the production registry recognizes ``source_snapshot`` as a
    Store-owned reference target and actually emits an edge for an observation's own
    ``source_snapshot_refs`` entry -- proving the registry does not vacuously skip the
    kind Round 3's own test-local vocabulary omitted."""

    assert "source_snapshot" in STORE_OWNED_REFERENCE_KINDS
    observation_body = {
        "source_snapshot_refs": [{"kind": "source_snapshot", "id": "SNAP-REAL-0001"}],
        "observation_evidence_refs": [],
    }
    edges = reference_edges("observation", observation_body)
    assert ("source_snapshot", "SNAP-REAL-0001") in edges


def test_missing_source_snapshot_fails_closed_before_any_write(tmp_path: Path) -> None:
    """P8-R4-F2 item: removing the auxiliary before-Observation's own required Source
    Snapshot from the pool fails the whole route closed -- the production
    ``except ObservationError: continue`` pattern this Finding forbids no longer silently
    admits an unresolved Source Snapshot reference."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs["auxiliary_source_snapshots"] = []
    with pytest.raises(ReflowValidationError):
        reflow(assembly["store"], **kwargs)

    fresh = FileStateStore(assembly["store"].root, schema_root=SCHEMA_ROOT)
    current = fresh.load_current(fx.PROJECT_ID)
    assert current["state_revision"] == assembly["genesis_state"]["state_revision"]
    assert fresh.reconstruct(fx.PROJECT_ID) == current


# --- P8-R4-F3: Difference genesis-event reference closure ------------------------------------- #


def test_the_genesis_lifecycle_event_resolves_from_a_fresh_store(tmp_path: Path) -> None:
    """P8-R4-F3 item: the Difference's own genesis lifecycle event (revision 0) -- named by
    ``difference.genesis_event_ref``/``closure_evaluation.difference_event_head_ref`` on the
    very first Reflow cycle -- is persisted, and a brand-new :class:`FileStateStore` over
    only the persisted backend can resolve it."""

    result = run_vertical_proof(tmp_path)
    genesis_ref = result["identity_ledger"]["difference_lifecycle_head_ref"]
    fresh = FileStateStore(result["store"].root, schema_root=SCHEMA_ROOT)
    genesis_event = fresh.resolve_record(fx.PROJECT_ID, "difference_event", genesis_ref["id"])
    assert genesis_event is not None
    assert genesis_event["event_revision"] == 0
    assert genesis_event["previous_event_id"] is None
    assert genesis_event["difference_id"] == result["difference"]["difference_id"]


def test_the_closure_evaluations_difference_event_head_ref_resolves(tmp_path: Path) -> None:
    """P8-R4-F3 item: the persisted ``closure_evaluation`` record's own
    ``difference_event_head_ref`` -- the genesis event, on the first cycle -- resolves
    through the public Store API, not only through the Evaluation's own bare claim."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    closure_evaluation_id = result["reflow_result"]["evaluation"]["closure_evaluation_id"]
    closure_evaluation = store.resolve_record(
        fx.PROJECT_ID, "closure_evaluation", closure_evaluation_id
    )
    assert closure_evaluation is not None
    head_ref = closure_evaluation["difference_event_head_ref"]
    assert store.resolve_record(fx.PROJECT_ID, head_ref["kind"], head_ref["id"]) is not None
    assert head_ref["id"] == result["identity_ledger"]["difference_lifecycle_head_ref"]["id"]


def test_missing_genesis_lifecycle_event_fails_closed_before_any_write(tmp_path: Path) -> None:
    """P8-R4-F3 item: omitting ``genesis_lifecycle_event`` on the very first Reflow cycle
    fails the whole route closed (its id can never otherwise resolve), never a silently
    unresolvable ``difference_event_head_ref``/genesis reference."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    kwargs.pop("genesis_lifecycle_event", None)
    with pytest.raises(ReflowValidationError, match="unresolved reference"):
        reflow(assembly["store"], **kwargs)

    fresh = FileStateStore(assembly["store"].root, schema_root=SCHEMA_ROOT)
    current = fresh.load_current(fx.PROJECT_ID)
    assert current["state_revision"] == assembly["genesis_state"]["state_revision"]
    assert fresh.reconstruct(fx.PROJECT_ID) == current


def test_a_genesis_event_with_a_tampered_body_fails_its_own_content_address(
    tmp_path: Path,
) -> None:
    """P8-R4-F3 item: a ``genesis_lifecycle_event`` whose body was altered after the real
    Difference owner produced it (so it no longer reproduces its own claimed id) is refused
    -- ``CALLER_SUPPLIED_CANONICAL_BODY_MAY_BE_TRUSTED=false``."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    tampered = dict(kwargs["genesis_lifecycle_event"])
    tampered_fingerprint = dict(tampered["state_fingerprint_evaluated"])
    tampered_fingerprint["digest"] = "0" * 64
    tampered["state_fingerprint_evaluated"] = tampered_fingerprint
    kwargs["genesis_lifecycle_event"] = tampered
    with pytest.raises(ReflowValidationError, match="content address"):
        reflow(assembly["store"], **kwargs)

    fresh = FileStateStore(assembly["store"].root, schema_root=SCHEMA_ROOT)
    current = fresh.load_current(fx.PROJECT_ID)
    assert current["state_revision"] == assembly["genesis_state"]["state_revision"]


def test_a_genesis_event_naming_a_different_id_than_genesis_event_ref_fails_closed(
    tmp_path: Path,
) -> None:
    """P8-R4-F3 item: a *self-consistent* genesis event (its own content address recomputes
    correctly) that nonetheless does not match ``difference.genesis_event_ref.id`` is still
    refused -- a real, well-formed body is not sufficient if it is not *this* Difference's
    own genesis event."""

    assembly = assemble_vertical_proof_route(tmp_path)
    kwargs = dict(assembly["reflow_kwargs"])
    genesis_event = dict(kwargs["genesis_lifecycle_event"])
    tampered_fingerprint = dict(genesis_event["state_fingerprint_evaluated"])
    tampered_fingerprint["digest"] = "0" * 64
    genesis_event["state_fingerprint_evaluated"] = tampered_fingerprint
    from manosube_agent_civilization.difference.identity import lifecycle_event_id

    genesis_event["difference_event_id"] = lifecycle_event_id(genesis_event)
    kwargs["genesis_lifecycle_event"] = genesis_event
    with pytest.raises(ReflowValidationError, match="genesis_event_ref"):
        reflow(assembly["store"], **kwargs)

    fresh = FileStateStore(assembly["store"].root, schema_root=SCHEMA_ROOT)
    current = fresh.load_current(fx.PROJECT_ID)
    assert current["state_revision"] == assembly["genesis_state"]["state_revision"]


def test_genesis_event_survives_replaying_the_same_committed_transaction(
    tmp_path: Path,
) -> None:
    """P8-R4-F3 item: replaying the exact committed transaction id with the identical
    canonical inputs (the Store's own idempotent-commit contract, ``FileStateStore.commit``)
    is a true no-op over the manifest that includes the genesis event -- never a duplicate
    or a second, diverging body under the same id."""

    result = run_vertical_proof(tmp_path)
    store = result["store"]
    genesis_ref = result["identity_ledger"]["difference_lifecycle_head_ref"]
    tx_id = result["reflow_result"]["state_transition_ref"]["id"]

    tx_root = store.root / "projects" / fx.PROJECT_ID / "state" / "recovery" / tx_id
    event = json.loads((tx_root / "event.json").read_text())
    manifest = [tuple(item) for item in json.loads((tx_root / "manifest.json").read_text())]
    records = [
        (kind, record_id, store.resolve_record(fx.PROJECT_ID, kind, record_id))
        for kind, record_id in manifest
    ]

    before_current = store.load_current(fx.PROJECT_ID)
    replayed = store.commit(
        fx.PROJECT_ID,
        event["from_revision"],
        event["before_fingerprint"],
        event["after_state"],
        event,
        records=records,
    )
    assert replayed == before_current
    assert store.resolve_record(fx.PROJECT_ID, "difference_event", genesis_ref["id"]) is not None


@pytest.mark.parametrize("stage", STAGES)
def test_crash_at_every_stage_never_exposes_a_partial_genesis_or_revision_one_event(
    stage: str, tmp_path: Path
) -> None:
    """P8-R4-F3 item: every crash-injection stage converges to exactly genesis (no new
    records) or the one fully-closed successor -- never a State advanced with only the
    genesis event visible and the revision-1 event missing, or vice versa (they are staged
    and promoted in the same atomic Store transaction)."""

    from tests.natural_cycle.proof import build_store

    def fault(current: str, _stage: str = stage) -> None:
        if current == _stage:
            raise SimulatedCrash(_stage)

    with pytest.raises(SimulatedCrash):
        run_vertical_proof(tmp_path, fault=fault)

    store = build_store(tmp_path)
    store.recover(fx.PROJECT_ID)
    current = store.load_current(fx.PROJECT_ID)
    if current["state_revision"] == 0:
        return
    report = _closure_report(store, fx.PROJECT_ID)
    assert report["unresolved"] == []
    kinds_seen = {kind for kind, _, _ in report["manifest_records"]}
    assert "difference_event" in kinds_seen
