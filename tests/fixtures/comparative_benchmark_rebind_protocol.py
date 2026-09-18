"""PR #90 corrected Round 6 rebind (``ADOPT_P90_R6_REBIND_PRE_RESULT_FREEZE_AND_FRESH_RUN``,
comment 5715652626) -- the frozen real-Agent protocol's own declared, predeclared fields for
``manosube_agent_civilization.comparative_benchmark.engine.build_protocol_freeze``.

Mirrors ``tests/fixtures/comparative_benchmark.py``'s own role for the Round 1-5 8-task
disclosed fixture, for this round's own 2-task real-Agent corpus. Never a completed protocol
freeze, result bundle, or reproduction receipt record itself -- those are produced every time by
calling the package's own real builders against the declarations this module supplies
(``NO_MANUAL_INTERMEDIATE_CANONICAL_RECORD_CONSTRUCTION=true``).

**Corrects the governance drift the Structural Advisor's own comment 5715630976 identified**:
every field below is fixed *before* this round's own fresh MANOSUBE_PRESENT/MANOSUBE_ABSENT
runs are executed -- ``PROTOCOL_FROZEN_BEFORE_RESULTS=true`` is enforced structurally by
``route.commit_protocol_freeze``/``route.commit_result_bundle`` (the latter refuses to commit
unless a matching, already-committed freeze resolves from the Store first), not merely by this
module's own call order.

**Honest scope of ``THIRD_PARTY_REPRODUCIBLE`` for this corpus** (recorded in
:func:`comparability_loss_receipts` below, per the adoption's own
``PLATFORM_ATTESTATION_CLAIM_ALLOWED=false``): both corpus tasks are fully deterministic and
independently computable (a SHA-256 digest of a fixed literal string; the ascending prime list
in ``[2, 50]``) -- :func:`reproduction_procedure` therefore names a plain, native-Agent-free
mechanical recomputation entrypoint. This is a narrower, honest claim than "the original Agent
execution was reproduced": it proves the frozen corpus's own declared outcomes are independently
re-derivable by any actor holding a Python interpreter, never that a native tool-using Agent
capability itself was cryptographically re-attested (``CONTENT_ADDRESS_IS_EXECUTOR_SIGNATURE=
false``, ``PLATFORM_ATTESTATION_CLAIMED=false``)."""

from __future__ import annotations

from typing import Any

#: This protocol's own dedicated project identity for the ``comparative_benchmark`` package's
#: own coordination-ledger records (protocol freeze / result bundle / trust anchor) -- distinct
#: from both the Round 1-5 fixture's ``PRJ-CB21-0001`` and this round's own separate Difference/
#: Authority/Change lifecycle project identity (:data:`tests.fixtures.
#: comparative_benchmark_frozen_protocol.PROJECT_ID`, ``PRJ-P90-R6F-0001``) -- the two are
#: orthogonal, exactly as ``tests/fixtures/comparative_benchmark.py``'s own module docstring
#: already documents for the Round 1-5 fixture pair.
CB_PROJECT_ID = "PRJ-CB21-R6-0001"
CB_PROJECT_BINDING_ID = "PB-CB21-R6-0001"

TASK_IDS: tuple[str, ...] = ("task_a", "task_b")

PRESENT_GROUP_ID = "manosube_present_real_agent_frozen_protocol"
ABSENT_GROUP_ID = "claude_code_alone_real_agent_frozen_protocol"

