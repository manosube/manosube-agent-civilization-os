"""Phase 21 Comparative Benchmark -- the bounded, deterministic fixture world (``00_KERNEL/
COMPARATIVE_BENCHMARK_CONTRACT.md``, Issue #89, ``ADOPT_PHASE_21_COMPARATIVE_BENCHMARK``).

This module is the Fixture Boundary for the comparative-benchmark protocol freeze: its own
frozen 8-task corpus identity (``TASK_IDS``), its four required comparison groups (Issue #89
section 4 -- ``Codex alone``, ``Claude Code alone``, ``existing agent framework``, ``MANOSUBE +
the same Agent``), and every predeclared protocol-freeze field (metric/threshold/claim
vocabulary, resource budget, authority-boundary-equivalence manifest, comparability-loss
receipts) -- never a completed protocol freeze, result bundle, or reproduction receipt record
itself. Those are produced every time by calling ``manosube_agent_civilization.
comparative_benchmark.engine``'s own real builders against the declarations this module
supplies (``NO_MANUAL_INTERMEDIATE_CANONICAL_RECORD_CONSTRUCTION=true``).

**Deliberately self-contained.** This module does not import ``tests/fixtures/long_running_
proof.py`` or ``tests/fixtures/vertical_proof.py`` -- the identical ``PHASE_8_FIXTURE_BINDING_NE_
PHASE_20_FIXTURE_BINDING=true`` reasoning both of those modules' own docstrings already give for
keeping phase fixture worlds independent. The one, disclosed exception to that independence
principle lives in ``tests/comparative_benchmark/orchestrator.py``, not here: driving the
``MANOSUBE_PRESENT`` comparison group's tasks through a genuine Observation -> Difference ->
Authority -> Change -> Evidence -> Sufficiency -> Reflow route requires the same large, several-
times-structurally-reviewed assembly ``tests/long_running_proof/cycle.py`` already proves
correct; re-deriving that assembly a third time from scratch for this one additional phase would
itself be new, unreviewed surface for exactly the class of subtle defect those structural-review
rounds exist to catch. The orchestrator therefore reuses ``tests.long_running_proof.cycle``'s
already-proven per-cycle composer directly, against the first 8 positions of ``tests.fixtures.
long_running_proof``'s own already-proven ``MAX_CYCLES=100`` deterministic corpus, as its real
natural-route backing for this module's own, separately-identified 8-task comparative-benchmark
corpus below (``CB_TASK_TO_NATURAL_ROUTE_CYCLE_INDEX``). This module itself never imports that
fixture world -- only the orchestrator does, and only to drive real records, never to mint one by
hand.

**P90-R1-F1: the ungated reference harness is a real, structurally-ungated execution -- never a
fixture table.** Every ``MANOSUBE_ABSENT`` comparison group (``codex_alone``,
``claude_code_alone``, ``existing_agent_framework``) is driven, by
``tests/comparative_benchmark/orchestrator.py``'s own
:func:`~tests.comparative_benchmark.orchestrator.run_ungated_reference_harness_group`, through
the identical real natural-route mechanism the ``MANOSUBE_PRESENT`` group's own real ``CLOSED``
tasks use (a fresh Store, a fresh genesis/Project Binding, the real Observation/Difference/
Authority/Change/Evidence/Reflow owners, reused through :mod:`tests.long_running_proof.cycle`)
-- never a hand-authored outcome table, and never a real invocation of any named external
product (``PRODUCTION_CREDENTIAL_USE_ALLOWED=false``, ``REMOTE_COMMAND_AUTHORITY_ALLOWED=
false``). "Ungated" names a structural fact, not an absence of Authority: no pre-flight Authority
decision ever gates whether a ``MANOSUBE_ABSENT`` task is *attempted*, but this module's own
:func:`resource_budget_manifest`/:func:`authority_boundary_equivalence_manifest` and
:data:`comparability_loss_receipts` still disclose the real, narrower asymmetry that remains
against ``MANOSUBE_PRESENT`` -- see their own docstrings/bodies below, never presented as
genuine product-for-product parity.
"""

from __future__ import annotations

from typing import Any

