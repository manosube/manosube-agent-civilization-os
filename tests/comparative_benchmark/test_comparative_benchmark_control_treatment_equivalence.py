"""Phase 21 Comparative Benchmark -- control/treatment equivalence tests (Issue #89's own
``COMPARABLE_PROJECT_AND_TASK_CORPUS_REQUIRED=true``/``COMPARABLE_RUNTIME_AND_RESOURCE_
ENVELOPE_REQUIRED=true``, adoption-comment ``CONTROL_TREATMENT_EQUIVALENCE_TESTS_REQUIRED=true``):
every declared comparison group runs against the byte-identical frozen corpus, in the identical
order, under the identical declared resource/time budget -- the *only* declared difference
between any two groups is their own ``mechanism_identity``/``agent_label``, never the corpus or
the budget."""

from __future__ import annotations

from typing import Any

from tests.fixtures import comparative_benchmark as cb


def test_every_comparison_group_declares_the_identical_frozen_task_id_order_and_count(
    comparative_benchmark_run: dict[str, Any],
) -> None:
    protocol_freeze = comparative_benchmark_run["protocol_freeze"]
    raw_events = comparative_benchmark_run["result_bundle"]["raw_events"]
    expected_task_ids = tuple(protocol_freeze["corpus_manifest"]["task_ids"])
    assert expected_task_ids == cb.TASK_IDS

    for group in protocol_freeze["comparison_groups"]:
        group_id = group["comparison_group_id"]
        actual_task_ids = tuple(
            e["task_id"] for e in raw_events if e["comparison_group_id"] == group_id
        )
        assert actual_task_ids == expected_task_ids, (
            f"comparison_group_id={group_id!r} attempted a different task_id sequence than the "
            "frozen corpus"
        )


def test_there_is_exactly_one_shared_resource_budget_manifest_never_a_per_group_one() -> None:
    """The protocol freeze schema itself makes a per-group resource/time/budget override
    structurally impossible: ``resource_budget_manifest`` is a single, top-level field, and each
    ``comparison_groups`` item's own schema (``additionalProperties: false``) admits only
    ``comparison_group_id``/``comparison_group_role``/``mechanism_identity``/``agent_label`` --
    never a per-group budget/timeout override (see NC-4 for the decisive fail-closed proof)."""

    kwargs = cb.protocol_freeze_kwargs(generated_at="2026-01-01T00:00:00.000001Z")
    assert "resource_budget_manifest" in kwargs
    for group in kwargs["comparison_groups"]:
        assert set(group) == {
            "comparison_group_id",
            "comparison_group_role",
            "mechanism_identity",
            "agent_label",
        }


def test_only_mechanism_identity_and_agent_label_ever_differ_between_declared_groups(
    comparative_benchmark_run: dict[str, Any],
) -> None:
    protocol_freeze = comparative_benchmark_run["protocol_freeze"]
    groups = protocol_freeze["comparison_groups"]
    assert len(groups) >= 2
    # Every group's own request is otherwise identical: the one shared corpus_manifest and the
    # one shared resource_budget_manifest, both top-level protocol-freeze fields the group
    # declarations themselves cannot override (see the test above).
    varying_keys = set()
    baseline = groups[0]
    for group in groups[1:]:
        for key in baseline:
            if key == "comparison_group_id":
                continue
            if group[key] != baseline[key]:
                varying_keys.add(key)
    assert varying_keys <= {"comparison_group_role", "mechanism_identity", "agent_label"}