PRESENT_MECHANISM_IDENTITY: dict[str, str] = {
    "mechanism": "manosube_real_agent_receipt_route",
    "version": "0.1",
}
ABSENT_MECHANISM_IDENTITY: dict[str, str] = {
    "mechanism": "direct_real_agent_action",
    "version": "0.1",
}
#: Identical declared Agent identity in both groups -- the one structural fact
#: ``SAME_AGENT_COMPARISON_AVAILABLE`` rests on, real this time via a genuine, fresh native
#: tool-using Agent execution in both conditions (never a fixture composer counted as the real
#: Agent -- P90-R6-IF1's own required correction, now carried into this frozen protocol).
#: ``comparative_benchmark_protocol_freeze.schema.json`` fixes ``agent_label`` to exactly
#: ``agent_family``/``version`` -- the fuller runtime/session identity (this session's own
#: ``claude.ai/code`` session ref) is instead recorded on every real raw event and receipt this
#: protocol's runs publish (see ``tests.comparative_benchmark.agent_execution_receipt``).
SAME_AGENT_LABEL: dict[str, str] = {"agent_family": "claude_code", "version": "claude-sonnet-5"}

TASK_INPUT: dict[str, str] = {
    "task_a": (
        "Compute the SHA-256 hex digest of the literal ASCII string "
        "MANOSUBE_PHASE21_ROUND6_TASK_A and write only that digest to the task's output file."
    ),
    "task_b": (
        "List every prime number p with 2 <= p <= 50, ascending, comma-separated, no spaces, "
        "and write only that line to the task's output file."
    ),
}
TOOL_SURFACE: list[str] = ["Bash", "Write"]
#: The real Agent execution receipt's own resource-budget vocabulary (``tests.
#: comparative_benchmark.agent_execution_receipt``) -- distinct from
#: :func:`resource_budget_manifest` below, whose own schema fixes a different,
#: time-based vocabulary (``per_task_timeout_seconds``/``total_time_budget_seconds``).
RESOURCE_BUDGET: dict[str, int] = {"max_turns": 1, "retries_allowed": 0}


def corpus_manifest() -> dict[str, Any]:
    return {
        "corpus_kind": "comparative_benchmark",
        "task_count": len(TASK_IDS),
        "task_ids": list(TASK_IDS),
    }


def comparison_groups() -> list[dict[str, Any]]:
    return [
        {
            "comparison_group_id": PRESENT_GROUP_ID,
            "comparison_group_role": "MANOSUBE_PRESENT",
            "mechanism_identity": dict(PRESENT_MECHANISM_IDENTITY),
            "agent_label": dict(SAME_AGENT_LABEL),
        },
        {
            "comparison_group_id": ABSENT_GROUP_ID,
            "comparison_group_role": "MANOSUBE_ABSENT",
            "mechanism_identity": dict(ABSENT_MECHANISM_IDENTITY),
            "agent_label": dict(SAME_AGENT_LABEL),
        },
    ]


def authority_boundary_equivalence_manifest() -> dict[str, Any]:
    return {
        "boundary_ref": {"kind": "authority_boundary", "id": "CBB-R6F-AUTH-BOUNDARY-0001"},
        "equivalence_statement": (
            "The MANOSUBE_PRESENT group's own live, pre-flight Authority check (load-bearing --"
            " Change/Reflow only proceed on its decision) and the MANOSUBE_ABSENT group's own"
            " direct action (no MANOSUBE owner touches the path at all) are not asserted"
            " equivalent -- see comparability_loss_receipts. Both groups use the identical real"
            " tool surface (Bash/Write), the identical resource budget, and the identical"
            " declared Agent identity; the only declared treatment difference is whether"
            " MANOSUBE's real Difference/Authority/Change/Observation/Evidence/Reflow lifecycle"
            " wraps the identical real write (NC-3)."
        ),
    }


def resource_budget_manifest() -> dict[str, Any]:
    """Raw ``float`` values -- ``engine.build_protocol_freeze`` runs the whole manifest through
    ``engine.stringify_floats`` before embedding it (identical convention to ``tests/fixtures/
    comparative_benchmark.py``'s own :func:`resource_budget_manifest`). This frozen corpus's own
    single-turn, no-retry Agent resource budget (:data:`RESOURCE_BUDGET`) is recorded verbatim
    on every real execution receipt this protocol's runs publish -- this manifest field is this
    schema's own fixed, time-based vocabulary instead."""

    return {"per_task_timeout_seconds": 60.0, "total_time_budget_seconds": 120.0}