#: This comparative benchmark's own dedicated project identity -- distinct from every other
#: phase's own fixture-world project id, so a defect in this fixture world can never be masked
#: or amplified by an unrelated suite's fixture state, and vice versa. (The orchestrator's real
#: natural-route driving nonetheless runs against Phase 20's own already-bound project -- see
#: the module docstring -- so this constant identifies the comparative-benchmark *protocol
#: freeze/result bundle/reproduction receipt* records' own ``project_id``, which the orchestrator
#: threads through independently of whichever project the reused natural-route composer itself
#: binds to commit its own Difference/Reflow records.)
PROJECT_ID = "PRJ-CB21-0001"
PROJECT_BINDING_ID = "PB-CB21-0001"

#: This corpus's own frozen task identity: 8 tasks, declared once, in this exact order --
#: ``COMPARABLE_PROJECT_AND_TASK_CORPUS_REQUIRED=true`` starts with one single ordered list
#: every comparison group is run against, never a per-group corpus.
TASK_IDS: tuple[str, ...] = tuple(f"TSK-CB21-{i:04d}" for i in range(8))

#: Maps each of this module's own comparative-benchmark task indices (0..7) to the identical-
#: index position of ``tests.fixtures.long_running_proof``'s own already-proven, deterministic
#: predicate corpus -- the orchestrator's one seam between this module's own task identity and
#: the reused natural-route fixture world's own predicate identity (see module docstring).
CB_TASK_TO_NATURAL_ROUTE_CYCLE_INDEX: dict[str, int] = {
    task_id: i for i, task_id in enumerate(TASK_IDS)
}

#: This corpus's own predeclared, frozen per-task plan for the ``MANOSUBE_PRESENT`` group --
#: which of the real natural route's own genuine terminal shapes each task is driven to. Chosen
#: so the corpus is deterministically varied enough that real success (``CLOSED``), a real
#: Authority refusal, a real non-``CLOSED`` (``RETAINED``) Reflow closure, and a real unhandled
#: production validation failure all genuinely occur -- ``FAILURES_INCLUDED`` is a fact about
#: this frozen plan, never something assembled after seeing results
#: (``CONTROL_GROUP_IDENTITY_FROZEN_BEFORE_RUN=true``).
PRESENT_TASK_PLAN: dict[str, str] = {
    TASK_IDS[0]: "CLOSED",
    TASK_IDS[1]: "CLOSED",
    TASK_IDS[2]: "REFUSED",
    TASK_IDS[3]: "CLOSED",
    TASK_IDS[4]: "RETAINED",
    TASK_IDS[5]: "CLOSED",
    TASK_IDS[6]: "FAILED",
    TASK_IDS[7]: "CLOSED",
}

#: The three required ``MANOSUBE_ABSENT`` comparison group ids (P90-R1-F1: each is now a real,
#: structurally-ungated execution of the identical natural-route mechanism, never a hand-
#: authored outcome table -- see the module docstring and ``orchestrator.
#: run_ungated_reference_harness_group``).
ABSENT_GROUP_IDS: tuple[str, ...] = ("codex_alone", "claude_code_alone", "existing_agent_framework")

#: The one ``MANOSUBE_PRESENT`` comparison group. Its own ``agent_label`` is deliberately
#: identical to the ``claude_code_alone`` absent group's own ``agent_label`` below -- the
#: structural fact that makes ``SAME_AGENT_COMPARISON_AVAILABLE`` real: the same declared
#: Agent identity, once run through the real natural route (MANOSUBE present) and once through
#: the ungated reference harness (MANOSUBE absent), never a differently-labeled substitute
#: agent standing in for "the same Agent".
PRESENT_GROUP_ID = "manosube_present_claude_code"
PRESENT_MECHANISM_IDENTITY: dict[str, str] = {
    "mechanism": "manosube_natural_route",
    "version": "0.1",
}
SAME_AGENT_LABEL: dict[str, str] = {"agent_family": "claude_code", "version": "claude-sonnet-5"}

#: The one mechanism identity every ``MANOSUBE_ABSENT`` group shares -- structurally disjoint
#: from :data:`PRESENT_MECHANISM_IDENTITY` (``engine.build_protocol_freeze``'s own fail-closed
#: disjointness check enforces this), and genuinely disjoint in fact: the ungated reference
#: harness never calls any real natural-route owner (see module docstring).
ABSENT_MECHANISM_IDENTITY: dict[str, str] = {
    "mechanism": "ungated_reference_harness",
    "version": "0.1",
}

