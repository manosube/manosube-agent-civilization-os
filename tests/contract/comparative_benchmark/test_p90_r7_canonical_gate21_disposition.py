"""Decisive proof for `00_KERNEL/COMPARATIVE_BENCHMARK_CONTRACT.md` section 11a's own newly
claimed facts (P90-R7, `ADOPT_P90_R7_CANONICAL_GATE_21_COMPLETION`, comment 5726787466).

Section 11a claims: (1) the original 8-task corpus's own `codex_alone`/`existing_agent_framework`
groups have never been, and are not now, disclosed as real external-product invocations -- only
as an honestly-labeled ungated reference harness; (2) the Round 6 frozen corpus's two available
real-evidence roles (`claude_code_alone_real_agent_frozen_protocol`, `manosube_present_real_
agent_frozen_protocol`) share an identical declared Agent identity, tool surface, and resource
budget; (3) the Round 6 frozen corpus's own Authority-boundary comparability-loss receipt
(`CLR-CB21-R6F-0003`) is present and states the asymmetry honestly. None of these are new claims
about capability that could reverse without changing the shipped source itself -- these tests
pin the source-level facts section 11a's own disposition rests on."""

from __future__ import annotations

import inspect

from tests.fixtures import comparative_benchmark as cb, comparative_benchmark_rebind_protocol as rb


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