def metric_definitions() -> list[dict[str, Any]]:
    return [
        {
            "metric_name": "completed_verified_count",
            "formula": "count(outcome == COMPLETED_VERIFIED) per comparison_group_id",
            "denominator": "raw_event_count for that comparison_group_id",
        },
        {
            "metric_name": "refused_count",
            "formula": "count(outcome == REFUSED) per comparison_group_id",
            "denominator": "raw_event_count for that comparison_group_id",
        },
        {
            "metric_name": "retained_incomplete_count",
            "formula": "count(outcome == RETAINED_INCOMPLETE) per comparison_group_id",
            "denominator": "raw_event_count for that comparison_group_id",
        },
        {
            "metric_name": "failed_count",
            "formula": "count(outcome == FAILED) per comparison_group_id",
            "denominator": "raw_event_count for that comparison_group_id",
        },
        {
            "metric_name": "timed_out_count",
            "formula": "count(outcome == TIMED_OUT) per comparison_group_id",
            "denominator": "raw_event_count for that comparison_group_id",
        },
    ]


def numeric_thresholds() -> list[dict[str, Any]]:
    """Predeclared, machine-checkable thresholds -- before any result exists
    (``THRESHOLDS_PREDECLARED_BEFORE_RESULTS=true``): this frozen 2-task corpus's own fixed,
    always-authorizing Authority Rule deterministically closes both tasks in both groups
    (identical reasoning to ``tests/fixtures/comparative_benchmark.py``'s own
    :func:`numeric_thresholds` for the Round 1-5 ``MANOSUBE_ABSENT`` groups)."""

    thresholds: list[dict[str, Any]] = []
    for group_id in (PRESENT_GROUP_ID, ABSENT_GROUP_ID):
        thresholds.append(
            {
                "metric_name": "raw_event_count",
                "comparison_group_id": group_id,
                "operator": "==",
                "threshold_value": len(TASK_IDS),
                "comparison_decision_rule": (
                    "every comparison group must record exactly one raw event per corpus task "
                    "(COMPARABLE_PROJECT_AND_TASK_CORPUS_REQUIRED=true)"
                ),
            }
        )
        thresholds.append(
            {
                "metric_name": "COMPLETED_VERIFIED",
                "comparison_group_id": group_id,
                "operator": "==",
                "threshold_value": len(TASK_IDS),
                "comparison_decision_rule": (
                    "this frozen 2-task corpus's own fixed, always-authorizing Authority Rule "
                    "deterministically completes every task in every declared group -- "
                    "predeclared before any result exists, never adjusted after seeing this "
                    "bundle's own recomputed count"
                ),
            }
        )
    return thresholds


def unknown_missing_handling() -> dict[str, Any]:
    return {
        "unknown_ne_zero": True,
        "refusal_ne_system_failure": True,
        "retained_ne_closed": True,
    }


def exclusion_policy() -> dict[str, Any]:
    return {
        "success_only_subset_forbidden": True,
        "post_hoc_protocol_mutation_forbidden": True,
        "raw_result_deletion_forbidden": True,
    }


def claim_vocabulary() -> list[dict[str, Any]]:
    return [
        {
            "claim_id": "CB21-R6F-CLAIM-SAME-AGENT-COMPLETION-COUNTS",
            "claim_statement_template": (
                "For this round's frozen 2-task real-Agent corpus, the recorded "
                "COMPLETED_VERIFIED count for "
                f"comparison_group_id={PRESENT_GROUP_ID} (MANOSUBE present) is "
                f"{{{PRESENT_GROUP_ID}}}, and for comparison_group_id={ABSENT_GROUP_ID} "
                "(the identical declared Agent, MANOSUBE absent) is "
                f"{{{ABSENT_GROUP_ID}}} -- exactly the counts recorded in this result "
                "bundle's own metrics; no causal or superiority claim is made beyond those "
                "recorded counts."
            ),
            "bound": (
                "Bounded strictly by this result bundle's own recorded raw_events/metrics for "
                "the declared comparison_group_id set; asserts no causal mechanism, no claim "
                "about any real external product's general capability, and no claim beyond "
                "this one frozen corpus's own recorded counts (CLAIMS_BOUNDED_BY_EVIDENCE)."
            ),
            "subject_metric_name": "COMPLETED_VERIFIED",
            "subject_group_ids": [PRESENT_GROUP_ID, ABSENT_GROUP_ID],
        }
    ]