COMPARISON_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "comparison_group_id": PRESENT_GROUP_ID,
        "comparison_group_role": "MANOSUBE_PRESENT",
        "mechanism_identity": dict(PRESENT_MECHANISM_IDENTITY),
        "agent_label": dict(SAME_AGENT_LABEL),
    },
    {
        "comparison_group_id": "claude_code_alone",
        "comparison_group_role": "MANOSUBE_ABSENT",
        "mechanism_identity": dict(ABSENT_MECHANISM_IDENTITY),
        "agent_label": dict(SAME_AGENT_LABEL),
    },
    {
        "comparison_group_id": "codex_alone",
        "comparison_group_role": "MANOSUBE_ABSENT",
        "mechanism_identity": dict(ABSENT_MECHANISM_IDENTITY),
        "agent_label": {"agent_family": "codex", "version": "reference-0.1"},
    },
    {
        "comparison_group_id": "existing_agent_framework",
        "comparison_group_role": "MANOSUBE_ABSENT",
        "mechanism_identity": dict(ABSENT_MECHANISM_IDENTITY),
        "agent_label": {"agent_family": "existing_agent_framework", "version": "reference-0.1"},
    },
)

ALL_GROUP_IDS: tuple[str, ...] = tuple(group["comparison_group_id"] for group in COMPARISON_GROUPS)


def corpus_manifest() -> dict[str, Any]:
    return {
        "corpus_kind": "comparative_benchmark",
        "task_count": len(TASK_IDS),
        "task_ids": list(TASK_IDS),
    }


def comparison_groups() -> list[dict[str, Any]]:
    return [dict(group) for group in COMPARISON_GROUPS]


def authority_boundary_equivalence_manifest() -> dict[str, Any]:
    return {
        "boundary_ref": {"kind": "authority_boundary", "id": "CBB-AUTH-BOUNDARY-0001"},
        "equivalence_statement": (
            "The MANOSUBE_PRESENT group's own live, pre-flight Authority check (load-bearing --"
            " Change/Reflow only proceed on its decision) and every MANOSUBE_ABSENT group's own"
            " retroactive, audit-only Authority classification (applied after the real Reflow"
            " closure, never gating whether a task is attempted) are not asserted equivalent --"
            " see comparability_loss_receipts. This manifest exists so that this Authority-"
            "boundary/tool-surface asymmetry is recorded and checkable (NC-3), never silently"
            " assumed away."
        ),
    }


def resource_budget_manifest() -> dict[str, Any]:
    """Raw ``float`` values -- ``engine.build_protocol_freeze`` runs the whole manifest through
    ``engine.stringify_floats`` before embedding it, so these are supplied here as real Python
    floats, never pre-stringified."""

    return {"per_task_timeout_seconds": 30.0, "total_time_budget_seconds": 600.0}


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
    """Machine-checkable, predeclared thresholds (P90-R1-F7) -- each names a real
    `(metric_name, comparison_group_id, operator, threshold_value)` tuple `engine.
    evaluate_numeric_thresholds` itself evaluates against the recomputed metrics, never an
    informational-only free-text rule. Bounded to a fact that is structurally true of every
    ``MANOSUBE_ABSENT`` group's own real, deterministic mechanism (P90-R1-F1): the identical
    fixed Authority Rule fixture (:func:`tests.fixtures.long_running_proof.authority_rule`)
    always authorizes this corpus's one in-scope ``WRITE_FILE`` action, so a fresh-Store,
    uniformly-plain-routed run over this frozen corpus deterministically closes every task --
    predeclared here before any result exists (``THRESHOLDS_PREDECLARED_BEFORE_RESULTS=true``),
    not fitted to a run's own observed counts after the fact."""

    return [
        {
            "metric_name": "raw_event_count",
            "comparison_group_id": "codex_alone",
            "operator": "==",
            "threshold_value": len(TASK_IDS),
            "comparison_decision_rule": (
                "every comparison group must record exactly one raw event per corpus task "
                "(COMPARABLE_PROJECT_AND_TASK_CORPUS_REQUIRED=true) -- a structural "
                "completeness check, predeclared before any result exists"
            ),
        },
        {
            "metric_name": "COMPLETED_VERIFIED",
            "comparison_group_id": "codex_alone",
            "operator": "==",
            "threshold_value": len(TASK_IDS),
            "comparison_decision_rule": (
                "the codex_alone ungated reference harness's own real, structurally-ungated "
                "mechanism (P90-R1-F1) deterministically closes every one of this frozen "
                "corpus's 8 tasks under the identical fixed Authority Rule fixture the "
                "MANOSUBE_PRESENT group's own real natural route uses -- predeclared before "
                "any result exists, never adjusted after seeing this bundle's own recomputed "
                "count"
            ),
        },
    ]


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
    """Predeclared claim vocabulary (P90-R1-F5) -- each entry names the real
    `subject_metric_name`/`subject_group_ids` `engine.derive_bounded_claims` itself reads from
    the recomputed metrics, and a `claim_statement_template` whose `{comparison_group_id}`
    placeholders that same function fills in via `.format(**computed_values)`. A claim's
    rendered `statement` is therefore always bound to the actual recomputed counts, never
    independent boilerplate."""

    return [
        {
            "claim_id": "CB21-CLAIM-SAME-AGENT-COMPLETION-COUNTS",
            "claim_statement_template": (
                "For the frozen 8-task corpus, the recorded COMPLETED_VERIFIED count for "
                f"comparison_group_id={PRESENT_GROUP_ID} (MANOSUBE present) is "
                f"{{{PRESENT_GROUP_ID}}}, and for comparison_group_id=claude_code_alone (the "
                "identical declared Agent, MANOSUBE absent) is {claude_code_alone} -- exactly "
                "the counts recorded in this result bundle's own metrics; no causal or "
                "superiority claim is made beyond those recorded counts."
            ),
            "bound": (
                "Bounded strictly by this result bundle's own recorded raw_events/metrics for "
                "the declared comparison_group_id set; asserts no causal mechanism, no claim "
                "about any real external product's general capability, and no claim beyond "
                "this one frozen corpus's own recorded counts (CLAIMS_BOUNDED_BY_EVIDENCE)."
            ),
            "subject_metric_name": "COMPLETED_VERIFIED",
            "subject_group_ids": [PRESENT_GROUP_ID, "claude_code_alone"],
        }
    ]


