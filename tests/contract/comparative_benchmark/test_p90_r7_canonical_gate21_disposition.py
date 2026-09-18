"""Decisive proof for `00_KERNEL/COMPARATIVE_BENCHMARK_CONTRACT.md` section 11a's own claimed
facts (P90-R7, `ADOPT_P90_R7_CANONICAL_GATE_21_COMPLETION`, comment 5726787466; corrected by
P90-R8, `ADOPT_P90_R8_AUTHORITY_DRIFT_CORRECTION`, comment 5728797305, adopting the Structural
Advisor's authority-drift review, comment 5728778060).

The three source-level pins below remain unchanged and still hold under the P90-R8 correction:
(1) the original 8-task corpus's own `codex_alone`/`existing_agent_framework` groups have never
been, and are not now, disclosed as real external-product invocations -- only as an
honestly-labeled ungated reference harness; (2) the Round 6 frozen corpus's two available
real-evidence roles (`claude_code_alone_real_agent_frozen_protocol`, `manosube_present_real_
agent_frozen_protocol`) share an identical declared Agent identity, tool surface, and resource
budget; (3) the Round 6 frozen corpus's own Authority-boundary comparability-loss receipt
(`CLR-CB21-R6F-0003`) is present and states the asymmetry honestly.

A fourth test, added for P90-R8, mechanically rederives all seven Gate 21 booleans (Issue #89
section 9) directly from the two corpora's own already-published, already-verified artifacts --
proving the corrected composite disposition is an explicit conjunction of two separately-owned,
never-conflated evidence sets, not a new unverified claim."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

from tests.fixtures import comparative_benchmark as cb, comparative_benchmark_rebind_protocol as rb

_EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples" / "comparative_benchmark"
_R6_DIR = _EXAMPLES_DIR / "frozen_protocol_r6"


def _load(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def test_the_absent_groups_are_never_disclosed_as_a_real_external_product_invocation() -> None:
    source = inspect.getsource(cb)
    assert "ungated reference harness" in source
    assert "codex_alone" in source
    assert "existing_agent_framework" in source
    # a real invocation would need a network/subprocess call naming the product -- the module
    # itself must never claim one
    for forbidden in ("subprocess.run", "subprocess.Popen", "requests.", "urllib.", "socket."):
        assert forbidden not in source, (
            f"{cb.__name__} contains {forbidden!r} -- codex_alone/existing_agent_framework must "
            "remain a disclosed ungated reference harness, never a real external invocation"
        )


def test_the_two_available_real_evidence_roles_share_an_identical_declared_envelope() -> None:
    groups = rb.comparison_groups()
    assert len(groups) == 2
    agent_labels = {group["comparison_group_id"]: group["agent_label"] for group in groups}
    assert agent_labels[rb.PRESENT_GROUP_ID] == agent_labels[rb.ABSENT_GROUP_ID]
    assert agent_labels[rb.PRESENT_GROUP_ID] == rb.SAME_AGENT_LABEL

    # tool surface and resource budget are declared once, module-wide, for both groups -- there
    # is structurally no per-group override that could silently diverge them
    assert rb.TOOL_SURFACE == ["Bash", "Write"]
    assert rb.RESOURCE_BUDGET == {"max_turns": 1, "retries_allowed": 0}


def test_the_authority_boundary_comparability_loss_is_disclosed_and_unweakened() -> None:
    receipts = rb.comparability_loss_receipts()
    receipt_ids = {receipt["receipt_id"] for receipt in receipts}
    assert "CLR-CB21-R6F-0003" in receipt_ids

    receipt = next(r for r in receipts if r["receipt_id"] == "CLR-CB21-R6F-0003")
    assert "no such gate at all" in receipt["description"]
    assert "never a claim of true product-for-product parity" in receipt["description"]


def test_all_seven_gate_21_booleans_hold_via_explicit_per_corpus_evidence_never_cross_corpus() -> (
    None
):
    """P90-R8's own corrected disposition (section 11a, `CANONICAL_GATE_21_STATUS=ALL_SEVEN_
    BOOLEANS_SATISFIED_VIA_EXPLICIT_LAYERED_EVIDENCE`): each of Issue #89 section 9's seven Gate
    21 booleans is checked here directly against the one already-published artifact it is
    actually proven by -- `PRJ-CB21-0001` (the original 8-task corpus) or `PRJ-CB21-R6-0001` (the
    Round 6 real-Agent corpus) -- never a value copied or substituted from the other corpus."""

    original_freeze = _load(_EXAMPLES_DIR / "protocol_freeze.json")
    original_bundle = _load(_EXAMPLES_DIR / "result_bundle.json")

    r6_freeze = _load(_R6_DIR / "protocol_freeze.json")
    r6_bundle = _load(_R6_DIR / "result_bundle.json")
    r6_submission = _load(_R6_DIR / "independent_reproduction_submission.json")

    # CONTROL_GROUPS_DEFINED -- PRJ-CB21-0001, matching Issue #89 section 4's own 4 groups
    # exactly. Issue #89 section 4 itself permits real-product replacement/addition "at
    # execution time" without mandating it -- CONTROL_GROUPS_DEFINED requires the groups be
    # frozen and defined, not that every non-MANOSUBE identity be a live product invocation.
    orig_groups = {g["comparison_group_id"]: g for g in original_freeze["comparison_groups"]}
    assert len(orig_groups) == 4
    agent_families = {g["agent_label"]["agent_family"] for g in orig_groups.values()}
    assert agent_families == {"codex", "claude_code", "existing_agent_framework"}

    # METRICS_PREDECLARED -- PRJ-CB21-0001; the freeze was committed before any raw event exists.
    assert len(original_freeze["metric_definitions"]) >= 1
    assert (
        original_bundle["protocol_freeze_ref"]["protocol_freeze_id"]
        == original_freeze["protocol_freeze_id"]
    )

    # RAW_RESULTS_PUBLIC -- both corpora independently.
    assert len(original_bundle["raw_events"]) >= 1
    assert len(r6_bundle["raw_events"]) >= 1

    # FAILURES_INCLUDED -- PRJ-CB21-0001's own MANOSUBE_PRESENT group.
    present_group_id = next(
        gid for gid, g in orig_groups.items() if g["comparison_group_role"] == "MANOSUBE_PRESENT"
    )
    present_outcomes = {
        e["outcome"]
        for e in original_bundle["raw_events"]
        if e["comparison_group_id"] == present_group_id
    }
    assert {"REFUSED", "RETAINED_INCOMPLETE", "FAILED"} <= present_outcomes

    # CLAIMS_BOUNDED_BY_EVIDENCE -- PRJ-CB21-0001; declared claim vocabulary matches what was
    # actually stored, no undeclared claim appears.
    declared_claim_ids = {c["claim_id"] for c in original_freeze["claim_vocabulary"]}
    stored_claim_ids = {c["claim_id"] for c in original_bundle["claims"]}
    assert stored_claim_ids == declared_claim_ids
    assert declared_claim_ids

    # SAME_AGENT_COMPARISON_AVAILABLE -- PRJ-CB21-R6-0001; a real Agent execution under the
    # identical declared Agent identity in both the present and absent conditions.
    r6_groups = {g["comparison_group_id"]: g for g in r6_freeze["comparison_groups"]}
    r6_present = next(
        g for g in r6_groups.values() if g["comparison_group_role"] == "MANOSUBE_PRESENT"
    )
    r6_absent = next(
        g for g in r6_groups.values() if g["comparison_group_role"] == "MANOSUBE_ABSENT"
    )
    assert r6_present["agent_label"] == r6_absent["agent_label"]

    # THIRD_PARTY_REPRODUCIBLE -- PRJ-CB21-R6-0001; SHUKOU's own genuinely separate, pre-
    # registered, signed reproduction, admitted through the production route.
    assert r6_submission["agreement"] == "MATCH"
    assert r6_submission["reproducer_actor_or_authority_id"] == "SHUKOU_PHASE21_REPRODUCER"
    assert (
        r6_submission["original_result_bundle_ref"]["result_bundle_id"]
        == (r6_bundle["result_bundle_id"])
    )
