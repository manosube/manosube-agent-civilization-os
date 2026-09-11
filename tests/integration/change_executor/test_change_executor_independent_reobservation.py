"""P18-R1-F1 (Structural Review Round 1, ADOPT_P18_R1_STRUCTURAL_CORRECTIONS) and P18-R2-F1
(Structural Review Round 2, ADOPT_P18_R2_STRUCTURAL_CORRECTIONS): independent after-state
re-observation gates ``VERIFIED``.

(a) **Negative control (P18-R1-F1)**: a receipt claiming ``outcome == "SUCCEEDED"`` whose own
embedded ``independent_after_state_observation`` disagrees (forged/mismatched, or simply not
``"MATCHED"``) must be refused by ``route_change_execution_to_evidence`` -- never silently
derived as ``VERIFIED``.

(a2) **Negative control (P18-R2-F1)**: R2_F1_NEGATIVE -- a receipt claiming ``outcome ==
"SUCCEEDED"`` whose own embedded ``independent_after_state_observation`` is *forged to agree*
(``"MATCHED"``, passing the P18-R1-F1 check above cleanly), but whose *actual* real on-disk bytes
(written directly by this test, independently of anything the receipt claims) genuinely disagree
with what the receipt's own ``operation`` requested, must still be refused -- proving the fix is
not merely re-trusting the same embedded field a second time under a different name: this is a
real, independent disagreement this hand-off's own SECOND, handoff-time-only re-read discovers.

(b) **Positive control (P18-R1-F1 and R2_F1_POSITIVE)**: a genuine ``execute()`` call through the
real route, with a real ``ControlledFilesystemAdapter`` writing the exact requested content to
real disk, must produce a receipt whose own ``independent_after_state_observation["outcome"] ==
"MATCHED"``, and ``route_change_execution_to_evidence`` must derive ``VERIFIED`` for it -- and the
SECOND, independently-performed, handoff-time re-read this hand-off itself performs must itself
independently confirm the real, freshly-read on-disk content (never merely re-trust the receipt's
own embedded field).

(d) **R3_F1_NEGATIVE (P18-R3-F1, Structural Review Round 3)**: the minted verification
Observation must itself be resolved back and bound to the receipt's own target/scope/operation --
never trusted merely because ``derive_evidence`` returned without raising. A genuine, otherwise
fully valid ``derive_evidence`` call whose returned Evidence record's own
``observed_result.observation_ref.id`` has been tampered (wrapped so it no longer equals the
identity this hand-off independently recomputes from the exact ``verification_observation_
request`` it built) must be refused by ``route_change_execution_to_evidence`` -- proving the two
pre-existing post-call checks (``verification_result_provenance`` self-comparison,
``target.project_id`` equality) are no longer the only thing standing between a receipt and a
``VERIFIED`` Evidence record. A second, white-box test additionally proves
``_expected_verification_observation_id`` is genuinely sensitive to the exact fields it is
supposed to be sensitive to (an added, unrequested ``source_snapshot_refs`` entry changes the
recomputed identity), never a function that would silently agree with anything handed to it.

(e) **R4_F1 (P18-R4-F1, Structural Review Round 4)**: observation identity equality (R3_F1's own
fix) proves *which* Observation grounds an Evidence record, but ``observation_id`` excludes
``source_occurrences``, their outcomes, and the derived ``status`` itself -- so equal identity
alone never proved the minted Observation actually *resolved* anything. Structural Review Round 4
reproduced a decisive counterexample at the prior head: a genuine ``SUCCEEDED`` receipt's second,
independent re-read still produced a minted Observation whose own ``status`` was ``INCOMPLETE``
(the Scope's ``observation_window``/``cutoff`` this hand-off built were still the *base* request's
own stale, pre-execution values, so ``observation.boundary.time_boundary_within_scope`` always
failed for a later, handoff-time re-read), while ``verification_result_provenance.status`` was
still ``VERIFIED`` regardless -- the receipt's own outcome, not the Observation, determined the
promotion. This round's fix is two-part: (i) :func:`_build_verification_observation_request` now
rebuilds the Scope's own ``observation_window``/``cutoff`` around the fresh ``captured_at`` instant
itself, and attaches one real ``attempts`` entry, so a genuinely successful re-read now reaches a
decisive ``EMPTY`` status (this module never asserts domain Facts, so ``COMPLETE`` is never
reachable, but ``EMPTY`` -- collection genuinely completed, nothing to report -- is the honest,
decisive result); (ii) ``route_change_execution_to_evidence`` now additionally requires, whenever
the receipt's own outcome precomputed ``VERIFIED``, that the resolved Observation's own
``observed_result.observation_status`` be a member of
:data:`~manosube_agent_civilization.change_executor.evidence_handoff.
_ADMISSIBLE_VERIFIED_OBSERVATION_STATUSES` (``{"COMPLETE", "EMPTY"}``) -- refusing outright rather
than returning a record whose own embedded facts contradict its own claimed status. The first test
below proves the genuine positive route no longer accidentally reaches ``INCOMPLETE`` at all; the
second is a decisive negative control that tampers only the resolved Observation's own status
(identity kept genuine) and proves the post-call gate refuses it regardless.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from tests.evidence_helpers import change_free_verification_evidence_request
from tests.fixtures.change_executor_kill_switch_issuer import issuer_public_key_hex
from tests.fixtures.change_executor_world import (
    CountingAdapter,
    bound,
    build_committed_change,
    commit_active_kill_switch,
    execution_boundary_for,
    git_worktree,
    operation_for,
    plant_terminal_receipt,
)

from manosube_agent_civilization.change_executor import evidence_handoff as evidence_handoff_module
from manosube_agent_civilization.change_executor.errors import ChangeExecutorError
from manosube_agent_civilization.change_executor.evidence_handoff import (
    route_change_execution_to_evidence,
)
from manosube_agent_civilization.change_executor.route import compose_change_executor
from manosube_agent_civilization.evidence import derive_evidence as _real_derive_evidence

_ADAPTER_IDENTITY = {"kind": "controlled_filesystem_adapter", "version": "0.1"}


def _rebind_project(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        return {key: _rebind_project(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [_rebind_project(item, old, new) for item in value]
    return new if value == old else value


# --------------------------------------------------------------------------------------- #
# (a) negative: a forged/disagreeing independent_after_state_observation on a SUCCEEDED
# receipt is refused, never derived as VERIFIED.
# --------------------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "forged_observation",
    (
        {
            "outcome": "MISMATCH",
            "checked_files": [{"path": "docs/x.md", "kind": "write", "status": "MISMATCH"}],
        },
        {"outcome": "NOT_PERFORMED", "checked_files": []},
        {
            "outcome": "MISSING",
            "checked_files": [{"path": "docs/x.md", "kind": "write", "status": "MISSING"}],
        },
    ),
)
def test_forged_succeeded_receipt_with_disagreeing_reobservation_is_refused(
    tmp_path: Path, forged_observation: dict[str, Any]
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE", writes=[{"path": "docs/x.md", "content_utf8": "hello"}]
        ),
        paths=["docs/x.md"],
    )
    change = result["change"]

    worktree = git_worktree(tmp_path)
    boundary = execution_boundary_for(worktree_root=str(worktree))

    # A genuine, real, schema-valid, self-consistent receipt (built by the real
    # engine.build_change_execution_receipt, never hand-forged) -- claiming SUCCEEDED, but with
    # its own independent_after_state_observation deliberately disagreeing. route.py itself would
    # never construct this combination (F1's own gate at classification time); this receipt is
    # planted directly to prove evidence_handoff's own defensive re-check refuses it regardless.
    forged = plant_terminal_receipt(
        store,
        project_id,
        change,
        result["decision"],
        boundary,
        _ADAPTER_IDENTITY,
        project_binding_id=info["project_binding_id"],
        worktree_root=str(worktree),
        claim_token="forged-claim",  # noqa: S106
        outcome="SUCCEEDED",
        performed_result_summary={
            "files_written": ["docs/x.md"],
            "bytes_written": 5,
            "files_deleted": [],
        },
        independent_after_state_observation=forged_observation,
    )

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    # (P18-R2-F1, Structural Review Round 2) route_change_execution_to_evidence now constructs
    # verification_observation_request itself, from a second, independent, handoff-time-only
    # re-read of the real resulting filesystem state -- it must not be caller-supplied.
    evidence_request["verification_observation_request"] = None
    with pytest.raises(ChangeExecutorError):
        route_change_execution_to_evidence(store, forged, project_id, evidence_request)


# --------------------------------------------------------------------------------------- #
# (a2) R2_F1_NEGATIVE: a receipt whose own embedded independent_after_state_observation is
# forged to MATCH, but whose real on-disk bytes genuinely disagree, is still refused -- proving
# the fix is a real, independent disagreement (this hand-off's own second, handoff-time-only
# re-read), never a re-check of the same embedded dict route.py itself already computed.
# --------------------------------------------------------------------------------------- #


def test_second_independent_reread_disagreement_refuses_a_receipt_forged_to_match(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)
    requested_content = "the real requested content"
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/second-reread.md", "content_utf8": requested_content}],
        ),
        paths=["docs/second-reread.md"],
    )
    change = result["change"]

    worktree = git_worktree(tmp_path)
    boundary = execution_boundary_for(worktree_root=str(worktree))

    # Real, DIFFERENT bytes are written directly to disk -- never through the adapter, never
    # matching what the receipt's own operation requests -- simulating a receipt whose own
    # embedded independent_after_state_observation was forged (or is simply stale/wrong) to
    # claim MATCHED regardless of what is actually on disk.
    (worktree / "docs").mkdir(parents=True, exist_ok=True)
    (worktree / "docs" / "second-reread.md").write_text(
        "DIFFERENT bytes than what was ever requested", encoding="utf-8"
    )

    forged_matching = plant_terminal_receipt(
        store,
        project_id,
        change,
        result["decision"],
        boundary,
        _ADAPTER_IDENTITY,
        project_binding_id=info["project_binding_id"],
        worktree_root=str(worktree),
        claim_token="forged-matching-claim",  # noqa: S106
        outcome="SUCCEEDED",
        performed_result_summary={
            "files_written": ["docs/second-reread.md"],
            "bytes_written": len(requested_content.encode("utf-8")),
            "files_deleted": [],
        },
        independent_after_state_observation={
            "outcome": "MATCHED",
            "checked_files": [
                {"path": "docs/second-reread.md", "kind": "write", "status": "MATCHED"}
            ],
        },
    )

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    evidence_request["verification_observation_request"] = None
    with pytest.raises(ChangeExecutorError):
        route_change_execution_to_evidence(store, forged_matching, project_id, evidence_request)


# --------------------------------------------------------------------------------------- #
# (b) positive: a genuine execute() call's own receipt carries a MATCHED independent
# re-observation, and route_change_execution_to_evidence genuinely derives VERIFIED for it.
# --------------------------------------------------------------------------------------- #


def test_genuine_execution_carries_a_matched_independent_reobservation_and_derives_verified(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)

    content = "# Independent Reobservation Proof\n\nWritten by a real adapter call.\n"
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/reobservation_proof.md", "content_utf8": content}],
        ),
        paths=["docs/reobservation_proof.md"],
    )
    change = result["change"]

    worktree_root = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree_root)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    outcome = execute(
        change["change_id"],
        claim_token="genuine-reobservation-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "SUCCEEDED"
    assert receipt["independent_after_state_observation"] == {
        "outcome": "MATCHED",
        "checked_files": [
            {"path": "docs/reobservation_proof.md", "kind": "write", "status": "MATCHED"}
        ],
    }

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    # (P18-R2-F1, Structural Review Round 2) route_change_execution_to_evidence now constructs
    # verification_observation_request itself, from a second, independent, handoff-time-only
    # re-read of the real resulting filesystem state -- it must not be caller-supplied.
    evidence_request["verification_observation_request"] = None
    evidence = route_change_execution_to_evidence(store, receipt, project_id, evidence_request)
    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
    assert (
        evidence["verification_result_provenance"]["observations"][
            "independent_after_state_observation"
        ]
        == receipt["independent_after_state_observation"]
    )

    # R2_F1_POSITIVE: the SECOND, independently-performed, handoff-time-only re-read this
    # hand-off itself performs (never the receipt's own embedded field) genuinely reflects real,
    # freshly-read file content -- proven directly, in white-box fashion, by calling the same
    # internal re-read this hand-off calls and independently confirming its own real snapshot
    # digests equal a real, independently-computed SHA-256 of the actual bytes on disk at test
    # time.
    snapshots, _occurrences, matches = (
        evidence_handoff_module._second_independent_after_state_reread(
            receipt["operation"],
            receipt["target"]["worktree_root"],
            captured_at="2026-08-30T10:00:00Z",
        )
    )
    assert matches is True
    assert len(snapshots) == 1
    real_bytes = (worktree_root / "docs" / "reobservation_proof.md").read_bytes()
    assert snapshots[0]["content_digest"] == "sha256:" + hashlib.sha256(real_bytes).hexdigest()
    assert snapshots[0]["source_locator"] == "docs/reobservation_proof.md"


# --------------------------------------------------------------------------------------- #
# (c) an adapter that writes the wrong content is caught: outcome is reclassified as
# REOBSERVATION_MISMATCH, and the hand-off derives FAILED, never VERIFIED.
# --------------------------------------------------------------------------------------- #


class _LyingAdapter:
    """A real adapter (delegates to a genuine ``ControlledFilesystemAdapter``) that writes
    deliberately *different* content than requested, then falsely reports the requested content
    was written -- the exact scenario independent re-observation exists to catch: the adapter's
    own self-reported facts (``files_written``) claim full success, but the actual on-disk bytes
    disagree with what was requested."""

    def __init__(self) -> None:
        from manosube_agent_civilization.change_executor.adapter import ControlledFilesystemAdapter

        self._inner = ControlledFilesystemAdapter(
            executor_identity="controlled_filesystem_adapter", executor_version="0.1"
        )
        self.call_count = 0

    def execute(self, operation: Any, *, worktree_root: str) -> dict[str, Any]:
        self.call_count += 1
        tampered_operation = {
            **operation,
            "file_writes": [
                {"path": entry["path"], "content_utf8": "TAMPERED-CONTENT-NEVER-REQUESTED"}
                for entry in operation.get("file_writes", [])
            ],
        }
        raw: dict[str, Any] = self._inner.execute(tampered_operation, worktree_root=worktree_root)
        return raw


def test_adapter_writing_wrong_content_is_caught_as_reobservation_mismatch(
    tmp_path: Path,
) -> None:
    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)

    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/lied-about.md", "content_utf8": "the real requested content"}],
        ),
        paths=["docs/lied-about.md"],
    )
    change = result["change"]

    worktree_root = git_worktree(tmp_path)
    adapter = _LyingAdapter()
    execute = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree_root)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )

    outcome = execute(
        change["change_id"],
        claim_token="lied-about-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "REOBSERVATION_MISMATCH"
    assert receipt["independent_after_state_observation"]["outcome"] == "MISMATCH"
    assert adapter.call_count == 1

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    # (P18-R2-F1, Structural Review Round 2) route_change_execution_to_evidence now constructs
    # verification_observation_request itself, from a second, independent, handoff-time-only
    # re-read of the real resulting filesystem state -- it must not be caller-supplied.
    evidence_request["verification_observation_request"] = None
    evidence = route_change_execution_to_evidence(store, receipt, project_id, evidence_request)
    assert evidence["verification_result_provenance"]["status"] == "FAILED"

    # A second call for the identical slot replays the identical REOBSERVATION_MISMATCH receipt
    # -- never re-calling the adapter, never silently upgrading it.
    replay = execute(
        change["change_id"],
        claim_token="lied-about-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:02Z",
    )
    assert replay["replay"] is True
    assert replay["receipt"] == receipt
    assert adapter.call_count == 1


# --------------------------------------------------------------------------------------- #
# (d) R3_F1_NEGATIVE (P18-R3-F1, Structural Review Round 3): the minted verification
# Observation must itself be resolved back and bound to the receipt's own target/scope/
# operation -- never trusted merely because derive_evidence returned without raising.
# --------------------------------------------------------------------------------------- #


def test_evidence_with_a_tampered_grounding_observation_reference_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A genuine, otherwise fully valid ``derive_evidence`` call whose returned Evidence
    record's own ``observed_result.observation_ref.id`` has been tampered (wrapped so it no
    longer equals the identity this hand-off independently recomputes from the exact
    ``verification_observation_request`` it built) must be refused -- proving the fix is a real
    resolve-and-check of the minted Observation, not merely the two pre-existing self-referential
    post-call checks (``verification_result_provenance`` compared to itself, ``target.
    project_id`` equality)."""

    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)

    content = "# R3-F1 grounding-observation proof\n"
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/r3-f1-grounding.md", "content_utf8": content}],
        ),
        paths=["docs/r3-f1-grounding.md"],
    )
    change = result["change"]

    worktree_root = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree_root)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )
    outcome = execute(
        change["change_id"],
        claim_token="r3-f1-grounding-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "SUCCEEDED"

    # Wrap (never replace the logic of) the real derive_evidence: every real check it performs
    # still runs in full -- only the returned record's own grounding Observation reference is
    # tampered afterward, simulating an Evidence owner whose report of what it minted cannot be
    # taken on faith.
    def _tampering_derive_evidence(request: Any) -> dict[str, Any]:
        genuine = _real_derive_evidence(request)
        tampered = dict(genuine)
        tampered_observed_result = dict(tampered["observed_result"])
        tampered_observed_result["observation_ref"] = {
            "kind": "observation",
            "id": "OBS-" + "0" * 64,
        }
        tampered["observed_result"] = tampered_observed_result
        return tampered

    monkeypatch.setattr(evidence_handoff_module, "derive_evidence", _tampering_derive_evidence)

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    evidence_request["verification_observation_request"] = None
    with pytest.raises(ChangeExecutorError, match="P18-R3-F1"):
        route_change_execution_to_evidence(store, receipt, project_id, evidence_request)


def test_expected_verification_observation_id_is_sensitive_to_an_unrequested_source_snapshot_ref(
    tmp_path: Path,
) -> None:
    """White-box proof that ``_expected_verification_observation_id`` is genuinely sensitive to
    the exact fields it is supposed to be sensitive to -- never a function that would silently
    agree with anything handed to it. An extra, unrequested ``source_snapshot_refs`` entry that
    no real re-read ever produced must change the recomputed identity."""

    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)

    content = "# R3-F1 sensitivity proof\n"
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/r3-f1-sensitivity.md", "content_utf8": content}],
        ),
        paths=["docs/r3-f1-sensitivity.md"],
    )
    change = result["change"]

    worktree_root = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree_root)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )
    outcome = execute(
        change["change_id"],
        claim_token="r3-f1-sensitivity-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "SUCCEEDED"

    captured_at = "2026-09-10T00:00:02Z"
    snapshots, occurrences, matches = (
        evidence_handoff_module._second_independent_after_state_reread(
            receipt["operation"], receipt["target"]["worktree_root"], captured_at=captured_at
        )
    )
    assert matches is True

    fresh_state = store.load_current(project_id)
    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    verification_observation_request = (
        evidence_handoff_module._build_verification_observation_request(
            evidence_request["observation_request"],
            project_id=project_id,
            fresh_state_revision=fresh_state["state_revision"],
            fresh_state_fingerprint=fresh_state["semantic_fingerprint"],
            snapshots=snapshots,
            occurrences=occurrences,
            captured_at=captured_at,
        )
    )

    genuine_id = evidence_handoff_module._expected_verification_observation_id(
        verification_observation_request
    )

    altered_request = dict(verification_observation_request)
    altered_request["source_snapshot_refs"] = [
        *verification_observation_request["source_snapshot_refs"],
        {"kind": "source_snapshot", "id": "SNAP-R3-F1-UNREQUESTED-EXTRA"},
    ]
    altered_id = evidence_handoff_module._expected_verification_observation_id(altered_request)

    assert altered_id != genuine_id
    # And recomputing from the genuine, unaltered request is deterministic/repeatable.
    assert (
        evidence_handoff_module._expected_verification_observation_id(
            verification_observation_request
        )
        == genuine_id
    )


# --------------------------------------------------------------------------------------- #
# (e) P18-R4-F1 (Structural Review Round 4): the minted verification Observation's own
# resolved status must be decisive before a receipt's precomputed VERIFIED provenance is
# ever returned.
# --------------------------------------------------------------------------------------- #


def test_genuine_execution_reaches_a_decisive_observation_status_not_incomplete(
    tmp_path: Path,
) -> None:
    """R4_F1_POSITIVE: a genuine ``execute()`` call's own real, second, handoff-time-only
    re-read must itself resolve to a decisive Observation status (``EMPTY`` -- this module never
    asserts domain Facts, so ``COMPLETE`` is never reachable) -- never the ``INCOMPLETE`` a stale,
    pre-execution Scope time window previously and unconditionally produced regardless of what
    was actually found on disk."""

    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)

    content = "# R4-F1 decisive-status proof\n"
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/r4-f1-decisive.md", "content_utf8": content}],
        ),
        paths=["docs/r4-f1-decisive.md"],
    )
    change = result["change"]

    worktree_root = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree_root)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )
    outcome = execute(
        change["change_id"],
        claim_token="r4-f1-decisive-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "SUCCEEDED"

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    evidence_request["verification_observation_request"] = None
    evidence = route_change_execution_to_evidence(store, receipt, project_id, evidence_request)

    assert evidence["verification_result_provenance"]["status"] == "VERIFIED"
    assert evidence["observed_result"]["observation_status"] in (
        evidence_handoff_module._ADMISSIBLE_VERIFIED_OBSERVATION_STATUSES
    )
    assert evidence["observed_result"]["observation_status"] != "INCOMPLETE"


def test_evidence_with_an_incomplete_grounding_observation_status_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R4_F1_NEGATIVE: a genuine, otherwise fully valid ``derive_evidence`` call whose returned
    Evidence record's own ``observed_result.observation_status`` has been tampered to
    ``INCOMPLETE`` -- with the Observation's own identity left genuine, so R3_F1's own identity
    check passes cleanly -- must still be refused, proving the resolved Observation's own status
    is genuinely checked, not merely its identity."""

    store, info = bound(tmp_path)
    project_id = info["project_id"]
    commit_active_kill_switch(store, project_id)

    content = "# R4-F1 incomplete-status proof\n"
    result = build_committed_change(
        store,
        project_id,
        action_kind="WRITE_DOCUMENTATION_FILE",
        operation=operation_for(
            "WRITE_DOCUMENTATION_FILE",
            writes=[{"path": "docs/r4-f1-incomplete.md", "content_utf8": content}],
        ),
        paths=["docs/r4-f1-incomplete.md"],
    )
    change = result["change"]

    worktree_root = git_worktree(tmp_path)
    adapter = CountingAdapter()
    execute = compose_change_executor(
        store,
        project_id=project_id,
        project_binding_id=info["project_binding_id"],
        execution_boundary=execution_boundary_for(worktree_root=str(worktree_root)),
        adapter_identity=_ADAPTER_IDENTITY,
        adapter=adapter,
        kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
    )
    outcome = execute(
        change["change_id"],
        claim_token="r4-f1-incomplete-claim",  # noqa: S106
        execution_instant="2026-09-10T00:00:01Z",
    )
    receipt = outcome["receipt"]
    assert receipt["outcome"] == "SUCCEEDED"

    # Wrap (never replace the logic of) the real derive_evidence: every real check it performs
    # still runs in full, including the genuine observation_id the minted Observation carries --
    # only observed_result.observation_status is tampered afterward.
    def _status_tampering_derive_evidence(request: Any) -> dict[str, Any]:
        genuine = _real_derive_evidence(request)
        tampered = dict(genuine)
        tampered_observed_result = dict(tampered["observed_result"])
        tampered_observed_result["observation_status"] = "INCOMPLETE"
        tampered["observed_result"] = tampered_observed_result
        return tampered

    monkeypatch.setattr(
        evidence_handoff_module, "derive_evidence", _status_tampering_derive_evidence
    )

    evidence_request = _rebind_project(
        change_free_verification_evidence_request(provenance=None), "PRJ-0001", project_id
    )
    evidence_request["verification_observation_request"] = None
    with pytest.raises(ChangeExecutorError, match="P18-R4-F1"):
        route_change_execution_to_evidence(store, receipt, project_id, evidence_request)