def reproduction_procedure() -> dict[str, Any]:
    return {
        "entrypoint": "tests.comparative_benchmark.orchestrator.run_comparative_benchmark",
        "corpus_kind": "comparative_benchmark",
    }


def comparability_loss_receipts() -> list[dict[str, Any]]:
    return [
        {
            "receipt_id": "CLR-CB21-0001",
            "description": (
                "The three MANOSUBE_ABSENT comparison groups (codex_alone, claude_code_alone, "
                "existing_agent_framework) are driven by a real, structurally-ungated execution "
                "of the identical natural-route mechanism the MANOSUBE_PRESENT group uses "
                "(P90-R1-F1) -- the same real Observation/Difference/Authority/Change/Evidence/"
                "Reflow owners, the same frozen 8-task corpus, the same fixed Authority Rule, "
                "each group against its own fresh Store/genesis -- never a real invocation of "
                "any named external product (PRODUCTION_CREDENTIAL_USE_ALLOWED=false, "
                "REMOTE_COMMAND_AUTHORITY_ALLOWED=false). The remaining disclosed Authority-"
                "boundary and tool-surface asymmetry against MANOSUBE_PRESENT is narrower but "
                "real: (1) MANOSUBE_PRESENT's own frozen task-routing policy deliberately "
                "drives distinct tasks through out-of-scope, malformed-request, or evidence-"
                "emptied branches to exercise REFUSED/FAILED/RETAINED_INCOMPLETE outcomes, "
                "while every MANOSUBE_ABSENT task always attempts the identical plain in-scope "
                "action uniformly -- this uniform routing is a fact about this frozen fixture "
                "plan, never a claim that a real ungated agent could never fail, refuse, or be "
                "retained; and (2) MANOSUBE_ABSENT's own Authority evaluation is applied "
                "retroactively, for audit/classification only, never as a live pre-flight gate "
                "deciding whether a task is attempted, while MANOSUBE_PRESENT's identical "
                "Authority evaluation is load-bearing before Change/Reflow ever proceeds. Never "
                "a claim of true product-for-product parity (NC-3)."
            ),
        }
    ]


def protocol_freeze_kwargs(*, generated_at: str) -> dict[str, Any]:
    """Every keyword ``manosube_agent_civilization.comparative_benchmark.engine.
    build_protocol_freeze`` needs to build this corpus's own one protocol freeze -- the complete
    pre-result declaration set, assembled once from this module's own frozen fields."""

    return {
        "project_binding_ref": {"kind": "project_binding", "id": PROJECT_BINDING_ID},
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