def reproduction_procedure() -> dict[str, Any]:
    return {
        "entrypoint": (
            "tests.comparative_benchmark.frozen_protocol_reproduction.reproduce_raw_events"
        ),
        "corpus_kind": "comparative_benchmark",
    }


def comparability_loss_receipts() -> list[dict[str, Any]]:
    return [
        {
            "receipt_id": "CLR-CB21-R6F-0001",
            "description": (
                "MANOSUBE_PRESENT's own real Agent action is bound to a real, machine-"
                "verifiable execution receipt (tests.comparative_benchmark."
                "agent_execution_receipt, P90-R6-IF1's own required correction) that "
                "independently re-derives and re-checks the real output bytes' own SHA-256 "
                "digest and the declared Agent identity/condition/task input/tool surface/"
                "resource budget against caller-supplied expectations. Per the Structural "
                "Advisor's own P90-R6-IF2 finding and the corrected rebind adoption "
                "(comment 5715630976/5715652626), this content-addressed receipt is disclosed "
                "honestly as integrity/provenance evidence, never as a claim of platform-"
                "issued executor authentication (CONTENT_ADDRESS_IS_EXECUTOR_SIGNATURE=false, "
                "PLATFORM_ATTESTATION_CLAIMED=false): no independently verifiable native-Agent "
                "issuer signature or attestation is available in this execution environment "
                "(BLOCKED_NO_MACHINE_VERIFIABLE_NATIVE_AGENT_ISSUER=true, comment 5715524639)."
            ),
        },
        {
            "receipt_id": "CLR-CB21-R6F-0002",
            "description": (
                "This frozen corpus's own two tasks are fully deterministic and independently "
                "computable without any native-Agent capability (a SHA-256 digest of a fixed "
                "literal string; the ascending prime list in [2, 50]). This protocol's own "
                "reproduction_procedure therefore names a plain, native-Agent-free mechanical "
                "recomputation entrypoint -- a narrower, honest THIRD_PARTY_REPRODUCIBLE claim "
                "than 're-invoking the original native Agent execution', which this repository "
                "has no capability to offer any third party (see receipt CLR-CB21-R6F-0001)."
            ),
        },
        {
            "receipt_id": "CLR-CB21-R6F-0003",
            "description": (
                "MANOSUBE_PRESENT's own Authority evaluation is load-bearing (Change/Reflow "
                "only proceed on its decision); MANOSUBE_ABSENT's own direct action has no "
                "such gate at all -- the identical asymmetry ``tests/fixtures/"
                "comparative_benchmark.py``'s own comparability_loss_receipts discloses for "
                "the Round 1-5 fixture, never a claim of true product-for-product parity "
                "(NC-3)."
            ),
        },
    ]


def protocol_freeze_kwargs(*, generated_at: str) -> dict[str, Any]:
    return {
        "project_binding_ref": {"kind": "project_binding", "id": CB_PROJECT_BINDING_ID},
        "corpus_manifest": corpus_manifest(),
        "comparison_groups": comparison_groups(),
        "authority_boundary_equivalence_manifest": authority_boundary_equivalence_manifest(),
        "resource_budget_manifest": resource_budget_manifest(),
        "metric_definitions": metric_definitions(),
        "numeric_thresholds": numeric_thresholds(),
        "unknown_missing_handling": unknown_missing_handling(),
        "exclusion_policy": exclusion_policy(),
        "claim_vocabulary": claim_vocabulary(),
        "reproduction_procedure": reproduction_procedure(),
        "comparability_loss_receipts": comparability_loss_receipts(),
        "generated_at": generated_at,
    }
