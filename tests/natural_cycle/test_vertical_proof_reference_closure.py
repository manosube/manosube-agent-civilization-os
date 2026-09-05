"""Phase 8 Vertical Proof -- persisted-reference-graph closure proof (P8-R3-F1, SHUKOU
Phase 8 final-closure round 3).

Round 2 proved the *accepted request graph* carried no placeholder Evidence id
(``test_vertical_proof.py::test_the_evidence_fixed_point_closes_across_the_full_accepted_
request_graph``). That is a different claim from this one: a persisted verification
Observation's own ``observation_evidence_refs`` genuinely named a real, well-formed
auxiliary Change-Free Verification Evidence id -- but that Evidence was never itself
persisted, so the reference did not resolve. The before-Observation and post-change
Observation the two real Evidence records already persisted (Observation Evidence,
Change-result Evidence) also declared, but never actually adopted.

This file proves ``PERSISTED_REFERENCE_GRAPH_CLOSED=true`` /
``UNRESOLVED_STORE_OWNED_REFERENCE_COUNT=0`` over the closed, explicitly-managed reference
vocabulary this Finding is about: an ``observation`` record's own ``source_snapshot_refs``
and ``observation_evidence_refs``, and an ``observation_evidence`` record's own
``observed_result.observation_ref``, ``lineage.derived_from`` (``observation``-kind members
only), and ``lineage.predecessor_evidence_refs``. References this Kernel names but never
gives a Store-owned producer of its own -- ``difference``, ``change``, ``authority_
decision``, ``artifact``, ``negative_evidence`` (no second canonical owner is created for
any of them here, or anywhere else in this vertical) -- are out of this proof's scope, not
silently treated as resolved; ``closure_evaluation.difference_event_head_ref`` in
particular names the Difference's own genesis lifecycle event, which this Kernel's own
design never persists as a separate ``difference_event`` record at genesis time (confirmed
directly: it does not resolve even before any ``reflow()`` call), and that pre-existing,
causally-unrelated non-resolution is disclosed here rather than folded into this proof's own
claim.

The recognition rule for a reference is structural, not a text search over key names: a
dict shaped like ``common/reference.schema.json`` (``kind``+``id``, both non-empty
strings), with ``kind`` restricted to :data:`STORE_OWNED_KINDS_IN_SCOPE` -- explicit and
reviewed, never "any key ending in ``_ref``/``_refs``".

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
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.store import STAGES, FileStateStore
from manosube_agent_civilization.store.errors import CorruptStoreError, SimulatedCrash

#: The two record kinds this Finding's own reference-closure claim is about, and the
#: only kinds :data:`STORE_OWNED_KINDS_IN_SCOPE` below ever names as a reference *target*.
STORE_OWNED_KINDS_IN_SCOPE = frozenset({"observation", "observation_evidence"})


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


def _in_scope_reference_edges(kind: str, body: dict[str, Any]) -> list[tuple[str, str]]:
    """The explicit, per-kind reference edges this closure proof recognizes -- never a
    fuzzy text search over key names. Only ``observation`` and ``observation_evidence``
    records are inspected, and only their own known reference-bearing fields."""

    edges: list[tuple[str, str]] = []

    def _edge(ref: Any) -> None:
        if (
            isinstance(ref, dict)
            and isinstance(ref.get("kind"), str)
            and ref["kind"] in STORE_OWNED_KINDS_IN_SCOPE
            and isinstance(ref.get("id"), str)
            and ref["id"]
        ):
            edges.append((ref["kind"], ref["id"]))

    if kind == "observation":
        for ref in body.get("source_snapshot_refs") or []:
            _edge(ref)
        for ref in body.get("observation_evidence_refs") or []:
            _edge(ref)
    elif kind == "observation_evidence":
        observed_result = body.get("observed_result") or {}
        _edge(observed_result.get("observation_ref"))
        lineage = body.get("lineage") or {}
        for ref in (lineage.get("derived_from") or {}).get("members") or []:
            _edge(ref)
        for ref in (lineage.get("predecessor_evidence_refs") or {}).get("members") or []:
            _edge(ref)
    return edges


def _closure_report(store: Any, project_id: str) -> dict[str, Any]:
    """Walk every manifest record's own in-scope reference edges and resolve each --
    ``PLACEHOLDER_STRING_ABSENCE`` alone is not completion; every real, in-scope reference
    this committed graph declares must resolve through the public Store API."""

    manifest_records = _manifest_records(store, project_id)
    edges_checked: set[tuple[str, str]] = set()
    unresolved: list[tuple[str, str, str, str]] = []
    for kind, record_id, body in manifest_records:
        for ref_kind, ref_id in _in_scope_reference_edges(kind, body):
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
    assert {"observation", "observation_evidence"} <= kinds_seen


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
    with pytest.raises(ReflowValidationError, match="observation_evidence_refs"):
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
